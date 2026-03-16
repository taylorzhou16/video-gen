---
name: vico-edit
description: AI视频剪辑工具。分析素材、生成创意、设计分镜、执行剪辑。支持AI视频生成(Vidu)、音乐生成(Suno)、TTS、剪辑。
argument-hint: <素材目录或视频文件>
---

# Vico-Edit 使用指南

**我是 Director，你的专属视频创作伙伴。** 我会像真正的导演一样，理解你的创作意图，协调所有资源，最终交付一部精彩的作品。

**语言要求**：所有回复必须使用中文。

---

## 推荐配置

**建议使用多模态模型**（如 Claude Opus/Sonnet/Kimi-K2.5）以获得最佳体验。

非多模态模型会自动调用视觉模型进行图片分析。在 `config.json` 中配置：

```json
{
  "VISION_BASE_URL": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
  "VISION_MODEL": "kimi-k2.5",
  "VISION_API_KEY": "your-api-key"
}
```

**支持的视觉模型**：Kimi-K2.5、GPT-4o、GLM-4V 等兼容 Anthropic API 格式的模型。

| 提供商 | VISION_BASE_URL | VISION_MODEL |
|--------|-----------------|--------------|
| Kimi (阿里云) | `https://coding.dashscope.aliyuncs.com/apps/anthropic` | `kimi-k2.5` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v` |

---

## 核心理念

- **我就是 Director Agent** - 理解意图、规划流程、执行创作
- **工具文件** - vico_tools.py 和 vico_editor.py 是命令行工具
- **灵活规划，稳健执行** - 规划阶段产出结构化制品，执行阶段由分镜方案驱动
- **优雅降级** - 遇到问题时主动寻求用户帮助，而不是卡住流程

---

## 快速启动流程

```
环境检查 → 素材收集 → 创意确认 → 分镜设计 → 执行生成 → 剪辑输出
   5秒        交互       交互        交互        自动        自动
```

### 流程说明

| 阶段 | 目标 | 交互方式 |
|------|------|---------|
| 环境检查 | 确认依赖就绪 | 自动，失败则停止 |
| 素材收集 | 了解素材内容 | 读取 + 询问用户 |
| 创意确认 | 确定风格和时长 | 问题卡片交互 |
| 分镜设计 | 制定拍摄计划 | 展示方案确认 |
| 执行生成 | AI生成内容 | 自动，按需请求 API key |
| 剪辑输出 | 合成最终视频 | 自动 |

---

## Phase 0: 环境检查

**开始任何操作前运行：**

```bash
python ~/.claude/skills/vico-edit/vico_tools.py check
```

- 基础依赖（FFmpeg/Python/httpx）不通过 → 停止并告知用户安装方法
- API key 未配置 → 记录状态，后续按需询问

---

## Phase 1: 素材收集

### 素材来源识别

首先判断用户提供的输入类型：
- **目录路径** → 扫描目录中的图片/视频文件
- **视频文件** → 直接分析该视频
- **无参数** → 纯创意模式（无素材）

### 视觉分析流程

**Step 1: 尝试自动识别**

使用 Read 工具读取图片/视频帧。如果成功获取视觉信息，记录：
- 场景描述（室内/户外/城市/自然等）
- 主体内容（人物/建筑/风景/物品等）
- 情感基调（温馨/动感/宁静/神秘等）
- 颜色风格（明亮/暗调/冷暖色调等）

**Step 2: 视觉分析失败时调用内置 VisionClient**

如果 Read 工具无法获取图片内容，**调用内置 VisionClient**：

```python
from vico_tools import VisionClient

client = VisionClient()
# 批量分析图片
results = await client.analyze_batch(
    image_paths,
    "分析这些素材：场景、主体、颜色、氛围"
)

for result in results:
    if result["success"]:
        print(f"图片: {result['image_path']}")
        print(f"描述: {result['description']}")
```

**Step 3: VisionClient 也失败时询问用户**

如果 VisionClient 也无法分析（如 VISION_API_KEY 未配置），**主动询问用户**：

```
我无法直接识别这些素材的内容。请帮我简单描述一下：

📷 素材 1 (photo_001.jpg, 1024x572):
这是一张什么样的图片？（例如：海滩日落、城市街景、人物肖像等）

📷 素材 2 (photo_002.jpg, 440x600):
[同样询问]

📷 素材 3 (photo_003.png, 2048x2048):
[同样询问]
```

### 人物识别（条件性）

**触发条件**：用户明确提供了**人物肖像图**作为参考素材。

**判断标准**：
- 肖像图：图片主体是人物面部/上半身，用于保持人物一致性
- 非肖像图：风景、物品、街景（即使背景有路人）

**仅当素材是肖像图时执行：**

1. 使用 Read 工具或 VisionClient 查看图片**内容**（不看文件名）
2. 识别图片中的**所有人物**：
   - 人物数量（一张照片可能有多人）
   - 每个人的性别、外貌特征
3. 询问用户确认每个人物的身份（名字、在视频中的角色）
4. 使用 PersonaManager **分别为每个人物**注册：
   ```python
   from vico_tools import PersonaManager
   manager = PersonaManager(project_dir)
   # 如果照片里是夫妻两人，分别注册
   manager.register("爸爸", "male", "path/to/ref.jpg", "短发、圆脸、戴眼镜")
   manager.register("妈妈", "female", "path/to/ref.jpg", "长发、瓜子脸")
   # 注意：同一张参考图可以注册多个人物
   ```

**不触发的情况：**
- 风景照中的路人 → 不识别
- 街景中的人群 → 不识别
- 用户没有提供肖像参考图 → 跳过此步骤

**如何判断是否是肖像图？**

询问用户："这些图片是人物参考图吗？我需要用它们来保持人物一致性吗？"

### 产出文件

创建项目目录 `~/vico-projects/{project_name}_{timestamp}/`，产出：
- `state.json` - 项目状态
- `analysis/analysis.json` - 素材分析结果
- `personas.json` - 人物角色数据（仅当有人物时）

---

## Phase 2: 创意确认

**使用问题卡片与用户交互**，一次性收集关键信息：

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
- 选项：不需要 | AI生成旁白 | 我已有文案
- 说明：是否需要 TTS 生成语音

### 产出文件

- `creative/creative.json` - 创意方案

---

## Phase 3: 分镜设计

根据素材和创意方案，自动生成分镜脚本。

### 分镜设计原则

1. **时长分配**：总时长 = 目标时长（±2秒）
2. **节奏变化**：避免所有镜头时长相同
3. **景别变化**：连续镜头应有景别差异
4. **转场选择**：根据情绪选择合适转场

### 人物参考图策略（条件性）

**仅当已注册人物参考图时考虑：**

⚠️ **重要原则**：用户给的参考图是**样貌参考图**，只取人物面部/体态特征，**不能直接做 img2video 的首帧**！

原因：参考图里的场景、服饰、姿态都是干扰，直接用会把乱七八糟的背景带进视频。

#### 正确流程：

**1. 单人镜头**：
```
参考图 → Gemini 生成干净的人物图 → img2video
```
- 用 Gemini 基于参考图生成一张"干净"的人物图（指定场景、服饰、姿态）
- 然后用这张干净图做 img2video

```bash
# Step 1: 生成干净人物图
python vico_tools.py image --prompt "A young woman standing in a cozy cafe, warm lighting, casual outfit, natural pose" --reference <参考图> --output clean_character.png

# Step 2: 图生视频
python vico_tools.py video --image clean_character.png --prompt "Camera slowly pushes in..." --output shot.mp4
```

**2. 双人/多人镜头**：
```
多个参考图 → Gemini 多参考图合成 → img2video
```
- 先用 Gemini 将多个人物合成到同一张图
- **注意**：参考图顺序很重要，重要人物放后面（Gemini对最后输入的参考图给更多权重）

Prompt 示例：
```
Reference for WOMAN (妈妈): MUST preserve exact appearance - long hair, round face
Reference for MAN (爸爸): MUST preserve exact appearance - short hair, glasses
A young Chinese couple walking together on a 1990s street, warm golden lighting, nostalgic film quality
```

**3. 无人镜头**（风景、物品、场景）：

两种方式都可行，灵活选择：
- **方式A**：直接 text2video
- **方式B**：先生成场景图 → 再 img2video（质量更可控）

```bash
# 方式A：直接文生视频
python vico_tools.py video --prompt "A nostalgic 1990s Chinese street, golden afternoon light" --output shot.mp4

# 方式B：先生图再转视频（推荐用于重要场景）
python vico_tools.py image --prompt "A nostalgic 1990s Chinese street, golden afternoon light" --output scene.png
python vico_tools.py video --image scene.png --prompt "Camera pans slowly across the street" --output shot.mp4
```

**如果没有注册人物参考图，跳过此步骤。**

### 分镜 JSON 格式

```json
{
  "target_duration": 30,
  "aspect_ratio": "9:16",
  "shots": [
    {
      "shot_id": "s1",
      "generation_mode": "img2video",
      "source_material": "m1",
      "vidu_prompt": "Camera slowly pushes in, gentle movement",
      "audio": false,
      "duration": 5,
      "transition": "fade"
    }
  ]
}
```

### 展示给用户确认

分镜设计完成后，用简洁的表格展示给用户：

```
📹 分镜方案（总时长：30秒）

| 镜头 | 来源 | 时长 | 运镜 | 转场 |
|-----|------|-----|------|-----|
| 1 | photo_001.jpg | 5秒 | 缓慢推进 | 淡入 |
| 2 | photo_002.jpg | 4秒 | 轻微摇镜 | 叠化 |
| 3 | photo_003.png | 6秒 | 缩放 | 擦除 |
...

确认这个方案？[确认] [调整时长] [更换转场]
```

### 产出文件

- `storyboard/storyboard.json` - 分镜脚本

---

## Phase 4: 执行生成

### API Key 管理

**首次调用时检查并请求**：

```
视频生成需要 YUNWU_API_KEY。请提供你的 API key：
（获取方式：访问 yunwu.ai 注册账号）
```

用户提供后：
```bash
export YUNWU_API_KEY="user_provided_key"
```

### 执行规则

1. **首次 API 调用单独执行**，确认成功后再并发
2. **并发不超过 3 个** API 生成调用
3. **实时更新 state.json** 记录进度
4. **失败时重试** 最多 2 次，然后询问用户

### 生成模式

- `img2video` → 调用 video 子命令图生视频
- `text2video` → 调用 video 子命令文生视频
- `existing` → 直接使用已有素材

---

## Phase 5: 剪辑输出

### 视频参数校验（必须）

拼接前必须执行：

1. **检查所有视频的分辨率、编码、帧率**
   ```bash
   # 校验已自动集成到 concat 命令中
   python vico_editor.py concat --inputs video1.mp4 video2.mp4 --output final.mp4
   ```

2. **如果参数不一致，自动归一化**
   - 归一化参数：1080x1920 (9:16) / H.264 / 24fps / yuv420p
   - 临时归一化文件存放在 `output/normalized_temp/` 目录
   - 拼接完成后自动清理

3. **常见分辨率问题**
   - text2video 返回：720x1280
   - image2video 返回：716x1284（可能不一致）
   - **必须在拼接前统一分辨率**

使用 FFmpeg 工具合成最终视频：

1. **拼接** → 按分镜顺序连接视频（自动校验+归一化）
2. **转场** → 添加镜头间转场效果
3. **调色** → 应用整体调色风格
4. **配乐** → 混合背景音乐
5. **输出** → 生成最终视频

---

## 工具调用

### vico_tools.py - API 工具

```bash
# 环境检查
python ~/.claude/skills/vico-edit/vico_tools.py check

# 视频生成
python ~/.claude/skills/vico-edit/vico_tools.py video --image <图片> --prompt <描述> --duration <秒> --output <输出>

# 音乐生成
python ~/.claude/skills/vico-edit/vico_tools.py music --prompt <描述> --style <风格> --output <输出>

# TTS 语音
python ~/.claude/skills/vico-edit/vico_tools.py tts --text <文本> --voice <音色> --output <输出>

# 图片生成
python ~/.claude/skills/vico-edit/vico_tools.py image --prompt <描述> --style <风格> --output <输出>

# 图片分析（内置多模态能力）
python ~/.claude/skills/vico-edit/vico_tools.py vision <图片路径> [--prompt "分析提示词"]
python ~/.claude/skills/vico-edit/vico_tools.py vision <目录路径> --batch [--prompt "分析提示词"]
```

### vico_editor.py - 剪辑工具

```bash
python ~/.claude/skills/vico-edit/vico_editor.py concat --inputs <视频列表> --output <输出>
python ~/.claude/skills/vico-edit/vico_editor.py mix --video <视频> --bgm <音乐> --output <输出>
python ~/.claude/skills/vico-edit/vico_editor.py transition --inputs <视频1> <视频2> --type <类型> --output <输出>
python ~/.claude/skills/vico-edit/vico_editor.py color --video <视频> --preset <预设> --output <输出>
```

**转场类型**：fade | dissolve | wipeleft | wiperight | wipeup | wipedown | slideleft | slideright | slideup | slidedown | circleopen | circleclose | pixelize | hblur

**调色预设**：warm | cool | vibrant | cinematic | desaturated | vintage

---

## 环境变量

| 变量 | 用途 | 何时需要 |
|------|------|---------|
| YUNWU_API_KEY | Vidu 视频生成 + Gemini 图片生成 | 生成视频/图片时 |
| SUNO_API_KEY | Suno 音乐生成 | 生成 BGM 时 |
| VOLCENGINE_TTS_APP_ID | 火山引擎 TTS | 生成旁白时 |
| VOLCENGINE_TTS_ACCESS_TOKEN | 火山引擎 TTS | 生成旁白时 |
| VISION_API_KEY | 内置视觉分析（非多模态模型 fallback） | Read 工具无法识别图片时 |
| VISION_BASE_URL | 视觉模型 API 地址 | 自定义视觉模型时 |
| VISION_MODEL | 视觉模型名称 | 自定义视觉模型时 |

---

## 文件结构

```
~/vico-projects/{project_name}_{timestamp}/
├── state.json           # 项目状态
├── materials/           # 原始素材
├── analysis/
│   └── analysis.json    # 素材分析
├── creative/
│   └── creative.json    # 创意方案
├── storyboard/
│   └── storyboard.json  # 分镜脚本
├── generated/
│   ├── videos/          # 生成的视频
│   └── music/           # 生成的音乐
└── output/
    └── final.mp4        # 最终视频
```

---

## 错误处理

| 问题 | 处理方式 |
|------|---------|
| 视觉分析失败 | 调用内置 VisionClient，失败则询问用户描述素材内容 |
| API key 未配置 | 首次调用时询问用户 |
| API 调用失败 | 重试 2 次，失败后询问用户 |
| 视频生成失败 | 尝试其他生成模式或使用原始素材 |
| 音乐生成失败 | 生成静音视频并告知用户 |

---

## 依赖

- FFmpeg 6.0+
- Python 3.9+
- httpx

---

## 关键经验总结

### 参考图使用原则（最重要）

⚠️ **用户给的参考图是样貌参考图，不能直接做 img2video 首帧！**

**正确流程**：参考图 → Gemini 生成干净人物图（指定场景/服饰/姿态）→ img2video

**原因**：参考图里的场景、服饰、姿态都是干扰，直接用会把乱七八糟的背景带进虚构叙事视频。

### Gemini 多参考图注意事项

1. **参考图顺序很重要**：重要人物放后面，Gemini 对最后输入的参考图给更多权重
2. **Prompt 要明确**：使用 `Reference for WOMAN (name): MUST preserve exact appearance`
3. **单人镜头**：先用参考图生成干净人物图，再转视频
4. **双人/多人镜头**：先用 Gemini 多参考图合成一张干净的场景图，再转视频

### 人物识别注意事项

1. 一张照片里可能有**多个人物**，需要分别识别和注册
2. 读取图片**内容**，不看文件名
3. 分别提取每个人物的：性别、外貌特征
4. 记录到 personas.json

### 视频生成参数

- text2video 返回：720x1280
- image2video 返回：716x1284（可能不一致）
- **必须在拼接前统一分辨率**（已自动处理）

### 无人镜头生成方式（灵活）

两种方式可选：
- **text2video**：快速，适合简单场景
- **先生图再 img2video**：质量更可控，适合重要场景

根据实际需求选择，不是固定的。