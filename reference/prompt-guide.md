# Prompt 编写与一致性规范

## 目录

1. [基础概念] — 人物注册命名标准、数据源、引用方式
2. [图片生成 Prompt] — 分镜图（Gemini）
3. [Kling/Vidu 视频生成 Prompt] — 通用结构（Kling-v3/Vidu）
4. [Kling-Omni 两阶段流程 Prompt] — 分镜图 + 视频生成Prompt (Kling-v3-Omni)
5. [一致性规范](#一致性规范) — 人物、道具跨镜头一致性
6. [比例约束](#比例约束) — 画面比例强制要求
7. [台词与音频](#台词与音频) — 同期声、TTS、BGM 约束
8. [附录：模板速查](#附录模板速查) — 常用模板汇总

---

## 基础概念

### 人物注册命名标准

| 层级 | 用途 | 命名规范 | 示例 |
|------|------|---------|------|
| **Element ID** | 技术ID，JSON/Prompt中的角色标识 | `Element_` + 英文名/拼音 | `Element_Chuyue` |
| **Display Name** | 显示名称，用户交互、中文描述 | 中文名 | `初月` |
| **Reference Tag** | Prompt中的图片占位符 | `<<<image_N>>>` | `<<<image_1>>>`, `<<<image_2>>>` |

### 单一数据源

人物信息统一存储在 `storyboard.json`：

```json
{
  "elements": {
    "characters": [
      {
        "element_id": "Element_Chuyue",
        "name": "初月",
        "reference_images": ["/path/to/ref.jpg"],
        "visual_description": "25岁亚洲女性，黑色长直发..."
      }
    ]
  },
  "character_image_mapping": {
    "Element_Chuyue": "image_1"
  }
}
```

### Prompt 中的引用方式

| 引用类型 | 写法 | 作用 |
|---------|------|------|
| 外貌引用 | `<<<image_1>>>` / `<<<image_2>>>` | 确保人物外貌稳定 |
| 分镜图引用 | `Shot_XXX_frame` | 确保场景布局、人物位置 |
| 角色标识 | `Element_Chuyue` | Motion sequence 中的角色标识 |

---

## 图片生成 Prompt

用于 Gemini 生成分镜图（Storyboard Frame）。

### 五要素结构

1. **场景**：时间、地点、环境
2. **主体**：人物外貌、服饰、姿态
3. **光影**：光线方向、色温、氛围
4. **风格**：cinematic / realistic / anime
5. **比例**：竖屏9:16 / 横屏16:9 / 正方形1:1

### 基础模板

```
Cinematic realistic start frame.

Scene: {具体场景描述}
Location details: {环境细节}

{角色外貌详细描述}，{姿态}，{表情}，{位置}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {灯光描述}
Color grade: {色调}
Aspect ratio: {画面比例}

Style: {cinematic realistic/film grain/etc.}
```

### 完整示例

```
Cinematic realistic start frame.

Scene: A wide three-person shot inside the men's restroom at the doorway
Location details: white tiles, sink and mirror visible, door frame as divider

A 25-year-old Asian woman with long black hair, wearing light grey blazer,
stands in doorway, hands raised in flustered waving gesture, forced apologetic smile

Shot scale: Wide/Full shot
Camera angle: Eye-level, frontal
Lighting: Cold white fluorescent overhead lighting
Color grade: Cool blue-white

Style: Cinematic realistic, film grain, shallow depth of field, 16:9 aspect ratio
```

---

## Kling/Vidu 视频生成 Prompt

用于 Kling-v3/Vidu 视频生成。

### 结构要素（按顺序）

1. **整体动作概述** — 简要描述镜头整体动作
2. **分段动作** — 按时间轴：0-2s, 2-5s...
3. **运镜描述** — 推/拉/摇/移/跟/升降
4. **运动节奏** — 缓慢/平稳/快速/急促
5. **画面稳定性** — 保持稳定/轻微晃动
6. **台词信息** — 角色、内容、情绪、语速
7. **比例保护** — "保持XX比例构图"
8. **BGM约束** — 根据 audio.no_bgm 决定

### 基础模板

```
整体：{镜头整体动作描述}

分段动作（{duration}秒）：
{time_range_1}: {动作描述}
{time_range_2}: {动作描述 + 台词同步}
...

运镜：{镜头运动描述}
节奏：{运动节奏}
画面稳定性：{保持稳定/轻微晃动}
{台词信息}
保持{比例}构图，不破坏画面比例
{BGM约束}
```

### 完整示例（5秒镜头）

```
整体：女主角从沉思中抬头看向窗外，嘴角逐渐上扬，露出温柔微笑。

分段动作（5秒）：
0-2s: 女主角侧脸对着镜头，目光望向窗外，表情平静
2-4s: 女主角嘴角微微上扬，眼神变得柔和
4-5s: 女主角完全转过身来，面向镜头自然微笑

运镜：镜头缓慢推近，保持稳定
节奏：缓慢平稳
画面稳定性：保持稳定
台词：女主角温柔地说："这是我最喜欢的地方。" 声音清澈，语速适中偏慢。
保持竖屏9:16构图，人物始终位于画面中央，不破坏画面比例
No background music. Natural ambient sound only.
```

---

## V3-Omni 两阶段流程

针对 Kling V3-Omni 的**分镜图 + 视频**两阶段生成。

### 流程概述

```
阶段1: Image Prompt → Gemini 生成分镜图（控制场景/画风）
         ↓
阶段2: 分镜图 + 角色参考图 → Omni 视频生成（保持角色一致性）
```

### 阶段1：Image Prompt（分镜图）

**关键**：必须包含角色参考（image_N），使用 `Element_XXX` 标识

```
Cinematic realistic start frame.

Referencing the facial features, face shape, skin tone, and clothing details of:
- image_1: Element_Chuyue, young Asian woman, long black hair, delicate features, wearing light grey blazer
- image_2: Element_Jiazhi, mature man, short hair, deep eyes, wearing black shirt

Scene: {场景描述}
Location details: {环境细节}

Element_Chuyue: {姿态}, {表情}, {位置}
Element_Jiazhi: {姿态}, {表情}, {位置}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {灯光描述}
Color grade: {色调}
Aspect ratio: {画面比例}

Style: Cinematic realistic, film grain
```

### 阶段2：Video Prompt（Omni视频）

**关键**：双重引用（Element_XXX + image_N），引用分镜图控制布局

```
Referencing the {frame_name} composition for scene layout and character positioning.

Element_{Name}'s appearance from {image_N} (facial features, hairstyle, outfit),
positioned as shown in {frame_name}.

Overall: {整体动作描述}

Motion sequence ({duration}s):
{time_range_1}: Element_{Name} {action}{, with lip-synced dialogue}
{time_range_2}: {action}

Dialogue exchange:
- Element_{Name} ({emotion}): "{line}"

Camera movement: {static/pan/tracking/etc.}
Sound effects: {环境音描述}

Style: Cinematic realistic style. No music, no subtitles.
```

### 两阶段关键要点

| 阶段 | 关键要求 |
|------|---------|
| **Image** | 必须包含角色参考（image_1, image_2），使用 Element_XXX 标识 |
| **Image** | 必须包含画面比例（16:9 / 9:16） |
| **Image** | 场景、灯光、相机参数要详细 |
| **Video** | 必须引用分镜图（Referencing XXX_frame composition） |
| **Video** | 尽量使用双重引用：Element_XXX（角色）+ image_N（外貌） |
| **Video** | 动作必须分段描述（0-2s, 2-5s...） |
| **Video** | 对白必须标注情绪和 lip-sync |

---

## 一致性规范

### 人物一致性

**每个包含人物的镜头，prompt 必须包含**：

1. **人物身份标识** — `Element_Chuyue`
2. **外貌特征** — 性别、年龄、发型、面部特征、体型、标志性特征
3. **服饰描述** — 款式、颜色、材质、配饰

**Omni模式特殊要求**：
- Image Prompt 用 `<<<image_1>>>`、`<<<image_2>>>` 引用外貌
- Video Prompt 用 `Element_XXX` + `<<<image_N>>>` 双重引用

### 道具一致性

跨镜头重复出现的重要道具：

1. **建立物料清单** — storyboard 的 `props` 字段
2. **每个镜头完整描述** — prompt 中包含道具特征
3. **关键道具类型** — 品牌Logo、产品外观、剧情关键物品

---

## 比例约束

### 文生图 Prompt

| 比例 | 必须包含的文字 |
|------|---------------|
| 9:16 | "竖屏构图，9:16画面比例，人物/主体位于画面中央" |
| 16:9 | "横屏构图，16:9画面比例" |
| 1:1 | "正方形构图，1:1画面比例，主体居中" |

### 图生视频 / 文生视频

- 所有 video_prompt 必须确保运镜不破坏原始画面比例
- 9:16 竖屏：避免会导致画面变横的运镜描述
- **所有视频生成模式都必须通过 CLI `--aspect-ratio` 参数传递比例**
- 参数值从 `storyboard.json` 的 `aspect_ratio` 字段读取

---

## 台词与音频

### 同期声 vs TTS

| 类型 | 生成方式 | 适用场景 |
|------|---------|---------|
| 同期声 | 视频生成模型（`audio.enabled: true`） | 角色对话、角色独白 |
| TTS 旁白 | TTS 后期配音 | 片头/片尾解说、场景描述 |

**核心原则**：能收同期声的镜头，不要用 TTS！

### BGM 约束

**storyboard.json 中的 `audio` 字段与 API 参数的映射**：

| storyboard 字段 | API 参数 | 说明 |
|----------------|----------|------|
| `audio.no_bgm = true` | prompt 末尾添加 `"No background music. Natural ambient sound only."` | BGM 由后期合成 |
| `audio.no_bgm = false` | 无额外约束 | 视频模型自由决定是否生成 BGM |
| `audio.enabled = true` | `sound: "on"` | 生成环境音/台词 |
| `audio.enabled = false` | `sound: "off"` | 静音输出 |

**注意**：不单独写 Sound effects，让模型根据画面内容自动生成环境音（如赛车引擎声、键盘声、风声等）。

### 台词融入 Prompt

当镜头包含台词时，必须在 video_prompt 中完整描述：角色（含外貌）、台词内容（引号包裹）、表情/情绪、声音特质和语速。

```
女主角（25岁亚洲女性，黑色长直发）抬头看向服务生，
温柔微笑着说："这里真的很安静，我很喜欢。"
声音清脆悦耳，语速适中偏慢。
```

---

## 附录：模板速查

### Image Prompt 模板（Omni分镜图）

```
Cinematic realistic start frame.

Referencing the facial features, face shape, skin tone, and clothing details of:
- image_1: Element_{Name}, {外貌详细描述}

Scene: {场景描述}
Location details: {环境细节}

Element_{Name}: {姿态}, {表情}，{位置}

Shot scale: {wide/medium/close-up}
Camera angle: {eye-level/high/low}
Lighting: {灯光描述}
Color grade: {色调}
Aspect ratio: {画面比例}

Style: Cinematic realistic, film grain, shallow depth of field
```

### Video Prompt 模板（Omni视频）

```
Referencing the {frame_name} composition for scene layout and character positioning.

Element_{Name}'s appearance from {image_N} ({外貌引用}),
positioned as shown in {frame_name}.

Overall: {整体动作描述}

Motion sequence ({duration}s):
{time_range}: Element_{Name} {action}{, with lip-synced dialogue}

Dialogue exchange:
- Element_{Name} ({emotion}): "{line}"

Camera movement: {static/pan/tracking/etc.}
Sound effects: {声音设计}

Style: Cinematic realistic style. No music, no subtitles.
```

### Video Prompt 模板（普通Kling，无Omni）

```
整体：{镜头整体动作描述}

分段动作（{duration}秒）：
{time_range_1}: {动作描述}
{time_range_2}: {动作描述 + 台词同步}

运镜：{镜头运动描述}
节奏：{运动节奏}
画面稳定性：{保持稳定/轻微晃动}
{台词信息}
保持{比例}构图，不破坏画面比例
{BGM约束}
```
