---
name: video-gen
description: AI视频剪辑工具。分析素材、生成创意、设计分镜、执行剪辑。支持Vidu/Kling/Kling Omni视频生成、Suno音乐生成、TTS配音、FFmpeg剪辑。当用户要求制作视频、剪辑视频、生成视频、创建短片、或提供素材目录要求生成作品时触发。
argument-hint: <素材目录或视频文件>
---

# video-gen 使用指南

**角色**：Director Agent — 理解创作意图、协调所有资源、交付视频作品。

**语言要求**：所有回复必须使用中文。

---

## 推荐配置

**建议使用多模态模型**（如 Claude Opus/Sonnet/Kimi-K2.5）以获得最佳体验。

非多模态模型会自动调用视觉模型进行图片分析，在 `config.json` 中配置 `VISION_BASE_URL`、`VISION_MODEL`、`VISION_API_KEY`。

### Provider 选择

**不同后端支持的 Provider 不同**：

| 后端 | 支持的 Provider | 说明 |
|------|----------------|------|
| `seedance` | **仅 piapi** | Seedance 只有 piapi 一个 provider，不支持 yunwu/fal |
| `kling-omni` | official, yunwu, fal | 官方 API 遇限制时可切换 |
| `kling` | official, yunwu | 官方 API 遇限制时可切换 |
| `vidu` | **仅 yunwu** | Vidu 只有 yunwu 一个 provider |
| `veo3` | **仅 compass** | Veo3 只有 compass 一个 provider |

当 Kling 官方 API 遇到并发限制（429）时，可使用 `--provider yunwu` 或 `--provider fal`：

```bash
# yunwu 代理（支持 Vidu/Kling/Kling-Omni）
python video_gen_tools.py video --provider yunwu --backend kling-omni --image-list ref.jpg ...

# fal.ai 代理（仅支持 kling-omni）
python video_gen_tools.py video --provider fal --backend kling-omni --image-list ref.jpg ...
```

**注意**：Seedance 不需要指定 `--provider`，因为它只有 piapi 一个 provider。

**Provider 自动选择优先级**：官方 API → fal → yunwu

---

## 核心理念

- **工具文件**：video_gen_tools.py（API 调用）和 video_gen_editor.py（FFmpeg 剪辑）是命令行工具
- **灵活规划，稳健执行**：规划阶段产出结构化制品，执行阶段由分镜方案驱动
- **优雅降级**：遇到问题时主动寻求用户帮助，而不是卡住流程

### 后端选择概览

**场景驱动选择**：

| 场景 | 优先后端 | 兜底后端 | 原因 |
|-----|---------|---------|------|
| **虚构片/短剧** | **Seedance** | Kling-Omni | 智能切镜 + 多参考图，角色一致性 |
| **广告片（无真实素材）** | **Seedance** | Kling-Omni | 长镜头 + 智能切镜 |
| **广告片（有真实素材）** | Kling-3.0 / Vidu | — | 首帧精确控制，真实素材 |
| **MV短片** | **Seedance** | Kling-Omni | 长镜头 + 音乐驱动 |
| **Vlog/写实类** | Kling-3.0 | Vidu | 首帧精确控制，不走 Seedance |
| **高质量写实短片** | **Veo3** | Kling-3.0 | Google Veo3 画质最佳，4/6/8s 短片 |

**visual_style 只影响用户照片处理方式（如有用户照片）**：

| visual_style | 用户照片处理 | 说明 |
|--------------|-------------|------|
| `realistic`（真人写实） | **Seedance 需转换** | 用户真人照片需先生成三视图，再作为参考图 |
| `anime`（动漫/二次元） | 直接使用 | 可直接作为参考图 |
| `mixed`（混合） | 分场景处理 | 真人场景需转换，动漫场景直接使用 |

**Seedance 用户真人照片转换流程**：
```
用户提供真人照片 →
  ├── 调用 Gemini 生成三视图（保持容貌、体态、身材细节）→
  │   - 正面视角
  │   - 侧面视角
  │   - 全身比例
  ├── 选择最佳视角作为角色参考图 →
  └── 注册到 personas.json
```

**关键规则**：
- **Seedance 优先用于虚构内容**（智能切镜是核心优势）
- **Kling-Omni 作为 Seedance 失败时的降级备选**
- **有真实素材时用 Kling/Vidu**（首帧精确控制）
- **同一项目使用同一模型**，不混用（mixed 模式除外）

详细后端对比和降级策略：See [reference/backend-guide.md](reference/backend-guide.md)

---

## 快速启动流程

```
Provider 选择 → 环境检查 → 素材收集 → 创意确认 → 分镜设计 → 执行生成 → 剪辑输出
    交互          5秒        交互       交互        交互        自动        自动
```

### 工作流进度清单

```
Task Progress:
- [ ] Phase 0: Provider 配置 + 环境检查
- [ ] Phase 1: 素材收集（扫描 + 视觉分析 + 人物识别）
- [ ] Phase 2: 创意确认（问题卡片交互 + 角色参考图收集）
- [ ] Phase 3: 分镜设计（生成 storyboard.json + 自动后端选择 + 用户确认）
- [ ] Phase 4: 执行生成（API 调用 + 进度跟踪）
- [ ] Phase 5: 剪辑输出（拼接 + 转场 + 调色 + 配乐）
```

---

## Phase 0: Provider 配置 + 环境检查

### Step 1: 选择视频生成 Provider

**必须在开始任何工作之前完成 API 配置。没有可用的 API key 时不得进入 Phase 1。**

首先运行 setup 查看当前配置状态：

```bash
python ~/.claude/skills/video-gen/video_gen_tools.py setup
```

输出包含所有可选 provider 及其 key 配置状态。**如果没有任何视频 provider 的 key 已配置**，必须引导用户选择并配置：

**向用户展示选项卡片**：

> 请选择视频生成 API（可后续更换）：
>
> **1. Seedance（推荐）** — 字节跳动出品，智能切镜 + 多参考图，适合虚构片/短剧/MV
>    - 需要：Seedance API Key（from piapi.ai）
>
> **2. Kling 官方** — 快手出品，首帧精确控制，适合写实/广告片
>    - 需要：Kling Access Key + Secret Key（from klingai.kuaishou.com）
>
> **3. Kling via fal.ai** — 绕过官方并发限制
>    - 需要：fal.ai API Key（from fal.ai）
>
> **4. Vidu via Yunwu** — 兜底方案
>    - 需要：Yunwu API Key（from yunwu.ai）
>
> **5. Veo3 via Compass** — Google Veo3，高质量写实短片（4/6/8s）
>    - 需要：Compass API Key（from compass.llm.shopee.io）

用户选择后，要求提供对应的 API key，然后保存：

```bash
# 例：用户选择 Seedance
python ~/.claude/skills/video-gen/video_gen_tools.py setup --set-key SEEDANCE_API_KEY=sk-xxx

# 例：用户选择 Kling 官方
python ~/.claude/skills/video-gen/video_gen_tools.py setup --set-key KLING_ACCESS_KEY=xxx KLING_SECRET_KEY=xxx

# 例：用户选择 fal
python ~/.claude/skills/video-gen/video_gen_tools.py setup --set-key FAL_API_KEY=xxx

# 例：用户选择 Veo3
python ~/.claude/skills/video-gen/video_gen_tools.py setup --set-key COMPASS_API_KEY=xxx
```

**可选服务**（保存 key 后继续询问）：
- 音乐生成（Suno）：`SUNO_API_KEY`
- TTS 语音合成（火山引擎）：`VOLCENGINE_TTS_APP_ID` + `VOLCENGINE_TTS_ACCESS_TOKEN`

用户可以跳过可选服务。

### Step 2: 环境检查

```bash
python ~/.claude/skills/video-gen/video_gen_tools.py check
```

- 基础依赖（FFmpeg/Python/httpx）不通过 → 停止并告知安装方法
- **至少一个视频 provider 的 API key 已配置** → 继续
- **没有任何视频 API key** → 返回 Step 1，不得继续

---

## Phase 1: 素材收集

### 素材来源识别

- **目录路径** → 扫描目录中的图片/视频文件
- **视频文件** → 直接分析该视频
- **无素材** → 纯创意模式

### 视觉分析流程（三级 fallback）

**Step 1**：使用 Read 工具读取图片。记录场景描述、主体内容、情感基调、颜色风格。

**Step 2**：Read 失败 → 调用内置 VisionClient：

```python
from video_gen_tools import VisionClient
client = VisionClient()
results = await client.analyze_batch(image_paths, "分析这些素材：场景、主体、颜色、氛围")
```

**Step 3**：VisionClient 也失败 → 主动询问用户描述每张素材内容。

### 人物识别（条件性）

**仅当用户提供了人物肖像图时触发**（不确定时询问用户）。

执行步骤：
1. 读取图片内容，识别所有人物
2. 询问用户确认每个人物的身份
3. 使用 PersonaManager 分别注册：

```python
from video_gen_tools import PersonaManager
manager = PersonaManager(project_dir)

# 情况A：用户提供了参考图
manager.register("小美", "female", "path/to/ref.jpg", "长发、瓜子脸")

# 情况B：用户未提供参考图（Phase 2 会补充）
manager.register("孙悟空", "male", None, "猴脸、金箍、虎皮裙")
```

**Phase 1 关键原则**：
- 只处理用户**已上传**的参考图
- 未上传的角色 reference_image 设为 `None`，由 Phase 2 补充
- 不要在此阶段询问未上传的参考图

### Phase 1 产出

创建项目目录 `~/video-gen-projects/{project_name}_{timestamp}/`，产出：
- `state.json` — 项目状态
- `analysis/analysis.json` — 素材分析结果
- `personas.json` — 人物注册表（reference_image 可能为 None）

**personas.json 结构**：
```json
{
  "personas": [
    {
      "name": "孙悟空",
      "gender": "male",
      "reference_image": null,  // Phase 1 未上传时为 null
      "features": "猴脸、金色毛发、火眼金睛、身穿锁子黄金甲"
    },
    {
      "name": "小美",
      "gender": "female",
      "reference_image": "/path/to/ref.jpg",  // 用户上传了参考图
      "features": "长发、瓜子脸"
    }
  ]
}
```

---

## Phase 2: 创意确认

**使用问题卡片与用户交互**，收集关键信息。

### 问题卡片设计

**问题 1: 视频风格**
- 选项：电影感 | Vlog风格 | 广告片 | 纪录片 | 艺术/实验
- 说明：决定调色、转场、配乐的整体基调

**问题 2: 目标时长**
- 选项：15秒（短视频）| 30秒（标准）| 60秒（长视频）| 自定义
- 说明：影响分镜数量和节奏

**问题 3: 画面比例**
- 选项：9:16（抖音/小红书）| 16:9（B站/YouTube）| 1:1（Instagram）
- 说明：根据发布平台选择

**问题 4: 配乐需求**
- 选项：AI生成BGM | 不需要配乐 | 我已有音乐
- 说明：是否需要 Suno 生成背景音乐

**问题 5: 旁白/解说**

**先判断视频类型是否适合加旁白**：

| 视频风格 | 旁白需求 | 说明 |
|---------|---------|------|
| 电影感/虚构片 | 通常不需要 | 角色台词为主，旁白会破坏沉浸感 |
| 纪录片 | 通常需要 | 场景解说、背景介绍 |
| Vlog风格 | 可能需要 | 旅行解说、心情记录 |
| 广告片 | 可能需要 | 产品介绍、品牌故事 |
| 艺术/实验 | 视情况 | 概念表达可能需要旁白 |

**拿不准时询问用户**：

> 这条视频是否需要旁白/解说？
> - **不需要旁白**（角色台词为主，或纯视觉表达）
> - **需要AI生成旁白**（我来根据分镜设计文案）
> - **我已有旁白文案**（用户提供完整文案）

**区分两种音频生成方式**：

**A. 角色台词（同期声）**
- 由视频生成模型直接生成
- 需要在分镜的 video_prompt 中明确描述：角色、台词、情绪、语速、声音特质
- 视频生成时设置 `audio: true`

**B. 旁白/解说（后期配音）**
- 由 TTS 后期生成，在剪辑阶段合入
- 用于场景解说、背景介绍、情感烘托
- Phase 3 会根据分镜设计旁白文案和时间点

**重要原则**：能收同期声的镜头，都不要用后期 TTS 配音！

### 问题 6: 角色画风选择

**触发条件**：虚构片/短剧、MV短片类型的项目（Vlog/写实类默认真人风格）。

> **请选择角色画风**
> - **A. 真人写实风格** — AI 生成的角色参考图采用真人演员风格
> - **B. 动漫/二次元风格** — AI 生成的角色参考图采用动漫风格
> - **C. 混合风格** — 分场景处理，真人场景和动漫场景各有不同画风

**选择后写入 `creative.json`**：
```json
{
  "visual_style": "realistic"  // realistic / anime / mixed
}
```

**说明**：

| visual_style | AI 参考图风格 | 用户真人照片处理（如有） |
|--------------|--------------|------------------------|
| `realistic` | 真人演员风格 | Seedance 需先生成三视图转换，Kling-Omni 可直接使用 |
| `anime` | 动漫/二次元风格 | 可直接作为参考图 |
| `mixed` | 分场景决定 | 真人场景照片需转换，动漫场景可直接使用 |

**关键认知**：
- **纯创意模式（无用户照片）**：visual_style 只决定 AI 生成的参考图风格，**不影响后端选择**
- **有用户照片模式**：visual_style 决定用户照片的处理方式（是否需要三视图转换）
- **后端选择依据**：项目需求（智能切镜 vs 角色一致性 vs 首帧控制），而非 visual_style

### 问题 7: 角色参考图收集

**触发条件**：检查 personas.json，存在 `reference_image` 为 null/空 的角色时触发。

**检查逻辑**：
```python
manager = PersonaManager(project_dir)
for persona_id in manager.list_personas_without_reference():
    # 询问用户该角色的参考图来源
    ask_user_for_reference(persona_id)
```

**询问内容**（每个无参考图的角色）：

> **角色「{name}」需要参考图**
>
> 请选择参考图来源：
> - **A. AI生成角色形象**（推荐，自动生成标准参考图）
> - **B. 上传参考图**（用户提供人物照片）
> - **C. 接受纯文字生成**（角色外貌可能在不同镜头中不一致）

**选择后处理**：

**A. AI生成**（根据 visual_style 决定画风）：
```python
# 读取 visual_style
visual_style = creative.get("visual_style", "realistic")

# 根据画风生成对应风格的参考图
if visual_style == "anime":
    style_suffix = "anime style, 2D animation, vibrant colors"
else:  # realistic
    style_suffix = "photorealistic, cinematic, realistic"

python video_gen_tools.py image \
  --prompt "{角色外貌描述}，{style_suffix}，正面半身照，纯色背景，高清肖像" \
  --output materials/personas/{name}_ref.png

# 更新 personas.json
manager.update_reference_image(persona_id, "materials/personas/{name}_ref.png")
```

**B. 上传参考图**：
- 请用户上传图片
- 保存到 `materials/personas/{name}_ref.{ext}`
- 更新 personas.json

**C. 纯文字**：
- 记录警告到 `creative/decision_log`
- 后续 Phase 3 将**强制生成分镜图**，然后使用 img2video 或 reference2video

**关键规则**：
- **必须生成参考图**：角色需要在**多个镜头**中出现时
- **可用 text2video**：单一场景出现、纯风景、用户明确接受外貌波动
- **AI 生成参考图时必须遵循 visual_style**：anime 风格或 realistic 风格

### Phase 2 产出

- `creative/creative.json` — 创意方案（含 visual_style 画风决策）
- 更新 `personas.json` — 补充 reference_images（如有）
- `creative/decision_log.json` — 记录参考图相关决策

**creative.json 结构**：

```json
{
  "title": "项目标题",
  "style": "cinematic",
  "duration": 30,
  "aspect_ratio": "16:9",
  "visual_style": "anime",  // realistic / anime / mixed — 画风决策
  "music": {
    "enabled": true,
    "source": "ai_generated",
    "prompt": "音乐描述",
    "style": "音乐风格"
  },
  "narration": {
    "type": "ai_generated",
    "voice_style": "温柔女声，语速适中",
    "user_text": null
  }
}
```

**visual_style 字段说明**：

| 值 | 说明 | 用户照片处理 |
|---|------|-------------|
| `realistic` | 真人写实风格 | Seedance 需先生成三视图转换，Kling-Omni 可直接使用 |
| `anime` | 动漫/二次元风格 | 可直接作为参考图 |
| `mixed` | 混合风格 | 真人场景照片需转换，动漫场景可直接使用 |

| type | 说明 | Phase 3 处理 |
|------|------|-------------|
| `none` | 不需要旁白 | 不规划 narration_segments |
| `ai_generated` | AI 设计文案 | 根据分镜自动撰写旁白，按镜头分段 |
| `user_provided` | 用户已有文案 | 将 user_text 按镜头时间点分段 |

---

## Phase 3: 分镜设计

根据素材和创意方案生成分镜脚本。

### 分镜生成前强制阅读

**在生成分镜脚本前，必须阅读以下三个文档**：

```
Read: reference/storyboard-spec.md   # T2V/I2V决策树、分镜规范、JSON格式
Read: reference/prompt-guide.md       # Prompt编写规范、一致性要求
Read: reference/backend-guide.md      # 后端选择决策树、参考图策略
```

### Step 1: 同步角色信息到 Storyboard

**从 personas.json 同步到 storyboard.json**：

```python
from video_gen_tools import PersonaManager

manager = PersonaManager(project_dir)

# 生成 storyboard.json 的 elements.characters
characters = manager.export_for_storyboard()

# 生成 character_image_mapping
image_mapping = manager.get_character_image_mapping()

# 写入 storyboard.json
storyboard["elements"] = {"characters": characters}
storyboard["character_image_mapping"] = image_mapping
```

**同步后 storyboard.json 结构**：
```json
{
  "elements": {
    "characters": [
      {
        "element_id": "Element_SunWukong",
        "name": "孙悟空",
        "name_en": "SunWukong",
        "reference_images": ["materials/personas/孙悟空_ref.png"],
        "visual_description": "猴脸、金色毛发..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_SunWukong": "image_1"
  }
}
```

### Step 2: 自动后端选择逻辑

**场景驱动选择**：

| 场景 | 优先后端 | 兜底后端 | 原因 |
|-----|---------|---------|------|
| **虚构片/短剧** | **Seedance** | Kling-Omni | 智能切镜 + 多参考图，角色一致性 |
| **广告片（无真实素材）** | **Seedance** | Kling-Omni | 长镜头 + 智能切镜 |
| **广告片（有真实素材）** | Kling-3.0 / Vidu | — | 首帧精确控制，真实素材 |
| **MV短片** | **Seedance** | Kling-Omni | 长镜头 + 音乐驱动 |
| **Vlog/写实类** | Kling-3.0 | Vidu | 首帧精确控制，不走 Seedance |
| **高质量写实短片** | **Veo3** | Kling-3.0 | Google Veo3 画质最佳，4/6/8s 短片 |

**首帧控制能力对比**：

| 后端 | 首帧控制 | 说明 |
|------|---------|------|
| **Kling-3.0** | ✅ `--image` | 视频从此图开始 |
| **Vidu** | ✅ `--image` | 首帧精确控制 |
| **Veo3** | ✅ `--image` | 首帧精确控制 |
| **Seedance** | ❌ 参考图 | 分镜图是视觉风格参考，不是首帧 |
| **Kling-Omni** | ❌ 参考图 | 只有 reference2video，无 img2video |

**visual_style 只在「有用户真人照片 + 用 Seedance」时生效**：
- `realistic` → 用户照片需先生成三视图转换
- `anime` → 用户照片可直接使用
- 纯创意模式下 visual_style 只影响 AI 参考图风格

**核心原则**：
1. **同一项目使用同一模型**
2. **虚构片不使用 text2video**
3. **需要首帧控制时只能用 Kling 或 Vidu**
4. **Seedance/Omni 分镜图是参考，不是首帧精确控制**

### Step 3: 生成分镜

**核心结构**：Storyboard 采用 `scenes[] → shots[]` 两层结构。

**关键设计原则**：

1. **时长设计（根据后端限制）**：
   | 后端 | Scene 总时长限制 | 设计策略 |
   |------|-----------------|---------|
   | **Seedance** | **仅支持 5/10/15s**（枚举值） | 每个 scene 必须是 5/10/15s，shots 合并后不能超出 |
   | Kling-Omni | 3-15s（连续范围） | scene 总时长 ≤15s 即可 |
   | Kling-3.0 | 3-15s（连续范围） | 每个单独 shot ≤15s |
   | Vidu | 5-10s | 每个 shot 5-10s |

2. 总时长 = 目标时长（±2秒），单镜头 2-5 秒
3. 同一分镜内最多 1 个动作，禁止空间变化
4. 所有 video_prompt 必须包含比例信息
5. 台词必须融入 video_prompt（角色 + 内容 + 情绪 + 声音）
6. 根据 Step 2 的自动选择结果设置 `generation_mode` 和 `reference_images`

**完整分镜规范**：See [reference/storyboard-spec.md](reference/storyboard-spec.md)
**Prompt 编写与一致性规范**：See [reference/prompt-guide.md](reference/prompt-guide.md)

**生成分镜时同步处理旁白**：

若 `creative.narration.type` 不为 `none`，则在生成分镜的同时规划旁白分段：

1. **读取 narration 信息**：
   - `voice_style` → 写入 `narration_config.voice_style`
   - `user_text`（如有）→ 按镜头时间点分段

2. **根据镜头内容设计旁白文案**：
   - 每段旁白对应一个镜头或一组连续镜头
   - 每段控制在 2-5 秒可说完的长度（约 30-50 字）

3. **规划时间点并写入 storyboard.json**：

```json
{
  "narration_config": {
    "voice_style": "温柔女声"
  },
  "narration_segments": [
    {"segment_id": "narr_1", "overall_time_range": "0-3s", "text": "这是一个宁静的下午..."},
    {"segment_id": "narr_2", "overall_time_range": "8-11s", "text": "她坐在窗边..."}
  ]
}
```

**旁白分段规范**：See [reference/storyboard-spec.md](reference/storyboard-spec.md) → 「旁白分段规划」

### Step 4: 展示给用户确认（强制步骤）

**必须在用户明确确认后才能进入 Phase 4！**

展示每个镜头的：
- 场景信息
- 生成模式（text2video/img2video/omni-video）
- 后端选择
- video_prompt
- image_prompt（如有）
- reference_images（如有）
- 台词
- 转场
- 时长

**若有旁白，额外展示**：
- narration_segments 分段列表
- 每段的时间点、文案

提供选项：确认并执行 / 修改分镜 / 调整旁白 / 调整时长 / 更换转场 / 取消

### Phase 3 产出

- `storyboard/storyboard.json` — 分镜脚本（包含 generation_mode、reference_images、后端选择、narration_segments）

---

## Phase 4: 执行生成

根据 storyboard.json 执行视频生成。

### Phase 4 执行前检查

**0. Storyboard 校验（必须通过）**

```bash
python ~/.claude/skills/video-gen/video_gen_tools.py validate --storyboard storyboard/storyboard.json
```

校验内容：Seedance 时长是否为 5/10/15、backend-mode 是否匹配、参考图是否存在、aspect_ratio 格式、API key 是否可用。
- 有 ERROR → 必须修复后再继续
- 只有 WARNING → 可继续，但需关注

**1. 参考图尺寸检查**
- 从 storyboard.json 读取每个镜头的 `reference_images`
- 检测所有参考图尺寸
- 最小边 < 720px → 自动放大到 1280px
- 最大边 > 2048px → 自动缩小到 2048px
- 自动生成调整后的图片（添加 `_resized` 后缀）

**2. 参数校验**
- **从 storyboard.json 读取 `aspect_ratio` 字段，传递给 CLI 的 `--aspect-ratio` 参数**
- 根据 storyboard 的 `audio` 配置设置 API 参数（详见 prompt-guide.md）

### 执行规则

1. **首次 API 调用单独执行**，确认成功后再并发
2. **并发不超过 3 个** API 生成调用
3. **实时更新 state.json** 记录进度
4. **失败时重试** 最多 2 次，然后询问用户

### API 错误处理与降级

当 API 调用失败时，按错误类型处理：

| 错误类型 | 处理方式 |
|---------|---------|
| **429 并发限制** | 询问用户：等待重试 或 降级到 Path B |
| **402 余额不足** | 告知用户充值，或降级到其他可用后端 |
| **网络超时** | 重试 2 次，失败后询问 |
| **其他错误** | 记录错误详情，询问用户 |

**降级决策流程**：

```
API 失败 → 判断错误类型 →
  ├── 429/402（资源限制）→ 询问用户降级
  │     ├── 用户选择等待 → 等待 60s 后重试
  │     ├── 用户选择降级 → 执行降级流程（见下文）
  │     └── 用户选择取消 → 停止生成
  └── 其他错误 → 重试 2 次 → 失败后询问用户
```

**降级执行流程**（Seedance → Omni 或 Path A → Path B）：

**Seedance 失败处理**（必须先重试）：
1. **第一次失败** → 重试一次（相同参数，等待 30s）
2. **重试仍失败** → 告知用户并询问降级选项：
   ```
   Seedance 生成失败（已重试 1 次）。
   
   可选方案：
   A. 降级到 Kling-Omni（失去智能切镜，需手动 multi-shot）
   B. 修改 prompt 后再次尝试 Seedance
   C. 取消本次生成
   
   请选择：
   ```
3. 用户选择 A → 执行降级流程

**Seedance → Omni**：
1. 告知用户降级后果（失去智能切镜，需手动 multi-shot）
2. 修改 storyboard.json 的 generation_backend 为 `kling-omni`
3. 每个 shot 单独调用 API（不合并）

**Omni → Kling img2video**：
1. 告知用户降级后果（角色一致性会降低）
2. 修改 storyboard.json 的生成模式字段
3. 先生成所有分镜图（使用 Gemini）
4. 用分镜图作为首帧调用 Kling img2video

**降级详细规范**：See [reference/backend-guide.md](reference/backend-guide.md) → "API 限制时的降级策略"

### 生成模式强制执行

**必须严格按照 storyboard.json 执行，禁止擅自更改**：

| generation_mode | CLI 参数 |
|----------------|----------|
| `seedance-video` | `--backend seedance --aspect-ratio {aspect_ratio} --image-list {frame} {ref1} {ref2} ...` |
| `omni-video` | `--backend kling-omni --aspect-ratio {aspect_ratio} --image-list {ref1} {ref2} ...` |
| `img2video` | `--aspect-ratio {aspect_ratio} --image {frame_path}` |
| `text2video` | `--aspect-ratio {aspect_ratio}` |

**重要**：`{aspect_ratio}` 从 `storyboard.json` 的 `aspect_ratio` 字段读取。

**示例（Seedance 模式）**：
```bash
# Seedance 智能切镜：分镜图 + 角色参考图
python video_gen_tools.py video \
  --backend seedance \
  --aspect-ratio 16:9 \
  --prompt "Referencing the scene1_frame composition... @image1..." \
  --image-list generated/frames/scene1_frame.png materials/personas/xiaomei_ref.jpg \
  --duration 10 \
  --output generated/videos/scene1.mp4
```

**示例（Omni 模式）**：
```bash
# 从 storyboard.json 读取 aspect_ratio（如 "16:9"）
python video_gen_tools.py video \
  --backend kling-omni \
  --aspect-ratio {aspect_ratio} \
  --prompt "孙悟空挥舞金箍棒..." \
  --image-list materials/personas/sunwukong_ref.png \
  --audio \
  --output generated/videos/scene1_shot1.mp4
```

### Seedance 执行逻辑（自动组装模式）

**当 `generation_backend = "seedance"` 时，使用 `--scene` 参数自动组装时间分段 prompt**。

工具会自动完成：时间分段计算、prompt 格式拼装、image_urls 排列、duration 对齐（5/10/15s）。

#### 执行步骤

**Step 1: 生成分镜图**
- 每个 Seedance scene 生成一张分镜图
- 使用 Gemini + 角色参考图生成
- 保存到 `generated/frames/{scene_id}_frame.png`

**Step 2: 调用自动组装**

```bash
python video_gen_tools.py video \
  --backend seedance \
  --storyboard storyboard/storyboard.json \
  --scene scene_1 \
  --output generated/videos/scene_1.mp4
```

工具内部自动：
1. 读取 scene 的 shots，计算时间偏移量，拼装时间分段 prompt
2. 从 `character_image_mapping` 解析角色参考图顺序
3. 组装 `image_urls`（分镜图在前，角色参考图在后）
4. 总时长自动对齐到最接近的 5/10/15s

**关键**：确保分镜图路径已填入 shot 的 `reference_images`，且 `video_prompt` 包含运镜 + 节奏描述。

#### 手动模式（兜底）

自动组装不满足需求时，仍可手动指定 prompt：

```bash
python video_gen_tools.py video \
  --backend seedance \
  --prompt "手动编写的时间分段 prompt..." \
  --image-list frame.png ref.jpg \
  --duration 10 \
  --output output.mp4
```

### API Key 管理

首次调用时检查并请求 API key，用户提供后通过 `export` 设置。

**工具调用详细参数**：See [reference/api-reference.md](reference/api-reference.md)

### 音乐生成

调用 `video_gen_tools.py music` 必须传 `--creative` 参数。

原因：从 `creative.json` 的 `music` 字段读取 `prompt`（音乐描述）和 `style`（音乐风格），避免使用默认风格。

### 旁白生成（条件触发）

**触发条件**：读取 `storyboard.json` 的 `narration_segments`，若存在则触发。

**生成流程**：

1. **读取 narration_config 和 narration_segments**
2. **按分段逐个调用 TTS**：

```bash
# 每段旁白单独生成
python video_gen_tools.py tts \
  --text "这是一个宁静的下午..." \
  --voice-style "温柔女声，语速适中" \
  --output generated/narration/narr_1.mp3

python video_gen_tools.py tts \
  --text "她坐在窗边..." \
  --voice-style "温柔女声，语速适中" \
  --output generated/narration/narr_2.mp3
```

3. **输出文件命名**：按 `segment_id` 命名（`narr_1.mp3`, `narr_2.mp3`...）

**执行顺序**：
```
视频片段生成 → 音乐生成 → 旁白生成（如有）→ 进入 Phase 5 剪辑
```

### Phase 4 产出

- `generated/videos/*.mp4` — 生成的视频片段
- `generated/music/*.mp3` — 生成的背景音乐（如有）
- `generated/narration/*.mp3` — 生成的旁白音频（如有）
- 更新 `state.json` — 记录生成进度

---

## Phase 5: 剪辑输出

### 视频拼接

调用 `video_gen_editor.py concat` 必须传 `--storyboard` 参数。

原因：从 `storyboard.json` 读取 `aspect_ratio`，确保输出视频比例正确。

### 音频保护

视频片段可能包含同期声、音效，拼接时不能丢失。无声片段会自动补静音轨，确保音画同步。

### 视频参数校验

拼接前自动检查分辨率/编码/帧率，不一致时自动归一化（1080x1920 / H.264 / 24fps）。

```bash
python ~/.claude/skills/video-gen/video_gen_editor.py concat --inputs video1.mp4 video2.mp4 --output final.mp4
```

### 合成流程

1. **拼接** → 按分镜顺序连接（自动归一化）
2. **插入旁白** → 按 `narration_segments` 的 `overall_time_range` 将旁白音频配到正确位置（如有）
3. **转场** → 添加镜头间转场效果
4. **调色** → 应用整体调色风格
5. **配乐** → 混合背景音乐
6. **输出** → 生成最终视频

### 音频混音规则

**核心原则**：FFmpeg `amix` 滤镜**必须使用 `normalize=0`**，防止自动均一化导致音量被压低。

**音量推荐值**（根据视频类型灵活调整）：

| 音频类型 | 推荐音量 | 说明 |
|---------|---------|------|
| 视频环境声/同期声 | 0.8 | 保留原始音频氛围 |
| 旁白/解说 | 1.5-2.0 | 确保人声清晰 |
| 背景音乐（BGM） | 0.1-0.15 | 背景衬托角色 |

**视频类型适配**：

| 视频类型 | BGM音量 | 原因 |
|---------|---------|------|
| Vlog/纪录片 | 0.1-0.15 | 旁白为主 |
| 电影感/虚构片 | 0.2-0.3 | 音乐烘托情绪 |
| 音乐MV | 0.5-0.7 | 音乐是核心元素 |
| 广告片 | 0.15-0.25 | 平衡产品介绍与音乐 |

**FFmpeg amix 语法**：
```bash
# 关键：normalize=0 保留原始音量比例
"[track1][track2]amix=inputs=2:duration=first:normalize=0[out]"
```

**实现说明**：`video_gen_editor.py` 的 `mix_audio()` 函数已硬编码 `normalize=0`（约第 470 行）。

### 旁白插入（条件触发）

**触发条件**：读取 `storyboard.json` 的 `narration_segments`，若存在则触发。

**插入方式**：使用 FFmpeg 在指定时间点插入旁白音频。

```bash
# 按 overall_time_range 插入旁白
python video_gen_editor.py narration \
  --video concat_output.mp4 \
  --storyboard storyboard/storyboard.json \
  --narration-dir generated/narration \
  --output with_narration.mp4
```

**时间点计算**：
- `overall_time_range` 格式：`"0-3s"` 表示从 0 秒开始，持续到 3 秒
- 旁白音频在 `overall_time_range` 的起始时间点插入
- 多段旁白按时间顺序依次叠加

### Phase 5 产出

- `output/final.mp4` — 最终视频

---

## 工具调用速查

```bash
# 环境检查
python ~/.claude/skills/video-gen/video_gen_tools.py check

# Storyboard 校验（Phase 4 执行前必须通过）
python ~/.claude/skills/video-gen/video_gen_tools.py validate --storyboard storyboard/storyboard.json

# 视频生成（必须从 storyboard.json 读取 aspect_ratio）
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt <描述> --aspect-ratio {aspect_ratio} --output <输出>

# Seedance 自动组装模式（推荐：工具自动计算时间分段、拼装 prompt、排列 image_urls）
python ~/.claude/skills/video-gen/video_gen_tools.py video \
  --backend seedance \
  --storyboard storyboard/storyboard.json \
  --scene scene_1 \
  --output generated/videos/scene_1.mp4

# Seedance 手动模式（兜底）
python ~/.claude/skills/video-gen/video_gen_tools.py video \
  --backend seedance \
  --prompt "手动编写的时间分段 prompt..." \
  --image-list frame.png ref.jpg \
  --duration 10 \
  --output output.mp4

# Veo3 文生视频（Google Veo3，4/6/8s 高质量短片）
python ~/.claude/skills/video-gen/video_gen_tools.py video \
  --backend veo3 \
  --prompt <描述> \
  --duration 8 \
  --output generated/videos/shot.mp4

# Veo3 图生视频（首帧控制）
python ~/.claude/skills/video-gen/video_gen_tools.py video \
  --backend veo3 \
  --image <首帧图> \
  --prompt <描述> \
  --duration 8 \
  --output generated/videos/shot.mp4

# 音乐（必须传 --creative，从 creative.json 读取 prompt 和 style）
python ~/.claude/skills/video-gen/video_gen_tools.py music --creative creative/creative.json --output <输出>

# 旁白（按 narration_segments 分段调用）
python ~/.claude/skills/video-gen/video_gen_tools.py tts --text <分段文案> --voice female_narrator --emotion gentle --output generated/narration/narr_1.mp3

# 图片生成
python ~/.claude/skills/video-gen/video_gen_tools.py image --prompt <描述> --aspect-ratio {aspect_ratio} --output <输出>

# 剪辑（concat 必须传 --storyboard，从 storyboard.json 读取 aspect_ratio）
python ~/.claude/skills/video-gen/video_gen_editor.py concat --inputs <视频列表> --output <输出> --storyboard storyboard/storyboard.json

# 旁白插入（按 overall_time_range 插入）
python ~/.claude/skills/video-gen/video_gen_editor.py narration --video <视频> --storyboard storyboard/storyboard.json --narration-dir generated/narration --output <输出>

# 其他剪辑命令
python ~/.claude/skills/video-gen/video_gen_editor.py mix --video <视频> --bgm <音乐> --output <输出>
python ~/.claude/skills/video-gen/video_gen_editor.py transition --inputs <v1> <v2> --type <类型> --output <输出>
python ~/.claude/skills/video-gen/video_gen_editor.py color --video <视频> --preset <预设> --output <输出>
```

---

## 文件结构

```
~/video-gen-projects/{project_name}_{timestamp}/
├── state.json           # 项目状态
├── materials/           # 原始素材
│   └── personas/        # 角色参考图（Phase 2 生成）
├── analysis/
│   └── analysis.json    # 素材分析
├── creative/
│   ├── creative.json    # 创意方案
│   └── decision_log.json # 决策记录
├── storyboard/
│   └── storyboard.json  # 分镜脚本（含 narration_segments）
├── generated/
│   ├── videos/          # 生成的视频
│   ├── music/           # 生成的音乐
│   ├── narration/       # 生成的旁白音频
│   └── image/           # 生成的图片
└── output/
    └── final.mp4        # 最终视频
```

---

## 错误处理

| 问题 | 处理方式 |
|------|---------|
| 视觉分析失败 | VisionClient fallback → 询问用户 |
| API key 未配置 | 首次调用时询问 |
| API 调用失败 | 重试 2 次 → 询问用户 |
| 视频生成失败 | 尝试其他模式或用原始素材 |
| 音乐生成失败 | 生成静音视频并告知 |

---

## 依赖

- FFmpeg 6.0+
- Python 3.9+
- httpx
