import io

from PIL import Image

from bandit.analysis.infrastructure.pillow_motion import PillowMotionDetector


def jpeg(color: int) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (320, 180), (color, color, color)).save(output, "JPEG")
    return output.getvalue()


def test_identical_images_have_no_motion():
    assert PillowMotionDetector().score(jpeg(40), jpeg(40)) == 0


def test_different_images_have_motion():
    assert PillowMotionDetector().score(jpeg(0), jpeg(255)) > 0.9
