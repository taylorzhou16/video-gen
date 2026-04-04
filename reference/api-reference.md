# API 工具参考

## video_gen_tools.py - API 工具

```bash
# 环境检查
python ~/.claude/skills/video-gen/video_gen_tools.py check

# Storyboard 校验（Phase 4 执行前必须通过）
python ~/.claude/skills/video-gen/video_gen_tools.py validate --storyboard storyboard/storyboard.json

# 视频生成（Kling 后端，默认）
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt <描述> --duration 5 --output <输出>
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <首帧图> --prompt <描述> --output <输出>

# 视频生成（Vidu 后端 - 兜底/快速原型）
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <图片> --prompt <描述> --backend vidu --duration <秒> --output <输出>

# Kling 首尾帧控制
python ~/.claude/skills/video-gen/video_gen_tools.py video --image <首帧图> --tail-image <尾帧图> --prompt "动作描述" --backend kling --duration 5

# Kling 多镜头模式
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "故事描述" --backend kling --multi-shot --shot-type intelligence --duration 10
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "总体描述" --backend kling --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"镜头1描述","duration":"3"},{"index":2,"prompt":"镜头2描述","duration":"4"}]' --duration 7

# 视频生成（Kling Omni 后端 - 参考图模式）
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "人物 <<<image_1>>> 在场景中" --image-list <参考图> --duration 5 --output <输出>

# Kling Omni 多参考图 + 多镜头
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend kling-omni --prompt "故事" --image-list <参考图1> <参考图2> --multi-shot --shot-type customize --multi-prompt '[{"index":1,"prompt":"<<<image_1>>> 镜头1","duration":"3"}]' --duration 7

# 自动后端选择（提供 --image-list 自动用 kling-omni，提供 --tail-image 自动用 kling）
python ~/.claude/skills/video-gen/video_gen_tools.py video --prompt "<<<image_1>>> 在赛场" --image-list ref.jpg --output out.mp4

# Seedance 自动组装模式（推荐：从 storyboard 自动计算时间分段、拼装 prompt、排列 image_urls）
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend seedance --storyboard storyboard/storyboard.json --scene scene_1 --output generated/videos/scene_1.mp4

# Seedance 手动模式（兜底）
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend seedance --prompt "时间分段 prompt..." --image-list frame.png ref.jpg --duration 10 --output out.mp4

# Veo3 文生视频（Google Veo3，仅支持 4/6/8s）
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend veo3 --prompt "描述..." --duration 8 --output out.mp4

# Veo3 图生视频（首帧控制）
python ~/.claude/skills/video-gen/video_gen_tools.py video --backend veo3 --image first_frame.png --prompt "描述..." --duration 8 --output out.mp4

# 音乐生成
python ~/.claude/skills/video-gen/video_gen_tools.py music --prompt <描述> --style <风格> --output <输出>

# TTS 语音
python ~/.claude/skills/video-gen/video_gen_tools.py tts --text <文本> --voice <音色> --output <输出>

# 图片生成
python ~/.claude/skills/video-gen/video_gen_tools.py image --prompt <描述> --style <风格> --output <输出>

# 图片分析（内置多模态能力）
python ~/.claude/skills/video-gen/video_gen_tools.py vision <图片路径> [--prompt "分析提示词"]
python ~/.claude/skills/video-gen/video_gen_tools.py vision <目录路径> --batch [--prompt "分析提示词"]
```

### Kling / Kling Omni 参数说明

| 参数 | 适用后端 | 说明 |
|------|---------|------|
| `--backend kling` | kling | Kling v3 后端（首帧/首尾帧控制） |
| `--backend kling-omni` | kling-omni | Kling Omni 后端（参考图模式） |
| `--image` | kling, vidu | 首帧图片路径（图生视频） |
| `--image-list` | kling-omni | 参考图路径列表（prompt 中用 `<<<image_1>>>` 引用） |
| `--tail-image` | kling | 尾帧图片路径（首尾帧控制） |
| `--multi-shot` | kling, kling-omni | 启用多镜头模式 |
| `--shot-type` | kling, kling-omni | `intelligence`（AI自动）或 `customize`（自定义） |
| `--multi-prompt` | kling, kling-omni | 自定义分镜列表（JSON格式） |
| `--audio` | kling, kling-omni | 启用音画同出 |
| `--mode` | kling, kling-omni | `std`（标准）或 `pro`（高质量） |

### Seedance 参数说明

| 参数 | 说明 |
|------|------|
| `--backend seedance` | 使用 Seedance 后端 |
| `--storyboard` + `--scene` | 自动组装模式：从 storyboard 读取 scene，自动计算时间分段、拼装 prompt、排列 image_urls、对齐 duration |
| `--prompt` | 手动模式：直接指定时间分段 prompt（兜底用） |
| `--image-list` | 手动模式：图片列表（分镜图在前，角色参考图在后） |
| `--duration` | 手动模式：时长（自动对齐到 5/10/15） |

### Veo3 参数说明

| 参数 | 说明 |
|------|------|
| `--backend veo3` | 使用 Veo3 后端（需要 COMPASS_API_KEY） |
| `--prompt` | 视频描述 |
| `--image` | 可选：首帧图片路径（图生视频模式） |
| `--duration` | 时长：仅支持 4/6/8 秒（自动对齐到最接近值） |
| `--aspect-ratio` | 宽高比 |
| `--output` | 输出文件路径 |

**注意**：Veo3 默认生成音频，无需 `--audio` 参数。不支持 `--image-list`、`--multi-shot`、`--tail-image`。

### validate 参数说明

| 参数 | 说明 |
|------|------|
| `--storyboard` | storyboard.json 路径（必填） |

**校验内容**：
- Schema: `scenes[]`、`aspect_ratio` 存在性
- Seedance: scene 总时长必须为 5/10/15
- Veo3: 单 shot 时长必须为 4/6/8
- Kling/Vidu: 单 shot 时长范围
- Backend-mode 一致性
- 参考图文件存在性
- API key 可用性

**输出格式**：`{"valid": bool, "errors": [...], "warnings": [...]}`

---

## video_gen_editor.py - 剪辑工具

```bash
# 拼接（自动校验分辨率 + 归一化）
python ~/.claude/skills/video-gen/video_gen_editor.py concat --inputs <视频列表> --output <输出>

# 音频混合
python ~/.claude/skills/video-gen/video_gen_editor.py mix --video <视频> --bgm <音乐> --output <输出>

# 转场
python ~/.claude/skills/video-gen/video_gen_editor.py transition --inputs <视频1> <视频2> --type <类型> --output <输出>

# 调色
python ~/.claude/skills/video-gen/video_gen_editor.py color --video <视频> --preset <预设> --output <输出>
```

**转场类型**：fade | dissolve | wipeleft | wiperight | wipeup | wipedown | slideleft | slideright | slideup | slidedown | circleopen | circleclose | pixelize | hblur

**调色预设**：warm | cool | vibrant | cinematic | desaturated | vintage

---

## 环境变量

| 变量 | 用途 | 何时需要 |
|------|------|---------|
| COMPASS_API_KEY | Gemini 图片生成 + Gemini TTS + **Veo3 视频** | 图片/TTS/Veo3 视频生成时 |
| FAL_API_KEY | Gemini 图片生成 + Kling-Omni 视频（fal.ai 代理） | 图片/视频生成时（备用） |
| YUNWU_API_KEY | Vidu/Kling/Kling-Omni 视频生成 + 图片生成（yunwu 代理） | 生成视频/图片时（最低优先级备用） |
| KLING_ACCESS_KEY | Kling 视频生成 Access Key | 使用 Kling/Kling Omni 官方 API 时 |
| KLING_SECRET_KEY | Kling 视频生成 Secret Key | 使用 Kling/Kling Omni 官方 API 时 |
| SEEDANCE_API_KEY | Seedance 视频生成（piapi.ai 代理） | 使用 Seedance 后端时 |
| SUNO_API_KEY | Suno 音乐生成 | 生成 BGM 时 |
| VOLCENGINE_TTS_APP_ID | 火山引擎 TTS | 生成旁白时 |
| VOLCENGINE_TTS_ACCESS_TOKEN | 火山引擎 TTS | 生成旁白时 |
| VISION_API_KEY | 内置视觉分析 fallback | Read 工具无法识别图片时 |
| VISION_BASE_URL | 视觉模型 API 地址 | 自定义视觉模型时 |
| VISION_MODEL | 视觉模型名称 | 自定义视觉模型时 |

**Provider 优先级**：
- 图片生成：compass → fal → yunwu
- 视频生成：official → fal → yunwu

API key 可通过环境变量或 `config.json` 配置。
