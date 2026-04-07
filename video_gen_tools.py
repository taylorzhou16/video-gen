#!/usr/bin/env python3
"""
Vico Tools - 视频创作API命令行工具集

用法：
  python video_gen_tools.py setup                                          # 交互式配置 API provider
  python video_gen_tools.py video --image <path> --prompt <text> --duration <seconds>
  python video_gen_tools.py music --prompt <text> --style <style>
  python video_gen_tools.py tts --text <text> --voice <voice_type>
  python video_gen_tools.py image --prompt <text> --style <style>
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== 图片尺寸验证与处理 ==============

def validate_and_resize_image(
    image_path: str,
    output_path: str = None,
    min_size: int = 720,
    max_size: int = 2048,
    target_size: int = 1280
) -> Dict[str, Any]:
    """
    验证并调整图片尺寸

    Args:
        image_path: 图片路径
        output_path: 输出路径（None 时自动生成）
        min_size: 最小边长限制（小于此值会放大）
        max_size: 最大边长限制（大于此值会缩小）
        target_size: 目标尺寸（放大时使用）

    Returns:
        {
            "success": True,
            "original_size": (w, h),
            "new_size": (w, h),
            "resized": True/False,
            "output_path": "..."
        }
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("⚠️ PIL 未安装，跳过图片尺寸检查")
        return {
            "success": True,
            "original_size": None,
            "new_size": None,
            "resized": False,
            "output_path": image_path
        }

    try:
        img = Image.open(image_path)
        w, h = img.size

        min_dim = min(w, h)
        max_dim = max(w, h)

        need_resize = False
        scale = 1.0

        if min_dim < min_size:
            scale = target_size / min_dim
            need_resize = True
            logger.info(f"📐 图片尺寸过小 {w}x{h}，需要放大到至少 {min_size}px")
        elif max_dim > max_size:
            scale = max_size / max_dim
            need_resize = True
            logger.info(f"📐 图片尺寸过大 {w}x{h}，需要缩小到最多 {max_size}px")

        if need_resize:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)

            if output_path is None:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_resized{ext}"

            img_resized.save(output_path, quality=95)
            logger.info(f"📐 图片尺寸调整: {w}x{h} → {new_w}x{new_h}")

            return {
                "success": True,
                "original_size": (w, h),
                "new_size": (new_w, new_h),
                "resized": True,
                "output_path": output_path
            }

        return {
            "success": True,
            "original_size": (w, h),
            "new_size": (w, h),
            "resized": False,
            "output_path": image_path
        }
    except Exception as e:
        logger.error(f"❌ 图片尺寸处理失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "original_size": None,
            "new_size": None,
            "resized": False,
            "output_path": image_path
        }

# ============== 配置管理 ==============

CONFIG_FILE = Path.home() / ".claude" / "skills" / "video-gen" / "config.json"


def load_config() -> Dict[str, str]:
    """从配置文件加载 API keys"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_config(config: Dict[str, str]):
    """保存配置到文件"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


class Config:
    """从配置文件和环境变量加载配置（配置文件优先）"""

    _cached_config = None

    @classmethod
    def _get_config(cls) -> Dict[str, str]:
        if cls._cached_config is None:
            cls._cached_config = load_config()
        return cls._cached_config

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """优先从配置文件获取，其次环境变量"""
        config = cls._get_config()
        return config.get(key, os.getenv(key, default))

    # Vidu (Yunwu) API
    @property
    def YUNWU_API_KEY(self) -> str:
        return self.get("YUNWU_API_KEY", "")

    YUNWU_BASE_URL: str = os.getenv("YUNWU_BASE_URL", "https://yunwu.ai")
    VIDU_MODEL: str = os.getenv("VIDU_MODEL", "viduq3-pro")
    VIDU_RESOLUTION: str = os.getenv("VIDU_RESOLUTION", "720p")

    # Suno API
    @property
    def SUNO_API_KEY(self) -> str:
        return self.get("SUNO_API_KEY", "")

    SUNO_API_URL: str = os.getenv("SUNO_API_URL", "https://api.sunoapi.org/api/v1")
    SUNO_MODEL: str = os.getenv("SUNO_MODEL", "V3_5")

    # Volcengine TTS
    @property
    def VOLCENGINE_TTS_APP_ID(self) -> str:
        return self.get("VOLCENGINE_TTS_APP_ID", "")

    @property
    def VOLCENGINE_TTS_TOKEN(self) -> str:
        return self.get("VOLCENGINE_TTS_ACCESS_TOKEN", "")

    VOLCENGINE_TTS_CLUSTER: str = os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")

    # Gemini Image（通过 Yunwu API，共用 YUNWU_API_KEY）
    @property
    def GEMINI_API_KEY(self) -> str:
        return self.get("YUNWU_API_KEY", "")

    GEMINI_IMAGE_URL: str = "https://yunwu.ai/v1beta/models/gemini-3.1-flash-image-preview:generateContent"

    # Compass API
    @property
    def COMPASS_API_KEY(self) -> str:
        return self.get("COMPASS_API_KEY", "")

    COMPASS_IMAGE_URL: str = "https://compass.llm.shopee.io/compass-api/v1/publishers/google/models/gemini-3.1-flash-image-preview:generateContent"
    COMPASS_VIDEO_URL: str = "https://compass.llm.shopee.io/compass-api/v1/publishers/google/models/veo-3.1-generate-001"

    # Kling API
    @property
    def KLING_ACCESS_KEY(self) -> str:
        return self.get("KLING_ACCESS_KEY", "")

    @property
    def KLING_SECRET_KEY(self) -> str:
        return self.get("KLING_SECRET_KEY", "")

    KLING_BASE_URL: str = "https://api-beijing.klingai.com"
    KLING_MODEL: str = "kling-v3"  # kling-v3 (v3-omni) 或 kling-v1-5 或 kling-v1

    # fal.ai API
    @property
    def FAL_API_KEY(self) -> str:
        return self.get("FAL_API_KEY", "")

    # Seedance API (via piapi)
    @property
    def SEEDANCE_API_KEY(self) -> str:
        return self.get("SEEDANCE_API_KEY", "")

    SEEDANCE_BASE_URL: str = "https://api.piapi.ai"
    SEEDANCE_MODEL: str = "seedance-2-fast-preview"  # 或 seedance-2-preview（高质量）


Config = Config()


# ============== Storyboard / Creative 读取工具 ==============

def get_aspect_from_storyboard(storyboard_path: str) -> Optional[str]:
    """从 storyboard.json 读取 aspect_ratio"""
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("aspect_ratio")
    except Exception:
        return None


def get_music_config_from_creative(creative_path: str) -> Optional[Dict[str, Any]]:
    """从 creative.json 读取音乐配置"""
    try:
        with open(creative_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            music = data.get("music", {})
            return {
                "need_bgm": music.get("need_bgm", True),
                "style": music.get("style"),
                "prompt": music.get("prompt")  # 可选的详细描述
            }
    except Exception:
        return None


def load_storyboard(storyboard_path: str) -> Optional[Dict[str, Any]]:
    """加载 storyboard.json"""
    try:
        with open(storyboard_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ 无法加载 storyboard: {e}")
        return None


# ============== Storyboard 校验 ==============

VALID_ASPECT_RATIOS = ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]

MODE_BACKEND_MAP = {
    "seedance-video": "seedance",
    "omni-video": "kling-omni",
    "img2video": "kling",
    "text2video": "kling",
    "veo3-text2video": "veo3",
    "veo3-img2video": "veo3",
}

BACKEND_PROVIDER_KEYS = {
    "seedance": ["SEEDANCE_API_KEY"],
    "kling": ["KLING_ACCESS_KEY", "FAL_API_KEY"],
    "kling-omni": ["KLING_ACCESS_KEY", "FAL_API_KEY"],
    "veo3": ["COMPASS_API_KEY"],
}


def validate_storyboard(storyboard_path: str) -> Dict[str, Any]:
    """��验 storyboard.json，返回 {valid, errors, warnings}"""
    errors = []
    warnings = []

    data = load_storyboard(storyboard_path)
    if data is None:
        return {"valid": False, "errors": [f"无法加载文件: {storyboard_path}"], "warnings": []}

    # --- Schema basics ---
    if "scenes" not in data or not isinstance(data.get("scenes"), list):
        errors.append("缺少 scenes 数组")
    if "aspect_ratio" not in data:
        errors.append("缺�� aspect_ratio 字段")
    elif data["aspect_ratio"] not in VALID_ASPECT_RATIOS:
        errors.append(f"aspect_ratio '{data['aspect_ratio']}' 无效，支持: {VALID_ASPECT_RATIOS}")

    scenes = data.get("scenes", [])
    if not scenes:
        errors.append("scenes 数组为空")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    # --- 收集 element IDs ---
    characters = data.get("elements", {}).get("characters", [])
    known_element_ids = {c.get("element_id") for c in characters if c.get("element_id")}

    # --- 逐 Scene 校验 ---
    for scene in scenes:
        scene_id = scene.get("scene_id", "unknown")
        shots = scene.get("shots", [])
        if not shots:
            warnings.append(f"[{scene_id}] 没有 shots")
            continue

        # 收集每个 shot 的后端信息
        seedance_shots = []
        for shot in shots:
            shot_id = shot.get("shot_id", "unknown")
            duration = shot.get("duration")
            backend = shot.get("generation_backend", "")
            mode = shot.get("generation_mode", "")

            # 时长检查
            if duration is None:
                errors.append(f"[{shot_id}] 缺��� duration")
                continue

            # Backend-mode 一致性
            expected_backend = MODE_BACKEND_MAP.get(mode)
            if expected_backend and expected_backend != backend:
                errors.append(
                    f"[{shot_id}] generation_mode '{mode}' 应使用 backend '{expected_backend}'，"
                    f"实际为 '{backend}'"
                )

            # 按后端类型校验时长
            if backend in ("kling", "kling-omni"):
                if duration < 3 or duration > 15:
                    errors.append(f"[{shot_id}] Kling 时长必须 3-15s，当前 {duration}s")
            elif backend == "veo3":
                if duration not in [4, 6, 8]:
                    errors.append(f"[{shot_id}] Veo3 时长必须为 4/6/8s，当前 {duration}s")

            # Seedance shots 收集（后续按 scene 汇总）
            if backend == "seedance":
                seedance_shots.append(shot)

            # 参考图文件存在性
            for ref in shot.get("reference_images", []):
                if ref and not os.path.exists(ref):
                    warnings.append(f"[{shot_id}] ��考图不存在: {ref}")

            # video_prompt 必须存在
            if not shot.get("video_prompt"):
                warnings.append(f"[{shot_id}] 缺少 video_prompt")

            # 角色引用检查
            for char in shot.get("characters", []):
                char_id = char if isinstance(char, str) else char.get("element_id", "")
                if char_id and char_id not in known_element_ids:
                    warnings.append(f"[{shot_id}] 引用了未注册角色: {char_id}")

        # --- Seedance scene 总时长校验 ---
        if seedance_shots:
            scene_total_duration = sum(s.get("duration", 0) for s in seedance_shots)
            if scene_total_duration < 4 or scene_total_duration > 15:
                errors.append(
                    f"[{scene_id}] Seedance scene 总时长必须在 4-15s 范围，当前 {scene_total_duration}s"
                )

    # --- Provider 可用性 ---
    used_backends = set()
    for scene in scenes:
        for shot in scene.get("shots", []):
            b = shot.get("generation_backend")
            if b:
                used_backends.add(b)

    for backend in used_backends:
        required_keys = BACKEND_PROVIDER_KEYS.get(backend, [])
        if required_keys and not any(getattr(Config, k, "") for k in required_keys):
            warnings.append(f"后端 '{backend}' 无可用 API key（需要: {' 或 '.join(required_keys)}）")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ============== Seedance Prompt 自动组装 ==============

def build_seedance_prompt(scene: Dict[str, Any], storyboard: Dict[str, Any]) -> tuple:
    """
    根据 storyboard 的 scene 自动组装 Seedance 时间分段 prompt。

    Returns:
        (prompt: str, image_urls: list[str], duration: int)
    """
    scene_id = scene.get("scene_id", "scene_1")
    shots = scene.get("shots", [])
    aspect_ratio = storyboard.get("aspect_ratio", "16:9")

    # --- 计算总时长 ---
    total_duration = sum(s.get("duration", 0) for s in shots)
    # 校验时长范围（4-15s）
    valid_duration = max(4, min(15, total_duration))
    if valid_duration != total_duration:
        logger.warning(f"⚠️ Scene {scene_id} 总时长 {total_duration}s → 调整为 {valid_duration}s")

    # --- 收集角色参考图 ---
    char_mapping = storyboard.get("character_image_mapping", {})
    characters = storyboard.get("elements", {}).get("characters", [])

    if not char_mapping and characters:
        logger.warning("⚠️ character_image_mapping 为空，角色参考图将不会包含在 prompt 中")

    # 找出此 scene 涉及的角色参考图（保持 image_N 顺序）
    scene_char_refs = []
    scene_char_tags = []
    for char in characters:
        eid = char.get("element_id", "")
        tag = char_mapping.get(eid)
        refs = char.get("reference_images", [])
        if tag and refs:
            scene_char_refs.append(refs[0])
            scene_char_tags.append((tag, char.get("name", ""), eid))

    # --- 查找分镜图 ---
    frame_image = None
    # 优先从第一个 shot 的 reference_images 中查找分镜图
    if shots and shots[0].get("reference_images"):
        first_refs = shots[0]["reference_images"]
        for ref in first_refs:
            if "frame" in ref.lower() or "frames" in ref.lower():
                frame_image = ref
                break
        if not frame_image:
            # 第一张如果不是角色参考图，当作分镜图
            if first_refs[0] not in scene_char_refs:
                frame_image = first_refs[0]

    # --- 组装 image_urls ---
    image_urls = []
    if frame_image:
        image_urls.append(frame_image)
    image_urls.extend(scene_char_refs)

    # --- 组装角色描述行 ---
    char_desc_parts = []
    for tag, name, eid in scene_char_tags:
        tag_str = f"@image{tag.replace('image_', '')}" if tag.startswith("image_") else f"@{tag}"
        char_desc_parts.append(f"{tag_str}（{name}）")
    char_line = "，".join(char_desc_parts) if char_desc_parts else ""

    # --- 组装视角/风格行（从 scene 或首个 shot 提取）---
    visual_style = scene.get("visual_style", "")
    narrative_goal = scene.get("narrative_goal", "")
    style_desc = visual_style or narrative_goal or ""

    # --- 组装时间分段 ---
    time_offset = 0
    segments = []
    for idx, shot in enumerate(shots):
        d = shot.get("duration", 0)
        start = time_offset
        end = time_offset + d
        prompt_text = shot.get("video_prompt", shot.get("description", ""))
        segments.append(f"{start}-{end}s：{prompt_text}；")
        time_offset = end

    # --- 组装完整 prompt ---
    lines = []

    # Referencing line
    if frame_image:
        lines.append(f"Referencing the {scene_id}_frame composition for scene layout and character positioning.")
        lines.append("")

    # 角色参考行
    if char_line:
        lines.append(f"{char_line}，{style_desc}；" if style_desc else f"{char_line}；")
        lines.append("")

    # 整体概述
    scene_desc = scene.get("scene_name", "") or scene.get("narrative_goal", "")
    if scene_desc:
        lines.append(f"整体：{scene_desc}")
        lines.append("")

    # 分段动作
    lines.append(f"分段动作（{valid_duration}s）：")
    lines.extend(segments)
    lines.append("")

    # 比例约束
    ratio_name = "横屏" if aspect_ratio == "16:9" else "竖屏" if aspect_ratio == "9:16" else ""
    lines.append(f"保持{ratio_name}{aspect_ratio}构图，不破坏画面比例")
    lines.append("No background music.")

    prompt = "\n".join(lines)

    logger.info(f"📝 Seedance prompt 自动组装完成 ({scene_id}, {valid_duration}s, {len(image_urls)} images)")
    logger.debug(f"Prompt:\n{prompt}")

    return prompt, image_urls, valid_duration


# ============== Vidu 视频生成（已废弃） ==============


class ViduClient:
    """
    Vidu 视频生成客户端（通过 Yunwu API）

    .. deprecated::
        Vidu 后端已废弃，不再支持。请使用 Kling、Kling-Omni、Seedance 或 Veo3。
        此类保留仅为向后兼容，将在未来版本中删除。
    """

    IMG2VIDEO_PATH = "/ent/v2/img2video"
    TEXT2VIDEO_PATH = "/ent/v2/text2video"
    QUERY_PATH = "/ent/v2/tasks/{task_id}/creations"

    def __init__(self):
        import warnings
        warnings.warn(
            "ViduClient 已废弃，请使用 KlingClient、KlingOmniClient、SeedanceClient 或 Veo3Client",
            DeprecationWarning,
            stacklevel=2
        )
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    async def create_img2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 5,
        resolution: str = None,
        audio: bool = False,
        output: str = None
    ) -> Dict[str, Any]:
        """图生视频"""
        resolution = resolution or Config.VIDU_RESOLUTION

        # 准备图片
        if image_path.startswith(('http://', 'https://')):
            image_input = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"图片不存在: {image_path}"}

            with open(image_path, 'rb') as f:
                image_data = f.read()

            base64_data = base64.b64encode(image_data).decode('utf-8')
            ext = os.path.splitext(image_path)[1].lower()
            # HEIC/HEIF 需要先转换
            if ext in ['.heic', '.heif']:
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                subprocess.run(['ffmpeg', '-i', image_path, '-q:v', '2', tmp_path, '-y'],
                              capture_output=True, check=True)
                with open(tmp_path, 'rb') as f:
                    image_data = f.read()
                os.unlink(tmp_path)
                ext = '.jpg'

            mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                       '.webp': 'image/webp', '.heic': 'image/jpeg', '.heif': 'image/jpeg'}
            mime_type = mime_map.get(ext, 'image/jpeg')
            image_input = f"data:{mime_type};base64,{base64_data}"

        payload = {
            "model": Config.VIDU_MODEL,
            "images": [image_input],
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "audio": audio,
            "off_peak": False,
            "watermark": False
        }

        logger.info(f"📤 创建图生视频任务: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{Config.YUNWU_BASE_URL}{self.IMG2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            task_id = result.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ 任务已创建: {task_id}")

            # 等待完成
            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ 图生视频失败: {e}")
            return {"success": False, "error": str(e)}

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        audio: bool = False,
        output: str = None
    ) -> Dict[str, Any]:
        """文生视频"""
        payload = {
            "model": Config.VIDU_MODEL,
            "prompt": prompt,
            "duration": duration,
            "resolution": Config.VIDU_RESOLUTION,
            "aspect_ratio": aspect_ratio,
            "bgm": audio,
            "off_peak": False,
            "watermark": False
        }

        logger.info(f"📤 创建文生视频任务: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{Config.YUNWU_BASE_URL}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )

            # 如果viduq3-pro不支持，fallback到viduq2
            if response.status_code in [400, 422]:
                payload["model"] = "viduq2"
                response = await self.client.post(
                    f"{Config.YUNWU_BASE_URL}{self.TEXT2VIDEO_PATH}",
                    json=payload,
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )

            response.raise_for_status()
            result = response.json()

            task_id = result.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ 任务已创建: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ 文生视频失败: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """等待任务完成"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ 等待任务完成: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ 任务超时 ({max_wait}秒)")
                return None

            try:
                response = await self.client.get(
                    f"{Config.YUNWU_BASE_URL}{self.QUERY_PATH.format(task_id=task_id)}",
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                state = result.get("state")

                if state == "success":
                    creations = result.get("creations", [])
                    if creations:
                        video_url = creations[0].get("url")
                        logger.info(f"✅ 任务完成 (耗时: {int(elapsed)}秒)")
                        return video_url

                elif state == "failed":
                    logger.error(f"❌ 任务失败: {result.get('fail_reason')}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ 查询失败: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Yunwu Kling 视频生成（已废弃） ==============


class YunwuKlingClient:
    """
    Kling v3 视频生成客户端（通过 Yunwu API）

    .. deprecated::
        Yunwu provider 已废弃，不再支持。请使用 Kling 官方 API 或 fal provider。
        此类保留仅为向后兼容，将在未来版本中删除。

    只支持 kling-v3 模型，用于 text2video 和 img2video。

    与官方 API 的关键差异：
    - 使用 `model` 参数而非 `model_name`
    - Bearer Token 认证（复用 YUNWU_API_KEY）
    - Base URL: https://yunwu.ai
    """

    TEXT2VIDEO_PATH = "/kling/v1/videos/text2video"
    IMAGE2VIDEO_PATH = "/kling/v1/videos/image2video"
    QUERY_PATH = "/kling/v1/videos/text2video/{task_id}"

    MODEL = "kling-v3"  # 固定使用 kling-v3

    def __init__(self):
        import warnings
        warnings.warn(
            "YunwuKlingClient 已废弃，请使用 KlingClient（官方 API）或 fal provider",
            DeprecationWarning,
            stacklevel=2
        )
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.base_url = Config.YUNWU_BASE_URL  # https://yunwu.ai

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        audio: bool = False,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        文生视频

        Args:
            prompt: 视频描述
            duration: 时长（3-15秒）
            mode: std 或 pro
            aspect_ratio: 宽高比 (16:9, 9:16, 1:1)
            audio: 是否生成音频
            multi_shot: 是否多镜头
            shot_type: intelligence（AI自动分镜）或 customize（自定义分镜）
            multi_prompt: 自定义分镜的镜头列表
            output: 输出文件路径
        """
        payload = {
            "model": self.MODEL,  # 注意：yunwu kling-v3 用 model 而非 model_name
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "audio": audio,
            "aspect_ratio": aspect_ratio
        }

        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 创建 Yunwu Kling 文生视频任务: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{self.base_url}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ 任务已创建: {task_id}")

            video_url = await self._wait_for_completion(task_id, "text2video")

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "并发任务数超限，请等待现有任务完成后再试"
            logger.error(f"❌ Yunwu Kling 文生视频失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def create_image2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        audio: bool = False,
        image_tail: str = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        图生视频（支持首尾帧控制）

        Args:
            image_path: 图片路径或URL
            prompt: 视频描述
            duration: 时长（3-15秒）
            mode: std 或 pro
            audio: 是否生成音频
            image_tail: 尾帧图片路径或URL
            output: 输出文件路径
        """
        # 准备图片
        image_url = await self._prepare_image(image_path)

        payload = {
            "model": self.MODEL,
            "image": image_url,
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "audio": audio
        }

        # 首尾帧控制
        if image_tail:
            tail_url = await self._prepare_image(image_tail)
            payload["image_tail"] = tail_url

        logger.info(f"📤 创建 Yunwu Kling 图生视频任务: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{self.base_url}{self.IMAGE2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ 任务已创建: {task_id}")

            video_url = await self._wait_for_completion(task_id, "image2video")

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Yunwu Kling 图生视频失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _prepare_image(self, image_path: str) -> str:
        """准备图片（URL 或 base64）"""
        if image_path.startswith(('http://', 'https://')):
            return image_path

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        # 验证并调整图片尺寸
        result = validate_and_resize_image(image_path)
        if not result["success"]:
            raise ValueError(f"图片处理失败: {result.get('error')}")

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        ext = os.path.splitext(result["output_path"])[1].lower()
        mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
        mime_type = mime_map.get(ext, 'image/jpeg')

        return f"data:{mime_type};base64,{base64_data}"

    async def _wait_for_completion(self, task_id: str, task_type: str = "text2video", max_wait: int = 600) -> Optional[str]:
        """等待任务完成"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)
        if task_type == "image2video":
            query_path = self.IMAGE2VIDEO_PATH + f"/{task_id}"

        logger.info(f"⏳ 等待 Yunwu Kling 任务完成: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ 任务超时 ({max_wait}秒)")
                return None

            try:
                response = await self.client.get(
                    f"{self.base_url}{query_path}",
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.error(f"❌ 任务查询失败: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ 任务完成 (耗时: {int(elapsed)}秒)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ 任务失败: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ 查询失败: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.client.aclose()


class YunwuKlingOmniClient:
    """
    Kling v3 Omni 视频生成客户端（通过 Yunwu API）

    .. deprecated::
        Yunwu provider 已废弃，不再支持。请使用 Kling Omni 官方 API 或 fal provider。
        此类保留仅为向后兼容，将在未来版本中删除。

    只支持 kling-v3-omni 模型，用于多参考图视频生成。

    与官方 API 的关键差异：
    - 使用 `model_name` 参数（与官方 API 相同）
    - Bearer Token 认证（复用 YUNWU_API_KEY）
    - Base URL: https://yunwu.ai
    """

    OMNI_VIDEO_PATH = "/kling/v1/videos/omni-video"
    QUERY_PATH = "/kling/v1/videos/omni-video/{task_id}"

    MODEL = "kling-v3-omni"  # 固定使用 kling-v3-omni

    def __init__(self):
        import warnings
        warnings.warn(
            "YunwuKlingOmniClient 已废弃，请使用 KlingOmniClient（官方 API）或 fal provider",
            DeprecationWarning,
            stacklevel=2
        )
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.base_url = Config.YUNWU_BASE_URL  # https://yunwu.ai

    async def create_omni_video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        audio: bool = False,
        image_list: List[str] = None,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Omni-Video 生成（支持多参考图）

        Args:
            prompt: 视频描述，可使用 <<<image_1>>> 引用图片
            duration: 时长（3-15秒）
            mode: std 或 pro
            aspect_ratio: 宽高比 (16:9, 9:16, 1:1)
            audio: 是否生成音频
            image_list: 图片路径列表，用于角色一致性
            multi_shot: 是否多镜头
            shot_type: intelligence 或 customize
            multi_prompt: 自定义分镜的镜头列表
            output: 输出文件路径
        """
        payload = {
            "model_name": self.MODEL,  # 注意：yunwu kling-v3-omni 用 model_name
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "sound": "on" if audio else "off",  # API规范要求 sound 参数，值为 "on"/"off"
            "aspect_ratio": aspect_ratio
        }

        # 处理 image_list（格式：[{"image_url": url_or_base64}, ...]）
        if image_list:
            processed_images = await self._prepare_image_list(image_list)
            if processed_images:
                payload["image_list"] = processed_images
                logger.info(f"📎 使用 {len(processed_images)} 张参考图")

        # 处理多镜头参数
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 创建 Yunwu Kling Omni-Video 任务: {prompt[:50]}...")

        try:
            response = await self.client.post(
                f"{self.base_url}{self.OMNI_VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ Omni-Video 任务已创建: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "并发任务数超限，请等待现有任务完成后再试"
            logger.error(f"❌ Yunwu Kling Omni-Video 失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _prepare_image_list(self, image_paths: List[str]) -> List[Dict]:
        """准备 image_list 参数"""
        result = []
        for img_path in image_paths:
            try:
                if img_path.startswith(('http://', 'https://')):
                    result.append({"image_url": img_path})
                else:
                    # 本地文件转 base64
                    base64_data = await self._file_to_base64(img_path)
                    if base64_data:
                        result.append({"image_url": base64_data})
            except Exception as e:
                logger.warning(f"⚠️ 参考图处理失败: {img_path}, {e}")
        return result

    async def _file_to_base64(self, file_path: str) -> Optional[str]:
        """文件转 base64（纯base64字符串，供yunwu API使用）"""
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ 文件不存在: {file_path}")
            return None

        # 验证并调整图片尺寸
        result = validate_and_resize_image(file_path)
        if not result["success"]:
            logger.warning(f"⚠️ 图片处理失败: {file_path}, {result.get('error')}")
            return None

        with open(result["output_path"], 'rb') as f:
            image_data = f.read()

        # 返回纯base64字符串（不要data URI前缀）
        # yunwu API期望纯base64，而不是 data:image/xxx;base64,... 格式
        return base64.b64encode(image_data).decode('utf-8')

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """等待任务完成"""
        import time
        start_time = time.monotonic()

        query_path = self.QUERY_PATH.replace("{task_id}", task_id)

        logger.info(f"⏳ 等待 Yunwu Kling Omni 任务完成: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ 任务超时 ({max_wait}秒)")
                return None

            try:
                response = await self.client.get(
                    f"{self.base_url}{query_path}",
                    headers={"Authorization": f"Bearer {Config.YUNWU_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.error(f"❌ 任务查询失败: {result.get('message')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ 任务完成 (耗时: {int(elapsed)}秒)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "unknown")
                    logger.error(f"❌ 任务失败: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ 查询失败: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Kling 视频生成 ==============

class KlingClient:
    """
    Kling 视频生成客户端 (kling-v3)

    使用 /v1/videos/text2video 和 /v1/videos/image2video 端点。
    支持文生视频、图生视频（首帧/首尾帧）、多镜头、音画同出。
    """

    TEXT2VIDEO_PATH = "/v1/videos/text2video"
    IMAGE2VIDEO_PATH = "/v1/videos/image2video"
    TEXT2VIDEO_QUERY_PATH = "/v1/videos/text2video/{task_id}"
    IMAGE2VIDEO_QUERY_PATH = "/v1/videos/image2video/{task_id}"

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
            }
        )
        self._token = None
        self._token_expire = 0

    def _generate_token(self) -> str:
        """生成 JWT 认证 token"""
        import jwt
        import time

        now = int(time.time())
        payload = {
            "iss": Config.KLING_ACCESS_KEY,
            "iat": now,
            "exp": now + 3600,
            "nbf": now - 5
        }
        return jwt.encode(payload, Config.KLING_SECRET_KEY, algorithm="HS256")

    def _get_token(self) -> str:
        """获取有效的 token（带缓存）"""
        import time
        if not self._token or time.time() > self._token_expire - 60:
            self._token = self._generate_token()
            self._token_expire = time.time() + 3600
        return self._token

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        sound: str = "on",
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        文生视频

        Args:
            prompt: 视频描述
            duration: 时长（3-15秒）
            mode: std 或 pro
            aspect_ratio: 宽高比 (16:9, 9:16, 1:1)
            sound: on 或 off
            multi_shot: 是否多镜头
            shot_type: intelligence（AI自动分镜）或 customize（自定义分镜）
            multi_prompt: 自定义分镜的镜头列表，格式 [{"index": 1, "prompt": "...", "duration": "3"}, ...]
            output: 输出文件路径
        """
        payload = {
            "model_name": Config.KLING_MODEL,
            "prompt": prompt,
            "negative_prompt": "",
            "duration": str(duration),
            "mode": mode,
            "sound": sound,
            "aspect_ratio": aspect_ratio
        }

        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 创建 Kling 文生视频任务: {prompt[:50]}...")

        try:
            token = self._get_token()
            response = await self.client.post(
                f"{Config.KLING_BASE_URL}{self.TEXT2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ 任务已创建: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "并发任务数超限，请等待现有任务完成后再试"
            elif "1201" in error_msg:
                error_msg = "模型不支持或参数错误，请检查 model_name 和 mode 参数"
            logger.error(f"❌ Kling 文生视频失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def create_image2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        sound: str = "on",
        tail_image_path: str = None,
        output: str = None,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        图生视频

        Args:
            image_path: 图片路径或URL
            prompt: 视频描述
            duration: 时长（3-15秒）
            mode: std 或 pro
            sound: on 或 off
            tail_image_path: 尾帧图片路径（用于首尾帧控制）
            output: 输出文件路径
            multi_shot: 是否多镜头
            shot_type: 多镜头类型 (intelligence/customize)
            multi_prompt: 多镜头配置列表
        """
        # 准备图片
        if image_path.startswith(('http://', 'https://')):
            image_url = image_path
        else:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"图片不存在: {image_path}"}

            # 验证并调整图片尺寸
            result = validate_and_resize_image(image_path)
            if not result["success"]:
                return {"success": False, "error": f"图片处理失败: {result.get('error')}"}

            processed_path = result["output_path"]

            with open(processed_path, 'rb') as f:
                image_data = f.read()

            ext = os.path.splitext(processed_path)[1].lower()
            if ext in ['.heic', '.heif']:
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                subprocess.run(['ffmpeg', '-i', processed_path, '-q:v', '2', tmp_path, '-y'],
                              capture_output=True, check=True)
                with open(tmp_path, 'rb') as f:
                    image_data = f.read()
                os.unlink(tmp_path)

            image_url = base64.b64encode(image_data).decode('utf-8')

        payload = {
            "model_name": Config.KLING_MODEL,
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": "",
            "duration": str(duration),
            "mode": mode,
            "sound": sound
        }

        # 处理多镜头参数
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt:
                payload["multi_prompt"] = multi_prompt

        # 处理尾帧图片（首尾帧控制）
        if tail_image_path:
            if tail_image_path.startswith(('http://', 'https://')):
                tail_image_url = tail_image_path
            else:
                if not os.path.exists(tail_image_path):
                    return {"success": False, "error": f"尾帧图片不存在: {tail_image_path}"}

                # 验证并调整尾帧图片尺寸
                tail_result = validate_and_resize_image(tail_image_path)
                if not tail_result["success"]:
                    return {"success": False, "error": f"尾帧图片处理失败: {tail_result.get('error')}"}

                with open(tail_result["output_path"], 'rb') as f:
                    tail_image_data = f.read()

                tail_image_url = base64.b64encode(tail_image_data).decode('utf-8')

            payload["image_tail"] = tail_image_url
            logger.info(f"📤 创建 Kling 图生视频任务（含尾帧）: {prompt[:50]}...")
        else:
            logger.info(f"📤 创建 Kling 图生视频任务: {prompt[:50]}...")

        try:
            token = self._get_token()
            response = await self.client.post(
                f"{Config.KLING_BASE_URL}{self.IMAGE2VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ 任务已创建: {task_id}")

            video_url = await self._wait_for_completion(task_id, query_path=self.IMAGE2VIDEO_QUERY_PATH)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "并发任务数超限，请等待现有任务完成后再试"
            elif "1201" in error_msg:
                error_msg = "模型不支持或参数错误，请检查 model_name 和 mode 参数"
            logger.error(f"❌ Kling 图生视频失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, query_path: str = None, max_wait: int = 600) -> Optional[str]:
        """等待任务完成"""
        import time
        if query_path is None:
            query_path = self.TEXT2VIDEO_QUERY_PATH
        start_time = time.monotonic()

        logger.info(f"⏳ 等待 Kling 任务完成: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ 任务超时 ({max_wait}秒)")
                return None

            try:
                token = self._get_token()
                response = await self.client.get(
                    f"{Config.KLING_BASE_URL}{query_path.format(task_id=task_id)}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.warning(f"⚠️ 查询失败: {result.get('message')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                task_status = data.get("task_status")

                # Kling 状态: submitted, processing, succeed, failed
                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ Kling 任务完成 (耗时: {int(elapsed)}秒)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"❌ Kling 任务失败: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ 查询失败: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.client.aclose()


class KlingOmniClient:
    """
    Kling Omni-Video 视频生成客户端 (kling-v3-omni)
    使用 /v1/videos/omni-video 端点，支持 image_list 和 multi_shot

    功能特点：
    - 文生视频（3-15秒）
    - 图生视频（支持 image_list 多参考图）
    - 多镜头视频（multi_shot）
    - 音画同出（sound: on/off）
    """

    OMNI_VIDEO_PATH = "/v1/videos/omni-video"
    QUERY_PATH = "/v1/videos/omni-video/{task_id}"

    DEFAULT_MODEL = "kling-v3-omni"

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
            }
        )
        self._token = None
        self._token_expire = 0

    def _generate_token(self) -> str:
        """生成 JWT 认证 token"""
        import jwt
        import time

        now = int(time.time())
        payload = {
            "iss": Config.KLING_ACCESS_KEY,
            "iat": now,
            "exp": now + 3600,
            "nbf": now - 5
        }
        return jwt.encode(payload, Config.KLING_SECRET_KEY, algorithm="HS256")

    def _get_token(self) -> str:
        """获取有效的 token（带缓存）"""
        import time
        if not self._token or time.time() > self._token_expire - 60:
            self._token = self._generate_token()
            self._token_expire = time.time() + 3600
        return self._token

    def _file_to_base64(self, file_path: str) -> str:
        """将文件转为纯 base64 字符串（不带 data URI 前缀）"""
        with open(file_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode('utf-8')

    async def create_omni_video(
        self,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        aspect_ratio: str = "9:16",
        sound: str = "on",
        image_list: List[str] = None,
        multi_shot: bool = False,
        shot_type: str = None,
        multi_prompt: List[Dict] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        Omni-Video 生成（支持 image_list + multi_shot）

        Args:
            prompt: 视频描述，可使用 <<<image_1>>> 引用图片
            duration: 时长（3-15秒）
            mode: std 或 pro
            aspect_ratio: 宽高比 (16:9, 9:16, 1:1)
            sound: on 或 off
            image_list: 图片路径列表，用于角色一致性
            multi_shot: 是否多镜头
            shot_type: intelligence（AI自动分镜）或 customize（自定义分镜）
            multi_prompt: 自定义分镜的镜头列表，格式 [{"index": 1, "prompt": "...", "duration": "3"}, ...]
            output: 输出文件路径
        """
        payload = {
            "model_name": self.DEFAULT_MODEL,
            "prompt": prompt,
            "negative_prompt": "",
            "duration": str(duration),
            "mode": mode,
            "sound": sound,
            "aspect_ratio": aspect_ratio
        }

        # 处理 image_list（纯 base64，不带 data URI 前缀）
        if image_list:
            processed_images = []
            for img_path in image_list:
                if not os.path.exists(img_path):
                    logger.warning(f"⚠️ 参考图不存在: {img_path}")
                    continue

                # 验证并调整图片尺寸
                result = validate_and_resize_image(img_path)
                if not result["success"]:
                    logger.warning(f"⚠️ 图片处理失败: {img_path}, {result.get('error')}")
                    continue

                processed_images.append({
                    "image_url": self._file_to_base64(result["output_path"])
                })

            payload["image_list"] = processed_images
            logger.info(f"📎 使用 {len(processed_images)} 张参考图")

        # 处理多镜头参数
        if multi_shot:
            payload["multi_shot"] = True
            if shot_type:
                payload["shot_type"] = shot_type
            if multi_prompt and shot_type == "customize":
                payload["multi_prompt"] = multi_prompt

        logger.info(f"📤 创建 Kling Omni-Video 任务: {prompt[:50]}...")

        try:
            token = self._get_token()
            response = await self.client.post(
                f"{Config.KLING_BASE_URL}{self.OMNI_VIDEO_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            result = response.json()

            code = result.get("code")
            if code != 0:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            data = result.get("data", {})
            task_id = data.get("task_id")
            if not task_id:
                return {"success": False, "error": "API未返回task_id"}

            logger.info(f"✅ Omni-Video 任务已创建: {task_id}")

            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": True, "video_url": video_url, "task_id": task_id}

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                error_msg = "并发任务数超限，请等待现有任务完成后再试"
            elif "1201" in error_msg:
                error_msg = "模型不支持或参数错误"
            logger.error(f"❌ Kling Omni-Video 失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """等待任务完成"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ 等待 Kling Omni-Video 任务完成: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ 任务超时 ({max_wait}秒)")
                return None

            try:
                token = self._get_token()
                response = await self.client.get(
                    f"{Config.KLING_BASE_URL}{self.QUERY_PATH.format(task_id=task_id)}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()

                code = result.get("code")
                if code != 0:
                    logger.warning(f"⚠️ 查询失败: {result.get('message')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    task_result = data.get("task_result", {})
                    videos = task_result.get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        logger.info(f"✅ Omni-Video 任务完成 (耗时: {int(elapsed)}秒)")
                        return video_url

                elif task_status == "failed":
                    task_status_msg = data.get("task_status_msg", "Unknown error")
                    logger.error(f"❌ Omni-Video 任务失败: {task_status_msg}")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ 查询失败: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.client.aclose()


class FalKlingClient:
    """
    Kling 视频生成客户端 (通过 fal.ai 代理)

    与官方 Kling API 完全一致：
    - prompt 写法一致
    - 参数字段一致（duration, aspect_ratio, generate_audio 等）
    - 图片输入方式一致

    唯一区别：使用 --provider fal 而非 --provider kling

    支持的功能：
    - 文生视频：只传 prompt
    - 单图生成：传 image_url
    - 多参考图：传 image_urls 列表
    - 首尾帧：传 image_url + tail_image_url
    """

    MODEL_ID = "fal-ai/kling-video/o3/pro/reference-to-video"

    def __init__(self):
        import fal_client
        import httpx
        self.fal_client = fal_client.AsyncClient(key=Config.FAL_API_KEY)
        self.http_client = httpx.AsyncClient(timeout=300.0)

    async def create_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
        image_url: str = None,        # 首帧/单图
        image_urls: List[str] = None,  # 多参考图
        tail_image_url: str = None,    # 尾帧
        output: str = None
    ) -> Dict[str, Any]:
        """
        统一视频生成方法

        Args:
            prompt: 视频描述
            duration: 时长（3-15秒）
            aspect_ratio: 宽高比 (16:9, 9:16, 1:1)
            generate_audio: 是否生成音频
            image_url: 首帧图片（路径或 URL）
            image_urls: 参考图列表（路径或 URL）
            tail_image_url: 尾帧图片（路径或 URL）
            output: 输出文件路径
        """
        payload = {
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio
        }

        # 首帧/单图 (fal.ai 使用 start_image_url)
        if image_url:
            payload["start_image_url"] = self._prepare_image_url(image_url)

        # 多参考图 (fal.ai 使用 image_urls，prompt 中用 @Image1 引用)
        if image_urls:
            payload["image_urls"] = [self._prepare_image_url(img) for img in image_urls]

        # 尾帧 (fal.ai 使用 end_image_url)
        if tail_image_url:
            payload["end_image_url"] = self._prepare_image_url(tail_image_url)

        return await self._submit_and_wait(payload, output)

    def _prepare_image_url(self, image_path: str) -> str:
        """准备图片 URL（本地文件转 data URI）"""
        if image_path.startswith(('http://', 'https://')):
            return image_path
        return self._file_to_data_uri(image_path)

    def _file_to_data_uri(self, file_path: str) -> str:
        """将本地文件转为 data URI 格式的 base64"""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        with open(file_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{ext};base64,{data}"

    async def _submit_and_wait(self, payload: dict, output: str = None) -> Dict[str, Any]:
        """提交任务并等待完成"""
        import time

        logger.info(f"📤 创建 fal Kling 任务: {payload.get('prompt', '')[:50]}...")

        try:
            # 使用 fal_client 提交任务，返回 AsyncRequestHandle
            handle = await self.fal_client.submit(self.MODEL_ID, arguments=payload)
            request_id = handle.request_id
            logger.info(f"✅ fal 任务已提交: {request_id}")
        except Exception as e:
            logger.error(f"❌ fal 任务提交失败: {e}")
            return {"success": False, "error": str(e)}

        # 等待完成
        video_url = await self._wait_for_completion(handle)

        if video_url and output:
            await self._download_file(video_url, output)
            return {"success": True, "video_url": video_url, "output": output, "request_id": request_id}

        return {"success": bool(video_url), "video_url": video_url, "request_id": request_id}

    async def _wait_for_completion(self, handle, max_wait: int = 600) -> Optional[str]:
        """等待任务完成"""
        import time

        logger.info(f"⏳ 等待 fal 任务完成: {handle.request_id}")
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ fal 任务超时 ({max_wait}秒)")
                return None

            try:
                # 使用 handle.status() 检查状态
                status = await handle.status()
                # status 是一个对象，如 InProgress 或 Completed
                status_class = status.__class__.__name__
                logger.info(f"   [{int(elapsed)}s] 状态: {status_class}")

                if status_class == "Completed":
                    # 使用 handle.get() 获取结果
                    result = await handle.get()
                    video_url = result.get("video", {}).get("url")
                    if video_url:
                        logger.info(f"✅ fal 任务完成 (耗时: {int(elapsed)}秒)")
                        return video_url
                    else:
                        logger.error(f"❌ fal 任务结果中无视频URL: {result}")
                        return None
                elif status_class == "Failed":
                    error = getattr(status, 'error', None) or "Unknown error"
                    logger.error(f"❌ fal 任务失败: {error}")
                    return None
            except Exception as e:
                logger.warning(f"   查询状态异常: {e}")

            await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        response = await self.http_client.get(url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.http_client.aclose()


class SeedanceClient:
    """
    Seedance 2 视频生成客户端（通过 piapi.ai 代理）

    核心能力：
    - Text-to-Video: 直接传 prompt（mode: text_to_video）
    - First/Last Frames: 1-2 张图片作为首尾帧（mode: first_last_frames）
    - Omni Reference: 多模态参考 - 图片/视频/音频（mode: omni_reference）

    关键参数：
    - model: "seedance"（固定）
    - task_type: "seedance-2-fast"（快速）或 "seedance-2"（高质量）
    - mode: "text_to_video" | "first_last_frames" | "omni_reference"（必填）
    - duration: 4-15 秒（任意整数）
    - aspect_ratio: 21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | auto
    - image_urls: 最多 12 张参考图
    - video_urls: 最多 1 个参考视频（omni_reference 模式）
    - audio_urls: 音频参考（omni_reference 模式，mp3/wav，≤15s）

    Prompt 语法：
    - 图片引用: "@image1" 引用第一张图片
    - 视频引用: "@video1" 引用视频
    - 音频引用: "@audio1" 引用音频
    """

    TASK_PATH = "/api/v1/task"
    STATUS_PATH = "/api/v1/task/{task_id}"

    VALID_ASPECT_RATIOS = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "auto"]

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_urls: List[str] = None,
        video_urls: List[str] = None,
        audio_urls: List[str] = None,
        mode: str = None,
        model: str = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        提交视频生成任务

        Args:
            prompt: 视频描述（支持 @imageN / @videoN / @audioN 引用）
            duration: 时长（4-15 秒，任意整数）
            aspect_ratio: 宽高比（21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16 | auto）
            image_urls: 参考图列表（最多 12 张）
            video_urls: 参考视频列表（omni_reference 模式）
            audio_urls: 参考音频列表（omni_reference 模式，mp3/wav，≤15s）
            mode: 生成模式（text_to_video | first_last_frames | omni_reference）
            model: "seedance-2-fast" 或 "seedance-2"
            output: 输出文件路径
        """
        # 自动推断 mode
        if mode is None:
            if video_urls or audio_urls:
                mode = "omni_reference"
            elif image_urls and len(image_urls) <= 2:
                mode = "omni_reference"  # 默认用 omni_reference 而非 first_last_frames
            else:
                mode = "text_to_video"

        # duration 校验（4-15）
        duration = max(4, min(15, duration))

        # aspect_ratio 校验
        if aspect_ratio not in self.VALID_ASPECT_RATIOS:
            logger.warning(f"⚠️ aspect_ratio {aspect_ratio} 不在支持列表中，使用 16:9")
            aspect_ratio = "16:9"

        model = model or Config.SEEDANCE_MODEL

        payload = {
            "model": "seedance",
            "task_type": model,
            "input": {
                "prompt": prompt,
                "mode": mode,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
            }
        }

        # 准备参考资源
        if image_urls:
            payload["input"]["image_urls"] = [self._prepare_url(img) for img in image_urls]

        if video_urls:
            payload["input"]["video_urls"] = [self._prepare_url(v) for v in video_urls]

        if audio_urls:
            payload["input"]["audio_urls"] = [self._prepare_url(a) for a in audio_urls]

        logger.info(f"📤 创建 Seedance 任务: {prompt[:80]}...")
        logger.info(f"   参数: mode={mode}, duration={duration}s, aspect_ratio={aspect_ratio}, model={model}")

        try:
            response = await self.client.post(
                f"{Config.SEEDANCE_BASE_URL}{self.TASK_PATH}",
                json=payload,
                headers={"Authorization": f"Bearer {Config.SEEDANCE_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            task_id = result.get("data", {}).get("task_id")
            if not task_id:
                error = result.get("data", {}).get("error", {})
                logger.error(f"❌ API 未返回 task_id: {error}")
                return {"success": False, "error": error.get("message", "Unknown error")}

            logger.info(f"✅ Seedance 任务已创建: {task_id}")

            # 等待完成
            video_url = await self._wait_for_completion(task_id)

            if video_url and output:
                await self._download_file(video_url, output)
                return {"success": True, "video_url": video_url, "output": output, "task_id": task_id}

            return {"success": bool(video_url), "video_url": video_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ Seedance 任务失败: {e}")
            return {"success": False, "error": str(e)}

    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_urls: List[str] = None,
        output: str = None
    ) -> Dict[str, Any]:
        """
        完整视频生成流程（快捷方法）
        """
        return await self.submit_task(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            image_urls=image_urls,
            output=output
        )

    async def check_task(self, task_id: str) -> Dict[str, Any]:
        """查询任务状态"""
        try:
            response = await self.client.get(
                f"{Config.SEEDANCE_BASE_URL}{self.STATUS_PATH.format(task_id=task_id)}",
                headers={"Authorization": f"Bearer {Config.SEEDANCE_API_KEY}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"⚠️ 查询任务状态失败: {e}")
            return {"error": str(e)}

    def _prepare_url(self, path: str) -> str:
        """准备 URL（本地文件转 data URI）"""
        if path.startswith(('http://', 'https://')):
            return path
        return self._file_to_data_uri(path)

    def _file_to_data_uri(self, file_path: str) -> str:
        """将本地文件转为 data URI 格式的 base64

        注意：piapi.ai 对请求体大小有限制，大图片需要压缩
        """
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        max_size = 100 * 1024  # 100KB 阈值

        if file_size > max_size:
            # 压缩图片
            logger.info(f"📦 图片较大 ({file_size/1024:.1f}KB)，正在压缩...")
            try:
                from PIL import Image
                import io

                img = Image.open(file_path)
                # 缩小到 512x512 以内
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                # 转为 RGB（去除 alpha 通道）
                img = img.convert('RGB')

                # 保存为 JPEG
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=70)
                data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                logger.info(f"✅ 压缩完成 ({len(data)/1024:.1f}KB)")
                return f"data:image/jpeg;base64,{data}"
            except Exception as e:
                logger.warning(f"⚠️ 图片压缩失败，使用原始图片: {e}")

        # 小图片直接读取
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        with open(file_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{ext};base64,{data}"

    async def _wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[str]:
        """等待任务完成"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ 等待 Seedance 任务完成: {task_id}")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Seedance 任务超时 ({max_wait}秒)")
                return None

            try:
                result = await self.check_task(task_id)
                data = result.get("data", {})
                status = data.get("status", "unknown")

                logger.info(f"   [{int(elapsed)}s] 状态: {status}")

                if status == "completed":
                    video_url = data.get("output", {}).get("video")
                    if video_url:
                        logger.info(f"✅ Seedance 任务完成 (耗时: {int(elapsed)}秒)")
                        return video_url
                    else:
                        logger.error(f"❌ 结果中无视频 URL: {data}")
                        return None

                elif status == "failed":
                    error = data.get("error", {})
                    logger.error(f"❌ Seedance 任务失败: {error.get('message', 'Unknown')}")
                    return None

                await asyncio.sleep(10)

            except Exception as e:
                logger.warning(f"⚠️ 查询异常: {e}")
                await asyncio.sleep(10)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.client.aclose()


class Veo3Client:
    """Google Veo3 视频生成客户端（通过 Compass 代理）"""

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
        self.api_key = Config.COMPASS_API_KEY
        self.base_url = Config.COMPASS_VIDEO_URL

    async def close(self):
        await self.client.aclose()

    async def create_text2video(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output: str = "output.mp4"
    ) -> Dict[str, Any]:
        """文生视频"""
        return await self._generate(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            output=output
        )

    async def create_image2video(
        self,
        image_path: str,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output: str = "output.mp4"
    ) -> Dict[str, Any]:
        """图生视频（首帧图）"""
        image_data = self._encode_image(image_path)
        instance = {
            "prompt": prompt,
            "image": {
                "inlineData": {
                    "mimeType": self._get_mime_type(image_path),
                    "data": image_data
                }
            }
        }
        return await self._generate(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            output=output,
            instance_override=instance
        )

    async def _generate(
        self,
        prompt: str,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        output: str = "output.mp4",
        instance_override: Dict = None
    ) -> Dict[str, Any]:
        """核心生成流程：提交 → 轮询 → 下载"""
        # 校验时长
        valid_durations = [4, 6, 8]
        if duration not in valid_durations:
            closest = min(valid_durations, key=lambda x: abs(x - duration))
            logger.warning(f"⚠️ Veo3 duration {duration}s 不支持，调整为 {closest}s")
            duration = closest

        instance = instance_override or {"prompt": prompt}
        if "prompt" not in instance:
            instance["prompt"] = prompt

        payload = {
            "instances": [instance],
            "parameters": {
                "aspectRatio": aspect_ratio,
                "durationSeconds": duration,
                "personGeneration": "allow_all"
            }
        }

        logger.info(f"📤 Veo3 视频生成: {prompt[:50]}... ({duration}s, {aspect_ratio})")

        try:
            response = await self.client.post(
                f"{self.base_url}:predictLongRunning",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            return {"success": False, "error": f"Veo3 提交失败: {e}"}

        operation_name = result.get("name")
        if not operation_name:
            return {"success": False, "error": f"无 operation name: {result}"}

        logger.info(f"⏳ 任务已提交，等待生成...")

        # 轮询
        video_url = await self._wait_for_completion(operation_name)
        if not video_url:
            return {"success": False, "error": "Veo3 生成失败或超时"}

        # 下载
        await self._download_file(video_url, output)
        return {
            "success": True,
            "output": output,
            "video_url": video_url,
            "duration": duration
        }

    async def _wait_for_completion(self, operation_name: str, max_wait: int = 600) -> Optional[str]:
        """轮询任务状态"""
        import time
        start_time = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ Veo3 任务超时 ({max_wait}秒)")
                return None

            try:
                response = await self.client.post(
                    f"{self.base_url}:fetchPredictOperation",
                    json={"operationName": operation_name},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                )
                response.raise_for_status()
                result = response.json()

                if result.get("done"):
                    # 检查是否有错误
                    if "error" in result:
                        error_msg = result["error"].get("message", "Unknown error")
                        logger.error(f"❌ Veo3 任务失败: {error_msg}")
                        return None

                    # 提取视频 URL
                    videos = result.get("response", {}).get("videos", [])
                    if videos:
                        video_url = videos[0].get("uri") or videos[0].get("gcsUri")
                        cost = result.get("priceCostUsd", 0)
                        logger.info(f"✅ Veo3 生成完成 (耗时: {int(elapsed)}秒, 费用: ${cost})")
                        return video_url
                    else:
                        logger.error(f"❌ 响应中无视频: {result}")
                        return None

                logger.info(f"   [{int(elapsed)}s] 生成中...")
                await asyncio.sleep(10)

            except Exception as e:
                logger.warning(f"⚠️ 轮询异常: {e}")
                await asyncio.sleep(10)

    async def _download_file(self, url: str, output_path: str):
        """下载视频文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0) as dl_client:
            response = await dl_client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    def _encode_image(self, image_path: str) -> str:
        """将图片编码为 base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _get_mime_type(self, image_path: str) -> str:
        """获取图片 MIME 类型"""
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
        return mime_map.get(ext, 'image/png')


class SunoClient:
    """Suno 音乐生成客户端"""

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        style: str = "Lo-fi, Chill",
        instrumental: bool = True,
        output: str = None
    ) -> Dict[str, Any]:
        """生成音乐"""
        payload = {
            "prompt": prompt,
            "instrumental": instrumental,
            "model": Config.SUNO_MODEL,
            "customMode": True,
            "style": style,
            "callbackUrl": "https://example.com/callback"
        }

        # 截断过长的 prompt（避免日志太长），不影响传给 API 的参数
        display_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
        logger.info(f"📤 创建音乐生成任务 - 描述: {display_prompt}, 风格: {style}")

        try:
            response = await self.client.post(
                f"{Config.SUNO_API_URL}/generate",
                json=payload,
                headers={"Authorization": f"Bearer {Config.SUNO_API_KEY}"}
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return {"success": False, "error": result.get("msg", "Unknown error")}

            task_id = result["data"]["taskId"]
            logger.info(f"✅ 任务已创建: {task_id}")

            audio_url = await self._wait_for_completion(task_id)

            if audio_url and output:
                await self._download_file(audio_url, output)
                return {"success": True, "audio_url": audio_url, "output": output}

            return {"success": True, "audio_url": audio_url, "task_id": task_id}

        except Exception as e:
            logger.error(f"❌ 音乐生成失败: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_completion(self, task_id: str, max_wait: int = 300) -> Optional[str]:
        """等待任务完成"""
        import time
        start_time = time.monotonic()

        logger.info(f"⏳ 等待音乐生成...")

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > max_wait:
                logger.error(f"❌ 任务超时 ({max_wait}秒)")
                return None

            try:
                response = await self.client.get(
                    f"{Config.SUNO_API_URL}/generate/record-info?taskId={task_id}",
                    headers={"Authorization": f"Bearer {Config.SUNO_API_KEY}"}
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") != 200:
                    logger.warning(f"⚠️ 查询失败: {result.get('msg')}")
                    await asyncio.sleep(5)
                    continue

                data = result.get("data", {})
                status = data.get("status")

                if status == "SUCCESS":
                    tracks = data.get("response", {}).get("sunoData", [])
                    if tracks:
                        audio_url = tracks[0].get("audioUrl")
                        logger.info(f"✅ 音乐生成完成 (耗时: {int(elapsed)}秒)")
                        return audio_url

                elif status == "FAILED":
                    logger.error("❌ 音乐生成失败")
                    return None

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"⚠️ 查询失败: {e}")
                await asyncio.sleep(5)

    async def _download_file(self, url: str, output_path: str):
        """下载文件"""
        import httpx
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
        logger.info(f"✅ 已保存到: {output_path}")

    async def close(self):
        await self.client.aclose()


# ============== Volcengine TTS（已废弃） ==============


class TTSClient:
    """
    火山引擎 TTS 客户端

    .. deprecated::
        火山引擎 TTS 已废弃，不再支持。请使用 Gemini TTS（需要 COMPASS_API_KEY）。
        此类保留仅为向后兼容，将在未来版本中删除。
    """

    API_URL = "https://openspeech.bytedance.com/api/v1/tts"

    VOICE_TYPES = {
        "female_narrator": "BV700_streaming",
        "female_gentle": "BV034_streaming",
        "male_narrator": "BV701_streaming",
        "male_warm": "BV033_streaming",
    }

    EMOTION_MAP = {
        "neutral": None,
        "happy": "happy",
        "sad": "sad",
        "gentle": "gentle",
        "serious": "serious",
    }

    def __init__(self):
        import warnings
        warnings.warn(
            "TTSClient（火山引擎）已废弃，请使用 GeminiTTSClient",
            DeprecationWarning,
            stacklevel=2
        )

    async def synthesize(
        self,
        text: str,
        output: str,
        voice: str = "female_narrator",
        emotion: str = None,
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """合成语音"""
        import httpx

        voice_type = self.VOICE_TYPES.get(voice, voice)

        payload = {
            "app": {
                "appid": Config.VOLCENGINE_TTS_APP_ID,
                "token": "access_token",
                "cluster": Config.VOLCENGINE_TTS_CLUSTER,
            },
            "user": {"uid": "vico_tts_user"},
            "audio": {
                "voice_type": voice_type,
                "encoding": "mp3",
                "rate": 24000,
                "speed_ratio": speed,
                "volume_ratio": 1.0,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }

        if emotion and emotion in self.EMOTION_MAP and self.EMOTION_MAP[emotion]:
            payload["audio"]["emotion"] = self.EMOTION_MAP[emotion]

        logger.info(f"📤 TTS合成: {text[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.API_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer;{Config.VOLCENGINE_TTS_TOKEN}",
                    }
                )
                response.raise_for_status()
                result = response.json()

            code = result.get("code", -1)
            if code != 3000:
                return {"success": False, "error": result.get("message", f"API error: {code}")}

            audio_data = base64.b64decode(result.get("data", ""))
            if not audio_data:
                return {"success": False, "error": "Empty audio data"}

            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "wb") as f:
                f.write(audio_data)

            duration_ms = int(result.get("addition", {}).get("duration", "0"))
            logger.info(f"✅ TTS已保存: {output} ({duration_ms}ms)")

            return {"success": True, "output": output, "duration_ms": duration_ms}

        except Exception as e:
            logger.error(f"❌ TTS失败: {e}")
            return {"success": False, "error": str(e)}


# ============== Gemini TTS（通过 Compass API）==============

class GeminiTTSClient:
    """Gemini TTS 客户端（通过 Compass API）"""

    # Gemini TTS 音色
    VOICE_TYPES = {
        # 女声
        "female_narrator": ("Kore", "cmn-CN"),      # 标准女声
        "female_gentle": ("Aoede", "cmn-CN"),        # 清亮女声
        "female_soft": ("Zephyr", "cmn-CN"),         # 柔和女声
        "female_bright": ("Leda", "cmn-CN"),         # 明亮女声
        # 男声
        "male_narrator": ("Charon", "cmn-CN"),       # 标准男声
        "male_warm": ("Orus", "cmn-CN"),             # 稳重男声
        "male_deep": ("Fenrir", "cmn-CN"),           # 深沉男声
        "male_bright": ("Puck", "cmn-CN"),           # 明亮男声
    }

    async def synthesize(
        self,
        text: str,
        output: str,
        voice: str = "female_narrator",
        emotion: str = None,
        speed: float = 1.0,
        prompt: str = None,
        language_code: str = "cmn-CN",
    ) -> Dict[str, Any]:
        """合成语音

        Args:
            text: 要朗读的文本，支持 inline 情感标注如 [brightly], [sigh], [pause]
            output: 输出文件路径
            voice: 音色名称或预设（female_narrator, male_narrator 等）
            emotion: 已废弃，请使用 prompt 或 inline 标注
            speed: 语速（Gemini TTS 暂不支持）
            prompt: 风格指令，控制口音/情感/语气/人设
            language_code: 语言代码（cmn-CN, en-US, ja-JP 等）
        """
        from google.cloud import texttospeech
        from google.api_core import client_options

        if not Config.COMPASS_API_KEY:
            return {
                "success": False,
                "error": "COMPASS_API_KEY 未配置",
                "hint": "请在 config.json 中添加 COMPASS_API_KEY"
            }

        # 获取音色配置
        voice_name = voice
        lang_code = language_code
        if voice in self.VOICE_TYPES:
            voice_name, lang_code = self.VOICE_TYPES[voice]

        logger.info(f"📤 Gemini TTS合成: {text[:30]}... (voice: {voice_name})")

        try:
            # 创建客户端
            client = texttospeech.TextToSpeechClient(
                client_options=client_options.ClientOptions(
                    api_endpoint="https://compass.llm.shopee.io/compass-api/v1",
                    api_key=Config.COMPASS_API_KEY,
                ),
                transport="rest",
            )

            # 构建输入
            synthesis_input = texttospeech.SynthesisInput(text=text)
            if prompt:
                synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

            # 音色配置
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name,
                model_name="gemini-2.5-flash-tts",
            )

            # 音频配置
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
            )

            # 合成语音
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            # 保存文件
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "wb") as f:
                f.write(response.audio_content)

            # 估算时长（约 15KB/秒）
            duration_ms = int(len(response.audio_content) / 15 * 1000)
            logger.info(f"✅ Gemini TTS已保存: {output} (约 {duration_ms}ms)")

            return {"success": True, "output": output, "duration_ms": duration_ms}

        except Exception as e:
            logger.error(f"❌ Gemini TTS失败: {e}")
            return {"success": False, "error": str(e)}


# ============== Gemini 图片生成（通过 Yunwu API）==============

class ImageClient:
    """Gemini 图片生成客户端（通过 Yunwu API）"""

    STYLE_PRESETS = {
        "cinematic": "cinematic style, film grain, dramatic lighting, movie still",
        "realistic": "photorealistic, natural lighting, high detail, 8k",
        "anime": "anime style, vibrant colors, clean lines, studio ghibli inspired",
        "artistic": "artistic style, painterly, expressive brushstrokes, impressionist",
    }

    async def generate(
        self,
        prompt: str,
        output: str = None,
        style: str = "cinematic",
        aspect_ratio: str = "9:16",
        reference_images: List[str] = None
    ) -> Dict[str, Any]:
        """生成图片，支持多参考图"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # 构建 parts 数组
        parts = []

        # 添加参考图（Gemini 对最后的参考图给更多权重，所以重要人物放后面）
        if reference_images:
            for ref_path in reference_images:
                if os.path.exists(ref_path):
                    with open(ref_path, 'rb') as f:
                        img_data = f.read()
                    ext = os.path.splitext(ref_path)[1].lower()
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
                    mime_type = mime_map.get(ext, 'image/jpeg')
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(img_data).decode('utf-8')
                        }
                    })

        # 添加文本 prompt
        parts.append({"text": full_prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "responseMimeType": "text/plain",
            }
        }

        ref_info = f" (with {len(reference_images)} reference images)" if reference_images else ""
        logger.info(f"📤 图片生成{ref_info}: {prompt[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    Config.GEMINI_IMAGE_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": Config.GEMINI_API_KEY,
                    }
                )
                response.raise_for_status()
                result = response.json()

            candidates = result.get("candidates", [])
            if not candidates:
                return {"success": False, "error": "No image generated"}

            parts = candidates[0].get("content", {}).get("parts", [])
            image_data = None
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"].get("data")
                    break

            if not image_data:
                return {"success": False, "error": "No image data in response"}

            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                with open(output, "wb") as f:
                    f.write(base64.b64decode(image_data))
                logger.info(f"✅ 图片已保存: {output}")
                return {"success": True, "output": output}

            return {"success": True, "image_base64": image_data}

        except Exception as e:
            logger.error(f"❌ 图片生成失败: {e}")
            return {"success": False, "error": str(e)}


class FalImageClient:
    """
    Gemini 图片生成客户端（通过 fal.ai API）

    .. deprecated::
        Fal Image 已废弃，不再支持。请使用 CompassImageClient（需要 COMPASS_API_KEY）。
    """

    def __init__(self):
        import warnings
        warnings.warn(
            "FalImageClient 已废弃，请使用 CompassImageClient",
            DeprecationWarning,
            stacklevel=2
        )

    FAL_IMAGE_URL = "https://fal.run/fal-ai/gemini-3.1-flash-image-preview"
    FAL_IMAGE_EDIT_URL = "https://fal.run/fal-ai/gemini-3.1-flash-image-preview/edit"

    STYLE_PRESETS = {
        "cinematic": "cinematic style, film grain, dramatic lighting, movie still",
        "realistic": "photorealistic, natural lighting, high detail, 8k",
        "anime": "anime style, vibrant colors, clean lines, studio ghibli inspired",
        "artistic": "artistic style, painterly, expressive brushstrokes, impressionist",
    }

    # fal 支持的 aspect_ratio
    ASPECT_RATIOS = ["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16", "4:1", "1:4", "8:1", "1:8"]

    async def generate(
        self,
        prompt: str,
        output: str = None,
        style: str = "cinematic",
        aspect_ratio: str = "9:16",
        reference_images: List[str] = None
    ) -> Dict[str, Any]:
        """生成图片，支持多参考图"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # fal 的 aspect_ratio 格式
        fal_aspect = aspect_ratio if aspect_ratio in self.ASPECT_RATIOS else "auto"

        payload = {
            "prompt": full_prompt,
            "aspect_ratio": fal_aspect,
            "num_images": 1,
        }

        # 图生图模式：有参考图时使用 edit endpoint
        is_edit_mode = reference_images and len(reference_images) > 0
        url = self.FAL_IMAGE_EDIT_URL if is_edit_mode else self.FAL_IMAGE_URL

        if is_edit_mode:
            # 上传参考图到临时存储或使用 base64
            image_urls = []
            for ref_path in reference_images:
                if os.path.exists(ref_path):
                    # 转换为 base64 data URI
                    with open(ref_path, 'rb') as f:
                        img_data = f.read()
                    ext = os.path.splitext(ref_path)[1].lower()
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
                    mime_type = mime_map.get(ext, 'image/jpeg')
                    data_uri = f"data:{mime_type};base64,{base64.b64encode(img_data).decode('utf-8')}"
                    image_urls.append(data_uri)

            payload["image_urls"] = image_urls
            logger.info(f"📤 图片生成（fal edit，{len(image_urls)} 参考图）: {prompt[:30]}...")
        else:
            logger.info(f"📤 图片生成（fal t2i）: {prompt[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Key {Config.FAL_API_KEY}",
                    }
                )
                response.raise_for_status()
                result = response.json()

            images = result.get("images", [])
            if not images:
                return {"success": False, "error": "No image generated"}

            image_url = images[0].get("url")
            if not image_url:
                return {"success": False, "error": "No image URL in response"}

            # 下载图片
            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as dl_client:
                    dl_resp = await dl_client.get(image_url)
                    dl_resp.raise_for_status()
                    with open(output, "wb") as f:
                        f.write(dl_resp.content)
                logger.info(f"✅ 图片已保存: {output}")
                return {"success": True, "output": output, "url": image_url}

            return {"success": True, "url": image_url}

        except Exception as e:
            logger.error(f"❌ 图片生成失败: {e}")
            return {"success": False, "error": str(e)}


class CompassImageClient:
    """Gemini 图片生成客户端（通过 Compass API）"""

    STYLE_PRESETS = {
        "cinematic": "cinematic style, film grain, dramatic lighting, movie still",
        "realistic": "photorealistic, natural lighting, high detail, 8k",
        "anime": "anime style, vibrant colors, clean lines, studio ghibli inspired",
        "artistic": "artistic style, painterly, expressive brushstrokes, impressionist",
    }

    async def generate(
        self,
        prompt: str,
        output: str = None,
        style: str = "cinematic",
        aspect_ratio: str = "9:16",
        reference_images: List[str] = None
    ) -> Dict[str, Any]:
        """生成图片，支持多参考图"""
        import httpx

        style_suffix = self.STYLE_PRESETS.get(style, style)
        full_prompt = f"{prompt}, {style_suffix}"

        # 构建 parts 数组
        parts = []

        # 添加参考图（图生图模式）
        if reference_images:
            for ref_path in reference_images:
                if os.path.exists(ref_path):
                    with open(ref_path, 'rb') as f:
                        img_data = f.read()
                    ext = os.path.splitext(ref_path)[1].lower()
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
                    mime_type = mime_map.get(ext, 'image/jpeg')
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(img_data).decode('utf-8')
                        }
                    })

        # 添加文本 prompt
        parts.append({"text": full_prompt})

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"]
            }
        }

        ref_info = f" (with {len(reference_images)} reference images)" if reference_images else ""
        logger.info(f"📤 图片生成（compass{ref_info}）: {prompt[:30]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    Config.COMPASS_IMAGE_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {Config.COMPASS_API_KEY}",
                    }
                )
                response.raise_for_status()
                result = response.json()

            candidates = result.get("candidates", [])
            if not candidates:
                return {"success": False, "error": "No candidates in response"}

            parts = candidates[0].get("content", {}).get("parts", [])
            image_data = None
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"].get("data")
                    break

            if not image_data:
                return {"success": False, "error": "No image data in response"}

            if output:
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                with open(output, "wb") as f:
                    f.write(base64.b64decode(image_data))
                logger.info(f"✅ 图片已保存: {output}")
                return {"success": True, "output": output}

            return {"success": True, "image_base64": image_data}

        except Exception as e:
            logger.error(f"❌ 图片生成失败: {e}")
            return {"success": False, "error": str(e)}


# ============== 人物角色管理（可选工具）==============

class PersonaManager:
    """
    人物角色管理器（可选工具）

    用于管理项目中的人物参考图。
    只有当视频涉及人物时才使用，纯风景/物品视频不需要。

    使用方式：
        manager = PersonaManager(project_dir)
        manager.register("小美", "female", "path/to/reference.jpg", "长发、圆脸、戴眼镜")
        ref_path = manager.get_reference("小美")
    """

    def __init__(self, project_dir: str = None):
        self.project_dir = Path(project_dir) if project_dir else None
        self.personas = {}  # {persona_id: {name, gender, features, reference_image}}
        self._persona_file = None

        if self.project_dir:
            self._persona_file = self.project_dir / "personas.json"
            self._load()

    def _load(self):
        """从文件加载人物数据"""
        if self._persona_file and self._persona_file.exists():
            try:
                with open(self._persona_file, "r", encoding="utf-8") as f:
                    self.personas = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 加载 personas.json 失败: {e}")
                self.personas = {}

    def _save(self):
        """保存人物数据到文件"""
        if self._persona_file:
            self._persona_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persona_file, "w", encoding="utf-8") as f:
                json.dump(self.personas, f, indent=2, ensure_ascii=False)

    def register(
        self,
        name: str,
        gender: str,
        reference_image: Optional[str] = None,
        features: str = ""
    ) -> str:
        """
        注册人物角色

        Args:
            name: 人物名称
            gender: 性别 (male/female)
            reference_image: 参考图路径（可为 None，Phase 2 补充）
            features: 外貌特征描述

        Returns:
            persona_id
        """
        # 生成唯一ID
        persona_id = name.lower().replace(" ", "_")
        counter = 1
        original_id = persona_id
        while persona_id in self.personas:
            persona_id = f"{original_id}_{counter}"
            counter += 1

        self.personas[persona_id] = {
            "name": name,
            "gender": gender,
            "reference_image": reference_image,
            "features": features
        }

        self._save()
        if reference_image:
            logger.info(f"✅ 已注册人物: {name} (ID: {persona_id}, 参考图: {reference_image})")
        else:
            logger.info(f"✅ 已注册人物: {name} (ID: {persona_id}, 无参考图)")

        return persona_id

    def update_reference_image(self, persona_id: str, reference_image: str) -> bool:
        """
        更新人物参考图（Phase 2 使用）

        Args:
            persona_id: 人物ID
            reference_image: 新的参考图路径

        Returns:
            是否成功
        """
        if persona_id not in self.personas:
            logger.warning(f"⚠️ 人物不存在: {persona_id}")
            return False

        self.personas[persona_id]["reference_image"] = reference_image
        self._save()
        logger.info(f"✅ 已更新 {persona_id} 的参考图: {reference_image}")
        return True

    def has_reference_image(self, persona_id: str) -> bool:
        """检查人物是否有参考图"""
        persona = self.personas.get(persona_id)
        if persona:
            return bool(persona.get("reference_image"))
        return False

    def list_personas_without_reference(self) -> List[str]:
        """返回所有没有参考图的人物ID列表"""
        return [
            pid for pid, data in self.personas.items()
            if not data.get("reference_image")
        ]

    def get_reference(self, persona_id: str) -> Optional[str]:
        """获取人物参考图路径"""
        persona = self.personas.get(persona_id)
        if persona:
            return persona.get("reference_image")
        return None

    def get_features(self, persona_id: str) -> str:
        """
        获取人物特征描述（用于 prompt）

        Returns:
            特征描述字符串，如 "young woman with long hair, round face, glasses"
        """
        persona = self.personas.get(persona_id)
        if not persona:
            return ""

        parts = []

        # 性别
        gender = persona.get("gender", "")
        if gender == "female":
            parts.append("woman")
        elif gender == "male":
            parts.append("man")

        # 特征
        features = persona.get("features", "")
        if features:
            parts.append(features)

        # 名字作为参考标识
        name = persona.get("name", "")
        if name:
            return f"{', '.join(parts)} (reference: {name})"

        return ", ".join(parts)

    def get_persona_prompt(self, persona_id: str) -> str:
        """
        获取用于 Vidu/Gemini 的人物 prompt

        格式: "Reference for {GENDER} ({name}): MUST preserve exact appearance - {features}"
        """
        persona = self.personas.get(persona_id)
        if not persona:
            return ""

        gender = persona.get("gender", "person")
        name = persona.get("name", "")
        features = persona.get("features", "")

        gender_upper = "WOMAN" if gender == "female" else "MAN" if gender == "male" else "PERSON"

        prompt = f"Reference for {gender_upper} ({name}): MUST preserve exact appearance"
        if features:
            prompt += f" - {features}"

        return prompt

    def list_personas(self) -> List[dict]:
        """列出所有人物"""
        return [
            {"id": pid, **pdata}
            for pid, pdata in self.personas.items()
        ]

    def export_for_storyboard(self) -> List[Dict[str, Any]]:
        """
        导出为 storyboard.json 兼容的 characters 格式

        Returns:
            符合 storyboard.json elements.characters 格式的列表
        """
        characters = []
        for pid, pdata in self.personas.items():
            name = pdata.get("name", "")
            # 生成 name_en（拼音/英文）
            name_en = pid.replace("_", " ").title().replace(" ", "")

            ref_image = pdata.get("reference_image")
            reference_images = [ref_image] if ref_image else []

            characters.append({
                "element_id": f"Element_{name_en}",
                "name": name,
                "name_en": name_en,
                "reference_images": reference_images,
                "visual_description": pdata.get("features", "")
            })

        return characters

    def get_character_image_mapping(self) -> Dict[str, str]:
        """
        生成 character_image_mapping（用于 storyboard.json）

        Returns:
            {Element_Name: image_1, ...}
        """
        mapping = {}
        for i, (pid, pdata) in enumerate(self.personas.items()):
            name_en = pid.replace("_", " ").title().replace(" ", "")
            element_id = f"Element_{name_en}"
            mapping[element_id] = f"image_{i + 1}"
        return mapping

    def has_personas(self) -> bool:
        """是否有人物注册"""
        return len(self.personas) > 0

    def remove(self, persona_id: str) -> bool:
        """删除人物"""
        if persona_id in self.personas:
            del self.personas[persona_id]
            self._save()
            return True
        return False

    def clear(self):
        """清空所有人物"""
        self.personas = {}
        self._save()


# ============== 多模态图片分析（内置 Vision 能力）==============

class VisionClient:
    """
    多模态图片分析客户端

    用于非多模态模型的 fallback，支持 Kimi K2.5、GPT-4o 等视觉模型。
    使用 Anthropic API 兼容格式。

    使用方式：
        client = VisionClient()
        result = await client.analyze_image("path/to/image.jpg", "描述这张图片")
        results = await client.analyze_batch(["img1.jpg", "img2.jpg"])
    """

    # 支持的图片格式
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=60.0)

    async def analyze_image(
        self,
        image_path: str,
        prompt: str = "请详细描述这张图片的内容，包括场景、主体、颜色、氛围等。",
    ) -> Dict[str, Any]:
        """分析单张图片"""
        if not os.path.exists(image_path):
            return {"success": False, "error": f"图片不存在: {image_path}"}

        # 读取并编码图片
        with open(image_path, 'rb') as f:
            image_data = f.read()

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        media_type = mime_map.get(ext, 'image/jpeg')

        base64_image = base64.b64encode(image_data).decode('utf-8')

        # 获取配置
        api_key = Config.get("VISION_API_KEY", "")
        base_url = Config.get("VISION_BASE_URL", "https://coding.dashscope.aliyuncs.com/apps/anthropic")
        model = Config.get("VISION_MODEL", "kimi-k2.5")

        if not api_key:
            return {"success": False, "error": "VISION_API_KEY 未配置"}

        # 构建 API 请求（Anthropic API 兼容格式）
        payload = {
            "model": model,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        try:
            response = await self.client.post(
                f"{base_url}/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                },
                json=payload
            )

            if response.status_code != 200:
                error_text = response.text
                return {
                    "success": False,
                    "error": f"API error {response.status_code}: {error_text[:200]}"
                }

            result = response.json()

            # 提取响应文本
            content = result.get("content", [])
            description = None
            for item in content:
                if item.get("type") == "text":
                    description = item.get("text", "")
                    break

            if not description:
                description = "无法解析响应"

            return {
                "success": True,
                "image_path": image_path,
                "description": description
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def analyze_batch(
        self,
        image_paths: List[str],
        prompt: str = "请详细描述这张图片的内容，包括场景、主体、颜色、氛围等。"
    ) -> List[Dict[str, Any]]:
        """批量分析多张图片"""
        results = []
        for path in image_paths:
            result = await self.analyze_image(path, prompt)
            results.append(result)
        return results

    async def close(self):
        await self.client.aclose()


# ============== 命令行入口 ==============

async def cmd_vision(args):
    """图片分析命令"""
    api_key = Config.get("VISION_API_KEY", "")
    if not api_key:
        print(json.dumps({
            "success": False,
            "error": "VISION_API_KEY 未配置",
            "hint": "请在 config.json 中添加 VISION_API_KEY",
            "config_file": str(CONFIG_FILE)
        }, indent=2, ensure_ascii=False))
        return 1

    client = VisionClient()
    try:
        if args.batch:
            # 批量分析目录
            directory = Path(args.image)
            if not directory.is_dir():
                print(json.dumps({
                    "success": False,
                    "error": f"目录不存在: {args.image}"
                }, indent=2, ensure_ascii=False))
                return 1

            image_files = []
            for ext in VisionClient.SUPPORTED_FORMATS:
                image_files.extend(directory.glob(f"*{ext}"))
                image_files.extend(directory.glob(f"*{ext.upper()}"))

            if not image_files:
                print(json.dumps({
                    "success": False,
                    "error": f"目录中没有找到图片文件: {args.image}"
                }, indent=2, ensure_ascii=False))
                return 1

            logger.info(f"找到 {len(image_files)} 张图片，开始分析...")
            results = await client.analyze_batch(
                [str(f) for f in sorted(image_files)],
                args.prompt
            )

            output = {"success": True, "total": len(results), "results": []}
            for r in results:
                if r.get("success"):
                    output["results"].append({
                        "image": r.get("image_path"),
                        "description": r.get("description")
                    })
                else:
                    output["results"].append({
                        "image": r.get("image_path", "unknown"),
                        "error": r.get("error")
                    })

            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0
        else:
            # 单张图片分析
            result = await client.analyze_image(args.image, args.prompt)
            if result.get("success"):
                output = {
                    "success": True,
                    "image": args.image,
                    "analysis": result.get("description")
                }
                print(json.dumps(output, indent=2, ensure_ascii=False))
                return 0
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 1
    finally:
        await client.close()


# ============== 命令行入口 ==============

async def cmd_video(args):
    """视频生成命令"""
    # 参数互斥校验：必须指定 --prompt 或 (--storyboard + --scene)
    has_prompt = bool(args.prompt)
    has_scene = bool(getattr(args, 'scene', None) and getattr(args, 'storyboard', None))
    if not has_prompt and not has_scene:
        print(json.dumps({
            "success": False,
            "error": "必须指定 --prompt 或 --storyboard + --scene"
        }, indent=2, ensure_ascii=False))
        return 1

    provider = getattr(args, 'provider', None)
    backend = getattr(args, 'backend', 'kling')

    # Provider 自动选择逻辑（如果用户未指定）
    if provider is None:
        if backend == 'seedance':
            provider = 'piapi'  # seedance 只有 piapi provider
        elif backend == 'veo3':
            provider = 'compass'  # veo3 只有 compass provider
        elif Config.KLING_ACCESS_KEY and Config.KLING_SECRET_KEY:
            provider = 'official'  # 优先使用官方 API
        elif Config.FAL_API_KEY:
            provider = 'fal'       # 其次使用 fal
        else:
            provider = 'official'  # 默认，会报错提示配置

    logger.info(f"🔧 使用 provider: {provider}, backend: {backend}")

    # 优先级：命令行 > storyboard.json > 默认值
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 从 storyboard.json 读取宽高比: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # 最终默认值
        logger.info(f"📐 使用默认宽高比: {aspect_ratio}")

    # ==================== fal.ai provider ====================
    # fal 使用统一的 Kling 模型，参数和 prompt 写法与官方完全一致
    if provider == 'fal':
        if not Config.FAL_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "FAL_API_KEY 未配置",
                "hint": "请在 config.json 中添加 FAL_API_KEY",
                "get_key": "访问 https://fal.ai 获取 API key"
            }, indent=2, ensure_ascii=False))
            return 1

        client = FalKlingClient()
        try:
            generate_audio = args.audio if hasattr(args, 'audio') else False
            duration = max(3, min(15, args.duration))

            result = await client.create_video(
                prompt=args.prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                generate_audio=generate_audio,
                image_url=args.image if args.image else None,
                image_urls=getattr(args, 'image_list', None),
                tail_image_url=getattr(args, 'tail_image', None),
                output=args.output
            )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"错误: {result.get('error')}")
                return 1
        finally:
            await client.close()

    # ==================== kling provider (官方 API) ====================
    # BackendRouter: 按功能需求强制切换
    # - image-list: kling-omni 和 seedance 都支持，不强制切换
    # - tail-image: 只有 kling 支持，需要强制切换
    image_list = getattr(args, 'image_list', None)
    tail_image = getattr(args, 'tail_image', None)
    if tail_image and backend not in ['kling']:
        backend = 'kling'
        logger.info("🔀 检测到 --tail-image，自动切换到 kling 后端")

    # ==================== official provider (官方 API) ====================
    # 检查对应后端的 API key
    if backend == 'kling':
        if not Config.KLING_ACCESS_KEY or not Config.KLING_SECRET_KEY:
            print(json.dumps({
                "success": False,
                "error": "Kling API 凭证未配置",
                "hint": "请在 config.json 中添加 KLING_ACCESS_KEY 和 KLING_SECRET_KEY",
                "get_key": "访问 https://klingai.kuaishou.com 获取 API 凭证"
            }, indent=2, ensure_ascii=False))
            return 1

        client = KlingClient()
        try:
            # Kling 参数转换：audio -> sound
            sound = "on" if args.audio else "off"
            # Kling 时长范围：3-15s
            duration = max(3, min(15, args.duration))

            # 处理多镜头参数
            multi_shot = getattr(args, 'multi_shot', False)
            shot_type = getattr(args, 'shot_type', None)
            multi_prompt = None
            if getattr(args, 'multi_prompt', None):
                try:
                    multi_prompt = json.loads(args.multi_prompt)
                except json.JSONDecodeError:
                    print(json.dumps({
                        "success": False,
                        "error": "multi_prompt JSON 解析失败"
                    }, indent=2, ensure_ascii=False))
                    return 1

            if args.image:
                result = await client.create_image2video(
                    image_path=args.image,
                    prompt=args.prompt,
                    duration=duration,
                    mode=args.mode if hasattr(args, 'mode') else "std",
                    sound=sound,
                    tail_image_path=getattr(args, 'tail_image', None),
                    output=args.output,
                    multi_shot=multi_shot,
                    shot_type=shot_type,
                    multi_prompt=multi_prompt
                )
            else:
                result = await client.create_text2video(
                    prompt=args.prompt,
                    duration=duration,
                    mode=args.mode if hasattr(args, 'mode') else "std",
                    aspect_ratio=aspect_ratio,
                    sound=sound,
                    multi_shot=multi_shot,
                    shot_type=shot_type,
                    multi_prompt=multi_prompt,
                    output=args.output
                )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"错误: {result.get('error')}")
                return 1
        finally:
            await client.close()

    elif backend == 'kling-omni':
        if not Config.KLING_ACCESS_KEY or not Config.KLING_SECRET_KEY:
            print(json.dumps({
                "success": False,
                "error": "Kling API 凭证未配置",
                "hint": "请在 config.json 中添加 KLING_ACCESS_KEY 和 KLING_SECRET_KEY",
                "get_key": "访问 https://klingai.kuaishou.com 获取 API 凭证"
            }, indent=2, ensure_ascii=False))
            return 1

        client = KlingOmniClient()
        try:
            sound = "on" if args.audio else "off"
            duration = max(3, min(15, args.duration))

            multi_shot = getattr(args, 'multi_shot', False)
            shot_type = getattr(args, 'shot_type', None)
            multi_prompt = None
            if getattr(args, 'multi_prompt', None):
                try:
                    multi_prompt = json.loads(args.multi_prompt)
                except json.JSONDecodeError:
                    print(json.dumps({
                        "success": False,
                        "error": "multi_prompt JSON 解析失败"
                    }, indent=2, ensure_ascii=False))
                    return 1

            image_list = getattr(args, 'image_list', None)

            result = await client.create_omni_video(
                prompt=args.prompt,
                duration=duration,
                mode=args.mode if hasattr(args, 'mode') else "std",
                aspect_ratio=aspect_ratio,
                sound=sound,
                image_list=image_list,
                multi_shot=multi_shot,
                shot_type=shot_type,
                multi_prompt=multi_prompt,
                output=args.output
            )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"错误: {result.get('error')}")
                return 1
        finally:
            await client.close()

    elif backend == 'seedance':
        if not Config.SEEDANCE_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "SEEDANCE_API_KEY 未配置",
                "hint": "请在 config.json 中添加 SEEDANCE_API_KEY",
                "get_key": "Seedance 通过 piapi.ai 代理，访问 https://piapi.ai 注册获取 API key"
            }, indent=2, ensure_ascii=False))
            return 1

        client = SeedanceClient()
        try:
            scene_id = getattr(args, 'scene', None)
            storyboard_path = getattr(args, 'storyboard', None)

            # --- 自动组装模式：--storyboard + --scene ---
            if storyboard_path and scene_id:
                storyboard_data = load_storyboard(storyboard_path)
                if not storyboard_data:
                    print(json.dumps({
                        "success": False,
                        "error": f"无法加载 storyboard: {storyboard_path}"
                    }, indent=2, ensure_ascii=False))
                    return 1

                # 查找指定 scene
                target_scene = None
                for sc in storyboard_data.get("scenes", []):
                    if sc.get("scene_id") == scene_id:
                        target_scene = sc
                        break
                if not target_scene:
                    print(json.dumps({
                        "success": False,
                        "error": f"未找到 scene: {scene_id}",
                        "available": [s.get("scene_id") for s in storyboard_data.get("scenes", [])]
                    }, indent=2, ensure_ascii=False))
                    return 1

                # 自动组装 prompt、image_urls、duration
                prompt, image_urls, duration = build_seedance_prompt(target_scene, storyboard_data)
                aspect_ratio = storyboard_data.get("aspect_ratio", aspect_ratio)

                logger.info(f"🎬 Seedance 自动组装: scene={scene_id}, duration={duration}s, images={len(image_urls)}")

                result = await client.submit_task(
                    prompt=prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    image_urls=image_urls if image_urls else None,
                    output=args.output
                )
            else:
                # --- 手动模式（向后兼容）---
                # Seedance 2 支持 4-15s 任意整数
                duration = max(4, min(15, args.duration))
                if duration != args.duration:
                    logger.warning(f"⚠️ Seedance 2 duration 调整为 {duration}s（范围 4-15s）")

                image_list = getattr(args, 'image_list', None)
                mode = getattr(args, 'mode', 'text_to_video')
                # 如果 mode 是 Kling 的 std/pro，则使用默认 text_to_video
                if mode in ['std', 'pro']:
                    mode = 'text_to_video'
                audio_urls = getattr(args, 'audio_urls', None)
                video_urls = getattr(args, 'video_urls', None)

                result = await client.submit_task(
                    prompt=args.prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    image_urls=image_list,
                    mode=mode,
                    audio_urls=audio_urls,
                    video_urls=video_urls,
                    output=args.output
                )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"错误: {result.get('error')}")
                return 1
        finally:
            await client.close()

    elif backend == 'veo3':
        if not Config.COMPASS_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "COMPASS_API_KEY 未配置",
                "hint": "请在 config.json 中添加 COMPASS_API_KEY",
                "get_key": "Compass API key 用于访问 Veo3 视频生成"
            }, indent=2, ensure_ascii=False))
            return 1

        client = Veo3Client()
        try:
            if args.image:
                result = await client.create_image2video(
                    image_path=args.image,
                    prompt=args.prompt,
                    duration=args.duration,
                    aspect_ratio=aspect_ratio,
                    output=args.output
                )
            else:
                result = await client.create_text2video(
                    prompt=args.prompt,
                    duration=args.duration,
                    aspect_ratio=aspect_ratio,
                    output=args.output
                )

            if result.get("success"):
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            else:
                print(f"错误: {result.get('error')}")
                return 1
        finally:
            await client.close()

    # 未知后端
    print(json.dumps({
        "success": False,
        "error": f"不支持的后端: {backend}",
        "supported_backends": ["kling", "kling-omni", "seedance", "veo3"]
    }, indent=2, ensure_ascii=False))
    return 1


async def cmd_music(args):
    """音乐生成命令"""
    # 优先级：命令行 > creative.json > 报错
    prompt = args.prompt
    style = args.style

    # 从 creative.json 读取 prompt 和 style
    if hasattr(args, 'creative') and args.creative:
        config = get_music_config_from_creative(args.creative)
        if config:
            if prompt is None:
                prompt = config.get("prompt")
                if prompt:
                    logger.info(f"🎵 从 creative.json 读取音乐描述: {prompt[:50]}...")
            if style is None:
                style = config.get("style")
                if style:
                    logger.info(f"🎵 从 creative.json 读取音乐风格: {style}")

    # prompt 必须提供
    if prompt is None:
        print(json.dumps({
            "success": False,
            "error": "必须提供音乐描述",
            "hint": "请通过 --prompt 或 --creative 参数提供音乐描述"
        }, indent=2, ensure_ascii=False))
        return 1

    # style 必须提供
    if style is None:
        print(json.dumps({
            "success": False,
            "error": "必须提供音乐风格",
            "hint": "请通过 --style 或 --creative 参数提供音乐风格"
        }, indent=2, ensure_ascii=False))
        return 1

    if not Config.SUNO_API_KEY:
        print(json.dumps({
            "success": False,
            "error": "SUNO_API_KEY 未配置",
            "hint": "请设置环境变量: export SUNO_API_KEY='your-api-key'",
            "get_key": "访问 https://sunoapi.org 获取 API key"
        }, indent=2, ensure_ascii=False))
        return 1

    client = SunoClient()
    try:
        result = await client.generate(
            prompt=prompt,
            style=style,
            instrumental=args.instrumental,
            output=args.output
        )

        if result.get("success"):
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        else:
            print(f"错误: {result.get('error')}")
            return 1
    finally:
        await client.close()


async def cmd_tts(args):
    """TTS合成命令 - 使用 Gemini TTS（通过 Compass API）"""
    if not Config.COMPASS_API_KEY:
        print(json.dumps({
            "success": False,
            "error": "COMPASS_API_KEY 未配置",
            "hint": "请配置 COMPASS_API_KEY 以使用 Gemini TTS",
            "get_key": "访问 compass.llm.shopee.io 获取 API key"
        }, indent=2, ensure_ascii=False))
        return 1

    logger.info("🔧 使用 Gemini TTS (Compass)")
    client = GeminiTTSClient()
    result = await client.synthesize(
        text=args.text,
        output=args.output,
        voice=args.voice,
        emotion=args.emotion,
        speed=args.speed,
        prompt=getattr(args, 'prompt', None),
    )

    if result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    else:
        print(f"错误: {result.get('error')}")
        return 1


async def cmd_image(args):
    """图片生成命令"""
    # Provider 自动选择逻辑
    provider = getattr(args, 'provider', None)
    if provider is None:
        # 优先级：compass → yunwu
        if Config.COMPASS_API_KEY:
            provider = 'compass'
        elif Config.GEMINI_API_KEY:  # GEMINI_API_KEY 实际上是 YUNWU_API_KEY
            provider = 'yunwu'
        else:
            provider = 'compass'  # 默认，会报错提示配置

    logger.info(f"🔧 使用 provider: {provider}")

    # 优先级：命令行 > storyboard.json > 默认值
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 从 storyboard.json 读取宽高比: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # 最终默认值
        logger.info(f"📐 使用默认宽高比: {aspect_ratio}")

    # compass provider
    if provider == 'compass':
        if not Config.COMPASS_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "COMPASS_API_KEY 未配置",
                "hint": "请在 config.json 中添加 COMPASS_API_KEY"
            }, indent=2, ensure_ascii=False))
            return 1

        client = CompassImageClient()
        result = await client.generate(
            prompt=args.prompt,
            output=args.output,
            style=args.style,
            aspect_ratio=aspect_ratio,
            reference_images=args.reference
        )

    # yunwu provider (Gemini via Yunwu)
    else:
        if not Config.GEMINI_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "YUNWU_API_KEY 未配置（用于 Gemini 图片生成）",
                "hint": "请设置环境变量: export YUNWU_API_KEY='your-api-key'",
                "get_key": "访问 https://yunwu.ai 注册获取 API key"
            }, indent=2, ensure_ascii=False))
            return 1

        client = ImageClient()
        result = await client.generate(
            prompt=args.prompt,
            output=args.output,
            style=args.style,
            aspect_ratio=aspect_ratio,
            reference_images=args.reference
        )

    if result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    else:
        print(f"错误: {result.get('error')}")
        return 1


async def cmd_setup(args):
    """交互式配置 API provider 和密钥"""

    # 定义所有可用的视频生成 provider 及其所需的 key
    VIDEO_PROVIDERS = {
        "1": {
            "name": "Seedance（字节跳动，推荐虚构片/短剧/MV）",
            "backend": "seedance",
            "provider": "piapi",
            "keys": [
                {"key": "SEEDANCE_API_KEY", "label": "Seedance API Key (piapi)", "url": "https://piapi.ai"}
            ]
        },
        "2": {
            "name": "Kling 官方 API（快手，推荐写实/广告片）",
            "backend": "kling",
            "provider": "official",
            "keys": [
                {"key": "KLING_ACCESS_KEY", "label": "Kling Access Key", "url": "https://klingai.kuaishou.com"},
                {"key": "KLING_SECRET_KEY", "label": "Kling Secret Key", "url": "https://klingai.kuaishou.com"}
            ]
        },
        "3": {
            "name": "Kling via fal.ai（绕过官方并发限制）",
            "backend": "kling-omni",
            "provider": "fal",
            "keys": [
                {"key": "FAL_API_KEY", "label": "fal.ai API Key", "url": "https://fal.ai"}
            ]
        },
        "4": {
            "name": "Veo3 via Compass（Google Veo3，高质量写实短片）",
            "backend": "veo3",
            "provider": "compass",
            "keys": [
                {"key": "COMPASS_API_KEY", "label": "Compass API Key", "url": "https://compass.llm.shopee.io"}
            ]
        },
    }

    OPTIONAL_SERVICES = {
        "music": {
            "name": "Suno 音乐生成",
            "keys": [
                {"key": "SUNO_API_KEY", "label": "Suno API Key", "url": "https://sunoapi.org"}
            ]
        },
    }

    config = load_config()

    # 输出为 JSON，便于 Claude 解析
    setup_info = {
        "action": "setup",
        "video_providers": {},
        "optional_services": {},
        "current_config": {}
    }

    for num, p in VIDEO_PROVIDERS.items():
        setup_info["video_providers"][num] = {
            "name": p["name"],
            "backend": p["backend"],
            "provider": p["provider"],
            "required_keys": [{"key": k["key"], "label": k["label"], "url": k["url"],
                               "configured": bool(config.get(k["key"]) or os.getenv(k["key"]))}
                              for k in p["keys"]]
        }

    for svc_id, svc in OPTIONAL_SERVICES.items():
        setup_info["optional_services"][svc_id] = {
            "name": svc["name"],
            "required_keys": [{"key": k["key"], "label": k["label"], "url": k["url"],
                               "configured": bool(config.get(k["key"]) or os.getenv(k["key"]))}
                              for k in svc["keys"]]
        }

    # 显示当前已配置的 keys
    for key in ["SEEDANCE_API_KEY", "KLING_ACCESS_KEY", "KLING_SECRET_KEY", "FAL_API_KEY",
                "YUNWU_API_KEY", "SUNO_API_KEY", "VOLCENGINE_TTS_APP_ID",
                "VOLCENGINE_TTS_ACCESS_TOKEN", "COMPASS_API_KEY"]:
        val = config.get(key) or os.getenv(key, "")
        setup_info["current_config"][key] = f"{val[:4]}***" if val else "未设置"

    # 非交互模式：带 --provider 参数时直接配置
    provider_choice = getattr(args, 'provider_choice', None)
    set_keys = getattr(args, 'set_key', None) or []

    if set_keys:
        for kv in set_keys:
            if "=" in kv:
                k, v = kv.split("=", 1)
                config[k] = v
                setup_info["saved"] = setup_info.get("saved", [])
                setup_info["saved"].append(k)
        save_config(config)
        Config._cached_config = None  # 清除缓存
        setup_info["status"] = "keys_saved"
    elif provider_choice and provider_choice in VIDEO_PROVIDERS:
        p = VIDEO_PROVIDERS[provider_choice]
        setup_info["selected_provider"] = p["name"]
        setup_info["need_keys"] = [k for k in p["keys"]
                                   if not (config.get(k["key"]) or os.getenv(k["key"]))]
        setup_info["status"] = "provider_selected"
    else:
        setup_info["status"] = "awaiting_selection"

    print(json.dumps(setup_info, indent=2, ensure_ascii=False))
    return 0


async def cmd_check(args):
    """环境检查命令"""
    import shutil
    import platform

    results = {
        "ready": True,
        "checks": {},
        "missing": [],
        "api_keys": {},
        "hints": []
    }

    # Python version
    py_ver = platform.python_version()
    py_ok = sys.version_info >= (3, 9)
    results["checks"]["python"] = {"version": py_ver, "ok": py_ok}
    if not py_ok:
        results["ready"] = False
        results["missing"].append(f"Python 3.9+ required (got {py_ver})")

    # FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    results["checks"]["ffmpeg"] = {
        "installed": ffmpeg_path is not None,
        "ffmpeg_path": ffmpeg_path,
        "ffprobe_path": ffprobe_path
    }
    if not ffmpeg_path:
        results["ready"] = False
        results["missing"].append("FFmpeg not found in PATH")
        results["hints"].append("Install FFmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")

    # httpx
    try:
        import httpx
        results["checks"]["httpx"] = {"installed": True, "version": httpx.__version__}
    except ImportError:
        results["checks"]["httpx"] = {"installed": False}
        results["ready"] = False
        results["missing"].append("httpx not installed")
        results["hints"].append("Install httpx: pip install httpx")

    # Environment variables (informational only)
    env_vars = {
        "SEEDANCE_API_KEY": {
            "value": Config.SEEDANCE_API_KEY,
            "purpose": "Seedance 视频生成（piapi.ai 代理）",
            "get_key": "https://piapi.ai"
        },
        "COMPASS_API_KEY": {
            "value": Config.COMPASS_API_KEY,
            "purpose": "Veo3 视频 + Gemini 图片 + Gemini TTS（Compass 代理）",
            "get_key": "https://compass.llm.shopee.io"
        },
        "YUNWU_API_KEY": {
            "value": Config.YUNWU_API_KEY,
            "purpose": "Vidu 视频生成 + Gemini 图片生成",
            "get_key": "https://yunwu.ai"
        },
        "KLING_ACCESS_KEY": {
            "value": Config.KLING_ACCESS_KEY,
            "purpose": "Kling 视频生成 Access Key",
            "get_key": "https://klingai.kuaishou.com"
        },
        "KLING_SECRET_KEY": {
            "value": Config.KLING_SECRET_KEY,
            "purpose": "Kling 视频生成 Secret Key",
            "get_key": "https://klingai.kuaishou.com"
        },
        "FAL_API_KEY": {
            "value": Config.FAL_API_KEY,
            "purpose": "fal.ai Kling 视频生成代理（绕过官方并发限制）",
            "get_key": "https://fal.ai"
        },
        "SUNO_API_KEY": {
            "value": Config.SUNO_API_KEY,
            "purpose": "Suno 音乐生成",
            "get_key": "https://sunoapi.org"
        },
    }

    for name, info in env_vars.items():
        is_set = bool(info["value"])
        masked = f"{info['value'][:4]}***" if is_set else "未设置"
        results["api_keys"][name] = {
            "set": is_set,
            "masked_value": masked,
            "purpose": info["purpose"],
            "get_key_url": info["get_key"]
        }

    # 检查是否至少有一个视频 provider 可用
    has_video_provider = any([
        Config.SEEDANCE_API_KEY,
        Config.COMPASS_API_KEY,
        Config.KLING_ACCESS_KEY and Config.KLING_SECRET_KEY,
        Config.FAL_API_KEY,
    ])
    results["has_video_provider"] = has_video_provider
    if not has_video_provider:
        results["ready"] = False
        results["missing"].append("没有配置任何视频生成 API key")
        results["hints"].append("请先运行 setup 命令配置 API: python video_gen_tools.py setup")

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["ready"] else 1


async def cmd_validate(args):
    """校验 storyboard.json"""
    result = validate_storyboard(args.storyboard)

    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["errors"]:
        logger.error(f"❌ 校验失败: {len(result['errors'])} 个错误")
    if result["warnings"]:
        logger.warning(f"⚠️ {len(result['warnings'])} 个警告")
    if result["valid"]:
        logger.info("✅ 校验通过")

    return 0 if result["valid"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Tools - 视频创作API命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # setup 子命令（交互式配置 provider + API key）
    setup_parser = subparsers.add_parser("setup", help="交互式配置 API provider 和密钥")
    setup_parser.add_argument("--provider", dest="provider_choice", choices=["1", "2", "3", "4"],
                              help="选择视频 provider: 1=Seedance, 2=Kling官方, 3=Kling(fal), 4=Veo3(compass)")
    setup_parser.add_argument("--set-key", nargs="+", metavar="KEY=VALUE",
                              help="设置 API key，格式: KEY=VALUE（可多个）")

    # check 子命令
    subparsers.add_parser("check", help="检查环境依赖和配置")

    # video 子命令
    video_parser = subparsers.add_parser("video", help="生成视频")
    video_parser.add_argument("--image", "-i", help="输入图片路径或URL（图生视频）")
    video_parser.add_argument("--prompt", "-p", default=None, help="视频描述（Seedance --scene 模式下可省略）")
    video_parser.add_argument("--duration", "-d", type=int, default=5, help="时长(秒)")
    video_parser.add_argument("--resolution", "-r", default="720p", help="分辨率")
    video_parser.add_argument("--aspect-ratio", "-a", default=None, help="宽高比（如 16:9, 9:16）")
    video_parser.add_argument("--storyboard", "-s", help="storyboard.json 路径，自动读取 aspect_ratio")
    video_parser.add_argument("--audio", action="store_true", help="生成原生音频")
    video_parser.add_argument("--output", "-o", help="输出文件路径")
    video_parser.add_argument("--provider", choices=["official", "fal", "compass"], default=None,
                              help="API provider (默认自动选择; veo3 仅支持 compass)")
    video_parser.add_argument("--backend", "-b", choices=["kling", "kling-omni", "seedance", "veo3"], default="kling",
                              help="视频生成后端 (默认 kling; kling-omni 用于参考图; seedance 用于智能切镜; veo3 用于高质量写实短片)")
    video_parser.add_argument("--mode", "-m", choices=["std", "pro", "text_to_video", "first_last_frames", "omni_reference"], default="std",
                              help="生成模式 (Kling: std 或 pro; Seedance: text_to_video, first_last_frames, omni_reference)")
    video_parser.add_argument("--multi-shot", action="store_true",
                              help="启用 Kling 多镜头模式")
    video_parser.add_argument("--shot-type", choices=["intelligence", "customize"],
                              help="多镜头分镜类型 (intelligence: AI自动, customize: 自定义)")
    video_parser.add_argument("--multi-prompt", type=str,
                              help="多镜头 prompt 列表 (JSON 格式)")
    video_parser.add_argument("--tail-image", type=str,
                              help="尾帧图片路径（用于首尾帧控制）")
    video_parser.add_argument("--image-list", nargs="+",
                              help="Omni-Video 多参考图路径列表（kling-omni 专用）；或 Seedance 首尾帧模式的首尾帧图")
    video_parser.add_argument("--scene", help="Scene ID（Seedance 专用：配合 --storyboard 自动组装时间分段 prompt）")
    video_parser.add_argument("--audio-urls", nargs="+",
                              help="音频参考 URL 列表（Seedance 2 专用）")
    video_parser.add_argument("--video-urls", nargs="+",
                              help="视频参考 URL 列表（Seedance 2 专用）")

    # music 子命令
    music_parser = subparsers.add_parser("music", help="生成音乐")
    music_parser.add_argument("--prompt", "-p", default=None, help="音乐描述（可从 creative.json 自动读取）")
    music_parser.add_argument("--style", "-s", default=None, help="音乐风格（可从 creative.json 自动读取）")
    music_parser.add_argument("--creative", "-c", help="creative.json 路径，自动读取 prompt 和 style")
    music_parser.add_argument("--no-instrumental", dest="instrumental", action="store_false", help="包含人声（默认纯音乐）")
    music_parser.set_defaults(instrumental=True)
    music_parser.add_argument("--output", "-o", help="输出文件路径")

    # tts 子命令
    tts_parser = subparsers.add_parser("tts", help="生成语音")
    tts_parser.add_argument("--text", "-t", required=True, help="要合成的文本")
    tts_parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    tts_parser.add_argument("--voice", "-v", default="female_narrator",
                           choices=["female_narrator", "female_gentle", "female_soft", "female_bright",
                                    "male_narrator", "male_warm", "male_deep", "male_bright"],
                           help="音色")
    tts_parser.add_argument("--emotion", "-e", choices=["neutral", "happy", "sad", "gentle", "serious"],
                           help="情感（已废弃，建议使用 --prompt）")
    tts_parser.add_argument("--prompt", "-p", help="风格指令，控制口音/情感/语气/人设（如：幽默解说，略带调侃）")
    tts_parser.add_argument("--speed", type=float, default=1.0, help="语速")

    # image 子命令
    image_parser = subparsers.add_parser("image", help="生成图片")
    image_parser.add_argument("--prompt", "-p", required=True, help="图片描述")
    image_parser.add_argument("--output", "-o", help="输出文件路径")
    image_parser.add_argument("--style", "-s", default="cinematic",
                              help="风格（自由文本，如 cinematic, watercolor illustration 等）")
    image_parser.add_argument("--aspect-ratio", "-a", default=None, help="宽高比")
    image_parser.add_argument("--storyboard", help="storyboard.json 路径，自动读取 aspect_ratio")
    image_parser.add_argument("--reference", "-r", nargs="+", help="参考图路径（支持多个，重要人物放后面）")
    image_parser.add_argument("--provider", choices=["compass", "yunwu"], default=None,
                              help="API provider (默认自动选择: compass 优先)")

    # vision 子命令（内置多模态分析）
    vision_parser = subparsers.add_parser("vision", help="分析图片内容")
    vision_parser.add_argument("image", help="图片路径或目录")
    vision_parser.add_argument("--batch", "-b", action="store_true", help="批量分析目录中的图片")
    vision_parser.add_argument("--prompt", "-p", default="请详细描述这张图片的内容，包括场景、主体、颜色、氛围等。", help="分析提示词")

    # validate 子命令
    validate_parser = subparsers.add_parser("validate", help="校验 storyboard.json")
    validate_parser.add_argument("--storyboard", "-s", required=True, help="storyboard.json 路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 运行对应命令
    commands = {
        "setup": cmd_setup,
        "check": cmd_check,
        "video": cmd_video,
        "music": cmd_music,
        "tts": cmd_tts,
        "image": cmd_image,
        "vision": cmd_vision,
        "validate": cmd_validate,
    }

    return asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    sys.exit(main())