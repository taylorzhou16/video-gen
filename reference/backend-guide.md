# 后端选择与参考图策略

## 目录

- 三种后端能力对比
- 后端选择决策树
- 自动选择逻辑
- 人物参考图两条路径
- **路径 A：Kling Omni（推荐）**
- 路径 B：Kling + Gemini 首帧
- Gemini Prompt 注意事项

---

## 三种后端能力对比

| 能力 | Vidu | Kling | Kling Omni |
|------|------|-------|------------|
| **后端名** | `vidu` | `kling` | `kling-omni` |
| **文生视频** | 5-10s | 3-15s | 3-15s |
| **图生视频** | 单图 | 首帧图（精确控制） | 用 image_list 代替 |
| **image_list 多参考图** | -- | -- | `<<<image_1>>>` 引用 |
| **multi_shot 多镜头** | -- | intelligence / customize | intelligence / customize |
| **首尾帧控制** | -- | `--image` + `--tail-image` | -- |
| **音画同出** | -- | `--audio` | `--audio` |
| **最佳场景** | 简单快速、兜底 | 首帧精确控制、场景一致 | 角色一致性、多人物 |

**重要区别**：
- Kling `--image` 是**首帧图**（视频从此图开始）
- Kling Omni `--image-list` 是**参考图**（人物保持一致）

---

## 后端选择决策树

**核心权衡：人物一致性 vs 场景精确度 vs 两者兼顾**

```
镜头是否包含人物？
├── 是 → 是否有注册的人物参考图？
│        ├── 是 → 需要场景精确控制吗？
│        │        ├── 是 → 需要角色一致性吗？
│        │        │        ├── 两者都要 → Omni + 分镜图参考 + 人物参考图 (Path A 最佳实践)
│        │        │        └── 首帧确定性优先 → Kling + Gemini 首帧 (Path B)
│        │        └── 否 → Omni --image-list (Path A 基础用法)
│        └── 否 → 是否需要精确控制首帧画面？
│                 ├── 是 → Kling + image（Gemini 生首帧）
│                 └── 否 → Kling text2video
└── 否 → 是否需要 multi_shot？
         ├── 是 → Kling
         └── 否 → Kling（默认）
```

### 场景速查

| 场景 | 后端 | 关键参数 |
|------|------|---------|
| **剧情视频，场景+角色都要** | **Omni** | `--image-list frame.png ref.jpg` |
| 快速原型、人物一致优先 | Omni | `--image-list ref.jpg` |
| 场景精确优先、角色可波动 | Kling | `--image first_frame.png` |
| 需要首尾帧动画 | Kling | `--image first.png --tail-image last.png` |
| 多镜头剧情 + 角色一致 | Omni | `--image-list ref.jpg --multi-shot` |
| 简单无人场景 / 快速原型 | Kling（默认）或 vidu | 无需特殊参数 |

---

## 自动选择逻辑

未指定 `--backend` 时默认使用 **kling**。特殊参数会强制切换后端：
- 提供 `--image-list` → 自动切换到 kling-omni（唯一支持）
- 提供 `--tail-image` → 保持 kling（唯一支持）
- 需要快速兜底 → 手动指定 `--backend vidu`

---

## 人物参考图两条路径

**仅当已注册人物参考图时考虑**

| | **Path A: Kling Omni（推荐）** | Path B: Kling + Gemini |
|---|---|---|
| **流程** | **分镜图 + 角色参考图 → `image_list`** | 分镜图 → `--image` → Kling img2video |
| **优势** | **两者兼顾：场景可控 + 角色一致** | 场景精确可控 |
| **一致性** | **好（参考图在 image_list 中）** | 适中 |
| **场景控制力** | **强（分镜图提供整体视觉）** | 强（分镜图作为首帧） |
| **适用** | **剧情视频（推荐）** | 首帧精确度优先、可接受角色波动 |

**选择建议**：
- **剧情视频、两者都要 → Path A: Kling Omni（推荐）**
- 首帧精确度优先、可接受角色波动 → Path B: Kling + Gemini

---

## 路径 A：Kling Omni（推荐）

**最佳实践：分镜图 + 角色参考图双重参考**

```
阶段1: Image Prompt → Gemini 生成分镜图（控制场景/画风/灯光/氛围/色彩/妆造）
         ↓
阶段2: 分镜图 + 角色参考图 → 作为 image_list 传入 Omni → 视频
```

**关键认知**：
- **分镜图**作为 `image_list` 传入，控制整体视觉（场景、画风、灯光、氛围、色彩、妆造）
- **角色参考图**同时传入 `image_list`，保证角色面貌/身材一致性
- Omni 会综合参考多张图片：分镜图提供整体视觉，角色参考图提供人物特征

### 快速原型（对场景、角色妆造一致性没有要求的场景）

只传角色参考图，不生成分镜图：

```bash
python vico_tools.py video \
  --backend kling-omni \
  --prompt "人物 <<<image_1>>> 在咖啡馆窗边坐下，微笑着看向窗外" \
  --image-list /path/to/person_ref.jpg \
  --audio --output output.mp4
```

### 最佳实践（分镜图 + 角色参考）

**Step 1**: 生成分镜图

```bash
python vico_tools.py image \
  --prompt "Cinematic realistic start frame.\nReferencing the facial features...\nScene: 男洗手间门口...\nLighting: 冷白色荧光..." \
  --reference /path/to/person_ref.jpg \
  --output generated/frames/{shot_id}_frame.png
```

**Step 2**: 分镜图 + 角色参考图一起传入 Omni

```bash
python vico_tools.py video \
  --backend kling-omni \
  --prompt "Referencing the composition, characters interact in the scene..." \
  --image-list generated/frames/{shot_id}_frame.png /path/to/person_ref.jpg \
  --audio --output output.mp4
```

**注意**：`image_list` 中图片顺序很重要，Omni 会综合参考所有图片。通常分镜图放前面提供整体视觉，角色参考图放后面确保人物特征。

### Omni 多参考图 + multi_shot

```bash
python vico_tools.py video --backend kling-omni \
  --prompt "故事" \
  --image-list frame.png ref1.jpg ref2.jpg \
  --multi-shot --shot-type customize \
  --multi-prompt '[{"index":1,"prompt":"镜头1","duration":"3"},{"index":2,"prompt":"镜头2","duration":"4"}]' \
  --duration 7
```

### Omni 模式 Storyboard 标注

```json
{
  "shot_id": "scene1_shot2",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "小美和小明在咖啡馆对话...",
  "reference_images": [
    "generated/frames/scene1_shot2_frame.png",
    "/path/to/xiaomei_ref.jpg",
    "/path/to/xiaoming_ref.jpg"
  ],
  "frame_strategy": "frame_as_reference"
}
```

---

## 路径 B：Kling + Gemini 首帧

**提醒**：人物参考图是**样貌参考图**，只取面部/体态特征，**不能直接做 img2video 首帧**。人物参考图中的场景、服饰、姿态都是干扰。

```
人物参考图 → Gemini 生成分镜图（指定场景/服饰/姿态）→ img2video（Kling普通版）
```

**注意**：此路径使用普通 Kling img2video（`--image` 首帧），**不使用** Omni。首帧场景控制好，但角色一致性不如 Path A。

### 单人镜头

**Step 1**：Gemini 基于参考图生成分镜图

```bash
python vico_tools.py image \
  --prompt "小美（25岁亚洲女性，黑色长直发，瓜子脸）坐在咖啡馆窗边，抬头微笑，下午阳光，电影感，竖屏9:16构图" \
  --reference <参考图路径> \
  --output generated/storyboard/scene1_shot2_frame.png
```

**Step 2**：分镜图做 img2video

```bash
python vico_tools.py video \
  --image generated/storyboard/scene1_shot2_frame.png \
  --prompt "小美抬头看向服务生，温柔微笑着说：'这里真的很安静，我很喜欢。'" \
  --backend kling --audio \
  --output generated/videos/scene1_shot2.mp4
```

### 双人/多人镜头

**Step 1**：Gemini 多参考图合成一张分镜图（**参考图顺序很重要，重要人物放后面**）

```bash
python vico_tools.py image \
  --prompt "小美和小明并肩走在街道上，温暖的金色光线，竖屏9:16构图" \
  --reference <次要人物参考图> <主要人物参考图> \
  --output generated/storyboard/scene2_shot1_frame.png
```

**Step 2**：合成图做 img2video

### Kling 路径 Storyboard 标注

```json
{
  "shot_id": "scene1_shot2",
  "generation_mode": "img2video",
  "generation_backend": "kling",
  "frame_strategy": "first_frame_only",
  "image_prompt": "小美坐在咖啡馆窗边，抬头微笑，竖屏9:16构图",
  "video_prompt": "小美抬头看向服务生，温柔微笑...",
  "reference_personas": ["小美"]
}
```

---

## Gemini Prompt 注意事项

必须包含：
- 人物身份标识 + 外貌特征（与参考图对应）
- 场景描述（当前分镜的场景，非参考图场景）
- 服饰描述（可能与参考图不同）
- 光影氛围
- **画面比例**（竖屏9:16构图）

**示例**：
```
Reference for 小美: MUST preserve exact appearance - 25岁亚洲女性，黑色长直发，瓜子脸
小美坐在温馨的咖啡馆窗边，穿着米色针织衫，下午阳光透过窗户洒进来，
电影感色调，浅景深虚化背景，竖屏构图，9:16画面比例，人物位于画面中央
```
