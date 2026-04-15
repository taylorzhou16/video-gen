# 一致性规范指南

本文档定义了跨镜头一致性审查的原则，供模型在 Phase 3.5 自动 review storyboard.json 时参考。

---

## 审查原则概览

| 原则 | 检测范围 | 核心要求 |
|------|---------|---------|
| **1. 时间光照一致性** | 同一 scene 内所有 shot | 光照描述必须与 `time_state` 语义一致 |
| **2. 空间元素一致性** | 同一 scene 内所有 shot | 关键元素描述必须保持样式一致（非仅名称相同） |
| **3. 人物妆造一致性** | 同一 scene 内所有 shot | 服装/发型/妆容必须锁定，除非剧情换装 |
| **4. image/video 描述匹配** | 同一 shot 内 | image_prompt 和 video_prompt 对同一元素描述必须一致 |
| **5. 跨 scene 资产连续性** | 连续的多个 scenes | 关键资产（人物妆造、场景布局）应保持视觉连续 |

---

## 原则 1：时间光照一致性

### 规则

同一 scene 内所有 shot 的光照描述必须与 `time_state` 保持语义一致。

**`time_state` 定义了场景的时间背景和光照基调**，所有 `image_prompt` 的 Lighting 行、`video_prompt` 的光线描述都应该继承 `time_state`。

### 禁止词对照表

| time_state 值 | 禁止出现的光照描述 |
|---------------|------------------|
| "春日下午"、"下午"、"daytime" | "黄昏"、"傍晚"、"日落"、"sunset"、"golden hour（特指日落前）"、"夜晚"、"night"、"moonlight" |
| "黄昏"、"日落"、"sunset" | "上午"、"清晨"、"morning"、"正午"、"noon"、"夜晚" |
| "夜晚"、"night" | "白天"、"daytime"、"阳光"、"sunlight"、"黄昏" |

### 例外情况

如果剧情明确需要时间流逝（如"从下午到黄昏"），需要在 scene 的 `narrative_goal` 或 shot 的 `description` 中说明。

**示例**：
```
narrative_goal: "展示主角从下午读书到黄昏收工的时间流逝"
→ shot_1: 下午光线 ✓
→ shot_2: 黄昏光线 ✓（有剧情说明）
```

### 检测示例

```
time_state: "春日下午，柔和阳光"
shot_1 Lighting: "Warm afternoon sunlight, soft golden glow" → ✓ 一致
shot_2 Lighting: "黄昏光线，低角度逆光" → ❌ 冲突，应修复
shot_3 Lighting: "Dramatic sunset lighting" → ❌ 冲突，应修复
```

---

## 原则 2：空间元素一致性

### 规则

同一 scene 内所有 shot 对关键场景元素的描述必须保持**样式一致**，不能只是名词相同但样式漂移。

**`spatial_setting` 定义了场景的空间布局和关键元素样式**，所有 shot 的 `image_prompt` Scene 行、`video_prompt` 的场景描述都应该继承这些元素。

### 样式锁定要求

不仅要元素名称一致，还要样式描述一致：

| spatial_setting 描述 | shot 描述 | 判断 |
|---------------------|----------|------|
| "垂杨柳（枝条细长下垂）" | "垂杨柳枝条下垂" | ✓ 名称 + 样式一致 |
| "垂杨柳（枝条细长下垂）" | "垂杨柳" | ⚠️ 名称一致但样式需补全 |
| "垂杨柳（枝条细长下垂）" | "古树" / "枯树" / "老柳树" | ❌ 语义漂移 |
| "石板路（青灰色）" | "青石板路" | ✓ 一致 |
| "石板路（青灰色）" | "泥土路" / "草地" | ❌ 漂移 |

### 元素禁止漂移词

| 关键元素 | 禁止漂移词 | 原因 |
|---------|-----------|------|
| 垂杨柳 | "枯"、"老"、"扭曲"、"粗壮"、"dead"、"ancient" | 会改变树的视觉形态 |
| 石板路 | "泥"、"土"、"草地"、"沙" | 会改变地面材质 |
| 水榭亭台 | "破旧"、"残缺"、"废墟" | 会改变建筑状态 |
| 青绿色调 | "黄色"、"红色"、"暖色调" | 会改变整体色系 |

### 检测示例

```
spatial_setting: "垂杨柳树下，石板路，水榭亭台"
shot_1 Scene: "垂杨柳枝条下垂，青石板路" → ✓ 一致
shot_2 Scene: "古树下，柳枝稀疏" → ❌ "古树"漂移，应为"垂杨柳"
shot_3 Scene: "枯柳树，泥土路面" → ❌ 多处漂移
```

---

## 原则 3：人物妆造一致性

### 规则

同一人物在同一 scene 内（未明确换装）服装/发型/妆容必须锁定。

**人物的 `visual_description` 或 `locked_costume` 定义了该人物的妆造基准**，所有 shot 对该人物的服装/发型引用必须一致。

### 字段定义

```json
{
  "element_id": "Element_LinDaiyu",
  "locked_costume": "淡青绿色广袖长袍，米白色交领中衣，墨绿色宽腰封",
  "locked_hairstyle": "古典高髻，两侧垂鬟",
  "locked_makeup": "细长柳叶眉，淡粉唇色，白皙底妆",
  "costume_scope": "scene_1, scene_2"  // 作用范围（可选）
}
```

### 作用范围说明

- `costume_scope` 指定人物妆造在哪些 scenes 内保持一致
- 留空表示全局一致（所有 scenes）
- 多个 scenes 用逗号分隔
- 当需要换装时，在新的 scene 开始时更新锁定字段并设置新的 scope

### 跨 scene 换装规则

如果剧情需要换装（如洗澡后换睡衣），需要在 scene 的 `narrative_goal` 或新 scene 的 `locked_costume` 中更新。

**没有明确说明换装的情况下，默认继承上一 scene 的妆造**。

### 检测示例

```
人物: 林黛玉，locked_costume="淡青绿罗裙"
shot_1: "淡青绿色长袍" → ✓ 一致
shot_2: "白色罗裙" → ❌ 颜色漂移，应为"淡青绿色"
shot_3: "素色汉服" → ❌ 描述模糊化，应为具体颜色
```

---

## 原则 4：image/video 描述匹配

### 规则

同一 shot 的 `image_prompt` 和 `video_prompt` 对同一元素的描述必须一致。

**image_prompt 决定分镜图的视觉基准**，**video_prompt 决定视频动态的一致性**，两者对关键元素（场景、人物、道具）的描述应该匹配。

### 检测重点

| 元素类型 | image_prompt 位置 | video_prompt 位置 | 检测内容 |
|---------|------------------|------------------|---------|
| 场景元素 | Scene 行 | 场景描述 | 元素名称 + 样式 |
| 光照 | Lighting 行 | 光线描述 | 时间 + 光线特征 |
| 人物服装 | Character 行 | 人物引用 | 服装颜色 + 样式 |

### 检测示例

```
shot_1:
  image_prompt: "垂杨柳枝条下垂，春日阳光"
  video_prompt: "古树摇曳，黄昏光线" → ❌ 多处不匹配
  
  修复建议：
  video_prompt: "垂杨柳枝条摇曳，春日下午柔和阳光"
```

---

## 原则 5：跨 scene 资产连续性

### 规则

如果多个 scenes 属于同一"叙事连续体"，关键资产应该保持视觉一致。

### 叙事连续体判断

**属于叙事连续体**：
- 多个 scenes 的 `spatial_setting` 相似且时间相近
- 连续的叙事段落（如同一事件的不同视角）

**不属于叙事连续体**：
- scenes 之间有明显场景切换（如"室内→室外"、"白天→夜晚"）
- 不同事件的独立叙事

### 连续性要求

| 资产类型 | 连续体要求 | 非连续体 |
|---------|-----------|---------|
| 人物妆造 | 默认锁定（除非剧情换装） | 可独立设计 |
| 场景布局 | 保持一致（柳树位置、建筑朝向） | 可重新设计 |
| 时间状态 | 逻辑推进（不能跳跃过大） | 可独立设定 |

### 检测示例

```
scene_1: time_state="下午2点", spatial_setting="垂杨柳下"
scene_2: time_state="下午4点", spatial_setting="垂杨柳下" → ✓ 连续体，资产一致

scene_1: time_state="下午"
scene_2: time_state="夜晚" → ⚠️ 需检查是否有剧情时间跳跃说明
```

---

## Review 输出格式

模型 review storyboard.json 后，应按以下格式输出：

```
📋 一致性审查结果

【发现问题】

1. [scene_1/scene1_shot2] 时间不一致：
   - time_state: "春日下午，柔和阳光"
   - Lighting: "黄昏光线" → 应为 "春日下午柔和阳光"

2. [scene_2/scene2_shot4] 空间漂移：
   - spatial_setting: "垂杨柳树下"
   - Scene 描述: "古树下" → 应为 "垂杨柳树下"

3. [scene_2/scene2_shot3] 人物服装漂移：
   - 人物 林黛玉 locked_costume: "淡青绿罗裙"
   - 描述: "白色长裙" → 应为 "淡青绿罗裙"

【修复建议】

修复 scene_1/scene1_shot2 image_prompt Lighting 行：
原值: "黄昏光线，低角度逆光"
修复为: "春日下午柔和阳光，暖色调，dappled shadows"

修复 scene_2/scene2_shot4 image_prompt Scene 行：
原值: "古树下，柳枝稀疏"
修复为: "垂杨柳树下，枝条细长下垂，春日园林"

修复 scene_2/scene2_shot3 image_prompt 人物服装描述：
原值: "白色长裙"
修复为: "淡青绿色罗裙，matching locked_costume"

---

共发现 N 个一致性问题，已自动修复。
```

---

## Review 执行流程

**触发时机**：Phase 3 分镜设计完成后，自动执行

**流程步骤**：

1. 读取 `storyboard.json`
2. 遍历所有 scenes 和 shots，按上述 5 个原则逐一检测
3. 发现问题 → 记录问题 + 生成修复建议
4. 自动应用修复建议（修改 storyboard.json）
5. 保存修复后的 storyboard.json
6. 输出审查结果通知用户

**无需用户确认**：发现明显不一致问题时直接修复，修复后通知用户。