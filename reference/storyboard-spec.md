# 分镜设计完整规范

## 目录

- Storyboard 结构（Scene / Shot）
- 人物注册与引用规范
- 分镜设计原则与时长限制
- shot_id 命名规则
- T2V/I2V/Omni/Seedance 选择规则
- 首尾帧生成策略
- 台词融入 video_prompt
- Storyboard JSON 格式
- V3-Omni 两阶段结构
- 多镜头模式（Kling / Kling Omni）
- **Seedance 智能切镜模式**
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
| **Reference Tag** | Prompt中的占位符（自动映射） | `<<<image_N>>>` | `<<<image_1>>>`, `<<<image_2>>>` |

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
- **根据项目类型选择生成模式**：
  - 虚构片/短剧、MV短片 → **所有镜头强制分镜图** → `reference2video`（Omni）或 `img2video`（兜底）
  - Vlog/写实类、广告片（有真实素材）→ 用户素材首帧 → `img2video`
- 生成 Prompt 时：
  - Image Prompt 用 `<<<image_1>>>`、`<<<image_2>>>` 引用外貌
  - Video Prompt 用 `Element_XXX` + `<<<image_N>>>` 双重引用

**Phase 4: 执行生成**
- 读取 `character_image_mapping`，按 `image_N` 顺序准备图片文件列表
- 调用 API 时传入对应的 reference images

### 场景字段（Scene）

- `scene_id`：场景编号（如 "scene_1"）
- `scene_name`：场景名称
- `duration`：场景总时长 = 下属所有分镜时长之和
- `narrative_goal`：主叙事目标
- `spatial_setting`：空间设定（**需精确化，见下方规范**）
- `time_state`：时间状态（**需精确化，见下方规范**）
- `visual_style`：视觉母风格
- `shots[]`：分镜列表

#### 字段精确化规范（一致性检测依赖）

**time_state 精确化要求**：

| 精确程度 | 示例 | 是否合格 |
|---------|------|---------|
| **精确** | "下午2-4点，柔和阳光"、"黄昏前一小时，golden hour暖光" | ✅ 合格 |
| **笼统** | "白天"、"下午"、"白天" | ❌ 不合格（无法锁定光照） |

**必须包含**：
- 时间段：如"下午2-4点"、"黄昏前一小时"
- 光照特征：如"柔和阳光"、"golden hour暖光"

**spatial_setting 精确化要求**：

| 精确程度 | 示例 | 是否合格 |
|---------|------|---------|
| **精确** | "垂杨柳（枝条细长下垂），石板路（青灰色），水榭亭台（飞檐翘角）" | ✅ 合格 |
| **笼统** | "园林"、"树下"、"花园" | ❌ 不合格（无法锁定元素样式） |

**必须包含**：
- 关键元素样式：如"垂杨柳（枝条细长下垂）"
- 建筑特征：如"水榭亭台（飞檐翘角）"

#### 人物妆造锁定字段（elements.characters）

```json
{
  "elements": {
    "characters": [
      {
        "element_id": "Element_LinDaiyu",
        "name": "林黛玉",
        "name_en": "LinDaiyu",
        "reference_images": ["materials/personas/lindaiyu_three_view.png"],
        "visual_description": "古典美女...",
        
        // 新增锁定字段（一致性检测使用）
        "locked_costume": "淡青绿色广袖长袍，米白色交领中衣，墨绿色宽腰封",
        "locked_hairstyle": "古典高髻，两侧垂鬟",
        "locked_makeup": "细长柳叶眉，淡粉唇色，白皙底妆",
        "costume_scope": "scene_1, scene_2"  // 作用范围（可选）
      }
    ]
  }
}
```

**作用范围说明**：
- `costume_scope` 指定人物妆造在哪些 scenes 内保持一致
- 留空表示全局一致（所有 scenes）
- 多个 scenes 用逗号分隔
- 当需要换装时，在新的 scene 开始时更新锁定字段并设置新的 scope

### 分镜字段（Shot）

- `shot_id`：分镜编号（格式见下文命名规则）
- `duration`：时长（单位：秒，范围：2-5秒）
- `shot_type`：景别类型，可选：establishing（全景）/ dialogue（对话）/ action（动作）/ closeup（特写）/ insert（插入镜头）
- `description`：简要描述
- `generation_mode`：生成模式，可选：text2video / img2video / omni-video / seedance-video
- `multi_shot`：是否为多镜头模式，true / false（与 shot_type 独立）
- `generation_backend`：后端选择，可选：kling / kling-omni / vidu / seedance
- `video_prompt`：视频生成提示词
- `image_prompt`：图片生成提示词（img2video/omni-video 时使用）
- `frame_path`：分镜图输出路径（Kling-Omni shot-level 必需），如 `generated/frames/{shot_id}_frame.png`
- `frame_strategy`：首尾帧策略，可选：none / first_frame_only / first_and_last_frame
  - **注意**：Omni 模式（`generation_mode: omni-video`）不使用此字段，因为 Omni 使用 `reference_images` 而非首帧控制
- `reference_images`：参考图路径列表（omni-video 必需，img2video 可选）
  - Omni 模式：包含分镜图 + 角色参考图
  - img2video 模式：可选，用于 Gemini 生成分镜图时的参考
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
| 多镜头模式 | `scene1_shot2to4_multi` | 合并分镜，范围用 `to` 连接，带 `_multi` 后缀 |

**多镜头命名规范**：
- 合并 shot2、shot3、shot4 → `scene1_shot2to4_multi`
- 合并 shot1 到 shot5 → `scene1_shot1to5_multi`
- **不要**使用下划线连接：`scene1_shot2_shot3_shot4_multi` ❌

---

## T2V/I2V/Ref2V 选择规则

**核心原则**：
- **虚构片不使用 text2video**
- **同一项目使用同一模型**

### 项目类型判断

| 用户意图关键词 | 项目类型 |
|---------------|---------|
| "短剧"、"剧情"、"故事" | 虚构片/短剧 |
| "vlog"、"旅行记录"、"生活记录" | Vlog/写实类 |
| "广告"、"宣传片"、"产品展示" | 广告片/宣传片 |
| "MV"、"音乐视频" | MV短片 |

### 自动选择决策树

**虚构片/短剧、MV短片**：
```
虚构内容 → 所有镜头强制先生成分镜图
           ├── 优先 → Seedance（智能切镜 + 多参考图）
           │         └── image_urls: [分镜图, 角色参考图...]
           │         └── 时间分段 prompt 自动触发 multi-shot
           │
           ├── 兜底1 → Kling-3.0-Omni（reference2video）
           │           └── image_list: [分镜图, 角色参考图]
           │
           └── 兜底2 → Kling-3.0 或 Vidu Q3 Pro（img2video）
                      └── --image: 分镜图首帧
```

**Vlog/写实类、广告片/宣传片（有真实素材）**：
```
真实素材 → 需要首帧控制
           └── Kling-3.0 或 Vidu Q3 Pro（img2video）
               └── --image: 用户素材首帧
```

### 选择规则表

| 项目类型 | 素材情况 | 生成模式 | 后端 | 说明 |
|---------|---------|---------|------|------|
| 虚构片/短剧 | 有/无角色参考图 | `seedance-video` | `seedance` | **优先**：智能切镜 + 多参考图 |
| 虚构片/短剧 | Seedance 不可用 | `omni-video` | `kling-omni` | 兜底：强制分镜图，Omni 保证一致性 |
| MV短片 | 有/无角色参考图 | `seedance-video` | `seedance` | **优先**：音乐驱动 + 智能切镜 |
| MV短片 | Seedance 不可用 | `omni-video` | `kling-omni` | 兜底：强制分镜图 |
| Vlog/写实类 | 用户真实素材 | `img2video` | `kling` 或 `vidu` | 用户素材首帧控制 |
| 广告片/宣传片 | 有真实素材 | `img2video` | `kling` 或 `vidu` | 产品/企业素材首帧 |
| 广告片/宣传片 | 无真实素材 | `seedance-video` | `seedance` | **优先**：智能切镜，长镜头 |
| 广告片/宣传片 | 无真实素材 + Seedance 不可用 | `omni-video` | `kling-omni` | 兜底：纯虚构展示 |

### 模型与生成路径支持

| 模型 | seedance-video | reference2video | img2video | text2video |
|------|----------------|-----------------|-----------|------------|
| **Seedance** | ✅ 支持 | ✅ 支持（image_urls） | ❌ 不支持首帧控制 | ✅ 支持 |
| **Kling-3.0-Omni** | ❌ 不支持 | ✅ 支持 | ❌ 不支持 | ✅ 支持 |
| **Kling-3.0** | ❌ 不支持 | ❌ 不支持 | ✅ 支持 | ✅ 支持 |
| **Vidu Q3 Pro** | ❌ 不支持 | ❌ 不支持 | ✅ 支持 | ✅ 支持 |

**关键**：
- **Seedance 不支持首帧精确控制**，分镜图作为参考而非首帧
- **Kling-3.0-Omni 不支持 img2video（首帧控制）**，需要首帧控制时不能用 Omni
- **Seedance 时间分段 = 自动 multi-shot**，无需额外参数

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

---

## 旁白分段规划（narration_segments）

**触发条件**：Phase 2 确认需要「AI生成旁白」后，Phase 3 生成分镜时必须规划旁白分段。

### 全局配置（根级别）

```json
{
  "narration_config": {
    "enabled": true,
    "voice_style": "温柔女声，语速适中偏慢，情感饱满"
  },
  "narration_segments": [
    {
      "segment_id": "narr_1",
      "time_range": "0-3s",
      "target_shot": "scene1_shot1",
      "text": "这是一个宁静的下午，阳光透过落地窗洒进咖啡馆..."
    },
    {
      "segment_id": "narr_2",
      "time_range": "8-11s",
      "target_shot": "scene1_shot3",
      "text": "她坐在窗边，望着窗外的风景，思绪飘向远方..."
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `narration_config.enabled` | boolean | 是否启用旁白 |
| `narration_config.voice_style` | string | 全局统一的旁白风格（一条视频内统一） |
| `narration_segments` | array | 旁白分段列表 |
| `segment_id` | string | 分段编号（格式：`narr_1`, `narr_2`...） |
| `time_range` | string | 整体时间轴位置（格式：`0-3s`, `8-11s`，从视频起点算） |
| `target_shot` | string | 对应的镜头 ID |
| `text` | string | 该分段的旁白文案 |

### 规划原则

1. **时间轴连续性**：`time_range` 从视频起点（0秒）开始计算，不是镜头内时间
2. **分段长度**：每段旁白控制在 2-5 秒可说完的长度（约 30-50 字）
3. **避免冲突**：旁白时间范围不要与角色台词（同期声）重叠
4. **镜头对应**：每个 segment 必须对应一个 target_shot
5. **voice_style 统一**：一条视频内使用同一种旁白风格

### 旁白文案分段技巧

**不要这样**（一大坨）：
```json
{
  "text": "这是一个宁静的下午，阳光透过落地窗洒进咖啡馆，她坐在窗边，望着窗外的风景，思绪飘向远方，回忆起那个特别的夏天。"
}
```

**应该这样**（按镜头分段）：
```json
{
  "narration_segments": [
    {"segment_id": "narr_1", "time_range": "0-3s", "target_shot": "scene1_shot1", "text": "这是一个宁静的下午，阳光透过落地窗洒进咖啡馆..."},
    {"segment_id": "narr_2", "time_range": "8-11s", "target_shot": "scene1_shot3", "text": "她坐在窗边，望着窗外的风景..."},
    {"segment_id": "narr_3", "time_range": "15-18s", "target_shot": "scene2_shot1", "text": "思绪飘向远方，回忆起那个特别的夏天..."}
  ]
}
```

### 与 creative.json 的关联

Phase 2 确认旁白需求后，`creative.json` 记录：
```json
{
  "narration": {
    "type": "ai_generated",
    "voice_style": "温柔女声",
    "full_text": "用户提供的完整旁白文案（如有多段）"
  }
}
```

Phase 3 生成分镜时：
- 读取 `creative.narration.type`
- 若为 `ai_generated`，则规划 `narration_segments`
- 将 `creative.narration.full_text` 按镜头时间点分段
- 将 `creative.narration.voice_style` 写入 `narration_config.voice_style`

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

**character_image_mapping**: 自动生成的映射表（Phase 3），**Storyboard 全局字段**
- Key: `element_id` (如 `Element_Chuyue`)
- Value: `image_N` tag (如 `image_1`)
- 映射规则：按 characters 数组顺序分配 image_1, image_2...
- 注意：此字段放在 storyboard 根级别，不在 shot 内部重复

### Kling Omni 模式示例

```json
{
  "shot_id": "scene2_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "小美（<<<image_1>>>）戴着耳机，在赛车模拟器前全神贯注。竖屏9:16构图。",
  "reference_images": ["materials/personas/xiaomei_ref.jpg"],
  "frame_strategy": "none",
  "image_prompt": "Cinematic realistic start frame...（可选，用于分镜图生成）",
  "multi_shot": false,
  "audio": {
    "enabled": true,
    "dialogue": null,
    "no_bgm": true
  }
}
```

**注意**：Omni 模式使用 `reference_images` 作为参考图，不使用 `frame_strategy` 首帧控制。`frame_strategy` 应设为 `none`。如果需要生成分镜图，使用 `image_prompt` 单独记录分镜图 prompt。

---

## V3-Omni 两阶段结构（推荐）

针对 Kling V3-Omni 的**分镜图 + 视频**两阶段生成流程，推荐采用分层数据结构。

### 与标准结构的关系

**V3-Omni 三层结构是标准 Shot 结构的扩展**，而非替代：
- 标准结构字段（`shot_id`, `duration`, `generation_mode`, `generation_backend` 等）仍然保留
- 三层结构将 `image_prompt` 和 `video_prompt` 展开为更详细的结构化字段
- `character_image_mapping` 始终放在 **Storyboard 全局**，不在 shot 内部重复

### 字段映射表

| 标准结构字段 | V3-Omni 结构对应 | 说明 |
|-------------|-----------------|------|
| `image_prompt` | `frame_generation.prompt` | 分镜图生成 prompt |
| `video_prompt` | `video_generation.prompt` | 视频生成 prompt |
| `reference_images` | `frame_generation` 生成后自动加入 | 分镜图输出 + 角色参考图 |
| `frame_strategy` | 始终为 `"none"` | Omni 不使用首帧控制 |

### 设计理念

**分镜图（Storyboard Frame）**：不只是首帧控制，还控制整体视觉（场景、画风、灯光、氛围、色彩、妆造）

**视频生成**：引用分镜图构图，叠加动作和人物参考

### Schema 结构

```json
{
  "shot_id": "scene1_shot1",
  "duration": 7,
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "multi_shot": false,
  "reference_images": [],

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

**注意**：`character_image_mapping` 始终放在 **Storyboard 全局**，不在 shot 内部重复。V3-Omni 结构使用 `frame_generation.character_refs` 引用角色。

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

---

## fallback_plan 字段（降级预案）

在 Phase 3 生成分镜时，推荐为每个镜头预留降级方案，避免临时编写 `image_prompt`。

### 字段结构

```json
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "...",
  "reference_images": ["materials/personas/xiaomei_ref.jpg"],
  "frame_strategy": "none",

  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic realistic start frame.\nScene: ...\nLighting: ...\nCharacter: Referencing <<<image_1>>> appearance...\nStyle: ...",
    "frame_strategy": "first_frame_only",
    "frame_output": "generated/frames/{shot_id}_frame.png",
    "reason": "Omni API 不可用时降级使用"
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `mode` | string | 降级后的生成模式：`img2video` 或 `text2video` |
| `backend` | string | 降级后的后端：`kling` 或 `vidu` |
| `image_prompt` | string | 生成分镜图的完整 prompt（降级时必须） |
| `frame_strategy` | string | 降级后的首帧策略：`first_frame_only` |
| `frame_output` | string | 分镜图输出路径模板 |
| `reason` | string | 降级原因说明 |

### 降级时的处理流程

当需要降级时：

1. 读取镜头的 `fallback_plan` 字段
2. 将以下字段从 `fallback_plan` 复制到镜头主字段：
   - `generation_mode` ← `fallback_plan.mode`
   - `generation_backend` ← `fallback_plan.backend`
   - `frame_strategy` ← `fallback_plan.frame_strategy`
   - `image_prompt` ← `fallback_plan.image_prompt`
3. 清空或调整 `reference_images`（img2video 不需要角色参考图）
4. 执行降级后的生成流程

### 示例：降级后的镜头

```json
// 降级前
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "小美（<<<image_1>>>）在咖啡馆窗边...",
  "reference_images": ["materials/personas/xiaomei_ref.jpg"],
  "frame_strategy": "none",
  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic start frame. 25岁亚洲女性...",
    "frame_strategy": "first_frame_only"
  }
}

// 降级后（已复制 fallback_plan 字段）
{
  "shot_id": "scene1_shot1",
  "generation_mode": "img2video",
  "generation_backend": "kling",
  "video_prompt": "小美在咖啡馆窗边...",  // 移除 <<<image_1>>> 引用
  "reference_images": [],
  "frame_strategy": "first_frame_only",
  "image_prompt": "Cinematic start frame. 25岁亚洲女性...",
  "frame_path": "generated/frames/scene1_shot1_frame.png",
  "fallback_plan": { ... }  // 保留原始预案，可再次降级
}
```

### 不需要 fallback_plan 的场景

- 纯 `text2video` 镜头（无需参考图，降级无意义）
- 用户明确表示不接受降级
- 简单原型，不需要保证角色一致性

---

## Seedance 智能切镜模式

**核心特点**：时间分段 prompt 自动触发 multi-shot，执行阶段合并同 scene 的多个 shots 为一个 API 调用。

**✅ 时长支持：4-15s 任意整数**

在 **Phase 3 分镜设计阶段**，选择 Seedance 后端时，scene 总时长可以是 **4 到 15 秒之间的任意整数**（如 6s、8s、12s 等，不再限制为 5/10/15）。

### 设计阶段时长规划（Phase 3）

**Seedance 后端时长设计规则**：

| Scene 总时长 | ✅ 支持 |
|-------------|--------|
| 4-15s 任意整数 | ✓ |

**设计流程**：
```
选择 Seedance → 确定 scene 总时长（4-15s 范围内任意整数）→ 分配 shots 时长
```

**示例**：
- 目标 15s scene → shots: 3s + 3s + 4s + 5s = 15s ✓
- 目标 10s scene → shots: 3s + 3s + 4s = 10s ✓
- 目标 8s scene → shots: 3s + 5s = 8s ✓（新支持！）
- 目标 18s scene → ✗ 超出范围，需拆分为两个 scene

### 设计原则

**Shot 结构保持不变**：Seedance 只在执行阶段合并，不改变 storyboard 的 `scenes → shots` 结构。

| 模型 | 执行方式 |
|------|---------|
| Kling/Vidu/Omni | 每个 shot 单独调用 API |
| **Seedance** | 同 scene 多 shots 合并为一个 API 调用（时间分段 prompt） |

### Scene → 视频片段划分规则

| Scene 时长 | Shot 数量 | 视频片段规划 |
|-----------|----------|-------------|
| ≤15s | 任意数量（如 3-5 个 shot） | **单个视频片段**，时间分段覆盖所有 shot |
| 16-30s | 较多（如 6-10 个 shot） | **2-3 个视频片段**，分段覆盖（如 15s + 15s） |
| >30s | 很多（如 >10 个 shot） | **3+ 个视频片段**，分段覆盖 |
| Scene 切换 | - | **各自独立视频片段**，不跨 Scene 合并 |

### 执行阶段处理流程

**示例**：Scene 1 包含 4 个 shots（总时长 15s）

```json
{
  "scene_id": "scene_1",
  "shots": [
    {"shot_id": "scene1_shot1", "duration": 3, "description": "摘苹果"},
    {"shot_id": "scene1_shot2", "duration": 3, "description": "投入雪克杯"},
    {"shot_id": "scene1_shot3", "duration": 4, "description": "成品特写"},
    {"shot_id": "scene1_shot4", "duration": 5, "description": "举杯展示"}
  ]
}
```

**Seedance 执行逻辑**：

1. 识别 `generation_backend = "seedance"`
2. 将 scene_1 的 4 个 shots（总 15s）合并为一个 API 调用
3. 生成分镜图（每个视频片段一张）
4. 生成时间分段 prompt：
   ```
   0-3s：摘苹果...；
   3-6s：投入雪克杯...；
   6-10s：成品特写...；
   10-15s：举杯展示...；
   ```
5. 调用 Seedance API

### 时间分段 Prompt 格式

```
Referencing the {segment_id}_frame composition for scene layout and character positioning.

@image1（角色参考图），[视角设定] [主题/风格]；

整体：[镜头整体动作概述]

分段动作（{duration}s）：
0-Xs：[场景] + [动作] + [运镜] + [节奏] + [音效/台词]；
X-Xs：[切镜] + [场景] + [动作] + [运镜] + [节奏] + [音效/台词]；
...

保持{比例}构图，不破坏画面比例
{BGM约束}
```

### image_urls 顺序约定

| index | 用途 | 引用方式 |
|-------|------|---------|
| `image_urls[0]` | 分镜图 | `Referencing the {segment_id}_frame composition...` |
| `image_urls[1]` | 角色参考图 1 | `@image1` |
| `image_urls[2]` | 角色参考图 2 | `@image2` |

### Seedance Storyboard 标注示例

```json
{
  "shot_id": "scene1_shot1",
  "duration": 3,
  "generation_mode": "seedance-video",
  "generation_backend": "seedance",
  "video_prompt": "你的手摘下一颗带晨露的阿克苏红苹果，固定镜头，节奏平稳，轻脆的苹果碰撞声",
  "reference_images": [
    "generated/frames/scene1_frame.png",
    "materials/personas/xiaomei_ref.jpg"
  ],
  "frame_strategy": "none",
  "seedance_merge_info": {
    "merged_shots": ["scene1_shot1", "scene1_shot2", "scene1_shot3", "scene1_shot4"],
    "total_duration": 15,
    "segment_index": 0
  }
}
```

### 限制与注意事项

| 限制 | 说明 |
|------|------|
| 时长范围 4-15s | 任意整数，不再限制为 5/10/15 |
| 最高 720p | 需要 1080p 时用 Kling/Vidu |
| 无首帧精确控制 | 分镜图是参考，不是首帧 |
| 图片引用语法 | 使用 `@imageN`（非 `<<<image_N>>>`） |
