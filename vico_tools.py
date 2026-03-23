#!/usr/bin/env python3
"""
Vico Tools - 视频创作API命令行工具集

用法：
  python vico_tools.py video --image <path> --prompt <text> --duration <seconds>
  python vico_tools.py music --prompt <text> --style <style>
  python vico_tools.py tts --text <text> --voice <voice_type>
  python vico_tools.py image --prompt <text> --style <style>
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

CONFIG_FILE = Path.home() / ".claude" / "skills" / "vico-edit" / "config.json"


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

    # Kling API
    @property
    def KLING_ACCESS_KEY(self) -> str:
        return self.get("KLING_ACCESS_KEY", "")

    @property
    def KLING_SECRET_KEY(self) -> str:
        return self.get("KLING_SECRET_KEY", "")

    KLING_BASE_URL: str = "https://api-beijing.klingai.com"
    KLING_MODEL: str = "kling-v3"  # kling-v3 (v3-omni) 或 kling-v1-5 或 kling-v1


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


# ============== Vidu 视频生成 ==============

class ViduClient:
    """Vidu 视频生成客户端（通过 Yunwu API）"""

    IMG2VIDEO_PATH = "/ent/v2/img2video"
    TEXT2VIDEO_PATH = "/ent/v2/text2video"
    QUERY_PATH = "/ent/v2/tasks/{task_id}/creations"

    def __init__(self):
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


# ============== Volcengine TTS ==============

class TTSClient:
    """火山引擎 TTS 客户端"""

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
    backend = getattr(args, 'backend', 'kling')

    # 优先级：命令行 > storyboard.json > 默认值
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 从 storyboard.json 读取宽高比: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # 最终默认值
        logger.info(f"📐 使用默认宽高比: {aspect_ratio}")

    # BackendRouter: 按功能需求强制切换（image-list 只有 omni 支持，tail-image 只有 kling 支持）
    image_list = getattr(args, 'image_list', None)
    tail_image = getattr(args, 'tail_image', None)
    if image_list and backend != 'kling-omni':
        backend = 'kling-omni'
        logger.info("🔀 检测到 --image-list，自动切换到 kling-omni 后端")
    elif tail_image and backend != 'kling':
        backend = 'kling'
        logger.info("🔀 检测到 --tail-image，自动切换到 kling 后端")

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

    else:
        # Vidu (Yunwu) 后端
        if not Config.YUNWU_API_KEY:
            print(json.dumps({
                "success": False,
                "error": "YUNWU_API_KEY 未配置",
                "hint": "请设置环境变量: export YUNWU_API_KEY='your-api-key'",
                "get_key": "访问 https://yunwu.ai 注册获取 API key"
            }, indent=2, ensure_ascii=False))
            return 1

        client = ViduClient()
        try:
            if args.image:
                result = await client.create_img2video(
                    image_path=args.image,
                    prompt=args.prompt,
                    duration=args.duration,
                    resolution=args.resolution,
                    audio=args.audio,
                    output=args.output
                )
            else:
                result = await client.create_text2video(
                    prompt=args.prompt,
                    duration=args.duration,
                    aspect_ratio=aspect_ratio,
                    audio=args.audio,
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


async def cmd_music(args):
    """音乐生成命令"""
    # 优先级：命令行 --style > creative.json > 报错提示
    style = args.style

    if style is None and hasattr(args, 'creative') and args.creative:
        config = get_music_config_from_creative(args.creative)
        if config:
            style = config.get("style")
            if style:
                logger.info(f"🎵 从 creative.json 读取音乐风格: {style}")

    if style is None:
        style = "Lo-fi, Chill"  # 最终默认值
        logger.info(f"🎵 使用默认音乐风格: {style}")

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
            prompt=args.prompt,
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
    """TTS合成命令"""
    if not Config.VOLCENGINE_TTS_APP_ID or not Config.VOLCENGINE_TTS_TOKEN:
        print(json.dumps({
            "success": False,
            "error": "火山引擎 TTS 凭证未配置",
            "hint": "请设置环境变量:\n  export VOLCENGINE_TTS_APP_ID='your-app-id'\n  export VOLCENGINE_TTS_ACCESS_TOKEN='your-token'",
            "get_key": "访问 https://www.volcengine.com/docs/656/79823 获取凭证"
        }, indent=2, ensure_ascii=False))
        return 1

    client = TTSClient()
    result = await client.synthesize(
        text=args.text,
        output=args.output,
        voice=args.voice,
        emotion=args.emotion,
        speed=args.speed
    )

    if result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    else:
        print(f"错误: {result.get('error')}")
        return 1


async def cmd_image(args):
    """图片生成命令"""
    # 优先级：命令行 > storyboard.json > 默认值
    aspect_ratio = args.aspect_ratio
    if aspect_ratio is None and hasattr(args, 'storyboard') and args.storyboard:
        aspect_ratio = get_aspect_from_storyboard(args.storyboard)
        if aspect_ratio:
            logger.info(f"📐 从 storyboard.json 读取宽高比: {aspect_ratio}")
    if aspect_ratio is None:
        aspect_ratio = "9:16"  # 最终默认值
        logger.info(f"📐 使用默认宽高比: {aspect_ratio}")

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
        "SUNO_API_KEY": {
            "value": Config.SUNO_API_KEY,
            "purpose": "Suno 音乐生成",
            "get_key": "https://sunoapi.org"
        },
        "VOLCENGINE_TTS_APP_ID": {
            "value": Config.VOLCENGINE_TTS_APP_ID,
            "purpose": "火山引擎 TTS App ID",
            "get_key": "https://www.volcengine.com/docs/656/79823"
        },
        "VOLCENGINE_TTS_ACCESS_TOKEN": {
            "value": Config.VOLCENGINE_TTS_TOKEN,
            "purpose": "火山引擎 TTS Access Token",
            "get_key": "https://www.volcengine.com/docs/656/79823"
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

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["ready"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Vico Tools - 视频创作API命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # check 子命令
    subparsers.add_parser("check", help="检查环境依赖和配置")

    # video 子命令
    video_parser = subparsers.add_parser("video", help="生成视频")
    video_parser.add_argument("--image", "-i", help="输入图片路径或URL（图生视频）")
    video_parser.add_argument("--prompt", "-p", required=True, help="视频描述")
    video_parser.add_argument("--duration", "-d", type=int, default=5, help="时长(秒)")
    video_parser.add_argument("--resolution", "-r", default="720p", help="分辨率")
    video_parser.add_argument("--aspect-ratio", "-a", default=None, help="宽高比（如 16:9, 9:16）")
    video_parser.add_argument("--storyboard", "-s", help="storyboard.json 路径，自动读取 aspect_ratio")
    video_parser.add_argument("--audio", action="store_true", help="生成原生音频")
    video_parser.add_argument("--output", "-o", help="输出文件路径")
    video_parser.add_argument("--backend", "-b", choices=["vidu", "kling", "kling-omni"], default="kling",
                              help="视频生成后端 (默认 kling; vidu 为兜底; kling-omni 用于参考图)")
    video_parser.add_argument("--mode", "-m", choices=["std", "pro"], default="std",
                              help="生成模式 (Kling 专用: std 或 pro)")
    video_parser.add_argument("--multi-shot", action="store_true",
                              help="启用 Kling 多镜头模式")
    video_parser.add_argument("--shot-type", choices=["intelligence", "customize"],
                              help="多镜头分镜类型 (intelligence: AI自动, customize: 自定义)")
    video_parser.add_argument("--multi-prompt", type=str,
                              help="多镜头 prompt 列表 (JSON 格式)")
    video_parser.add_argument("--tail-image", type=str,
                              help="尾帧图片路径（用于首尾帧控制）")
    video_parser.add_argument("--image-list", nargs="+",
                              help="Omni-Video 多参考图路径列表（kling-omni 专用）")

    # music 子命令
    music_parser = subparsers.add_parser("music", help="生成音乐")
    music_parser.add_argument("--prompt", "-p", required=True, help="音乐描述")
    music_parser.add_argument("--style", "-s", default=None, help="音乐风格（可从 creative.json 自动读取）")
    music_parser.add_argument("--creative", "-c", help="creative.json 路径，自动读取音乐风格")
    music_parser.add_argument("--no-instrumental", dest="instrumental", action="store_false", help="包含人声（默认纯音乐）")
    music_parser.set_defaults(instrumental=True)
    music_parser.add_argument("--output", "-o", help="输出文件路径")

    # tts 子命令
    tts_parser = subparsers.add_parser("tts", help="生成语音")
    tts_parser.add_argument("--text", "-t", required=True, help="要合成的文本")
    tts_parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    tts_parser.add_argument("--voice", "-v", default="female_narrator",
                           choices=["female_narrator", "female_gentle", "male_narrator", "male_warm"],
                           help="音色")
    tts_parser.add_argument("--emotion", "-e", choices=["neutral", "happy", "sad", "gentle", "serious"],
                           help="情感")
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

    # vision 子命令（内置多模态分析）
    vision_parser = subparsers.add_parser("vision", help="分析图片内容")
    vision_parser.add_argument("image", help="图片路径或目录")
    vision_parser.add_argument("--batch", "-b", action="store_true", help="批量分析目录中的图片")
    vision_parser.add_argument("--prompt", "-p", default="请详细描述这张图片的内容，包括场景、主体、颜色、氛围等。", help="分析提示词")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 运行对应命令
    commands = {
        "check": cmd_check,
        "video": cmd_video,
        "music": cmd_music,
        "tts": cmd_tts,
        "image": cmd_image,
        "vision": cmd_vision,
    }

    return asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    sys.exit(main())