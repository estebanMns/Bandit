"""Detector de movimiento barato para no gastar llamadas en escenas quietas."""

import io

from PIL import Image, ImageChops, ImageStat

_SAMPLE_SIZE = (64, 36)
_MAX_LEVEL = 255


def _thumbnail(jpeg: bytes) -> Image.Image:
    with Image.open(io.BytesIO(jpeg)) as image:
        return image.convert("L").resize(_SAMPLE_SIZE)


class PillowMotionDetector:
    def score(self, previous_jpeg: bytes, current_jpeg: bytes) -> float:
        difference = ImageChops.difference(_thumbnail(previous_jpeg), _thumbnail(current_jpeg))
        return float(ImageStat.Stat(difference).mean[0]) / _MAX_LEVEL
