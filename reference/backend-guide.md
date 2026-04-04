# 后端选择与参考图策略

## 目录

- 四种后端能力对比
- 后端选择决策树
- Seedance 智能切镜模式
- 自动选择逻辑
- 人物参考图两条路径
- **路径 A：Kling Omni（推荐）**
- 路径 B：Kling + Gemini 首帧
- Gemini Prompt 注意事项

---

## 五种后端能力对比

| 能力 | Vidu | Kling | Kling Omni | **Seedance** | **Veo3** |
|------|------|-------|------------|--------------|----------|
| **后端名** | `vidu` | `kling` | `kling-omni` | `seedance` | `veo3` |
| **Provider** | yunwu | official/yunwu/fal | official/yunwu/fal | piapi | **compass** |
| **文生视频** | 5-10s | 3-15s | 3-15s | **5/10/15s** | **4/6/8s** |
| **图生视频** | 单图 | 首帧图（精确控制） | 用 image_list 代替 | 分镜图 + 参考图 | **首帧图** |
| **image_list 多参考图** | -- | -- | `<<<image_1>>>` 引用 | **`@image1` 引用（最多 9 张）** | -- |
| **智能切镜** | -- | multi-shot 参数控制 | multi-shot 参数控制 | **时间分段 prompt 自动触发** | -- |
| **首尾帧控制** | -- | `--image` + `--tail-image` | -- | --（分镜图作为参考） | `--image`（首帧） |
| **音画同出** | -- | `--audio` | `--audio` | **✓ 默认生成音频** | **✓ 默认生成音频** |
| **最高分辨率** | 1080p | 1080p | 1080p | **720p** ⚠️ | **720p** |
| **最佳场景** | 简单快速、兜底 | 首帧精确控制、场景一致 | 角色一致性、多人物 | **虚构片/短剧、智能切镜** | **高质量写实短片** |

**重要区别**：
- Kling `--image` 是**首帧图**（视频从此图开始）
- Kling Omni `--image-list` 是**参考图**（人物保持一致）
- **Seedance 时间分段 = 自动 multi-shot**：无需额外参数，时间分段 prompt 自动触发智能切镜
- **Seedance 分镜图是参考**：不是首帧精确控制，而是视觉风格参考
- **Veo3 时长仅支持 4/6/8s**（枚举值），默认生成音频，画质最佳但时长较短

---

## 后端选择决策树

**场景驱动选择**：

| 场景 | 优先后端 | 兜底后端 | 原因 |
|-----|---------|---------|------|
| **虚构片/短剧** | **Seedance** | Kling-Omni | 智能切镜 + 多参考图，角色一致性 |
| **广告片（无真实素材）** | **Seedance** | Kling-Omni | 长镜头 + 智能切镜 |
| **广告片（有真实素材）** | Kling-3.0 / Vidu | — | 首帧精确控制，真实素材 |
| **MV短片** | **Seedance** | Kling-Omni | 长镜头 + 音乐驱动 |
| **Vlog/写实类** | Kling-3.0 | Vidu | 首帧精确控制，不走 Seedance |
| **高质量写实短片** | **Veo3** | Kling-3.0 | Google Veo3 画质最佳，4/6/8s |
| **超短镜头（≤ 4s）** | **Veo3** | Kling | Veo3 最短 4s，Kling 最短 3s |

**首帧控制能力对比**：

| 后端 | 首帧控制 | 说明 |
|------|---------|------|
| **Kling-3.0** | ✅ `--image` | 视频从此图开始 |
| **Vidu** | ✅ `--image` | 首帧精确控制 |
| **Veo3** | ✅ `--image` | 首帧精确控制 |
| **Seedance** | ❌ 参考图 | 分镜图是视觉风格参考，不是首帧 |
| **Kling-Omni** | ❌ 参考图 | 只有 reference2video，无 img2video |

**核心原则**：
1. **需要智能切镜 → Seedance**（时间分段自动触发 multi-shot）
2. **需要首帧控制 → Kling/Vidu**（只有这两个支持）
3. **Seedance 失败 → 降级 Kling-Omni**（失去智能切镜，保留角色一致性）

### 场景速查

| 场景 | 后端 | 关键参数 |
|------|------|---------|
| **虚构片/短剧** | **Seedance** | `--backend seedance --image-list frame.png ref.jpg` |
| **广告片（无真实素材）** | **Seedance** | 时间分段 prompt + 分镜图 |
| **广告片（有真实素材）** | Kling-3.0 | `--image first_frame.png` |
| **MV短片** | **Seedance** | 时间分段 prompt + 分镜图 |
| **Vlog/写实类** | Kling-3.0 | `--image first_frame.png` |
| 需要首尾帧动画 | Kling | `--image first.png --tail-image last.png` |
| 高质量写实短片 | **Veo3** | `--backend veo3 --duration 8` |
| 简单无人场景 / 快速原型 | Kling（默认）或 vidu | 无需特殊参数 |

---

## Seedance 智能切镜模式

**核心特点**：时间分段 prompt 自动触发 multi-shot 智能切镜，无需额外参数。

### API 参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `model` | `"seedance"` | 固定值 |
| `task_type` | `"seedance-2-fast-preview"` / `"seedance-2-preview"` | 快速 / 高质量 |
| `prompt` | 文本描述 | 支持 `@imageN` 引用图片，支持时间分段 |
| `duration` | 5 / 10 / 15 | 秒数（仅支持这三个枚举值） |
| `aspect_ratio` | 16:9/9:16/4:3/3:4 | 四种比例 |
| `image_urls` | 数组 | 最多 9 张参考图 |

### 输出规格

| 规格 | 值 |
|------|-----|
| 时长 | 5/10/15s（仅三个枚举值） |
| 分辨率 | 480p / 720p（最高 720p）⚠️ |
| 音频 | 自动生成（AAC 立体声） |

### 时间分段 Prompt 语法

**格式**：
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

**示例**：
```
Referencing the scene_1_seg_1_frame composition for scene layout and character positioning.

@image1，第一人称视角果茶宣传广告；Element_Chuyue 为女性角色；

整体：第一人称视角展示果茶制作全过程，从摘苹果到成品呈现，自然流畅。

分段动作（10s）：
0-2s：你的手摘下一颗带晨露的阿克苏红苹果，固定镜头，节奏平稳，轻脆的苹果碰撞声；
2-4s：快速切镜，你的手将苹果块投入雪克杯，加入冰块与茶底，用力摇晃，镜头轻微跟随，节奏轻快，冰块碰撞声卡点鼓点；
4-6s：第一人称成品特写，分层果茶倒入透明杯，你的手轻挤奶盖，镜头缓慢推进，节奏平稳，液体流动声；
6-8s：镜头推进，杯身贴上粉红包标，展示分层纹理，节奏舒缓，轻柔背景音；
8-10s：第一人称手持举杯，@image2，果茶举到镜头前，固定镜头，节奏平稳，杯身标签清晰可见，背景音：「来一口鲜爽」；

保持横屏16:9构图，不破坏画面比例
背景音：「鲜切现摇」「来一口鲜爽」，女声音色。
```

### image_urls 顺序约定

| index | 用途 | 引用方式 |
|-------|------|---------|
| `image_urls[0]` | 分镜图 | `Referencing the {segment_id}_frame composition...` |
| `image_urls[1]` | 角色参考图 1 | `@image1` |
| `image_urls[2]` | 角色参考图 2 | `@image2` |
| ... | ... | ... |
| `image_urls[9]` | 角色参考图 9（最多） | `@image9` |

**关键点**：
1. **分镜图是参考，不是首帧精确控制** — 提供整体视觉风格参考
2. **角色参考图用 `<<<image_N>>>` 引用** — 与 Kling-Omni 统一语法
3. **时间分段自动触发智能切镜** — 无需 `--multi-shot` 参数
4. **最高 720p** — 需要 1080p 时使用 Kling 或 Vidu

### CLI 使用示例

```bash
# Text-to-Video（纯文字生成）
python video_gen_tools.py video \
  --backend seedance \
  --prompt "时间分段描述..." \
  --duration 10 \
  --aspect-ratio 16:9 \
  --output output.mp4

# Image-to-Video（分镜图 + 角色参考图）
python video_gen_tools.py video \
  --backend seedance \
  --prompt "Referencing the composition... @image1..." \
  --image-list generated/frames/scene1_frame.png materials/personas/xiaomei_ref.jpg \
  --duration 10 \
  --output output.mp4
```

### 推荐场景

| 场景 | 优先后端 | 兜底后端 | 原因 |
|------|---------|---------|------|
| **虚构片/短剧** | **Seedance** | Kling-Omni | 智能切镜 + 多参考图，角色一致性 |
| **广告片（无真实素材）** | **Seedance** | Kling-Omni | 长镜头 + 智能切镜 |
| **广告片（有真实素材）** | Kling-3.0 / Vidu | — | 首帧精确控制，真实素材 |
| **MV短片** | **Seedance** | Kling-Omni | 长镜头 + 音乐驱动 |
| **Vlog/写实类** | Kling-3.0 | Vidu | 首帧精确控制，不走 Seedance |
| **超短镜头（< 5s）** | Kling / Vidu | — | Seedance 最短 5s |

---

## 自动选择逻辑

未指定 `--backend` 时默认使用 **kling**。特殊参数会强制切换后端：
- 提供 `--image-list` → 自动切换到 kling-omni（唯一支持）
- 提供 `--tail-image` → 保持 kling（唯一支持）
- 需要快速兜底 → 手动指定 `--backend vidu`

### Provider 选择优先级

当未指定 `--provider` 时，按以下优先级自动选择：

| 条件 | Provider | 说明 |
|------|----------|------|
| 有 KLING_ACCESS_KEY + KLING_SECRET_KEY | `official` | Kling 官方 API |
| 有 FAL_API_KEY | `fal` | fal.ai 代理 |
| 有 YUNWU_API_KEY | `yunwu` | yunwu.ai 代理 |

**手动指定 provider**：

```bash
# 使用 yunwu 代理（绕过官方 API 并发限制）
python video_gen_tools.py video --provider yunwu --backend kling-omni --image-list ref.jpg ...

# 使用 fal.ai 代理
python video_gen_tools.py video --provider fal --backend kling-omni --image-list ref.jpg ...
```

**yunwu vs fal 对比**：

| Provider | 支持后端 | 优势 | 适用场景 |
|----------|---------|------|---------|
| `yunwu` | vidu, kling, kling-omni | 支持全系列、国内访问 | 官方 API 不可用时的首选备用 |
| `fal` | kling-omni | 国际访问稳定 | 仅需 kling-omni 时的备选 |

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
python video_gen_tools.py video \
  --backend kling-omni \
  --prompt "人物 <<<image_1>>> 在咖啡馆窗边坐下，微笑着看向窗外" \
  --image-list /path/to/person_ref.jpg \
  --audio --output output.mp4
```

### 最佳实践（分镜图 + 角色参考）

**Step 1**: 生成分镜图

```bash
python video_gen_tools.py image \
  --prompt "Cinematic realistic start frame.\nReferencing the facial features...\nScene: 男洗手间门口...\nLighting: 冷白色荧光..." \
  --reference /path/to/person_ref.jpg \
  --output generated/frames/{shot_id}_frame.png
```

**Step 2**: 分镜图 + 角色参考图一起传入 Omni

```bash
python video_gen_tools.py video \
  --backend kling-omni \
  --prompt "Referencing the composition, characters interact in the scene..." \
  --image-list generated/frames/{shot_id}_frame.png /path/to/person_ref.jpg \
  --audio --output output.mp4
```

**注意**：`image_list` 中图片顺序很重要，Omni 会综合参考所有图片。通常分镜图放前面提供整体视觉，角色参考图放后面确保人物特征。

### Omni 多参考图 + multi_shot

```bash
python video_gen_tools.py video --backend kling-omni \
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
python video_gen_tools.py image \
  --prompt "小美（25岁亚洲女性，黑色长直发，瓜子脸）坐在咖啡馆窗边，抬头微笑，下午阳光，电影感，竖屏9:16构图" \
  --reference <参考图路径> \
  --output generated/storyboard/scene1_shot2_frame.png
```

**Step 2**：分镜图做 img2video

```bash
python video_gen_tools.py video \
  --image generated/storyboard/scene1_shot2_frame.png \
  --prompt "小美抬头看向服务生，温柔微笑着说：'这里真的很安静，我很喜欢。'" \
  --backend kling --audio \
  --output generated/videos/scene1_shot2.mp4
```

### 双人/多人镜头

**Step 1**：Gemini 多参考图合成一张分镜图（**参考图顺序很重要，重要人物放后面**）

```bash
python video_gen_tools.py image \
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

---

## API 限制时的降级策略

当 API 遇到 429（并发限制）、402（余额不足）、超时、或其他不可恢复错误时，需要降级。

### 降级前提条件

**必须满足以下条件才能降级**：
1. 已重试一次仍失败（Seedance 超时需等待 10 分钟）
2. 用户明确同意降级
3. 降级后仍有可用后端

### 降级路径

| 原模式 | 降级后模式 | 后端变化 | 能力变化 |
|--------|-----------|----------|----------|
| `seedance-video` | `omni-video` (kling-omni) | Seedance → Kling-Omni | 失去智能切镜，需手动 multi-shot |
| `omni-video` (kling-omni) | `img2video` (kling) | Omni → Kling | 失去多参考图能力，角色一致性降低 |
| `img2video` (kling) | `text2video` (kling) | 无变化 | 失去首帧控制 |

**禁止的降级**：
- ❌ `seedance-video` → Vidu text2video（Vidu 不支持 image_list）
- ❌ `omni-video` → Vidu text2video（Vidu 不支持 image_list）

### Seedance → Kling-Omni 降级流程

当 Seedance 超时或失败时，降级到 Kling-Omni：

**Step 1：询问用户**
```
Seedance 生成失败（已重试 1 次）。

可选方案：
A. 降级到 Kling-Omni（失去智能切镜，需手动 multi-shot）
B. 修改 prompt 后再次尝试 Seedance
C. 取消本次生成

请选择：
```

**Step 2：用户选择 A 后，修改 storyboard.json**

```json
// 原始（Seedance）
{
  "generation_mode": "seedance-video",
  "generation_backend": "seedance",
  "reference_images": ["分镜图", "角色参考图1", "角色参考图2"]
}

// 降级后（Kling-Omni）
{
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "reference_images": ["角色参考图1", "角色参考图2"]
}
```

**Step 3：执行 Kling-Omni**

- provider 按优先级自动选择：official → fal → yunwu
- 每个 shot 单独调用 API（不合并）
- 保留角色参考图，保持角色一致性

### Kling-Omni → Kling img2video 降级流程

当 Kling-Omni 无法执行时，降级到 img2video：

**Step 1：询问用户**
```
Kling-Omni API 当前不可用（原因：429并发限制 / 402余额不足）。

可选方案：
A. 等待并重试（可能需要较长时间）
B. 降级到 Kling img2video（角色一致性会降低，需先生成分镜图）
C. 取消本次生成

请选择：
```

**Step 2：用户选择 B 后，修改 storyboard.json**

需要修改每个镜头的字段：

```json
// 原始（Omni）
{
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "reference_images": ["角色参考图", "分镜图"],
  "frame_strategy": "none"
}

// 降级后（img2video）
{
  "generation_mode": "img2video",
  "generation_backend": "kling",
  "reference_images": [],
  "frame_strategy": "first_frame_only",
  "frame_path": "generated/frames/{shot_id}_frame.png",
  "image_prompt": "..." // 必须补充，用于生成分镜图
}
```

**Step 3：执行 Path B**

1. 先生成所有分镜图（使用 Gemini + 角色参考图）
2. 用分镜图作为首帧调用 Kling img2video

### storyboard.json 降级修改详情

| 字段 | Path A (omni-video) | Path B (img2video) |
|------|---------------------|---------------------|
| `generation_mode` | `omni-video` | `img2video` |
| `generation_backend` | `kling-omni` | `kling` |
| `reference_images` | `[角色参考图, 分镜图]` | `[]`（分镜图单独传入） |
| `frame_strategy` | `none` | `first_frame_only` |
| `frame_path` | 无 | `generated/frames/{shot_id}_frame.png` |
| `image_prompt` | 可选 | **必须** |

**不变的字段**：
- `shot_id`, `duration`, `shot_type`, `description`
- `video_prompt`（可能需微调：移除 `<<<image_N>>>` 引用）
- `dialogue`, `transition`, `audio`
- `characters`（镜头涉及的角色）

### 预留 fallback_plan（推荐）

在 Phase 3 生成分镜时，预先写好降级方案，避免临时编写 `image_prompt`：

```json
{
  "shot_id": "scene1_shot1",
  "generation_mode": "omni-video",
  "generation_backend": "kling-omni",
  "video_prompt": "...",
  "reference_images": ["..."],

  "fallback_plan": {
    "mode": "img2video",
    "backend": "kling",
    "image_prompt": "Cinematic realistic start frame.\nScene: ...\nLighting: ...\nStyle: ...",
    "frame_strategy": "first_frame_only",
    "reason": "Omni API 不可用时降级"
  }
}
```

降级时只需切换字段，直接使用 `fallback_plan.image_prompt`。
