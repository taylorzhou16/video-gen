#!/usr/bin/env python3
"""
Vico Editor - FFmpeg 视频剪辑命令行工具

用法：
  python video_gen_editor.py concat --inputs <video1> <video2> --output <output.mp4>
  python video_gen_editor.py subtitle --video <video> --srt <subtitle.srt> --output <output.mp4>
  python video_gen_editor.py mix --video <video> --bgm <music.mp3> --output <output.mp4>
  python video_gen_editor.py transition --inputs <video1> <video2> --type fade --output <output.mp4>
  python video_gen_editor.py color --video <video> --preset warm --output <output.mp4>
  python video_gen_editor.py speed --video <video> --rate 1.5 --output <output.mp4>
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 300  # 5 分钟


# ============== 工具函数 ==============

async def run_ffmpeg(cmd: List[str], timeout: int = FFMPEG_TIMEOUT) -> Tuple[bool, str]:
    """运行 FFmpeg 命令"""
    logger.info(f"执行: {' '.join(cmd[:10])}...")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return False, f"FFmpeg 超时 ({timeout}秒)"

        if process.returncode == 0:
            return True, "成功"
        else:
            error_msg = stderr.decode()[:500]
            logger.error(f"FFmpeg 错误: {error_msg}")
            return False, error_msg

    except Exception as e:
        return False, str(e)


def get_resolution_for_aspect(aspect: str) -> Tuple[int, int]:
    """获取指定宽高比的分辨率"""
    if aspect == "16:9":
        return (1920, 1080)
    elif aspect == "1:1":
        return (1080, 1080)
    return (1080, 1920)  # 默认 9:16


def get_aspect_from_storyboard(storyboard_path: str) -> Optional[str]:
    """从 storyboard.json 读取 aspect_ratio"""
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("aspect_ratio")
    except Exception:
        return None


async def has_audio_track(video_path: str) -> bool:
    """检测视频是否有音频轨"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        video_path
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return len(stdout.strip()) > 0
    except Exception:
        return False


async def get_video_info(video_path: str) -> Dict[str, Any]:
    """获取视频信息"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return json.loads(stdout.decode())
        return {}
    except Exception as e:
        logger.error(f"获取视频信息失败: {e}")
        return {}


async def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    info = await get_video_info(video_path)
    if info:
        duration = info.get("format", {}).get("duration")
        if duration:
            return float(duration)
    return 0.0


async def get_video_specs(video_path: str) -> Dict[str, Any]:
    """获取视频详细参数"""
    info = await get_video_info(video_path)
    if not info:
        return {"path": video_path, "error": "无法获取视频信息"}

    specs = {"path": video_path}

    # 从 streams 中获取视频参数
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            specs["width"] = stream.get("width", 0)
            specs["height"] = stream.get("height", 0)
            specs["codec"] = stream.get("codec_name", "unknown")
            specs["pix_fmt"] = stream.get("pix_fmt", "unknown")
            # 帧率可能是 "24/1" 或 "23.976" 格式
            fps_str = stream.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                specs["fps"] = round(int(num) / int(den), 3) if int(den) != 0 else 0
            else:
                specs["fps"] = float(fps_str)
            break

    # 时长
    specs["duration"] = float(info.get("format", {}).get("duration", 0))

    return specs


async def validate_videos(video_paths: List[str]) -> Dict[str, Any]:
    """
    校验所有视频参数是否一致

    Returns:
        {
            "consistent": bool,
            "issues": List[str],  # 问题描述
            "specs": List[dict],  # 每个视频的参数
        }
    """
    specs_list = []
    for path in video_paths:
        specs = await get_video_specs(path)
        specs_list.append(specs)

    # 提取关键参数
    resolutions = set()
    codecs = set()
    fps_values = set()
    issues = []

    for specs in specs_list:
        if "error" in specs:
            issues.append(f"视频参数错误: {specs['path']} - {specs['error']}")
            continue

        resolutions.add((specs.get("width", 0), specs.get("height", 0)))
        codecs.add(specs.get("codec", "unknown"))
        fps_values.add(specs.get("fps", 0))

    # 检查一致性
    if len(resolutions) > 1:
        res_str = ", ".join([f"{w}x{h}" for w, h in resolutions])
        issues.append(f"分辨率不一致: {res_str}")

    if len(codecs) > 1:
        issues.append(f"编码不一致: {', '.join(codecs)}")

    if len(fps_values) > 1:
        # 允许轻微的帧率差异（如 23.976 vs 24）
        fps_range = max(fps_values) - min(fps_values)
        if fps_range > 1:
            issues.append(f"帧率差异较大: {', '.join(map(str, fps_values))}")

    return {
        "consistent": len(issues) == 0,
        "issues": issues,
        "specs": specs_list
    }


async def normalize_videos(
    video_paths: List[str],
    output_dir: str,
    aspect: str = "9:16"
) -> List[str]:
    """
    归一化所有视频到统一参数

    统一参数：
    - 分辨率：9:16 → 1080x1920, 16:9 → 1920x1080, 1:1 → 1080x1080
    - 编码：H.264
    - 帧率：24fps
    - 像素格式：yuv420p
    - 音频：统一 48kHz 立体声，无声片段补静音轨

    Returns:
        归一化后的视频路径列表
    """
    w, h = get_resolution_for_aspect(aspect)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    normalized_paths = []
    vf_filter = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"

    for i, video_path in enumerate(video_paths):
        output_file = output_path / f"normalized_{i:03d}.mp4"

        # 检测是否有音频轨
        has_audio = await has_audio_track(video_path)

        if has_audio:
            # 有音频：正常归一化
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", vf_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-r", "24",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-ar", "48000",
                str(output_file)
            ]
        else:
            # 无音频：补静音轨
            logger.info(f"🔇 视频无音频轨，补静音轨: {video_path}")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-vf", vf_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-r", "24",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                str(output_file)
            ]

        success, msg = await run_ffmpeg(cmd)

        if success:
            normalized_paths.append(str(output_file))
            logger.info(f"✅ 视频归一化完成: {output_file}")
        else:
            logger.warning(f"⚠️ 视频归一化失败，使用原文件: {video_path}")
            normalized_paths.append(video_path)

    return normalized_paths


# ============== 拼接视频 ==============

async def concat_videos(
    inputs: List[str],
    output: str,
    aspect: str = "9:16"
) -> Dict[str, Any]:
    """
    拼接多个视频（使用 concat filter，保证音画同步）

    Args:
        inputs: 输入视频路径列表（所有片段必须有音频轨，由 normalize_videos 保证）
        output: 输出视频路径
        aspect: 目标宽高比
    """
    if not inputs:
        return {"success": False, "error": "没有输入视频"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # 如果只有一个视频，直接复制
    if len(inputs) == 1:
        import shutil
        shutil.copy(inputs[0], output)
        return {"success": True, "output": output}

    # 使用 concat filter（所有片段必须有音频轨）
    n = len(inputs)
    filter_str = f"concat=n={n}:v=1:a=1[outv][outa]"

    # 构建输入参数
    input_args = []
    for inp in inputs:
        input_args.extend(["-i", inp])

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ 视频拼接完成: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 添加字幕 ==============

# ASS 颜色格式: &HBBGGRR& (注意是 BGR 顺序)
ASS_COLORS = {
    "white": "&HFFFFFF&",
    "black": "&H000000&",
    "red": "&H0000FF&",
    "green": "&H00FF00&",
    "blue": "&HFF0000&",
    "yellow": "&H00FFFF&",
    "cyan": "&HFFFF00&",
    "magenta": "&HFF00FF&",
}


async def add_subtitles(
    video: str,
    srt: str,
    output: str,
    font_size: int = 40,
    font_color: str = "white",
    position: str = "bottom"
) -> Dict[str, Any]:
    """
    添加字幕到视频

    Args:
        video: 输入视频
        srt: SRT 字幕文件
        output: 输出视频
        font_size: 字体大小
        font_color: 字体颜色
        position: 位置 (bottom/top/center)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"视频不存在: {video}"}
    if not os.path.exists(srt):
        return {"success": False, "error": f"字幕文件不存在: {srt}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    ass_color = ASS_COLORS.get(font_color, font_color)

    subtitle_filter = f"subtitles='{os.path.abspath(srt)}':force_style='FontSize={font_size},PrimaryColour={ass_color},OutlineColour=&H000000&,Outline=2'"

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ 字幕添加完成: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 音频混合 ==============

async def mix_audio(
    video: str,
    output: str,
    bgm: str = None,
    tts: str = None,
    video_volume: float = 0.3,
    bgm_volume: float = 0.6,
    tts_volume: float = 1.0
) -> Dict[str, Any]:
    """
    混合音频

    Args:
        video: 输入视频
        output: 输出视频
        bgm: 背景音乐（可选）
        tts: 旁白音频（可选）
        video_volume: 原视频音量（0-1）
        bgm_volume: BGM 音量（0-1）
        tts_volume: TTS 音量（0-1）
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"视频不存在: {video}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # 构建音频混合滤镜
    audio_inputs = []
    filter_parts = []

    # 原视频音频
    audio_inputs.extend(["-i", video])
    filter_parts.append(f"[0:a]volume={video_volume}[a0]")

    input_idx = 1

    # BGM
    if bgm and os.path.exists(bgm):
        audio_inputs.extend(["-i", bgm])
        # 循环 BGM 以匹配视频时长
        video_duration = await get_video_duration(video)
        filter_parts.append(f"[{input_idx}:a]volume={bgm_volume},aloop=loop=-1:size=2e+09,atrim=duration={video_duration}[a{input_idx}]")
        input_idx += 1

    # TTS
    if tts and os.path.exists(tts):
        audio_inputs.extend(["-i", tts])
        filter_parts.append(f"[{input_idx}:a]volume={tts_volume}[a{input_idx}]")
        input_idx += 1

    # 混合所有音频
    mix_inputs = "".join([f"[a{i}]" for i in range(input_idx)])
    # normalize=0: 禁止FFmpeg自动均一化，保留原始音量比例
    filter_parts.append(f"{mix_inputs}amix=inputs={input_idx}:duration=first:dropout_transition=2:normalize=0[aout]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
    ] + audio_inputs + [
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output
    ]

    success, msg = await run_ffmpeg(cmd, timeout=600)

    if success:
        logger.info(f"✅ 音频混合完成: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 转场效果 ==============

# 支持的转场类型
TRANSITION_TYPES = [
    "fade", "dissolve", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose", "diagtl", "diagtr", "diagbl", "diagbr",
    "pixelize", "hblur", "wipel"
]


async def add_transition(
    inputs: List[str],
    output: str,
    transition_type: str = "fade",
    duration: float = 0.5
) -> Dict[str, Any]:
    """
    添加转场效果

    Args:
        inputs: 输入视频列表（两个）
        output: 输出视频
        transition_type: 转场类型
        duration: 转场时长（秒）
    """
    if len(inputs) != 2:
        return {"success": False, "error": "需要两个输入视频"}

    video1, video2 = inputs

    if not os.path.exists(video1):
        return {"success": False, "error": f"视频不存在: {video1}"}
    if not os.path.exists(video2):
        return {"success": False, "error": f"视频不存在: {video2}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # 验证转场类型
    if transition_type not in TRANSITION_TYPES:
        transition_type = "fade"

    # 获取第一个视频的时长
    duration1 = await get_video_duration(video1)
    if duration1 <= 0:
        return {"success": False, "error": "无法获取视频时长"}

    # 计算转场偏移量
    offset = duration1 - duration

    # 使用 xfade 滤镜
    filter_complex = f"[0:v][1:v]xfade=transition={transition_type}:duration={duration}:offset={offset}[outv];[0:a][1:a]acrossfade=d={duration}[outa]"

    cmd = [
        "ffmpeg", "-y",
        "-i", video1,
        "-i", video2,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output
    ]

    success, msg = await run_ffmpeg(cmd, timeout=600)

    if success:
        logger.info(f"✅ 转场添加完成: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 调色 ==============

COLOR_PRESETS = {
    "warm": "colorbalance=rs=0.1:gs=0:bs=-0.1,eq=contrast=1.1:saturation=1.2",
    "cool": "colorbalance=rs=-0.1:gs=0:bs=0.1,eq=contrast=1.05:saturation=1.1",
    "vibrant": "eq=contrast=1.2:saturation=1.4",
    "cinematic": "curves=preset=vintage,eq=contrast=1.2:saturation=0.9",
    "desaturated": "eq=saturation=0.7",
    "vintage": "curves=preset=vintage,eq=contrast=1.1:saturation=0.8",
}


async def color_grade(
    video: str,
    output: str,
    preset: str = "warm"
) -> Dict[str, Any]:
    """
    视频调色

    Args:
        video: 输入视频
        output: 输出视频
        preset: 调色预设 (warm/cool/vibrant/cinematic/desaturated/vintage)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"视频不存在: {video}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    filter_str = COLOR_PRESETS.get(preset, COLOR_PRESETS["warm"])

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ 调色完成 ({preset}): {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 变速 ==============

def _build_atempo_chain(rate: float) -> str:
    """Build chained atempo filters for rates outside 0.5-2.0 range."""
    filters = []
    remaining = rate
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.4f}")
    return ",".join(filters)


async def change_speed(
    video: str,
    output: str,
    rate: float = 1.0
) -> Dict[str, Any]:
    """
    视频变速

    Args:
        video: 输入视频
        output: 输出视频
        rate: 速度倍率 (0.5=慢放, 2.0=快放)
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"视频不存在: {video}"}
    if rate <= 0:
        return {"success": False, "error": f"倍率必须大于0: {rate}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    video_filter = f"setpts={1/rate}*PTS"
    audio_filter = _build_atempo_chain(rate)

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-filter:v", video_filter,
        "-filter:a", audio_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ 变速完成 ({rate}x): {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 裁剪视频 ==============

async def trim_video(
    video: str,
    output: str,
    start: float = 0,
    duration: float = None
) -> Dict[str, Any]:
    """
    裁剪视频

    Args:
        video: 输入视频
        output: 输出视频
        start: 开始时间（秒）
        duration: 持续时间（秒），None 表示到结尾
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"视频不存在: {video}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video,
    ]

    if duration:
        cmd.extend(["-t", str(duration)])

    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output
    ])

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ 裁剪完成: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 图片生成视频 ==============

async def image_to_video(
    image: str,
    output: str,
    duration: float = 5.0,
    aspect: str = "9:16",
    zoom: bool = True
) -> Dict[str, Any]:
    """
    图片生成视频（Ken Burns 效果）

    Args:
        image: 输入图片
        output: 输出视频
        duration: 时长（秒）
        aspect: 宽高比
        zoom: 是否添加缓慢缩放效果
    """
    if not os.path.exists(image):
        return {"success": False, "error": f"图片不存在: {image}"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    w, h = get_resolution_for_aspect(aspect)

    if zoom:
        # Ken Burns 效果：缓慢缩放
        fps = 25
        total_frames = int(duration * fps)
        filter_str = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.001,1.2)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}"
    else:
        filter_str = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image,
        "-t", str(duration),
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        output
    ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ 图片生成视频完成: {output}")
        return {"success": True, "output": output}
    else:
        return {"success": False, "error": msg}


# ============== 旁白合成 ==============

async def add_narration(
    video: str,
    output: str,
    storyboard: str = None,
    narration_dir: str = None,
    narration_volume: float = 1.0,
    video_volume: float = 1.0
) -> Dict[str, Any]:
    """
    将旁白音频按时间点合成到视频中

    Args:
        video: 输入视频
        output: 输出视频
        storyboard: storyboard.json 路径（包含 narration_segments）
        narration_dir: 旁白音频目录
        narration_volume: 旁白音量
        video_volume: 原视频音量
    """
    if not os.path.exists(video):
        return {"success": False, "error": f"视频不存在: {video}"}

    # 读取 storyboard.json 获取旁白时间点
    narration_segments = []
    if storyboard and os.path.exists(storyboard):
        with open(storyboard, 'r', encoding='utf-8') as f:
            data = json.load(f)
            narration_segments = data.get("narration_segments", [])

    if not narration_segments:
        logger.warning("⚠️ 没有找到 narration_segments，直接复制视频")
        import shutil
        shutil.copy(video, output)
        return {"success": True, "output": output, "warning": "没有旁白分段"}

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # 构建 filter_complex
    # 输入: [0] 视频, [1-N] 旁白音频
    inputs = ["-i", video]
    filter_parts = []

    # 构建音频混合
    audio_mix_parts = [f"[0:a]volume={video_volume}[video]"]

    audio_counter = 0  # 实际添加的音频计数
    for i, seg in enumerate(narration_segments):
        audio_file = None
        if narration_dir:
            # 尝试多种命名格式
            seg_id = seg.get("segment_id", str(i+1))
            possible_paths = [
                os.path.join(narration_dir, f"narr_{seg_id}.mp3"),
                os.path.join(narration_dir, f"narration_{seg_id}.mp3"),
                os.path.join(narration_dir, f"{seg_id}.mp3"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    audio_file = p
                    break

        if not audio_file:
            logger.warning(f"⚠️ 未找到旁白音频: segment {seg_id}")
            continue

        inputs.extend(["-i", audio_file])
        audio_counter += 1

        # 获取时间范围
        time_range = seg.get("overall_time_range", "0-5")
        if isinstance(time_range, str) and "-" in time_range:
            start, end = time_range.split("-")
            start = float(start)
        else:
            start = 0

        # 延迟音频到正确的时间点
        # audio_idx: 视频是输入0，第一个旁白是输入1，第二个是输入2...
        audio_idx = audio_counter
        filter_parts.append(f"[{audio_idx}:a]adelay={int(start*1000)}|{int(start*1000)},volume={narration_volume}[narr{audio_counter}]")
        audio_mix_parts.append(f"[narr{audio_counter}]")

    # 混合所有音频
    if len(audio_mix_parts) > 1:
        # 有旁白音频
        filter_parts.append(f"{''.join(audio_mix_parts)}amix=inputs={len(audio_mix_parts)}:duration=first[aout]")
        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            output
        ]
    else:
        # 没有旁白音频，直接复制
        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-c", "copy",
            output
        ]

    success, msg = await run_ffmpeg(cmd)

    if success:
        logger.info(f"✅ 旁白合成完成: {output}")
        return {"success": True, "output": output, "segments": len(narration_segments)}
    else:
        return {"success": False, "error": msg}


# ============== 命令行入口 ==============

async def cmd_concat(args):
    """拼接命令"""
    # 优先级：命令行 > storyboard.json > 默认值
    aspect = args.aspect
    if aspect is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect = get_aspect_from_storyboard(args.storyboard)
        if aspect:
            logger.info(f"📐 从 storyboard.json 读取宽高比: {aspect}")
    if aspect is None:
        aspect = "9:16"  # 最终默认值
        logger.info(f"📐 使用默认宽高比: {aspect}")

    inputs = args.inputs
    output_dir = Path(args.output).parent

    # 先校验视频参数
    logger.info("🔍 校验视频参数...")
    validation = await validate_videos(inputs)

    if not validation["consistent"]:
        logger.warning(f"⚠️ 视频参数不一致: {validation['issues']}")
        logger.info("🔧 自动归一化视频...")

        # 创建临时目录存放归一化后的视频
        normalize_dir = output_dir / "normalized_temp"
        inputs = await normalize_videos(inputs, str(normalize_dir), aspect)

        # 清理临时文件标记
        args._normalized_dir = normalize_dir

    # 然后拼接
    result = await concat_videos(
        inputs=inputs,
        output=args.output,
        aspect=aspect
    )

    # 清理临时归一化文件
    if hasattr(args, '_normalized_dir') and args._normalized_dir.exists():
        import shutil
        shutil.rmtree(args._normalized_dir)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_subtitle(args):
    """字幕命令"""
    result = await add_subtitles(
        video=args.video,
        srt=args.srt,
        output=args.output,
        font_size=args.font_size,
        font_color=args.font_color,
        position=args.position
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_mix(args):
    """音频混合命令"""
    result = await mix_audio(
        video=args.video,
        output=args.output,
        bgm=args.bgm,
        tts=args.tts,
        video_volume=args.video_volume,
        bgm_volume=args.bgm_volume,
        tts_volume=args.tts_volume
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_transition(args):
    """转场命令"""
    result = await add_transition(
        inputs=args.inputs,
        output=args.output,
        transition_type=args.type,
        duration=args.duration
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_color(args):
    """调色命令"""
    result = await color_grade(
        video=args.video,
        output=args.output,
        preset=args.preset
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_speed(args):
    """变速命令"""
    result = await change_speed(
        video=args.video,
        output=args.output,
        rate=args.rate
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_trim(args):
    """裁剪命令"""
    result = await trim_video(
        video=args.video,
        output=args.output,
        start=args.start,
        duration=args.duration
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_image(args):
    """图片生成视频命令"""
    # 优先级：命令行 > storyboard.json > 默认值
    aspect = args.aspect
    if aspect is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect = get_aspect_from_storyboard(args.storyboard)
        if aspect:
            logger.info(f"📐 从 storyboard.json 读取宽高比: {aspect}")
    if aspect is None:
        aspect = "9:16"  # 最终默认值
        logger.info(f"📐 使用默认宽高比: {aspect}")

    result = await image_to_video(
        image=args.image,
        output=args.output,
        duration=args.duration,
        aspect=aspect,
        zoom=args.zoom
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


async def cmd_narration(args):
    """旁白合成命令"""
    result = await add_narration(
        video=args.video,
        output=args.output,
        storyboard=args.storyboard,
        narration_dir=args.narration_dir,
        narration_volume=args.narration_volume,
        video_volume=args.video_volume
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Editor - FFmpeg 视频剪辑命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # concat 子命令
    concat_parser = subparsers.add_parser("concat", help="拼接视频")
    concat_parser.add_argument("--inputs", "-i", nargs="+", required=True, help="输入视频列表")
    concat_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    concat_parser.add_argument("--aspect", "-a", default=None, help="宽高比（如 16:9, 9:16）")
    concat_parser.add_argument("--storyboard", "-s", help="storyboard.json 路径，自动读取 aspect_ratio")

    # subtitle 子命令
    subtitle_parser = subparsers.add_parser("subtitle", help="添加字幕")
    subtitle_parser.add_argument("--video", "-v", required=True, help="输入视频")
    subtitle_parser.add_argument("--srt", "-s", required=True, help="SRT 字幕文件")
    subtitle_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    subtitle_parser.add_argument("--font-size", type=int, default=40, help="字体大小")
    subtitle_parser.add_argument("--font-color", default="white", help="字体颜色")
    subtitle_parser.add_argument("--position", default="bottom", choices=["bottom", "top", "center"], help="字幕位置")

    # mix 子命令
    mix_parser = subparsers.add_parser("mix", help="音频混合")
    mix_parser.add_argument("--video", "-v", required=True, help="输入视频")
    mix_parser.add_argument("--bgm", "-b", help="背景音乐")
    mix_parser.add_argument("--tts", "-t", help="旁白音频")
    mix_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    mix_parser.add_argument("--video-volume", type=float, default=0.3, help="原视频音量")
    mix_parser.add_argument("--bgm-volume", type=float, default=0.6, help="BGM 音量")
    mix_parser.add_argument("--tts-volume", type=float, default=1.0, help="TTS 音量")

    # transition 子命令
    transition_parser = subparsers.add_parser("transition", help="添加转场")
    transition_parser.add_argument("--inputs", "-i", nargs="+", required=True, help="输入视频列表")
    transition_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    transition_parser.add_argument("--type", "-t", default="fade", choices=TRANSITION_TYPES, help="转场类型")
    transition_parser.add_argument("--duration", "-d", type=float, default=0.5, help="转场时长(秒)")

    # color 子命令
    color_parser = subparsers.add_parser("color", help="视频调色")
    color_parser.add_argument("--video", "-v", required=True, help="输入视频")
    color_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    color_parser.add_argument("--preset", "-p", default="warm", choices=list(COLOR_PRESETS.keys()), help="调色预设")

    # speed 子命令
    speed_parser = subparsers.add_parser("speed", help="视频变速")
    speed_parser.add_argument("--video", "-v", required=True, help="输入视频")
    speed_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    speed_parser.add_argument("--rate", "-r", type=float, default=1.0, help="速度倍率")

    # trim 子命令
    trim_parser = subparsers.add_parser("trim", help="裁剪视频")
    trim_parser.add_argument("--video", "-v", required=True, help="输入视频")
    trim_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    trim_parser.add_argument("--start", "-s", type=float, default=0, help="开始时间(秒)")
    trim_parser.add_argument("--duration", "-d", type=float, help="持续时间(秒)")

    # image 子命令
    image_parser = subparsers.add_parser("image", help="图片生成视频")
    image_parser.add_argument("--image", "-i", required=True, help="输入图片")
    image_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    image_parser.add_argument("--duration", "-d", type=float, default=5.0, help="时长(秒)")
    image_parser.add_argument("--aspect", "-a", default=None, help="宽高比")
    image_parser.add_argument("--storyboard", "-s", help="storyboard.json 路径，自动读取 aspect_ratio")
    image_parser.add_argument("--zoom", action="store_true", help="添加 Ken Burns 缩放效果")

    # narration 子命令
    narration_parser = subparsers.add_parser("narration", help="旁白合成")
    narration_parser.add_argument("--video", "-v", required=True, help="输入视频")
    narration_parser.add_argument("--output", "-o", required=True, help="输出视频路径")
    narration_parser.add_argument("--storyboard", "-s", help="storyboard.json 路径（包含 narration_segments）")
    narration_parser.add_argument("--narration-dir", "-n", help="旁白音频目录")
    narration_parser.add_argument("--narration-volume", type=float, default=1.0, help="旁白音量")
    narration_parser.add_argument("--video-volume", type=float, default=1.0, help="原视频音量")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 运行对应命令
    commands = {
        "concat": cmd_concat,
        "subtitle": cmd_subtitle,
        "mix": cmd_mix,
        "transition": cmd_transition,
        "color": cmd_color,
        "speed": cmd_speed,
        "trim": cmd_trim,
        "image": cmd_image,
        "narration": cmd_narration,
    }

    return asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    sys.exit(main())