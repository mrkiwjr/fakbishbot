import os
import json
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PhotoCache:
    def __init__(self, cache_file: str = "data/photo_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки кеша фото: {e}")
                return {}
        return {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кеша фото: {e}")

    def get_file_id(self, photo_key: str, photo_path: str) -> Optional[str]:
        if not photo_path or not os.path.exists(photo_path):
            return None

        file_stat = os.stat(photo_path)
        file_size = file_stat.st_size
        file_mtime = file_stat.st_mtime

        cached = self.cache.get(photo_key)
        if cached:
            if cached.get('size') == file_size and cached.get('mtime') == file_mtime:
                logger.debug(f"Использование кешированного file_id для {photo_key}")
                return cached.get('file_id')

        return None

    def save_file_id(self, photo_key: str, photo_path: str, file_id: str):
        if not photo_path or not os.path.exists(photo_path):
            return

        try:
            file_stat = os.stat(photo_path)
            self.cache[photo_key] = {
                'file_id': file_id,
                'size': file_stat.st_size,
                'mtime': file_stat.st_mtime,
                'path': photo_path
            }
            self._save_cache()
            logger.info(f"Сохранен file_id для {photo_key}")
        except Exception as e:
            logger.error(f"Ошибка сохранения file_id для {photo_key}: {e}")

    def validate_photo(self, photo_path: str) -> tuple[bool, Optional[str]]:
        if not os.path.exists(photo_path):
            return False, "Файл не найден"

        file_size = os.path.getsize(photo_path)
        max_size = 10 * 1024 * 1024

        if file_size > max_size:
            return False, f"Размер файла {file_size / 1024 / 1024:.2f} МБ превышает лимит 10 МБ"

        try:
            from PIL import Image
            with Image.open(photo_path) as img:
                width, height = img.size

                if width > 10000 or height > 10000:
                    return False, f"Разрешение {width}x{height} превышает лимит 10000px"

                ratio = max(width, height) / min(width, height)
                if ratio > 20:
                    return False, f"Соотношение сторон {ratio:.1f}:1 превышает лимит 20:1"

            return True, None

        except ImportError:
            logger.warning("Pillow не установлен, пропуск валидации размерности изображения")
            return True, None
        except Exception as e:
            logger.error(f"Ошибка валидации изображения {photo_path}: {e}")
            return False, f"Ошибка валидации: {e}"

photo_cache = PhotoCache()
