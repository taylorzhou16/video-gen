# Vico Edit - AI 视频剪辑 Skill

一个 Claude Code Skill，将 AI 视频剪辑能力带入你的对话中。

## 架构

**核心理念**：Claude 本身就是 Director Agent，不需要额外的 Agent 代码。

```
~/.claude/skills/vico-edit/
├── SKILL.md           # 给 Claude 的指令 + prompt 模板
├── vico_tools.py      # API 工具（视频/音乐/TTS/图片生成）
├── vico_editor.py     # FFmpeg 剪辑工具
└── README.md          # 本文件
```

**职责划分**：
- **Claude**：意图识别、创意生成、分镜设计、工作流规划
- **vico_tools.py**：Vidu/Suno/TTS/Gemini API 调用
- **vico_editor.py**：FFmpeg 视频剪辑操作

## 功能

- **素材分析**：自动识别图片/视频内容、场景、情感
- **创意生成**：交互式问题卡片，定制视频创意方案
- **分镜设计**：生成分镜脚本和 Vidu Prompt
- **AI 视频生成**：Vidu Q3 Pro 图生视频/文生视频
- **AI 音乐生成**：Suno V4.5 背景音乐
- **TTS 语音合成**：火山引擎 TTS
- **AI 图片生成**：Gemini 图片生成
- **视频剪辑**：转场、字幕、调色、变速、音频混合

## 安装

```bash
# 复制整个目录到 skills 目录
mkdir -p ~/.claude/skills/vico-edit
cp -r SKILL.md vico_tools.py vico_editor.py README.md requirements.txt ~/.claude/skills/vico-edit/

# 安装依赖
cd ~/.claude/skills/vico-edit && pip install -r requirements.txt
```

## 使用方法

```
/vico-edit <素材目录>
```

### 示例

```bash
# 完整创作流程
/vico-edit ~/Videos/旅行素材/

# 继续上次的项目
/vico-edit ~/vico-projects/trip_20260310/
```

## 工具调用

### vico_tools.py

```bash
# 视频生成
python vico_tools.py video --image <图片> --prompt "<描述>" --duration 5 --output video.mp4

# 音乐生成
python vico_tools.py music --prompt "<描述>" --style "Lo-fi" --output music.mp3

# TTS
python vico_tools.py tts --text "<文本>" --voice female_narrator --output audio.mp3

# 图片生成
python vico_tools.py image --prompt "<描述>" --style cinematic --output image.png
```

### vico_editor.py

```bash
# 拼接
python vico_editor.py concat --inputs v1.mp4 v2.mp4 --output out.mp4

# 字幕
python vico_editor.py subtitle --video video.mp4 --srt subs.srt --output out.mp4

# 音频混合
python vico_editor.py mix --video video.mp4 --bgm music.mp3 --output out.mp4

# 转场
python vico_editor.py transition --inputs v1.mp4 v2.mp4 --type fade --output out.mp4

# 调色
python vico_editor.py color --video video.mp4 --preset warm --output out.mp4

# 变速
python vico_editor.py speed --video video.mp4 --rate 1.5 --output out.mp4
```

## 环境变量

```bash
# Yunwu API - 用于 Vidu 视频生成 + Gemini 图片生成
export YUNWU_API_KEY="your-api-key"

# Suno 音乐生成
export SUNO_API_KEY="your-api-key"

# 火山引擎 TTS
export VOLCENGINE_TTS_APP_ID="your-app-id"
export VOLCENGINE_TTS_ACCESS_TOKEN="your-token"
```

**注意**：Gemini 图片生成也走 Yunwu API，使用同一个 YUNWU_API_KEY。

## 工作流程

```
素材分析 → 创意生成 → 分镜设计 → 内容生成 → 剪辑输出
```

## 输出目录结构

```
~/vico-projects/{project_name}_{timestamp}/
├── state.json              # 项目状态
├── materials/              # 原始素材
├── analysis/               # 分析结果
├── creative/               # 创意方案
├── storyboard/             # 分镜脚本
├── generated/              # 生成的内容
│   ├── videos/
│   └── music/
└── output/                 # 最终视频
```

## 依赖

- FFmpeg 6.0+（视频处理）
- Python 3.9+（工具运行）
- httpx（HTTP 客户端）

## 更新日志

### v1.1.0 (2026-03-10)
- 🐛 修复Suno API `Please enter callBackUrl` 错误，添加缺失的callbackUrl参数
- ✨ 支持Suno V3.5/V4.5模型切换，默认使用更快的V3.5模型
- ✨ 新增requirements.txt依赖管理
- ✨ 优化音乐生成超时处理，提高成功率
- ✨ 完善音频混合功能，自动循环背景音乐匹配视频时长

### v1.0.0 (2026-03-01)
- 🎉 初始版本发布
- ✨ 支持Vidu图生视频/文生视频
- ✨ 支持Suno音乐生成
- ✨ 支持火山引擎TTS语音合成
- ✨ 支持Gemini图片生成
- ✨ 完整的视频剪辑功能（拼接、转场、调色、音频混合等）
- ✨ 自动项目管理和工作流

## License

MIT