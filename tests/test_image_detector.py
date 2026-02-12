"""ImageDetector 单元测试."""

import os
import tempfile

import cv2
import numpy as np
import pytest

from src.image_detector import ImageDetector, MatchResult


@pytest.fixture
def template_path(tmp_path):
    """创建临时模板图片."""
    img = np.zeros((50, 100, 3), dtype=np.uint8)
    # 画一个红色矩形作为模板特征
    cv2.rectangle(img, (10, 10), (90, 40), (0, 0, 255), -1)
    path = str(tmp_path / "template.png")
    cv2.imwrite(path, img)
    return path


@pytest.fixture
def detector(template_path):
    """创建 ImageDetector 实例."""
    return ImageDetector(
        template_path=template_path,
        threshold=0.8,
        method="TM_CCOEFF_NORMED",
        grayscale=True,
    )


class TestImageDetectorInit:
    """测试 ImageDetector 初始化."""

    def test_init_success(self, template_path):
        """正常初始化."""
        det = ImageDetector(template_path=template_path)
        assert det.template is not None
        assert det.template_w == 100
        assert det.template_h == 50

    def test_init_file_not_found(self):
        """模板文件不存在."""
        with pytest.raises(FileNotFoundError):
            ImageDetector(template_path="/nonexistent/template.png")

    def test_init_invalid_method(self, template_path):
        """无效的匹配算法."""
        with pytest.raises(ValueError, match="不支持的匹配算法"):
            ImageDetector(template_path=template_path, method="INVALID")

    def test_init_invalid_threshold(self, template_path):
        """无效的阈值范围."""
        with pytest.raises(ValueError, match="阈值必须在"):
            ImageDetector(template_path=template_path, threshold=1.5)

        with pytest.raises(ValueError, match="阈值必须在"):
            ImageDetector(template_path=template_path, threshold=-0.1)

    def test_init_grayscale_false(self, template_path):
        """非灰度模式初始化."""
        det = ImageDetector(template_path=template_path, grayscale=False)
        assert len(det.template.shape) == 3  # BGR 三通道

    def test_init_grayscale_true(self, template_path):
        """灰度模式初始化."""
        det = ImageDetector(template_path=template_path, grayscale=True)
        assert len(det.template.shape) == 2  # 单通道


class TestImageDetectorDetect:
    """测试 ImageDetector 检测功能."""

    def test_detect_match(self, detector, template_path):
        """在包含模板的截图中检测."""
        # 创建一个更大的图像，将模板嵌入其中
        screenshot = np.zeros((200, 300, 3), dtype=np.uint8)
        template = cv2.imread(template_path)
        # 放在 (50, 30) 位置
        screenshot[30 : 30 + 50, 50 : 50 + 100] = template

        result = detector.detect(screenshot)
        assert result.found is True
        assert result.confidence >= 0.8
        # 中心应该大约在 (100, 55) 附近
        assert 45 <= result.center_x <= 155
        assert 25 <= result.center_y <= 80

    def test_detect_no_match(self, detector):
        """在不包含模板的截图中检测."""
        # 纯白图像不应匹配
        screenshot = np.ones((200, 300, 3), dtype=np.uint8) * 200
        result = detector.detect(screenshot)
        assert result.found is False

    def test_detect_none_input(self, detector):
        """输入 None."""
        result = detector.detect(None)
        assert result.found is False
        assert result.confidence == 0.0

    def test_detect_empty_image(self, detector):
        """输入空图像."""
        empty = np.array([], dtype=np.uint8)
        result = detector.detect(empty)
        assert result.found is False

    def test_detect_small_image(self, detector):
        """输入比模板小的图像."""
        small = np.zeros((10, 10, 3), dtype=np.uint8)
        result = detector.detect(small)
        assert result.found is False

    def test_match_result_fields(self, detector, template_path):
        """验证 MatchResult 字段完整性."""
        screenshot = np.zeros((200, 300, 3), dtype=np.uint8)
        template = cv2.imread(template_path)
        screenshot[30 : 30 + 50, 50 : 50 + 100] = template

        result = detector.detect(screenshot)
        assert isinstance(result, MatchResult)
        assert isinstance(result.found, bool)
        assert isinstance(result.confidence, float)
        assert isinstance(result.x, (int, np.integer))
        assert isinstance(result.y, (int, np.integer))
        assert result.width == 100
        assert result.height == 50


class TestImageDetectorMethods:
    """测试不同匹配算法."""

    @pytest.mark.parametrize(
        "method",
        ["TM_CCOEFF_NORMED", "TM_CCORR_NORMED", "TM_SQDIFF_NORMED"],
    )
    def test_all_methods(self, template_path, method):
        """所有支持的匹配算法都能正常初始化和检测."""
        det = ImageDetector(
            template_path=template_path,
            threshold=0.5,
            method=method,
        )
        screenshot = np.zeros((200, 300, 3), dtype=np.uint8)
        template = cv2.imread(template_path)
        screenshot[30 : 30 + 50, 50 : 50 + 100] = template

        result = det.detect(screenshot)
        assert isinstance(result, MatchResult)
        assert 0.0 <= result.confidence <= 1.0
