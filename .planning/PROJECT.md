# content-extractor

## What This Is

Content pipeline Step 03: 多模态内容提取器。接收 content-downloader 输出的 ContentItem 目录（视频/图片/文章/gallery），通过 adapter 模式提取结构化文本。视频用本地 Whisper turbo 转录，图片用 Claude vision (CLI Proxy API) 识别，文章做清洗+结构化。输出包含转录文本、结构化分析（主题/观点/情绪/takeaway）和 markdown 格式的完整内容。CLI + Python library 形态，无 HTTP 服务。

## Core Value

把原始多媒体内容变成可被下游（curator/rewriter）消费的结构化文本 — 没有 extractor，整条 content pipeline 后面的步骤全都没有输入。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 读取 content-downloader 标准输出目录（`{platform}/{author_id}/{content_id}/`），解析 `content_item.json`
- [ ] Video adapter: 用本地 Whisper turbo 转录视频音频，输出带时间戳的分段 transcript
- [ ] Image adapter: 用 Claude vision (CLI Proxy API) 描述图片内容（文字识别 + 视觉描述）
- [ ] Article adapter: 清洗已有文本（去 HTML/广告/重复），结构化为 markdown
- [ ] Gallery adapter: 每张图 Claude vision 描述 + 整体叙事合成
- [ ] LLM 分析层: 对提取的文本做结构化分析 — 主题、核心观点、情绪倾向、可操作 takeaway
- [ ] 标准化输出: 每个 ContentItem 生成 `transcript.json` + `analysis.json` + `structured_text.md`
- [ ] CLI 入口: 支持单个 ContentItem 目录和批量扫描整个 output 目录
- [ ] Python library: 可被其他 Python 项目直接 import 调用
- [ ] 幂等处理: 已提取的内容跳过（除非 --force）

### Out of Scope

- FastAPI / HTTP 服务 — pipeline 内 Python 直接调用，不需要 HTTP 开销
- 实时流式转录 — 离线批处理足够
- 自训练模型 — 用现成的 Whisper + Claude vision
- 多语言翻译 — 提取原文即可，翻译是 rewriter 的事
- 视频画面分析（逐帧） — 只提取封面/关键帧，不做全视频视觉分析

## Context

**上游**: content-downloader 输出结构:
```
{output_dir}/{platform}/{author_id}/{content_id}/
    media/              ← video.mp4 / *.jpg / *.png
    metadata.json       ← 原始平台数据
    content_item.json   ← ContentItem (platform, content_type, title, description, media_files, ...)
```

**ContentItem.content_type 取值**: `video` | `image` | `article` | `gallery`

**已有碎片能力**:
- videocut 里的 `whisper_transcribe.sh` — Whisper 本地转录 + 火山引擎兼容格式转换
- douyin-downloader 的 markdown 格式化逻辑

**下游消费者**: content-curator (100 选 3 筛选) 和 content-rewriter (变成我的内容)

**LLM 接入**: CLI Proxy API (`~/.cli-proxy-api/claude-*.json`)，本质是 Max plan 的 Anthropic API token，成本约为零。

## Constraints

- **Tech stack**: Python 3.13+ / Pydantic / pytest — 与 content-downloader 保持一致
- **LLM 成本**: 必须走 CLI Proxy API，不额外付费
- **Whisper**: 本地运行，默认 turbo 模型 (~1.6GB)，可通过参数切换
- **输出兼容**: 输出目录结构不能破坏 content-downloader 已有的文件布局，新文件追加到 ContentItem 目录中

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Whisper turbo 而非 small/large | turbo 是 large-v3 蒸馏版，质量接近 large 但快 8 倍，只 1.6GB | — Pending |
| CLI Proxy API 而非直接 Anthropic API | 用户已有 Max plan，成本为零 | — Pending |
| CLI + library 而非 FastAPI | pipeline 内 Python 直接调用，HTTP 是不必要的复杂度 | — Pending |
| 输出追加到 ContentItem 目录 | 保持单一目录包含所有信息，下游只需一个路径 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-30 after initialization*
