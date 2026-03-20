# 分镜设计完整规范

## 目录

- Storyboard 结构（Scene / Shot）
- 人物注册与引用规范
- 分镜设计原则与时长限制
- shot_id 命名规则
- T2V/I2V/Omni 选择规则
- 首尾帧生成策略
- 台词融入 video_prompt
- Storyboard JSON 格式
- V3-Omni 两阶段结构
- 多镜头模式（Kling / Kling Omni）
- Review 检查机制
- 展示给用户确认

---

## Storyboard 结构

采用 **场景-分镜两层结构**：`scenes[] → shots[]`

- **场景 (Scene)**：语义+视觉+时空相对稳定的叙事单元，时长通常 10-30 秒
- **分镜 (Shot)**：最小视频生成单元，时长 2-5 秒

## 人物注册与引用规范

### 三层命名体系

| 层级 | 用途 | 命名规范 | 示例 |
|------|------|---------|------|
| **Element ID** | 技术ID，用于JSON引用、Prompt中的角色标识 | `Element_` + 英文名/拼音 | `Element_Chuyue`, `Element_Xiaomei` |
| **Display Name** | 显示名称，用于用户交互、中文描述 | 中文名 | `初月`, `小美` |
| **Reference Tag** | Prompt中的占位符（自动映射） | `image_N` | `image_1`, `image_2` |

### Workflow 中的使用流程

**Phase 1: 人物识别**
- 用户确认人物身份后，生成 `element_id`（自动：Element_ + 拼音/英文名）
- 写入 `storyboard.json` 的 `elements.characters`
- **注意**：Phase 1 只处理用户已上传的参考图，未上传的 `reference_images` 留空，由 Phase 2 补充

**Phase 2: 角色参考图收集（关键）**
- 检查 `reference_images` 为空的角色
- 询问用户：AI生成 / 上传参考图 / 接受纯文字（警告）
- 更新 `personas.json` 和 `storyboard.json` 的 `reference_images`

**Phase 3: 分镜设计（LLM 自动生成）**
- LLM 根据 `elements.characters` 生成分镜
- 自动分配 `character_image_mapping`（按 characters 数组顺序：image_1, image_2...）
- 根据 `reference_images` 是否存在，自动选择 `generation_mode`：
  - 有参考图 + 多镜头 → `omni-video`
  - 有参考图 + 单镜头 → `img2video`
  - 无参考图 → `text2video`
- 生成 Prompt 时：
  - Image Prompt 用 `image_1`、`image_2` 引用外貌
  - Video Prompt 用 `Element_XXX` + `image_N` 双重引用

**Phase 4: 执行生成**
- 读取 `character_image_mapping`，按 `image_N` 顺序准备图片文件列表
- 调用 API 时传入对应的 reference images

### 场景字段（Scene）

- `scene_id`：场景编号（如 "scene_1"）
- `scene_name`：场景名称
- `duration`：场景总时长 = 下属所有分镜时长之和
- `narrative_goal`：主叙事目标
- `spatial_setting`：空间设定
- `time_state`：时间状态
- `visual_style`：视觉母风格
- `shots[]`：分镜列表

### 分镜字段（Shot）

- `shot_id`：分镜编号（格式见下文命名规则）
- `duration`：时长（2-5秒）
- `shot_type`：establishing / dialogue / action / closeup / multi_shot
- `description`：简要描述
- `generation_mode`：text2video / img2video / omni-video
- `multi_shot`：true / false
- `generation_backend`：kling / kling-omni / vidu
- `video_prompt`：视频生成提示词
- `image_prompt`：图片生成提示词（img2video/omni-video 时使用）
- `frame_strategy`：none / first_frame_only / first_and_last_frame
- `reference_images`：参考图路径列表（omni-video 必需，img2video 可选）
- `dialogue`：台词信息（结构化）
- `transition`：转场效果
- `audio`：音频配置（enabled, no_bgm, dialogue）

---

## 分镜设计原则

1. **时长分配**：总时长 = 目标时长（±2秒）
2. **节奏变化**：避免所有镜头时长相同
3. **景别变化**：连续镜头应有景别差异
4. **转场选择**：根据情绪选择合适转场
5. **单一动作原则**：同一分镜内最多 1 个动作
6. **空间不变原则**：禁止在 shot 内发生空间环境变化
7. **描述具体原则**：禁止抽象动作描述，用具体动作替代

### 时长限制

- 普通镜头：2-3 秒
- 复杂运动镜头：≤2 秒
- 静态情绪镜头：≤5 秒

---

## shot_id 命名规则

格式：`scene{场景号}_shot{分镜号}`

| 类型 | 示例 | 说明 |
|------|------|------|
| 单分镜 | `scene1_shot1`、`scene2_shot1` | 标准命名 |
| 多镜头模式 | `scene1_shot2to4_multi` | 合并分镜，带 `_multi` 后缀 |

---

## T2V/I2V/Ref2V 选择规则

**自动选择决策树**（Phase 3 执行）：

```
镜头是否包含人物？
├── 是 → 人物是否有 reference_images？
│        ├── 是 → 角色在多镜头中出现？
│        │        ├── 是 → omni-video（Kling Omni）
│        │        └── 否 → img2video（Kling）
│        └── 否 → text2video（Kling，Phase 2 已警告）
└── 否 → text2video（Kling）
```

**选择规则表**：

| 条件 | 生成模式 | 后端 | 说明 |
|------|---------|------|------|
| 有参考图 + 多镜头人物 | `omni-video` | `kling-omni` | 保证跨镜头角色一致性 |
| 有参考图 + 单镜头人物 | `img2video` | `kling` | 首帧精确控制 |
| 无参考图 + 人物 | `text2video` | `kling` | Phase 2 已警告 |
| 纯场景无人物 | `text2video` | `kling` | 默认 |

**旧的简化规则**（供参考）：

| 镜头类型 | 生成模式 | 首尾帧策略 |
|---------|---------|-----------|
| 场景建立镜头（无人物） | text2video | none |
| 人物介绍/对话/动作（简单） | img2video | first_frame_only |
| 人物动作（复杂） | img2video | first_and_last_frame |
| 风景/物品特写 | text2video 或 img2video | none 或 first_frame_only |

---

## 首尾帧生成策略

| frame_strategy | 说明 | 执行方式 |
|---|------|---------|
| `none` | 无需首尾帧 | 直接调用文生视频 API |
| `first_frame_only` | 仅首帧 | 生成首帧图 → image2video API |
| `first_and_last_frame` | 首尾帧 | 生成首帧和尾帧 → Kling API（`image_tail` 参数） |

首尾帧字段扩展（`first_and_last_frame` 时）：

```json
{
  "frame_strategy": "first_and_last_frame",
  "image_prompt": "首帧描述",
  "last_frame_prompt": "尾帧描述"
}
```

---

## 台词融入 video_prompt

当镜头包含台词时，**必须在 video_prompt 中完整描述**：角色（含外貌）、台词内容（引号包裹）、表情/情绪、声音特质和语速。

```json
{
  "shot_id": "scene1_shot5",
  "video_prompt": "小美（25岁亚洲女性，黑色长直发）抬头看向服务生，温柔微笑着说：'这里真的很安静，我很喜欢。' 声音清脆悦耳，语速适中偏慢。保持竖屏9:16构图。",
  "dialogue": {
    "speaker": "小美",
    "content": "这里真的很安静，我很喜欢。",
    "emotion": "温柔、愉悦",
    "voice_type": "清脆女声"
  },
  "audio": {
    "enabled": true,
    "dialogue": {
      "speaker": "小美",
      "text": "这里真的很安静，我很喜欢。",
      "emotion": "温柔、愉悦"
    },
    "no_bgm": true
  }
}
```

### audio 字段说明

`audio` 字段采用对象格式，包含以下子字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | boolean | 是否生成音频（包含环境音 + 台词），默认 true |
| `dialogue` | object/null | 台词信息，null 表示无台词 |
| `dialogue.speaker` | string | 说话角色 |
| `dialogue.text` | string | 台词内容 |
| `dialogue.emotion` | string | 情绪/语气 |
| `no_bgm` | boolean | 是否在 prompt 中明确 "No background music" |

### BGM 决策逻辑

在 creative.json 中定义 `bgm` 字段：

```json
{
  "bgm": {
    "type": "ai_generated",
    "style": "史诗感、赛车主题"
  }
}
```

`bgm.type` 取值：
- `"ai_generated"` → 所有镜头 `audio.no_bgm = true`（BGM 由 Suno 后期合成）
- `"user_provided"` → 所有镜头 `audio.no_bgm = true`（BGM 由用户提供）
- `"none"` → 所有镜头 `audio.no_bgm = false`（视频模型自由决定）

`dialogue` 字段用途：TTS 生成、字幕提取、用户快速查看。

**TTS 旁白仅用于**：片头/片尾解说、不需要角色开口的场景描述、情感烘托旁白。**能收同期声的镜头不要用 TTS！**

---

## Storyboard JSON 格式

```json
{
  "project_name": "项目名称",
  "target_duration": 60,
  "aspect_ratio": "9:16",
  "elements": {
    "characters": [
      {
        "element_id": "Element_Chuyue",
        "name": "初月",
        "name_en": "Chuyue",
        "reference_images": ["/path/to/ref.jpg"],
        "visual_description": "25岁亚洲女性，黑色长直发及腰，瓜子脸..."
      },
      {
        "element_id": "Element_Jiazhi",
        "name": "嘉志",
        "name_en": "Jiazhi",
        "reference_images": ["/path/to/ref2.jpg"],
        "visual_description": "成熟男性，短发，深邃眼神..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_Chuyue": "image_1",
    "Element_Jiazhi": "image_2"
  },
  "scenes": [
    {
      "scene_id": "scene_1",
      "scene_name": "开场 - 咖啡馆相遇",
      "duration": 18,
      "narrative_goal": "展示女主角在咖啡馆的日常",
      "spatial_setting": "温馨的城市咖啡馆",
      "time_state": "下午3点",
      "visual_style": "温暖色调，电影感",
      "shots": [
        {
          "shot_id": "scene1_shot1",
          "duration": 3,
          "shot_type": "establishing",
          "description": "咖啡馆全景",
          "generation_mode": "text2video",
          "generation_backend": "kling",
          "video_prompt": "温馨的城市咖啡馆内部全景，午后阳光透过落地窗洒进来，镜头缓慢推近。保持竖屏9:16构图。No background music. Natural ambient sound only.",
          "frame_strategy": "none",
          "multi_shot": false,
          "dialogue": null,
          "transition": "fade_in",
          "audio": {
            "enabled": true,
            "dialogue": null,
            "no_bgm": true
          }
        }
      ]
    }
  ],
  "props": [],
  "decision_log": {}
}
```

### 字段说明

**elements.characters**: 人物注册表，Phase 1 识别后写入
- `element_id`: 技术ID，格式 `Element_` + 英文名/拼音
- `name`: 中文显示名
- `name_en`: 英文名
- `reference_images`: 参考图路径列表
- `visual_description`: 视觉特征描述

**character_image_mapping**: 自动生成的映射表（Phase 3）
- Key: `element_id` (如 `Element_Chuyue`)
- Value: `image_N` tag (如 `image_1`)
- 映射规则：按 characters 数组顺序分配 image_1, image_2...

### Kling Omni 模式示例

```json
{
  "shot_id": "scene2_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "小美（<<<image_1>>>）戴着耳机，在赛车模拟器前全神贯注。竖屏9:16构图。",
  "reference_images": ["materials/personas/xiaomei_ref.jpg"],
  "frame_strategy": "first_frame_only",
  "image_prompt": "Cinematic realistic start frame...",
  "multi_shot": false,
  "audio": {
    "enabled": true,
    "dialogue": null,
    "no_bgm": true
  }
}
```

---

## V3-Omni 两阶段结构（推荐）

针对 Kling V3-Omni 的**分镜图 + 视频**两阶段生成流程，推荐采用分层数据结构：

### 设计理念

**分镜图（Storyboard Frame）**：不只是首帧控制，还控制整体视觉（场景、画风、灯光、氛围、色彩、妆造）

**视频生成**：引用分镜图构图，叠加动作和人物参考

### Schema 结构

```json
{
  "shot_id": "scene1_shot1",
  "duration": 7,
  "workflow_version": "v3_omni_v1",
  "character_image_mapping": {
    "Element_Chuyue": "image_1",
    "Element_Jiazhi": "image_2",
    "Element_Tianyu": "image_3"
  },

  "storyboard": {
    "chinese_description": "连续动作与对话 (约7s)全景。初月手忙脚乱退到门外...",
    "shot_scale": "全景",
    "location": "男洗手间门口过渡区",
    "dialogue_segments": [
      {"time": "0-2s", "speaker": "初月", "line": "可以，我承认...", "emotion": "尴尬赔笑"},
      {"time": "2-4s", "speaker": "天宇", "line": "那你别一脸见鬼。", "emotion": "flat"}
    ],
    "transition": "cut"
  },

  "frame_generation": {
    "output_key": "scene1_shot1_frame",
    "prompt": "Cinematic realistic start frame...",
    "character_refs": ["Element_Chuyue", "Element_Jiazhi", "Element_Tianyu"],
    "scene": "男洗手间门口，白色瓷砖...",
    "lighting": "冷白色荧光灯",
    "camera": {"shot_scale": "wide", "angle": "eye-level"},
    "style": "cinematic realistic, cool blue-white"
  },

  "video_generation": {
    "backend": "kling_v3_omni",
    "frame_reference": "scene1_shot1_frame",
    "prompt": "Referencing scene1_shot1_frame composition...",
    "motion_overall": "Chuyue fumbles backward...",
    "motion_segments": [
      {"time": "0-2s", "action": "steps back past threshold...", "character": "Element_Chuyue"},
      {"time": "2-5s", "action": "three-way dialogue exchange", "lip_sync": true}
    ],
    "camera_movement": "static wide shot",
    "sound_effects": "shuffling footsteps on tile"
  }
}
```

### 字段说明

**character_image_mapping**: 角色到参考图占位符的映射
- Key: Element ID (如 `Element_Chuyue`)
- Value: Reference Tag (如 `image_1`)
- 用于自动替换 Prompt 中的占位符

**storyboard 层**（中文，给人看）
- `chinese_description`: 剧情描述
- `shot_scale`: 景别（全景/中景/特写等）
- `location`: 场景位置
- `dialogue_segments`: 对白时间轴
- `transition`: 转场效果

**frame_generation 层**（生成分镜图）
- `output_key`: 输出文件名
- `prompt`: 完整的 Image Prompt
- `character_refs`: 引用的角色元素
- `scene`: 场景描述
- `lighting`: 灯光描述
- `camera`: 相机参数（shot_scale, angle, lens）
- `style`: 视觉风格

**video_generation 层**（生成视频）
- `frame_reference`: 引用的分镜图 output_key
- `prompt`: 完整的 Video Prompt
- `motion_overall`: 整体动作描述
- `motion_segments`: 分段动作（带时间轴）
- `camera_movement`: 镜头运动
- `sound_effects`: 声音设计

---

## 多镜头模式（Kling / Kling Omni）

Kling 和 Kling Omni 均支持多镜头一镜到底。

### 配置字段

```json
{
  "shot_id": "scene1_shot2to4_multi",
  "duration": 10,
  "multi_shot": true,
  "multi_shot_config": {
    "mode": "customize",
    "shots": [
      {"shot_id": "scene1_shot2", "duration": 3, "prompt": "镜头1描述"},
      {"shot_id": "scene1_shot3", "duration": 4, "prompt": "镜头2描述"},
      {"shot_id": "scene1_shot4", "duration": 3, "prompt": "镜头3描述"}
    ]
  }
}
```

### 两种模式

- **intelligence**：AI 自动分镜，适合简单叙事
- **customize**（推荐）：精确控制每个镜头内容和时长

### 多镜头规则

- 总时长 3-15s，每个镜头至少 1s
- 所有镜头时长之和 = 视频总时长

| 场景 | 推荐模式 |
|------|---------|
| 剧情视频（故事、广告） | multi_shot + customize |
| 简单叙事 | multi_shot + intelligence |
| 素材混剪（vlog、展示） | 单镜头逐个生成 |
| 简单短视频（<10s） | 单镜头 text2video |

---

## Review 检查机制

生成 storyboard 后，必须检查以下项目：

**1. 结构完整性**
- 总时长匹配目标时长（±2秒）
- 场景时长 = 下属分镜时长之和

**2. 分镜规则**
- 每个分镜时长 2-5 秒
- 无多动作分镜、无分镜内空间变化

**3. Prompt 规范**
- 所有 video_prompt 包含比例信息
- 台词已融入 video_prompt
- 无抽象动作描述

**4. 技术选择**
- T2V/I2V 选择合理
- 后端选择匹配需求
- 首尾帧策略正确

---

## 展示给用户确认（强制步骤）

**必须在用户明确确认后，才能进入 Phase 4！**

确认时展示每个镜头的：场景信息、生成模式、后端、video_prompt、image_prompt（如有）、台词、转场、时长。

用户可选择：确认并执行 / 修改分镜 / 调整时长 / 更换转场 / 取消。
