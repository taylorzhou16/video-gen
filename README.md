# 🎬 Video-Gen - AI 视频剪辑 Skill

一个 Claude Code Skill，将 AI 视频剪辑能力带入你的对话中。

## 🎥 Demo 演示

官网：[video-gen-5si.pages.dev](https://video-gen-5si.pages.dev/)

以下是使用 video-gen 生成的演示视频：

| # | 视频名称 | 类型 | 下载 |
|---|---------|------|------|
| 1 | Merry Christmas Mr Lawrence | 音乐短片 | [demo3_merry_christmas.mp4](https://github.com/taylorzhou16/video-gen/releases/download/v1.0.0-demo/demo3_merry_christmas.mp4) |
| 2 | 咖啡 & 抱石周末 | Vlog | [demo2_coffee_bouldering.mp4](https://github.com/taylorzhou16/video-gen/releases/download/v1.0.0-demo/demo2_coffee_bouldering.mp4) |
| 3 | 迪士尼照片集 Vlog | Vlog | [demo1_disney_vlog.mp4](https://github.com/taylorzhou16/video-gen/releases/download/v1.0.0-demo/demo1_disney_vlog.mp4) |
| 4 | F1 上海站 — 与维斯塔潘同场竞技 | 赛事模拟 | [demo4_f1_shanghai.mp4](https://github.com/taylorzhou16/video-gen/releases/download/v1.0.0-demo/demo4_f1_shanghai.mp4) |
| 5 | 乐于助人小故事 | 虚构短剧 | [demo5_helpful_story.mp4](https://github.com/taylorzhou16/video-gen/releases/download/v1.0.0-demo/demo5_helpful_story.mp4) |
| 6 | 牛奶风波之断我口粮 | 虚构短剧 | [demo6_milk_incident.mp4](https://github.com/taylorzhou16/video-gen/releases/download/v1.0.0-demo/demo6_milk_incident.mp4) |
| 7 | 一月水费1700 | 虚构短剧 | [demo7_water_fee.mp4](https://github.com/taylorzhou16/video-gen/releases/download/v1.0.0-demo/demo7_water_fee.mp4) |

> 💡 点击下载链接可在浏览器中直接播放，或下载到本地观看。

## 🏗️ 架构

**核心理念**：Claude 本身就是 Director Agent，不需要额外的 Agent 代码。

```
~/.claude/skills/video-gen/
├── SKILL.md                # 核心工作流指令（~290 行）
├── reference/
│   ├── storyboard-spec.md  # 分镜设计完整规范
│   ├── backend-guide.md    # 后端选择与参考图策略
│   ├── prompt-guide.md     # Prompt 编写与一致性规范
│   └── api-reference.md    # CLI 参数与环境变量
├── video_gen_tools.py           # API 工具（视频/音乐/TTS/图片生成）
├── video_gen_editor.py          # FFmpeg 剪辑工具
└── config.json             # API 密钥配置
```

**职责划分**：
- **Claude**：意图识别、创意生成、分镜设计、工作流规划
- **video_gen_tools.py**：Vidu/Kling/Suno/TTS/Gemini API 调用
- **video_gen_editor.py**：FFmpeg 视频剪辑操作

## ✨ 功能

- ✅ **素材分析** - 自动识别图片/视频内容、场景、情感
- ✅ **创意生成** - 交互式问题卡片，定制视频创意方案
- ✅ **分镜设计** - 生成分镜脚本和视频生成 Prompt
- ✅ **AI 视频生成**
  - **Seedance 2**（推荐虚构片）：4-15秒、智能切镜、多参考图、音画同出
  - **Kling v3**：3-15秒、首帧精确控制、画面质感好
  - **Kling v3 Omni**：3-15秒、多参考图、角色一致性最佳
  - **Veo3**：4/6/8秒、全局兜底模型
- ✅ **AI 音乐生成** - Suno V3.5 背景音乐
- ✅ **TTS 语音合成** - Gemini TTS（多种音色、风格提示）
- ✅ **AI 图片生成** - Gemini 3.1 Flash Image（migoo/yunwu）
- ✅ **视频剪辑** - 转场、字幕、调色、变速、音频混合

## 💡 使用建议

### 推荐模型

**建议使用多模态模型（如 Kimi K2.5）以获得最佳体验。**

多模态模型对素材的理解能力更强，能够更准确地识别图片/视频中的场景、人物、情感和视觉风格。如果你使用的主模型不是多模态的，可以通过调用 `/vision` skill 来补充视觉理解能力。

### 引导模型

目前能力还比较初级，**建议在使用过程中多引导模型**。例如：
- 主动说明想要的视频风格、节奏和情绪
- 对分镜方案提出具体的修改意见
- 在生成过程中及时反馈，帮助模型调整方向

### 项目定位

这个项目的本意是希望充分发挥 Claude Code Agent 的智能能力，给足视频生成相关的所有工具和能力，探索 AI 辅助视频创作的实际效果。**这是一个偏探索性质的项目，仍在不断更新迭代中。** 欢迎尝试各种创意，你的使用反馈将帮助我们持续改进。

**灵活的 API 支持**：项目中使用的图片和视频生成 API（如 Vidu、Gemini）可以自行替换为你熟悉的渠道。`video_gen_tools.py` 中的 API 调用封装清晰，方便接入其他服务商（如 OpenAI、Midjourney、Stability AI 等）。

## 🚀 安装

```bash
# 复制整个目录到 skills 目录
mkdir -p ~/.claude/skills/video-gen
cp -r SKILL.md reference/ video_gen_tools.py video_gen_editor.py config.json.example README.md requirements.txt ~/.claude/skills/video-gen/

# 安装依赖
cd ~/.claude/skills/video-gen && pip install -r requirements.txt

# 配置 API 密钥
cp config.json.example config.json
# 编辑 config.json 填入你的 API 密钥
```

## 📖 使用方法

```
/video-gen <素材目录>
```

### 示例

```bash
# 完整创作流程
/video-gen ~/Videos/旅行素材/

# 继续上次的项目
/video-gen ~/video-gen-projects/trip_20260310/
```

## 🛠️ 工具调用

### video_gen_tools.py

```bash
# 视频生成（Kling 后端，默认）
python video_gen_tools.py video --prompt "<描述>" --duration 5 --output video.mp4
python video_gen_tools.py video --image <首帧图> --prompt "<描述>" --output video.mp4

# 视频生成（Kling Omni 后端 - 参考图模式）
python video_gen_tools.py video --backend kling-omni --prompt "<<<image_1>>> 在场景中" --image-list <参考图> --output video.mp4

# 视频生成（Vidu 后端 - 兜底/快速原型）
python video_gen_tools.py video --backend vidu --image <图片> --prompt "<描述>" --duration 5 --output video.mp4

# Kling 多镜头模式
python video_gen_tools.py video --prompt "<故事描述>" --multi-shot --shot-type intelligence --duration 10
python video_gen_tools.py video --prompt "<总体描述>" --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"镜头1","duration":"3"}]' --duration 5

# Kling 首尾帧控制
python video_gen_tools.py video --image <首帧图> --tail-image <尾帧图> --prompt "<动作描述>" --duration 5

# 音乐生成
python video_gen_tools.py music --prompt "<描述>" --style "Lo-fi" --output music.mp3

# TTS
python video_gen_tools.py tts --text "<文本>" --voice female_narrator --output audio.mp3

# 图片生成
python video_gen_tools.py image --prompt "<描述>" --style cinematic --output image.png
```

### 🎥 视频生成后端对比

| 后端 | 模型 | 时长 | 特点 |
|------|------|------|------|
| **Seedance 2** | seedance-2 | 4-15s | 智能切镜、多参考图（最多9张）、首尾帧控制、音画同出 |
| **Kling Omni** | kling-3.0-omni | 3-15s | 多参考图(reference2video)、角色一致性、音画同出 |
| **Kling** | kling-3.0 | 3-15s | 首帧精确控制(img2video)、画面质感好 |
| **Veo3** | veo-3.1-generate-001 | 4/6/8s | 全局兜底、首帧控制、默认音频 |

**关键区别**：
- **Seedance 2 / Kling Omni** 支持多参考图（角色一致性），Seedance 2 还支持首尾帧控制
- **Kling / Veo3** 支持首帧精确控制

**选择建议**：
| 场景 | 优先后端 | 兜底后端 | 原因 |
|-----|---------|---------|------|
| **虚构片/短剧** | **Seedance 2** | Kling-Omni | 智能切镜 + 多参考图 |
| **广告片（无真实素材）** | **Seedance 2** | Kling-Omni | 长镜头 + 智能切镜 |
| **广告片（有真实素材）** | Kling-3.0 | — | 首帧精确控制 |
| **MV短片** | **Seedance 2** | Kling-Omni | 长镜头 + 音乐驱动 |
| **Vlog/写实类** | Kling-3.0 | Veo3 | 首帧精确控制 |

**Veo3 说明**：作为全局最兜底的视频生成模型，除非用户主动要求使用 Veo3，否则不主动调用 Veo3。

### video_gen_editor.py

```bash
# 拼接
python video_gen_editor.py concat --inputs v1.mp4 v2.mp4 --output out.mp4

# 字幕
python video_gen_editor.py subtitle --video video.mp4 --srt subs.srt --output out.mp4

# 音频混合
python video_gen_editor.py mix --video video.mp4 --bgm music.mp3 --output out.mp4

# 转场
python video_gen_editor.py transition --inputs v1.mp4 v2.mp4 --type fade --output out.mp4

# 调色
python video_gen_editor.py color --video video.mp4 --preset warm --output out.mp4

# 变速
python video_gen_editor.py speed --video video.mp4 --rate 1.5 --output out.mp4
```

## 🔑 环境变量

```bash
# Seedance API - Seedance 2 视频生成（推荐虚构片/短剧）
export SEEDANCE_API_KEY="your-seedance-api-key"

# Kling API - Kling v3 视频生成（推荐写实/Vlog）
export KLING_ACCESS_KEY="your-access-key"
export KLING_SECRET_KEY="your-secret-key"

# Veo3 API - Google Veo3 视频生成（全局兜底模型）
export MIGOO_API_KEY="your-migoo-api-key"

# Suno 音乐生成
export SUNO_API_KEY="your-api-key"

# Gemini 图片生成（migoo 优先）
export MIGOO_API_KEY="your-migoo-api-key"
export YUNWU_API_KEY="your-yunwu-api-key"  # 备用
```

**注意**：
- **视频生成 Provider**：Seedance（piapi）、Kling（official/fal）、Veo3（migoo）
- **图片生成 Provider 优先级**：migoo → yunwu

## 🔄 工作流程

```
素材分析 → 创意生成 → 分镜设计 → 内容生成 → 剪辑输出
```

## 📁 输出目录结构

```
~/video-gen-projects/{project_name}_{timestamp}/
├── state.json              # 项目状态
├── materials/              # 原始素材
├── analysis/               # 分析结果
├── creative/               # 创意方案
├── storyboard/             # 分镜脚本
├── generated/              # 生成的内容
│   ├── videos/
│   └── music/
└── output/                 # 最终视频
```

## 📦 依赖

- FFmpeg 6.0+（视频处理）
- Python 3.9+（工具运行）
- httpx（HTTP 客户端）

## 📋 更新日志

### v1.6.1 (2026-04-07)
🐛 **Bug 修复**

- 🐛 **Seedance 自动组装模式图片路径解析** — CLI 运行目录与项目目录不一致时，相对路径无法正确解析，导致 `FileNotFoundError`。新增 `resolve_path()` 函数自动将相对路径转换为绝对路径
- 🐛 **narration 命令 audio_idx 计算错误** — FFmpeg filter_complex 中音频输入索引计算错误（`len(inputs) // 2` → `i + 1`），导致多旁白场景引用不存在的输入流

### v1.6.0 (2026-04-07)
🔄 **Provider 体系重构 + Seedance 2 升级**

#### 废弃清理
- 🗑️ **移除 yunwu 视频生成 Provider** — Vidu/Kling/Kling-Omni 的 yunwu provider 全部废弃，yunwu 仅保留 Gemini 图片生成
- 🗑️ **移除 FalImageClient** — 图片生成仅保留 migoo/yunwu 两个 provider
- 🗑️ **废弃火山引擎 TTS** — TTS 仅保留 Gemini TTS（通过 Migoo LLM API）
- 🗑️ **移除 Vidu 后端** — 不再支持 Vidu 视频生成

#### Seedance 2 升级
- ✨ **时长支持扩展** — 从 5/10/15s 枚举值改为 4-15s 任意整数
- ✨ **新增 21:9 宽高比** — 支持电影级宽银幕比例
- ✨ **新增 `--mode` 参数** — `text_to_video` / `first_last_frames` / `omni_reference`
- ✨ **新增 `--audio-urls` / `--video-urls`** — 支持音频/视频参考
- ✨ **首尾帧控制** — `mode: first_last_frames` 支持首尾帧精确控制

#### 架构优化
- 🔄 **Provider 矩阵简化** — 视频 4 后端（Seedance/Kling/Kling-Omni/Veo3），图片 2 provider（migoo/yunwu）
- 🔄 **TTS 统一为 Gemini** — 移除火山引擎 TTS 调用路径
- 📝 **文档全面更新** — SKILL.md、backend-guide.md、api-reference.md 同步更新

#### 当前支持模型
| 类型 | 模型 | Provider |
|------|------|----------|
| 视频 | Seedance 2 | piapi |
| 视频 | Kling v3 | official / fal |
| 视频 | Kling v3 Omni | official / fal |
| 视频 | Veo3 | migoo |
| 图片 | Gemini 3.1 Flash Image | migoo / yunwu |
| TTS | Gemini TTS | migoo |
| 音乐 | Suno V3.5 | official |

### v1.5.1 (2026-04-03)
🎤 **Gemini TTS 集成**

#### 新增功能
- ✨ **GeminiTTSClient** — 新增 Gemini TTS 客户端（通过 Migoo LLM API）
  - 优先级高于火山引擎 TTS
  - 支持风格提示（prompt 参数）
  - 支持 inline 情感标注：`[brightly]`, `[sigh]`, `[pause]`
  - 音色：Kore/Aoede/Charon/Orus 等

#### 音色预设
| 预设 | 音色 | 性别 |
|------|------|------|
| `female_narrator` | Kore | 女声 |
| `female_gentle` | Aoede | 女声（清亮）|
| `female_soft` | Zephyr | 女声（柔和）|
| `male_narrator` | Charon | 男声 |
| `male_warm` | Orus | 男声（稳重）|

#### TTS 优先级
- **Gemini TTS**（MIGOO_API_KEY）→ 火山引擎 TTS（VOLCENGINE_TTS_*）

### v1.5.0 (2026-04-03)
🎬 **Seedance 智能切镜 + fal 图片生成**

#### 新增功能
- ✨ **SeedanceClient** — 新增 Seedance 视频生成客户端（通过 piapi.ai 代理）
  - 智能切镜：时间分段 prompt 自动触发 multi-shot
  - 时长限制：仅支持 5/10/15s（三个枚举值）
  - 宽高比：16:9 / 9:16 / 4:3 / 3:4
  - 图片引用语法：`@imageN`（非 `<<<image_N>>>`）
- ✨ **FalImageClient** — 新增 fal.ai Gemini 3.1 Flash 图片生成客户端
  - 文生图、图生图、多参考图编辑
- ✨ **narration 命令** — video_gen_editor.py 新增旁白合成命令

#### 架构优化
- 🔄 **Provider 优先级调整** — yunwu 放到最后：`official → fal → yunwu`
- 🔄 **visual_style 语义变更** — 从"后端选择"改为"用户照片处理方式"
  - `realistic`：Seedance 需先生成三视图转换，Kling-Omni 可直接使用
  - `anime`：可直接作为参考图

#### 文档修正
- 📝 **Seedance 时长限制** — 修正为 5/10/15s（非 4-15s 范围）
- 📝 **Seedance 图片语法** — 修正为 `@imageN`
- 📝 **移除 21:9** — Seedance 不支持 21:9 宽高比
- 📝 **时间分段 prompt 格式** — 新增完整模板和示例

#### 文件变更
- 📝 `video_gen_tools.py` — 新增 SeedanceClient、FalImageClient
- 📝 `video_gen_editor.py` — 新增 narration 命令
- 📝 `SKILL.md` — 新增 Seedance 执行逻辑、时间分段格式、照片转换流程
- 📝 `reference/backend-guide.md` — 更新 Provider 优先级、Seedance 参数
- 📝 `reference/storyboard-spec.md` — 新增 Seedance 时长规划章节

### v1.4.6 (2026-04-02)
🔧 **API 字段名修复**

#### Bug 修复
- 🐛 **FalKlingClient 字段名修正** — 使用 fal.ai 官方正确的字段名
  - `image_url` → `start_image_url`（首帧控制）
  - `tail_image_url` → `end_image_url`（尾帧控制）
- 🐛 **YunwuKlingOmniClient 参数修正**
  - `audio` 布尔值 → `sound: "on"/"off"` 字符串
  - `_file_to_base64()` 返回纯 base64 而非 data URI 格式

#### 测试验证
- ✅ 文生视频（纯 prompt）
- ✅ 首帧生视频（start_image_url，角色保持正确）
- ✅ 多参考图生视频（image_urls + @Image1/@Image2，带音频）

### v1.4.5 (2026-04-02)
📝 **文档补充**

- 补充 v1.4.4 版本遗漏的 yunwu provider 文档说明

### v1.4.4 (2026-04-02)
📚 **Yunwu Provider 文档增强**

#### 文档更新
- 📝 `api-reference.md` — YUNWU_API_KEY 作用范围扩展，支持 Kling/Kling-Omni
- 📝 `backend-guide.md` — 新增 Provider 选择优先级说明
- 📝 `README.md` — 新增 Kling 可使用 Yunwu 作为官方 API 备用
- 📝 `SKILL.md` — 新增 Provider 选择章节，说明如何绕过并发限制

### v1.4.3 (2026-04-02)
🔌 **Yunwu Kling Provider 支持**

#### 新增功能
- ✨ **YunwuKlingClient** — 新增 yunwu kling-v3 客户端，支持 text2video、img2video、multi_shot、首尾帧控制、audio
- ✨ **YunwuKlingOmniClient** — 新增 yunwu kling-v3-omni 客户端，支持 omni-video、image_list 多参考图、multi_shot、audio
- ✨ **--provider 参数** — 新增 provider 选择（official/yunwu/fal），支持同一 backend 切换不同 provider
- ✨ **Provider 自动选择** — 未指定时按优先级自动选择：official > fal > yunwu

#### 架构优化
- 🔄 **Backend/Provider 分离** — backend 选择功能（vidu/kling/kling-omni），provider 选择服务源（official/yunwu/fal）
- 📝 **功能支持矩阵** — 明确各 provider 的功能支持情况（multi_shot、首尾帧、audio 等）

#### API 差异处理
- 🔧 **Yunwu kling-v3 使用 `model` 参数**（官方 API 用 `model_name`）
- 🔧 **Yunwu kling-v3-omni 使用 `model_name` 参数**（与官方 API 相同）
- 🔧 **视频 URL 解析路径** — `data.task_result.videos[0].url`（非 `task_info`）

#### 文件变更
- 📝 `video_gen_tools.py` — 新增 YunwuKlingClient、YunwuKlingOmniClient，修改 cmd_video 函数

### v1.4.2 (2026-04-01)
🔊 **音频混音修复与规范化**

#### Bug 修复
- 🐛 **FFmpeg amix normalize=0** — 禁止自动均一化，保留原始音量比例，修复旁白被压低问题

#### 新增功能
- ✨ **混音规则文档** — SKILL.md Phase 5 新增「音频混音规则」章节
  - 音量推荐值：视频环境声 0.8、旁白 1.5-2.0、BGM 0.1-0.15
  - 视频类型适配：MV → 0.5-0.7、Vlog → 0.1-0.15、电影感 → 0.2-0.3

#### 文件变更
- 📝 `video_gen_editor.py` — mix_audio() 函数添加 normalize=0（第 470 行）
- 📝 `SKILL.md` — Phase 5 新增音频混音规则章节

### v1.4.1 (2026-03-31)
🎤 **旁白分段规划功能**

#### 新增功能
- ✨ **Phase 2 旁白需求判断** — 根据视频类型推荐是否需要旁白（纪录片/Vlog 通常需要，电影感/虚构片通常不需要）
- ✨ **Phase 3 同步设计旁白** — 生成分镜时同步规划 `narration_segments`，按镜头时间点分段
- ✨ **Phase 4 旁白生成** — 视频/音乐生成后新增 TTS 旁白生成步骤（火山引擎）
- ✨ **Phase 5 旁白插入** — 按 `overall_time_range` 时间点将旁白音频配到正确位置

#### 文档更新
- 📝 `storyboard-spec.md` — 新增 `narration_config` 和 `narration_segments` 字段规范
- 📝 `prompt-guide.md` — 新增 TTS 旁白生成流程和参数说明

### v1.4.0 (2026-03-30)
🎬 **视频生成最佳实践重构**

#### 核心架构变更
- ✨ **项目类型驱动决策** — 根据用户意图自动判断项目类型（虚构片/短剧、Vlog/写实类、广告片/宣传片、MV短片），无需用户手动选择
- ✨ **虚构片禁用 text2video** — 所有虚构内容强制先生成分镜图，再走 reference2video 或 img2video
- ✨ **同一项目统一模型** — 项目内不混用多种模型，选定一个后全项目统一

#### 模型与生成路径
- 📝 **更新模型名称** — Kling-3.0-Omni、Kling-3.0、Vidu Q3 Pro
- 📝 **明确模型能力边界** — Kling-3.0-Omni 支持 reference2video 但**不支持 img2video（首帧控制）**
- 📝 **决策矩阵优化** — 虚构片优先 Omni（角色一致性），Vlog/广告片用 Kling/Vidu（首帧控制）

#### Bug 修复
- 🐛 **Omni 引用格式修正** — `image_1` → `<<<image_1>>>`，符合官方文档要求

#### 文档更新
- 📝 `SKILL.md` — 后端选择概览、Phase 3 决策树重写
- 📝 `storyboard-spec.md` — Reference Tag 格式、T2V/I2V/Ref2V 选择规则重写
- 📝 `prompt-guide.md` — Omni 模式引用格式修正

### v1.3.10 (2026-03-23)
🎵 **音乐生成参数规范化**

#### 修复
- 🐛 **music 命令 style 参数必须提供** — 删除 Lo-fi Chill 默认值，避免风格不匹配
  - 必须通过 `--creative` 从 creative.json 读取
  - 或手动传 `--prompt` 和 `--style` 参数

### v1.3.9 (2026-03-23)
🎬 **音画同步修复**

#### 修复
- 🐛 **视频拼接音画不同步问题** — 无声片段导致后续视频音频错位
  - 新增 `has_audio_track()` 检测视频是否有音频轨
  - `normalize_videos()` 对无声片段自动补静音轨
  - `concat_videos()` 改用 concat filter，保证音画同步

#### 改进
- 🔄 `music` 命令 `--prompt` 改为非必须，可从 creative.json 读取
- 📝 SKILL.md: Phase 5 新增音频保护说明

### v1.3.8 (2026-03-23)
🔧 **参数传递规范化**

#### 修复
- 🐛 **硬编码默认值问题** — CLI 参数应优先从 storyboard.json 读取
  - `video_gen_editor.py`: concat/image 命令添加 `--storyboard` 参数
  - `video_gen_tools.py`: video/image 添加 `--storyboard`，music 添加 `--creative` 参数
  - 统一 KlingClient/KlingOmniClient 默认 aspect_ratio 为 `"9:16"`

#### 改进
- 🔄 Suno 日志同时显示 prompt 和 style，避免误导用户

### v1.3.7 (2026-03-20)
🔧 **执行阶段修复 & 图片尺寸优化**

#### 修复
- 🐛 **Phase 4 aspect_ratio 传递** — 执行阶段必须从 storyboard.json 读取画面比例并传递给 CLI
- 🐛 修复图片尺寸不一致导致的生成失败问题

#### 新功能
- ✨ **图片尺寸自动校验与调整** — 新增 `validate_and_resize_image()` 函数
  - 最小边 < 720px 自动放大到 1280px
  - 最大边 > 2048px 自动缩小到 2048px
  - Kling/KlingOmni 调用前自动处理

### v1.3.6 (2026-03-20)
📝 **文档修复**

#### 修复
- 🐛 修复 `storyboard-spec.md` 中的冲突和歧义描述
- 📝 澄清三层结构的字段定义和使用场景

### v1.3.5 (2026-03-19)
🎬 **角色一致性流程完善**

#### 新功能
- ✨ **Phase 1 角色注册增强**
  - 新增 `personas.json` 结构，支持 `reference_image` 为 null
  - 只处理用户已上传的参考图，未上传的留待 Phase 2 补充

- ✨ **Phase 2 角色参考图收集**
  - 新增问题 6：角色参考图来源选择
  - 支持三种方式：AI 生成 / 用户上传 / 纯文字生成
  - 自动调用 `video_gen_tools.py image` 生成标准角色参考图

- ✨ **Phase 3 自动后端选择**
  - 有参考图 + 多镜头人物 → `kling-omni` (角色一致性最佳)
  - 有参考图 + 单镜头人物 → `kling` (首帧精确控制)
  - 无参考图 + 人物 → `kling` text2video (已警告用户)
  - 纯场景无人物 → `kling` text2video

#### PersonaManager 增强
- ✨ `list_personas_without_reference()` — 列出无参考图的角色
- ✨ `update_reference_image()` — 更新角色参考图路径
- ✨ `export_for_storyboard()` — 导出为 storyboard 兼容格式
- ✨ `get_character_image_mapping()` — 生成 character_image_mapping

#### SKILL.md 流程优化
- 📝 新增「分镜生成前强制阅读」步骤
- 📝 新增「Step 1: 同步角色信息到 Storyboard」
- 📝 完善产出文件说明和 JSON 结构示例

### v1.3.4 (2026-03-19)
🎬 **Kling V3-Omni 双阶段工作流规范化**

#### 文档更新
- ✨ **新增 V3-Omni 三层结构规范** — storyboard + frame_generation + video_generation
  - `storyboard-spec.md`：添加三层 schema 定义（storyboard/frame/video）
  - `prompt-guide.md`：添加 Image Prompt 和 Video Prompt 编写规范
  - `backend-guide.md`：新增 Path C（V3-Omni 推荐路径），更新决策树和路径对比

- 📝 **Image Prompt 规范**
  - 结构：Cinematic realistic start frame → Character refs → Scene → Lighting → Camera → Style
  - 必须包含角色参考（image_1, image_2...）、画面比例、场景、灯光、相机参数

- 📝 **Video Prompt 规范**
  - 结构：Referencing frame composition → Motion segments → Dialogue exchange → Camera → Sound
  - 时间分段格式（"0-2s", "2-5s"）、对白同步标记、声音设计描述

#### 架构调整
- 🗑️ 移除错误创建的 `vico-templates` Python 代码（应作为文档规范而非代码模板）

### v1.3.3 (2026-03-18)
📐 **SKILL.md 架构重构 & 默认后端切换**

#### 架构重构（Anthropic Skill 规范优化）
- ✨ **渐进式披露架构** — SKILL.md 从 1401 行压缩至 ~290 行（-80%），符合 Anthropic 推荐的 500 行上限
- ✨ **拆分 4 个子文件** — 分镜规范、Prompt 指南、后端选择、API 参考，按需加载
- ✨ **优化 description** — 加入 Kling Omni 关键词和触发条件描述
- ✨ **新增工作流清单** — Anthropic 推荐的 checklist pattern
- ✨ **新增 config.json.example** — 安全的配置模板（不含真实密钥）
- 🔄 精简冗余内容：移除重复解释、旧版兼容格式、过长 JSON 示例

#### 默认后端切换
- 🔄 **默认后端从 Vidu 改为 Kling** — CLI `--backend` 默认值 `vidu` → `kling`
- ✨ **自动选择逻辑增强** — 按功能需求强制切换后端（`--image-list` → omni，`--tail-image` → kling），不再仅限默认后端触发

### v1.3.2 (2026-03-18)
🎬 **Kling Omni 后端集成**

#### 新功能
- ✨ **Kling Omni API 支持**
  - 新增 `--backend kling-omni` 后端选项
  - `--image-list` 多参考图模式，prompt 中用 `<<<image_1>>>` 引用
  - 支持多参考图 + multi_shot 组合
- ✨ **自动后端选择**
  - 提供 `--image-list` 自动用 kling-omni
  - 提供 `--tail-image` 自动用 kling
- ✨ **三后端选择策略** — 人物一致性 vs 场景精确度的核心权衡
- ✨ **两条人物参考图路径** — Omni 路径（推荐）vs Kling+Gemini 首帧路径

#### CLI 更新
- 🔧 添加 `--image-list` 参数（Kling Omni 多参考图）
- 🔧 添加 `--backend kling-omni` 选项

### v1.3.1 (2026-03-17)
📋 **Storyboard 结构优化 & 流程完善**

#### Storyboard 结构升级
- ✨ **场景-分镜两层结构**
  - 从单层 `shots` 数组改为 `scenes` -> `shots` 两层结构
  - 新增场景字段：`scene_id`、`scene_name`、`narrative_goal`、`spatial_setting`、`time_state`、`visual_style`
  - 场景时长自动计算（下属分镜时长之和）

- ✨ **shot_id 命名规范化**
  - 新格式：`scene{场景号}_shot{分镜号}`
  - 单分镜示例：`scene1_shot1`、`scene1_shot2`
  - 多镜头模式：`scene1_shot2to4_multi`（带 `_multi` 后缀）

#### 字段优化
- 🔄 `vidu_prompt` → `video_prompt`（通用名称）
- ✨ 新增字段：
  - `multi_shot`：是否为多镜头模式
  - `generation_backend`：后端选择（kling/vidu）
  - `frame_strategy`：首尾帧策略（none/first_frame_only/first_and_last_frame）
  - `multi_shot_config`：Kling 多镜头配置
  - `reference_personas`：引用的人物参考图

#### 流程完善
- 📝 **T2V/I2V 选择规则**：决策树 + 规则表
- 📝 **首尾帧生成策略**：支持 `image_tail` 参数
- 📝 **台词融入规则**：video_prompt 中直接包含台词信息
- 📝 **Review 检查机制**：自动化检查项（结构完整性、分镜规则、Prompt 规范、技术选择）

#### 人物参考图流程
- 📝 完善人物参考图使用流程：
  - 核心原则：参考图不能直接做首帧
  - 完整流程：`人物参考图 → Gemini 生成分镜图 → img2video`
  - 单人/双人镜头处理方案
  - 分镜 JSON 标注 `reference_personas` 和 `notes`

#### CLI 更新
- 🔧 添加 `--multi-shot` 参数启用多镜头模式
- 🔧 添加 `--shot-type` 参数选择分镜类型（intelligence/customize）
- 🔧 添加 `--multi-prompt` 参数传入自定义分镜列表（JSON 格式）
- 🔧 添加 `--tail-image` 参数支持首尾帧控制

### v1.3.0 (2026-03-16)
🎬 **Kling 视频生成 API 集成**

#### 新功能
- ✨ **Kling API 支持**
  - 新增 KlingClient 类，支持 Kling v3 模型
  - JWT Token 认证方式（iss, iat, exp, nbf）
  - 文生视频 (text2video) 和图生视频 (image2video)
  - 支持 3-15 秒时长范围
  - 支持 std/pro 两种生成模式
  - 支持音画同出 (sound: on/off)

- ✨ **多镜头模式**
  - 支持一次生成包含多个镜头的视频
  - intelligence 模式（AI 自动分镜）
  - customize 模式（自定义分镜）

#### CLI 更新
- 🔧 添加 `--backend` 参数选择视频生成后端（vidu/kling）
- 🔧 添加 `--mode` 参数选择生成模式（std/pro）

#### 文档更新
- 📝 SKILL.md 添加 Kling 使用说明和多镜头分镜设计文档
- 📝 README 更新功能列表、工具调用示例、环境变量配置

### v1.2.0 (2026-03-16)
🎯 **分镜流程规范化 & 使用体验优化**

#### 流程规范
- ✅ **视频比例全流程约束**
  - 文生图、图生视频两个阶段的 prompt 强制包含比例信息
  - 9:16/16:9/1:1 不同比例对应明确的中文描述规范
  - 生成前自动检查比例一致性

- ✅ **严格执行分镜规划的生成模式**
  - `generation_mode` 必须在分镜中明确指定，执行阶段严禁改变
  - img2video/text2video/existing 三种模式对应严格的执行规则
  - 违规时立即停止执行并报告错误

- ✅ **台词生成方式明确区分**
  - 同期声（视频模型生成）vs 后期 TTS 旁白的使用场景清晰划分
  - 同期声在 vidu_prompt 中明确描述角色、台词、情绪、语速、声音特质
  - TTS 仅用于场景解说、背景介绍，不用于角色对话

- ✅ **Prompt 详细程度与语言规范**
  - 视频生成 prompt 必须使用中文编写
  - 强制包含运镜描述、运动节奏、画面稳定性、比例保护、台词信息
  - 图片生成 prompt 必须包含场景、主体、光影、风格、比例五要素

- ✅ **素材一致性强制保障**
  - 跨镜头人物必须在 prompt 中包含详细的身份标识和外貌特征描述
  - 关键道具建立物料清单，每个镜头包含完整描述确保一致性
  - 提供人物/道具描述的 Prompt 模板和示例

- ✅ **强制用户确认分镜**
  - 分镜方案必须得到用户明确确认后才能进入执行阶段
  - 详细展示每个镜头的生成模式、prompt、时长、转场等信息
  - state.json 新增 `storyboard_confirmed` 和 `confirmation_details` 字段

#### 文档优化
- 📝 README 新增「使用建议」章节，说明推荐模型、引导技巧、项目定位

### v1.1.0 (2026-03-12)
🔧 **稳定性增强 & 人物管理**

#### 新功能
- ✨ **视频参数自动校验与归一化**
  - 拼接前自动检测所有视频的分辨率、编码、帧率
  - 参数不一致时自动归一化到统一格式（1080x1920 / H.264 / 24fps）
  - 解决不同 API 返回视频分辨率不一致导致的画面卡住问题

- ✨ **人物角色管理器 (PersonaManager)**
  - 管理项目中的人物参考图，保持跨场景人物一致性
  - 自动生成 Vidu/Gemini 可用的 prompt
  - 支持单人/双人镜头的不同策略

#### 文档优化
- 📝 SKILL.md 新增条件性工作流程：
  - 人物识别流程（仅当素材是肖像图时触发）
  - 人物参考图策略（单人/双人镜头处理方案）
  - 视频参数校验流程（拼接前必须执行）
- 📝 添加关键经验总结：Gemini 多参考图注意事项、视频生成参数差异

#### 修复
- 🐛 修复 text2video (720x1280) 和 image2video (716x1284) 分辨率不一致导致的拼接问题

### v1.0.0 (2026-03-10)
🎉 **完整首次发布**

#### 核心功能
- ✨ **AI导演工作流**：完整的视频创作流程 - 素材分析 → 创意确认 → 分镜设计 → 生成 → 剪辑输出
- ✨ **多模态AI生成**：
  - Vidu Q3 Pro 图生视频/文生视频（720p/1080p，最高10秒）
  - Suno V3.5/V4.5 音乐生成（支持自定义风格、时长、纯音乐）
  - 火山引擎 TTS 语音合成（多种音色、情感、语速）
  - Gemini 图片生成（多种风格、比例）
- ✨ **专业剪辑工具**：
  - 视频拼接（自动调整分辨率为9:16/16:9/1:1）
  - 转场效果（16种转场：淡入淡出、叠化、擦除、滑动等）
  - 音频混合（自动循环BGM匹配视频时长、音量调节）
  - 调色预设（温暖、冷色调、鲜艳、电影感、复古等）
  - 变速、字幕支持
- ✨ **自动项目管理**：
  - 自动创建项目目录结构
  - 状态跟踪和断点续做
  - 所有中间产物自动保存
- ✨ **交互式创作**：
  - 素材自动识别和分析
  - 问题卡片式创意确认
  - 分镜方案预览和调整

#### 技术实现
- ✨ 基于httpx的异步API调用，支持并发生成
- ✨ FFmpeg底层视频处理，性能优异
- ✨ 环境自动检查和依赖管理
- ✨ 完善的错误处理和重试机制
- 🐛 修复Suno API callbackUrl缺失问题，全功能可用

## 📄 License

MIT

chuyue responsible of aftereffect optimisation
