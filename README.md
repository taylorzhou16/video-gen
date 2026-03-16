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

## 💡 使用建议

### 推荐模型

**建议使用多模态模型（如 Kimi K2.5）以获得最佳体验。**

多模态模型对素材的理解能力更强，能够更准确地识别图片/视频中的场景、人物、情感和视觉风格。如果你使用的主模型不是多模态的，可以通过调用 `/vision` skill 来补充视觉理解能力。

### 引导模型

目前能力还比较初级，**建议在使用过程中多引导模型**。例如：
- 主动说明想要的视频风格、节奏和情绪
- 对分镜方案提出具体的修改意见
- 在生成过程中及时反馈，帮助模型调整方向

### 项目定位

这个项目的本意是希望充分发挥 Claude Code Agent 的智能能力，给足视频生成相关的所有工具和能力，探索 AI 辅助视频创作的实际效果。**这是一个偏探索性质的项目，仍在不断更新迭代中。** 欢迎尝试各种创意，你的使用反馈将帮助我们持续改进。

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

### v1.2.0 (2026-03-16)
🎯 **分镜流程规范化 & 使用体验优化**

#### 流程规范
- ✅ **视频比例全流程约束**
  - 文生图、图生视频两个阶段的 prompt 强制包含比例信息
  - 9:16/16:9/1:1 不同比例对应明确的中文描述规范
  - 生成前自动检查比例一致性

- ✅ **严格执行分镜规划的生成模式**
  - `generation_mode` 必须在分镜中明确指定，执行阶段严禁改变
  - img2video/text2video/existing 三种模式对应严格的执行规则
  - 违规时立即停止执行并报告错误

- ✅ **台词生成方式明确区分**
  - 同期声（视频模型生成）vs 后期 TTS 旁白的使用场景清晰划分
  - 同期声在 vidu_prompt 中明确描述角色、台词、情绪、语速、声音特质
  - TTS 仅用于场景解说、背景介绍，不用于角色对话

- ✅ **Prompt 详细程度与语言规范**
  - 视频生成 prompt 必须使用中文编写
  - 强制包含运镜描述、运动节奏、画面稳定性、比例保护、台词信息
  - 图片生成 prompt 必须包含场景、主体、光影、风格、比例五要素

- ✅ **素材一致性强制保障**
  - 跨镜头人物必须在 prompt 中包含详细的身份标识和外貌特征描述
  - 关键道具建立物料清单，每个镜头包含完整描述确保一致性
  - 提供人物/道具描述的 Prompt 模板和示例

- ✅ **强制用户确认分镜**
  - 分镜方案必须得到用户明确确认后才能进入执行阶段
  - 详细展示每个镜头的生成模式、prompt、时长、转场等信息
  - state.json 新增 `storyboard_confirmed` 和 `confirmation_details` 字段

#### 文档优化
- 📝 README 新增「使用建议」章节，说明推荐模型、引导技巧、项目定位

### v1.1.0 (2026-03-12)
🔧 **稳定性增强 & 人物管理**

#### 新功能
- ✨ **视频参数自动校验与归一化**
  - 拼接前自动检测所有视频的分辨率、编码、帧率
  - 参数不一致时自动归一化到统一格式（1080x1920 / H.264 / 24fps）
  - 解决不同 API 返回视频分辨率不一致导致的画面卡住问题

- ✨ **人物角色管理器 (PersonaManager)**
  - 管理项目中的人物参考图，保持跨场景人物一致性
  - 自动生成 Vidu/Gemini 可用的 prompt
  - 支持单人/双人镜头的不同策略

#### 文档优化
- 📝 SKILL.md 新增条件性工作流程：
  - 人物识别流程（仅当素材是肖像图时触发）
  - 人物参考图策略（单人/双人镜头处理方案）
  - 视频参数校验流程（拼接前必须执行）
- 📝 添加关键经验总结：Gemini 多参考图注意事项、视频生成参数差异

#### 修复
- 🐛 修复 text2video (720x1280) 和 image2video (716x1284) 分辨率不一致导致的拼接问题

### v1.0.0 (2026-03-10)
🎉 **完整首次发布**

#### 核心功能
- ✨ **AI导演工作流**：完整的视频创作流程 - 素材分析 → 创意确认 → 分镜设计 → 生成 → 剪辑输出
- ✨ **多模态AI生成**：
  - Vidu Q3 Pro 图生视频/文生视频（720p/1080p，最高10秒）
  - Suno V3.5/V4.5 音乐生成（支持自定义风格、时长、纯音乐）
  - 火山引擎 TTS 语音合成（多种音色、情感、语速）
  - Gemini 图片生成（多种风格、比例）
- ✨ **专业剪辑工具**：
  - 视频拼接（自动调整分辨率为9:16/16:9/1:1）
  - 转场效果（16种转场：淡入淡出、叠化、擦除、滑动等）
  - 音频混合（自动循环BGM匹配视频时长、音量调节）
  - 调色预设（温暖、冷色调、鲜艳、电影感、复古等）
  - 变速、字幕支持
- ✨ **自动项目管理**：
  - 自动创建项目目录结构
  - 状态跟踪和断点续做
  - 所有中间产物自动保存
- ✨ **交互式创作**：
  - 素材自动识别和分析
  - 问题卡片式创意确认
  - 分镜方案预览和调整

#### 技术实现
- ✨ 基于httpx的异步API调用，支持并发生成
- ✨ FFmpeg底层视频处理，性能优异
- ✨ 环境自动检查和依赖管理
- ✨ 完善的错误处理和重试机制
- 🐛 修复Suno API callbackUrl缺失问题，全功能可用

## License

MIT