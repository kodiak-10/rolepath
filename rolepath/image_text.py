"""On-device macOS Vision OCR. Image bytes are never sent to the model."""
import json
import platform
from pathlib import Path
import subprocess
import tempfile

IMAGE_TYPES = ('png', 'jpg', 'jpeg', 'heic', 'heif')
UPLOAD_TYPES = ['txt', 'md', 'pdf', *IMAGE_TYPES]


def is_image(name):
    return Path(name).suffix.lower().lstrip('.') in IMAGE_TYPES


def read_image(data, name):
    if not data or len(data) > 5 * 1024 * 1024:
        raise ValueError('图片为空或超过 5MB')
    if not is_image(name):
        raise ValueError('不支持此图片格式')
    from .cloud_settings import cloud_mode
    if cloud_mode():
        raise ValueError('线上照片请到「学习笔记 → 照片笔记助手」直接看图；旧版自动识别已停用，避免保存乱码。')
    if platform.system() != 'Darwin':
        return read_image_linux(data)
    script = Path(__file__).parent / 'native' / 'recognize_text.swift'
    with tempfile.TemporaryDirectory(prefix='rolepath-ocr-') as directory:
        file = Path(directory) / ('image' + Path(name).suffix.lower())
        file.write_bytes(data)
        cache = Path(tempfile.gettempdir()) / 'rolepath-swift-cache'
        try:
            result = subprocess.run(['/usr/bin/swift', '-module-cache-path', str(cache), str(script), str(file)],
                capture_output=True, text=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('本机图片识别未能完成，请检查 Swift 环境或稍后再试') from exc
        if result.returncode:
            # Avoid dumping native compiler logs or filesystem details into the UI.
            known = ('图片损坏、格式不受支持，或像素超过 6000 万',
                     '未识别到文字，请上传清晰、正向且包含文字的图片',
                     '图片文字识别失败，请检查图片格式与清晰度')
            message = next((m for m in known if m in result.stderr), '本机图片识别启动失败，请检查 Swift 环境')
            raise ValueError(message)
        try:
            text = json.loads(result.stdout)['text']
            if not isinstance(text, str) or not text.strip():
                raise ValueError('识别结果为空')
            return text
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('图片识别结果无效，未保存文件') from exc


def read_image_linux(data):
    """Explicit Linux OCR backend; no silent fallback on failed recognition."""
    from io import BytesIO
    from PIL import Image, ImageOps
    from pillow_heif import register_heif_opener
    import pytesseract
    register_heif_opener()
    try:
        with Image.open(BytesIO(data)) as photo:
            if photo.width * photo.height > 60000000:
                raise ValueError('图片像素超过 6000 万')
            photo = ImageOps.exif_transpose(photo).convert('RGB')
            text = pytesseract.image_to_string(photo,lang='chi_sim+chi_tra+eng',timeout=90).strip()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('图片识别失败，请检查格式或稍后重试；未保存。') from exc
    if not text:
        raise ValueError('未识别到文字，请上传清晰图片。')
    return text
