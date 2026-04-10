<div align="center">

# content-extractor

**多模态内容提取器 — 把视频/图片/文章/图集(或裸视频文件)变成结构化文本 + 智能分析**

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-221%20passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

```
in  ContentItem 目录 (content-downloader 输出的 video/image/article/gallery)
    | 裸视频/音频文件 (.mp4/.mp3/.wav/.m4a/等，自动包装为 ContentItem)
out transcript.json + analysis.json + structured_text.md

fail unsupported content_type → UnsupportedContentTypeError + 已支持类型列表
fail invalid content_item.json → ContentItemInvalidError + 具体字段错误
fail whisper 幻觉检测        → is_suspicious=true + hallucination_warnings
fail gallery 单图失败         → 整个 gallery 标记失败 (all-or-nothing)
fail LLM 分析失败             → 降级为空白 analysis，提取结果仍然保留
fail 批量中单条失败           → 跳过 + 记录，继续处理剩余

Adapters: video, image, article, gallery
```

## 示例输出

```bash
# 直接丢一个 mp4 文件 — 不需要 content_item.json
$ content-extractor extract ./interview.mp4
Detected bare media file. Wrapping as ContentItem...
Extracted: interview
  Type: video
  Words: 1204
  Time: 12.7s

# 提取 content-downloader 输出的标准目录
$ content-extractor extract ./douyin/102174692353/7621048932151414054/
Extracted: 7621048932151414054
  Type: video
  Words: 342
  Time: 8.3s

# 批量提取整个目录
$ content-extractor extract-batch ./output/ --whisper-model turbo
⠸ 7621048932151414054 ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:01:42

Processed 47 items: 42 succeeded, 3 skipped, 2 failed

                    Errors
┌──────────────────────┬──────────────────────┐
│ Content Directory    │ Error                │
├──────────────────────┼──────────────────────┤
│ ./xhs/user/abc123    │ No media files found │
│ ./douyin/user/def456 │ FFmpeg codec error    │
└──────────────────────┴──────────────────────┘
```

**每个 ContentItem 生成三个文件：**

`transcript.json` — 带时间戳的转录/描述
```json
{
  "content_id": "7621048932151414054",
  "language": "zh",
  "segments": [
    {"text": "如何做到真正的复利", "start": 0.0, "end": 3.2, "confidence": 0.94},
    {"text": "山姆奥特曼说过一句话", "start": 3.2, "end": 5.8, "confidence": 0.91}
  ],
  "full_text": "如何做到真正的复利..."
}
```

`analysis.json` — 主题/观点/情绪/takeaway
```json
{
  "topics": ["复利思维", "长期主义", "认知升级"],
  "viewpoints": ["持续专注比短期爆发更重要", "复利的本质是认知的积累"],
  "sentiment": {"overall": "positive", "confidence": 0.87},
  "takeaways": ["选择一个方向持续投入", "避免频繁切换赛道"]
}
```

`structured_text.md` — 人可读的研究简报
```markdown
# 如何做到真正的复利

## Summary
山姆奥特曼关于复利思维的解读...

## Key Takeaways
- 选择一个方向持续投入
- 避免频繁切换赛道

## Full Transcript
[00:00] 如何做到真正的复利...

## Analysis
**Topics:** 复利思维, 长期主义, 认知升级
**Sentiment:** positive (0.87)
```

## 架构

```
input ──▶ bare file? ──yes──▶ auto-wrap ──▶ ContentItem dir
              │no                               │
              └────────────────────────────────▶ │
                                                 ▼
content_item.json ──▶ loader ──▶ router ──▶ adapter ──▶ output writer
                                   │
                       ┌───────────┼───────────┬──────────────┐
                       ▼           ▼           ▼              ▼
                   article     image       video          gallery
                   trafilatura Claude      FFmpeg         per-image
                   HTML→MD     vision      ↓              Claude vision
                                           whisper        ↓
                                           (mlx on Apple  narrative
                                            Silicon, else  synthesis
                                            faster-whisper)
                                           ↓
                                           VAD + 幻觉检测
                                                   │
                                                   ▼
                                           analysis (Claude LLM)
                                           topics/viewpoints/sentiment/takeaways
                                                   │
                                                   ▼
                                   transcript.json + analysis.json + structured_text.md
```

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/zinan92/content-extractor.git
cd content-extractor

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 系统依赖
brew install ffmpeg      # macOS
# apt install ffmpeg     # Ubuntu

# 4. 配置 LLM (二选一)
# 方式 A: CLI Proxy API (Max plan 用户，自动读取 ~/.cli-proxy-api/claude-*.json)
# 方式 B: 环境变量
export ANTHROPIC_API_KEY=sk-ant-xxx

# 5. 提取单个内容 (支持目录或裸文件)
content-extractor extract ./path/to/content_item_dir/
content-extractor extract ./recording.mp4

# 6. 批量提取
content-extractor extract-batch ./path/to/output_dir/
```

## 功能一览

| 功能 | 说明 | 状态 |
|------|------|------|
| 裸文件直接提取 | 传入 .mp4/.mp3 等文件，自动包装为 ContentItem 后提取 | ✅ |
| 视频转录 | Whisper turbo + 中文显式设置 + 时间戳（Apple Silicon 自动用 mlx-whisper GPU） | ✅ |
| 音频预处理 | FFmpeg loudnorm 音量标准化 (-16 LUFS) | ✅ |
| VAD 过滤 | Silero VAD 过滤非语音段，speech_ratio < 10% 自动跳过 | ✅ |
| 幻觉检测 | 置信度/字符速率/重复句三重检测 + hallucination_warnings | ✅ |
| 图片 OCR + 描述 | Claude vision 单次调用同时 OCR + 视觉描述 | ✅ |
| 中文文字叠加识别 | 优化小红书常见的图片文字叠加 | ✅ |
| 文章清洗 | trafilatura HTML→Markdown，保留结构 | ✅ |
| CJK 字数统计 | 中文按字符计数，不是 split() | ✅ |
| 图集叙事合成 | 逐图 Claude vision → LLM 合成连贯叙事 | ✅ |
| LLM 结构化分析 | 主题/观点/情绪/可操作 takeaway | ✅ |
| 批量处理 | Rich 进度条 + 错误隔离 + 幂等 | ✅ |
| Python Library API | `from content_extractor import extract` | ✅ |

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 运行时 | Python 3.13+ | 核心语言 |
| 数据模型 | Pydantic 2.12+ | 输入/输出 schema，frozen immutable models |
| 视频转录 | faster-whisper 1.2+ / mlx-whisper 0.4+ | 双后端：Apple Silicon 自动用 mlx-whisper (Metal GPU, ~15x 实时)，其他平台用 faster-whisper (CPU int8, ~1x 实时) |
| 音频处理 | FFmpeg 7.x | 音频提取 + 音量标准化 |
| 图片分析 | anthropic SDK 0.86+ | Claude vision OCR + 描述 |
| 文章清洗 | trafilatura 2.0 | HTML → Markdown (F1=0.96) |
| CLI | Typer 0.24+ / Rich 14+ | 命令行界面 + 进度条 |
| 序列化 | orjson 3.10+ | 快速 JSON 读写 |
| 测试 | pytest 9.0 | 221 tests, 96% coverage |

## 项目结构

```
content-extractor/
├── src/content_extractor/
│   ├── adapters/           # 内容类型适配器
│   │   ├── base.py         # Extractor Protocol
│   │   ├── video.py        # 视频 → 转录
│   │   ├── image.py        # 图片 → OCR + 描述
│   │   ├── article.py      # 文章 → 清洗 + 结构化
│   │   └── gallery.py      # 图集 → 逐图分析 + 叙事
│   ├── video/              # 视频处理子模块
│   │   ├── ffmpeg.py       # 音频提取 + 标准化
│   │   ├── transcribe.py   # faster-whisper 转录
│   │   └── hallucination.py # 幻觉检测
│   ├── analysis.py         # LLM 结构化分析
│   ├── cli.py              # Typer CLI (含裸文件自动包装)
│   ├── config.py           # ExtractorConfig
│   ├── extract.py          # 顶层编排 (extract_content / extract_batch)
│   ├── llm.py              # Claude API 客户端工厂
│   ├── loader.py           # ContentItem 加载器
│   ├── models.py           # 8 个 Pydantic 模型
│   ├── output.py           # 原子文件写入
│   ├── router.py           # content_type → adapter 路由
│   ├── text_utils.py       # 语言检测 + CJK 字数统计
│   └── vision.py           # Claude vision 图片分析
├── tests/                  # 19 个测试文件，221 个测试
├── pyproject.toml          # 项目配置
└── .planning/              # GSD 规划文档
```

## 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--whisper-model` | Whisper 模型选择 | `turbo` |
| `--force` | 强制重新提取已完成的内容 | `false` |
| `ANTHROPIC_API_KEY` | Claude API 密钥 (CLI Proxy API 优先) | — |
| `CONTENT_EXTRACTOR_WHISPER_BACKEND` | 强制指定 Whisper 后端 (`mlx` / `faster`) | 自动检测 |

LLM 内部参数（model、temperature、max_tokens）已硬编码为最佳默认值，不暴露给用户。

## For AI Agents

本节面向需要将此项目作为工具或依赖集成的 AI Agent。

### Capability Contract

```yaml
name: content-extractor
version: 0.1.0
capability:
  summary: "Extract structured text and analysis from multimedia content (video/image/article/gallery) or bare media files"
  in: "ContentItem directory (content-downloader output) OR bare video/audio file (.mp4/.mp3/.wav/.m4a/etc)"
  out: "transcript.json + analysis.json + structured_text.md"
  fail:
    - "unsupported content_type → UnsupportedContentTypeError"
    - "invalid content_item.json → ContentItemInvalidError"
    - "whisper hallucination → is_suspicious=true, extraction continues"
    - "gallery image failure → entire gallery fails (all-or-nothing)"
    - "LLM analysis failure → placeholder analysis, extraction result preserved"
    - "batch item failure → skip + log, continue remaining"
  adapters: [video, image, article, gallery]
cli_command: content-extractor
cli_args:
  - name: path
    type: string
    required: true
    description: "Path to ContentItem directory, parent directory, or bare media file"
cli_flags:
  - name: --whisper-model
    type: string
    description: "Whisper model (tiny/base/small/medium/turbo/large-v3)"
  - name: --force
    type: boolean
    description: "Reprocess already-extracted content"
bare_file_support:
  extensions: [.mp4, .mov, .mkv, .avi, .webm, .flv, .m4v, .mp3, .wav, .m4a, .aac, .ogg, .flac]
  behavior: "Auto-wraps as ContentItem in .extract-tmp-{stem}/ sibling directory"
```

### Agent 调用示例

```python
from pathlib import Path
from content_extractor import extract, extract_batch, ExtractorConfig, ExtractionResult

# 单个 ContentItem 目录
result: ExtractionResult = extract(Path("./douyin/author/content_id/"))
print(result.raw_text)              # 完整文本
print(result.quality.confidence)    # 置信度
print(result.transcript.segments)   # 带时间戳的段落

# 批量提取
config = ExtractorConfig(whisper_model="turbo", force_reprocess=False)
batch = extract_batch(Path("./output/"), config)
print(f"{batch.success_count} succeeded, {batch.failure_count} failed")
for error in batch.failed:
    print(f"  {error.content_dir}: {error.error}")
```

```bash
# CLI: 裸文件直接提取 (agent 通过 subprocess 调用)
content-extractor extract ./recording.mp4
# 输出写入 ./.extract-tmp-recording/ 目录
```

## 相关项目

| 项目 | 说明 | 链接 |
|------|------|------|
| content-downloader | 上游：统一下载能力，URL → 原始文件 + 平台元数据 | [zinan92/content-downloader](https://github.com/zinan92/content-downloader) |

## License

MIT
