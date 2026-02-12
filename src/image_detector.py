"""图像识别模块 - 基于 OpenCV 模板匹配检测红包."""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# OpenCV 匹配算法映射
_MATCH_METHODS = {
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}


@dataclass
class MatchResult:
    """模板匹配结果."""

    found: bool  # 是否找到匹配
    confidence: float  # 匹配置信度
    x: int  # 匹配区域左上角 X（相对于截图）
    y: int  # 匹配区域左上角 Y（相对于截图）
    width: int  # 匹配区域宽度
    height: int  # 匹配区域高度
    center_x: int  # 匹配区域中心 X
    center_y: int  # 匹配区域中心 Y


class ImageDetector:
    """图像识别器.

    使用 OpenCV 模板匹配算法在窗口截图中检测红包图片。
    """

    def __init__(
        self,
        template_path: str,
        threshold: float = 0.8,
        method: str = "TM_CCOEFF_NORMED",
        grayscale: bool = True,
    ) -> None:
        """初始化图像识别器.

        Args:
            template_path: 红包模板图片路径。
            threshold: 匹配阈值 (0.0 ~ 1.0)。
            method: 匹配算法名称。
            grayscale: 是否使用灰度匹配。

        Raises:
            FileNotFoundError: 模板图片不存在。
            ValueError: 不支持的匹配算法或无效阈值。
        """
        if not os.path.isfile(template_path):
            raise FileNotFoundError(f"模板图片不存在: {template_path}")

        if method not in _MATCH_METHODS:
            raise ValueError(
                f"不支持的匹配算法: {method}，"
                f"可选: {', '.join(_MATCH_METHODS.keys())}"
            )

        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"阈值必须在 0.0 到 1.0 之间，当前: {threshold}")

        self.threshold = threshold
        self.method = _MATCH_METHODS[method]
        self.method_name = method
        self.grayscale = grayscale
        self._is_sqdiff = "SQDIFF" in method

        # 加载模板图片
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            raise ValueError(f"无法读取模板图片: {template_path}")

        if grayscale:
            self.template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            self.template = template

        self.template_h, self.template_w = self.template.shape[:2]
        logger.info(
            "图像识别器初始化: 模板=%s (%dx%d), 阈值=%.2f, 算法=%s, 灰度=%s",
            template_path,
            self.template_w,
            self.template_h,
            threshold,
            method,
            grayscale,
        )

    def detect(self, screenshot: np.ndarray) -> MatchResult:
        """在截图中检测红包.

        Args:
            screenshot: 窗口截图 (BGR numpy数组)。

        Returns:
            匹配结果。
        """
        if screenshot is None or screenshot.size == 0:
            return MatchResult(
                found=False, confidence=0.0,
                x=0, y=0, width=0, height=0,
                center_x=0, center_y=0,
            )

        try:
            # 确保截图尺寸大于模板
            img_h, img_w = screenshot.shape[:2]
            if img_h < self.template_h or img_w < self.template_w:
                logger.debug(
                    "截图尺寸 (%dx%d) 小于模板 (%dx%d)，跳过",
                    img_w, img_h, self.template_w, self.template_h,
                )
                return MatchResult(
                    found=False, confidence=0.0,
                    x=0, y=0, width=0, height=0,
                    center_x=0, center_y=0,
                )

            # 转换为匹配所需格式
            if self.grayscale:
                img = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            else:
                img = screenshot

            # 执行模板匹配
            result = cv2.matchTemplate(img, self.template, self.method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            # SQDIFF 系列：值越小越匹配
            if self._is_sqdiff:
                confidence = 1.0 - min_val
                match_loc = min_loc
            else:
                confidence = max_val
                match_loc = max_loc

            found = confidence >= self.threshold
            x, y = match_loc
            center_x = x + self.template_w // 2
            center_y = y + self.template_h // 2

            if found:
                logger.info(
                    "检测到红包! 置信度=%.4f, 位置=(%d, %d), "
                    "中心=(%d, %d)",
                    confidence, x, y, center_x, center_y,
                )
            else:
                logger.debug("未检测到红包, 最高置信度=%.4f", confidence)

            return MatchResult(
                found=found,
                confidence=confidence,
                x=x,
                y=y,
                width=self.template_w,
                height=self.template_h,
                center_x=center_x,
                center_y=center_y,
            )

        except Exception as e:
            logger.error("图像识别出错: %s", e)
            return MatchResult(
                found=False, confidence=0.0,
                x=0, y=0, width=0, height=0,
                center_x=0, center_y=0,
            )
