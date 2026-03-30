---
name: vico-edit
description: AI视频剪辑工具。分析素材、生成创意、设计分镜、执行剪辑。支持Vidu/Kling/Kling Omni视频生成、Suno音乐生成、TTS配音、FFmpeg剪辑。当用户要求制作视频、剪辑视频、生成视频、创建短片、或提供素材目录要求生成作品时触发。
argument-hint: <素材目录或视频文件>
---

# Vico-Edit 使用指南

**角色**：Director Agent — 理解创作意图、协调所有资源、交付视频作品。

**语言要求**：所有回复必须使用中文。

---

## 推荐配置

**建议使用多模态模型**（如 Claude Opus/Sonnet/Kimi-K2.5）以获得最佳体验。

非多模态模型会自动调用视觉模型进行图片分析，在 `config.json` 中配置 `VISION_BASE_URL`、`VISION_MODEL`、`VISION_API_KEY`。

---

## 核心理念

- **工具文件**：vico_tools.py（API 调用）和 vico_editor.py（FFmpeg 剪辑）是命令行工具
- **灵活规划，稳健执行**：规划阶段产出结构化制品，执行阶段由分镜方案驱动
- **优雅降级**：遇到问题时主动寻求用户帮助，而不是卡住流程

### 后端选择概览

| 模型 | 核心优势 | 推荐场景 |
|------|---------|---------|
| **Kling-3.0-Omni** (`kling-omni`) | image_list 多参考图、角色一致性最佳 | 虚构片/短剧、MV短片（reference2video） |
| **Kling-3.0** (`kling`) | 首帧精确控制、画面质感好 | Vlog/写实类、广告片（img2video） |
| **Vidu Q3 Pro** (`vidu`) | 稳定、快速 | 兜底、快速处理真实素材 |

**核心原则**：
- **同一项目使用同一模型**，不混用
- **虚构片优先 Kling-3.0-Omni**（reference2video）
- **首帧控制用 Kling-3.0 或 Vidu**（img2video，Omni不支持首帧控制）

详细后端对比和参考图策略：See [reference/backend-guide.md](reference/backend-guide.md)

---

## 快速启动流程

```
环境检查 → 素材收集 → 创意确认 → 分镜设计 → 执行生成 → 剪辑输出
   5秒        交互       交互        交互        自动        自动
```

### 工作流进度清单

```
Task Progress:
- [ ] Phase 0: 环境检查（python vico_tools.py check）
- [ ] Phase 1: 素材收集（扫描 + 视觉分析 + 人物识别）
- [ ] Phase 2: 创意确认（问题卡片交互 + 角色参考图收集）
- [ ] Phase 3: 分镜设计（生成 storyboard.json + 自动后端选择 + 用户确认）
- [ ] Phase 4: 执行生成（API 调用 + 进度跟踪）
- [ ] Phase 5: 剪辑输出（拼接 + 转场 + 调色 + 配乐）
```

---

## Phase 0: 环境检查

```bash
python ~/.claude/skills/vico-edit/vico_tools.py check
```

- 基础依赖（FFmpeg/Python/httpx）不通过 → 停止并告知安装方法
- API key 未配置 → 记录状态，后续按需询问

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
from vico_tools import VisionClient
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
from vico_tools import PersonaManager
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

创建项目目录 `~/vico-projects/{project_name}_{timestamp}/`，产出：
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

**问题 5: 旁白/字幕**

区分两种音频生成方式：

**A. 角色台词（同期声）**
- 由视频生成模型直接生成
- 需要在分镜的 video_prompt 中明确描述：角色、台词、情绪、语速、声音特质
- 视频生成时设置 `audio: true`

**B. 旁白/解说（后期配音）**
- 由 TTS 生成
- 用于场景解说、背景介绍、情感烘托
- 选项：不需要 | AI生成旁白 | 我已有文案

**重要原则**：能收同期声的镜头，都不要用后期 TTS 配音！

### 问题 6: 角色参考图收集

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

**A. AI生成**：
```python
# 生成角色参考图
python vico_tools.py image \
  --prompt "{角色外貌描述}，正面半身照，纯色背景，高清肖像" \
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

### Phase 2 产出

- `creative/creative.json` — 创意方案
- 更新 `personas.json` — 补充 reference_images（如有）
- `creative/decision_log.json` — 记录参考图相关决策

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
from vico_tools import PersonaManager

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

**根据项目类型自动选择后端**（无需人工决策）：

#### 项目类型判断（Phase 1 自动识别）

| 用户意图关键词 | 项目类型 |
|---------------|---------|
| "短剧"、"剧情"、"故事" | 虚构片/短剧 |
| "vlog"、"旅行记录"、"生活记录" | Vlog/写实类 |
| "广告"、"宣传片"、"产品展示" | 广告片/宣传片 |
| "MV"、"音乐视频" | MV短片 |

#### 决策树

**虚构片/短剧、MV短片**：
```
虚构内容 → 所有镜头强制先生成分镜图
           ├── 优先 → Kling-3.0-Omni（reference2video）
           │         └── image_list: [分镜图, 角色参考图]
           │
           └── 兜底 → Kling-3.0 或 Vidu Q3 Pro（img2video）
                      └── --image: 分镜图首帧
```

**Vlog/写实类、广告片/宣传片（有真实素材）**：
```
真实素材 → 需要首帧控制
           └── Kling-3.0 或 Vidu Q3 Pro（img2video）
               └── --image: 用户素材首帧
```

#### 选择规则表

| 项目类型 | 素材情况 | 生成模式 | 后端 |
|---------|---------|---------|------|
| 虚构片/短剧 | 有/无角色参考图 | **reference2video** | kling-omni |
| MV短片 | 有/无角色参考图 | **reference2video** | kling-omni |
| Vlog/写实类 | 用户真实素材 | **img2video** | kling 或 vidu |
| 广告片/宣传片 | 有真实素材 | **img2video** | kling 或 vidu |
| 广告片/宣传片 | 无真实素材 | **reference2video** | kling-omni |

**核心原则**：
1. **同一项目使用同一模型**，不混用
2. **虚构片不使用 text2video**
3. **Omni 不支持首帧控制**，需要首帧控制时用 Kling-3.0 或 Vidu

### Step 3: 生成分镜

**核心结构**：Storyboard 采用 `scenes[] → shots[]` 两层结构。

**关键设计原则**：
1. 总时长 = 目标时长（±2秒），单镜头 2-5 秒
2. 同一分镜内最多 1 个动作，禁止空间变化
3. 所有 video_prompt 必须包含比例信息
4. 台词必须融入 video_prompt（角色 + 内容 + 情绪 + 声音）
5. 根据 Step 2 的自动选择结果设置 `generation_mode` 和 `reference_images`

**完整分镜规范**：See [reference/storyboard-spec.md](reference/storyboard-spec.md)
**Prompt 编写与一致性规范**：See [reference/prompt-guide.md](reference/prompt-guide.md)

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

提供选项：确认并执行 / 修改分镜 / 调整时长 / 更换转场 / 取消

### Phase 3 产出

- `storyboard/storyboard.json` — 分镜脚本（包含 generation_mode、reference_images、后端选择）

---

## Phase 4: 执行生成

根据 storyboard.json 执行视频生成。

### Phase 4 执行前检查

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

**降级执行流程**（Path A → Path B）：

1. 告知用户降级后果（角色一致性会降低）
2. 修改 storyboard.json 的生成模式字段
3. 先生成所有分镜图（使用 Gemini）
4. 用分镜图作为首帧调用 Kling img2video

**降级详细规范**：See [reference/backend-guide.md](reference/backend-guide.md) → "API 限制时的降级策略"

### 生成模式强制执行

**必须严格按照 storyboard.json 执行，禁止擅自更改**：

| generation_mode | CLI 参数 |
|----------------|----------|
| `omni-video` | `--backend kling-omni --aspect-ratio {aspect_ratio} --image-list {ref1} {ref2} ...` |
| `img2video` | `--aspect-ratio {aspect_ratio} --image {frame_path}` |
| `text2video` | `--aspect-ratio {aspect_ratio}` |

**重要**：`{aspect_ratio}` 从 `storyboard.json` 的 `aspect_ratio` 字段读取。

**示例（Omni 模式）**：
```bash
# 从 storyboard.json 读取 aspect_ratio（如 "16:9"）
python vico_tools.py video \
  --backend kling-omni \
  --aspect-ratio {aspect_ratio} \
  --prompt "孙悟空挥舞金箍棒..." \
  --image-list materials/personas/sunwukong_ref.png \
  --audio \
  --output generated/videos/scene1_shot1.mp4
```

### API Key 管理

首次调用时检查并请求 API key，用户提供后通过 `export` 设置。

**工具调用详细参数**：See [reference/api-reference.md](reference/api-reference.md)

### 音乐生成

调用 `vico_tools.py music` 必须传 `--creative` 参数。

原因：从 `creative.json` 的 `music` 字段读取 `prompt`（音乐描述）和 `style`（音乐风格），避免使用默认风格。

### Phase 4 产出

- `generated/videos/*.mp4` — 生成的视频片段
- `generated/music/*.mp3` — 生成的背景音乐（如有）
- 更新 `state.json` — 记录生成进度

---

## Phase 5: 剪辑输出

### 视频拼接

调用 `vico_editor.py concat` 必须传 `--storyboard` 参数。

原因：从 `storyboard.json` 读取 `aspect_ratio`，确保输出视频比例正确。

### 音频保护

视频片段可能包含同期声、音效，拼接时不能丢失。无声片段会自动补静音轨，确保音画同步。

### 视频参数校验

拼接前自动检查分辨率/编码/帧率，不一致时自动归一化（1080x1920 / H.264 / 24fps）。

```bash
python ~/.claude/skills/vico-edit/vico_editor.py concat --inputs video1.mp4 video2.mp4 --output final.mp4
```

### 合成流程

1. **拼接** → 按分镜顺序连接（自动归一化）
2. **转场** → 添加镜头间转场效果
3. **调色** → 应用整体调色风格
4. **配乐** → 混合背景音乐
5. **输出** → 生成最终视频

### Phase 5 产出

- `output/final.mp4` — 最终视频

---

## 工具调用速查

```bash
# 环境检查
python ~/.claude/skills/vico-edit/vico_tools.py check

# 视频生成（必须从 storyboard.json 读取 aspect_ratio）
python ~/.claude/skills/vico-edit/vico_tools.py video --prompt <描述> --aspect-ratio {aspect_ratio} --output <输出>

# 音乐（必须传 --creative，从 creative.json 读取 prompt 和 style）
python ~/.claude/skills/vico-edit/vico_tools.py music --creative creative/creative.json --output <输出>
python ~/.claude/skills/vico-edit/vico_tools.py tts --text <文本> --output <输出>
python ~/.claude/skills/vico-edit/vico_tools.py image --prompt <描述> --aspect-ratio {aspect_ratio} --output <输出>

# 剪辑（concat 必须传 --storyboard，从 storyboard.json 读取 aspect_ratio）
python ~/.claude/skills/vico-edit/vico_editor.py concat --inputs <视频列表> --output <输出> --storyboard storyboard/storyboard.json
python ~/.claude/skills/vico-edit/vico_editor.py mix --video <视频> --bgm <音乐> --output <输出>
python ~/.claude/skills/vico-edit/vico_editor.py transition --inputs <v1> <v2> --type <类型> --output <输出>
python ~/.claude/skills/vico-edit/vico_editor.py color --video <视频> --preset <预设> --output <输出>
```

---

## 文件结构

```
~/vico-projects/{project_name}_{timestamp}/
├── state.json           # 项目状态
├── materials/           # 原始素材
│   └── personas/        # 角色参考图（Phase 2 生成）
├── analysis/
│   └── analysis.json    # 素材分析
├── creative/
│   ├── creative.json    # 创意方案
│   └── decision_log.json # 决策记录
├── storyboard/
│   └── storyboard.json  # 分镜脚本
├── generated/
│   ├── videos/          # 生成的视频
│   ├── music/           # 生成的音乐
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
