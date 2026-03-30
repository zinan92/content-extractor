# Phase 6: Video Quality Research

**Researched:** 2026-03-30
**Scope:** VAD preprocessing, volume normalization, hallucination guard

## VID-02: VAD Preprocessing

### Current State

faster-whisper already has `vad_filter=True` in `transcribe.py` line 108 with `min_silence_duration_ms=500`. This provides basic silence filtering during transcription. However, this is Whisper-internal VAD -- it filters segments post-transcription, not pre-transcription.

### What We Need

A **standalone VAD pass before transcription** that:
1. Computes speech ratio (speech duration / total duration) to detect no-speech audio
2. Filters non-speech segments from the audio file BEFORE Whisper sees it
3. Flags audio with <10% speech as `no_speech` to skip transcription entirely (per PITFALLS.md Pitfall 12)

### Approach: Use faster-whisper's Built-in Silero VAD

faster-whisper ships with Silero VAD v6 (ONNX). The `get_speech_timestamps()` function in `faster_whisper/vad.py` returns speech segment timestamps. The `TranscriptionInfo` object returned by `model.transcribe()` includes `duration` and `duration_after_vad`, which gives us speech ratio directly.

**Key insight:** We do NOT need a separate VAD library. faster-whisper's `TranscriptionInfo.duration_after_vad / TranscriptionInfo.duration` gives us the speech ratio. We just need to:
1. Capture `TranscriptionInfo` from transcribe (currently discarded as `_info`)
2. Compute speech_ratio from it
3. Return speech_ratio alongside segments
4. In VideoExtractor, skip transcription if speech_ratio < 0.10 (10%)

For the pre-filtering approach, we can also use `faster_whisper.vad.get_speech_timestamps()` directly to get speech timestamps, then use FFmpeg to extract only those segments. But this adds complexity. The simpler approach: let faster-whisper's built-in VAD handle it (already enabled), and use the speech_ratio from TranscriptionInfo to flag/skip.

**Decision: Enhance existing integration, not add separate VAD pipeline.** The vad_filter=True already strips silence before Whisper processes each chunk. We just need to capture and use the metadata.

### Parameters

```python
vad_parameters = {
    "threshold": 0.5,              # Speech probability threshold (default 0.5)
    "neg_threshold": 0.35,         # Below this = silence (default threshold - 0.15)
    "min_silence_duration_ms": 500, # Already set in current code
    "speech_pad_ms": 400,          # Padding around speech (default)
}
```

## VID-06: Volume Normalization

### Problem

Quiet recordings from Douyin/XHS produce poor transcriptions. Whisper works best on -16 LUFS normalized audio.

### Approach: FFmpeg loudnorm Filter

Single-pass normalization using FFmpeg's `loudnorm` filter:

```bash
ffmpeg -i input.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 16000 -ac 1 -f wav output.wav
```

Parameters:
- `I=-16` -- Target integrated loudness in LUFS (EBU R128 standard)
- `TP=-1.5` -- True peak limit in dBTP (prevents clipping)
- `LRA=11` -- Loudness range target

**Where to insert:** Between `extract_audio()` and `transcribe_audio()` in VideoExtractor. New function `normalize_audio()` in `video/ffmpeg.py`.

**Design:** The normalize step takes the extracted WAV and produces a normalized WAV. If normalization fails (unlikely for valid WAV), fall back to the unnormalized audio rather than failing the entire extraction.

### Alternative Considered

Two-pass loudnorm (measure then apply) is more precise but doubles FFmpeg processing time. For speech transcription, single-pass is sufficient -- we are not mastering music.

## VID-07: Hallucination Guard

### Current Anti-Hallucination Settings

Already in `transcribe.py`:
- `condition_on_previous_text=False` -- prevents cascade hallucination
- `vad_filter=True` -- filters silence
- `no_speech_prob > 0.6` filtering -- skips non-speech segments
- `initial_prompt="以下是普通话的句子。"` -- biases toward Simplified Chinese

### What We Still Need

1. **Per-segment confidence flagging**: Mark segments with confidence < 0.4 as `low_confidence`
2. **Words-per-second check**: Chinese speech ~3-4 chars/sec. If a segment exceeds 6 chars/sec, flag as suspicious (Pitfall 1 from PITFALLS.md)
3. **Repetition detection**: Hallucinated text often repeats phrases. Detect repeated n-grams
4. **Overall transcript quality score**: Combine speech_ratio, avg_confidence, hallucination_flags into a single quality assessment
5. **Warning in output metadata**: Add `hallucination_warnings` field to QualityMetadata

### Model Changes

`QualityMetadata` needs a new optional field:
```python
hallucination_warnings: tuple[str, ...] = ()
```

`TranscriptSegment` needs a flag:
```python
is_suspicious: bool = False
```

### Hallucination Heuristics

| Check | Threshold | Warning |
|-------|-----------|---------|
| Speech ratio | < 10% | "Audio has <10% speech -- transcript may be unreliable" |
| Segment confidence | < 0.4 | Segment marked is_suspicious=True |
| Chars per second | > 6 CJK chars/sec | Segment marked is_suspicious=True |
| Repeated 4-grams | > 3 occurrences | "Repetitive text detected -- possible hallucination" |
| Overall avg confidence | < 0.5 | "Low overall confidence -- review recommended" |

## Implementation Plan

**Plan 01 (Wave 1):** VAD metadata capture + volume normalization in FFmpeg
- Modify `transcribe.py` to return TranscriptionInfo metadata (speech_ratio)
- Add `normalize_audio()` to `ffmpeg.py`
- Update VideoExtractor pipeline: extract -> normalize -> transcribe

**Plan 02 (Wave 2):** Hallucination guard + model updates
- Add hallucination detection heuristics module
- Update models (QualityMetadata.hallucination_warnings, TranscriptSegment.is_suspicious)
- Wire into VideoExtractor, populate warnings in output

## Sources

- [faster-whisper VAD source](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/vad.py)
- [FFmpeg loudnorm filter](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)
- [EBU R128 loudness standard](https://tech.ebu.ch/docs/r/r128.pdf)
- [Whisper hallucination patterns](https://arxiv.org/html/2501.11378v1)
- PITFALLS.md Pitfall 1 (Whisper hallucinations) and Pitfall 12 (missing audio detection)
