"""人类化操作模块 - 模拟真实用户的鼠标操作和延时行为."""

import logging
import random
import time
from typing import Optional, Tuple

import pyautogui

logger = logging.getLogger(__name__)

# PyAutoGUI 安全设置
pyautogui.FAILSAFE = True  # 鼠标移到左上角触发 FailSafe
pyautogui.PAUSE = 0.05  # 操作间最小间隔

# tween 函数映射
_TWEEN_FUNCTIONS = {
    "easeInOutQuad": pyautogui.easeInOutQuad,
    "easeOutQuad": pyautogui.easeOutQuad,
    "linear": pyautogui.linear,
    "easeInQuad": pyautogui.easeInQuad,
    "easeInOutSine": getattr(pyautogui, "easeInOutSine", pyautogui.linear),
}


class Humanizer:
    """人类化操作器.

    通过随机偏移、贝塞尔曲线鼠标轨迹和随机延时
    模拟真实人类的鼠标操作行为。
    """

    def __init__(
        self,
        move_duration_min: float = 0.2,
        move_duration_max: float = 0.5,
        click_offset_x: int = 5,
        click_offset_y: int = 5,
        click_wait_min: float = 0.3,
        click_wait_max: float = 0.8,
        action_wait_min: float = 0.5,
        action_wait_max: float = 1.5,
        tween_function: str = "easeInOutQuad",
    ) -> None:
        """初始化人类化操作器.

        Args:
            move_duration_min: 鼠标移动最短时长（秒）。
            move_duration_max: 鼠标移动最长时长（秒）。
            click_offset_x: 点击X轴随机偏移范围（像素）。
            click_offset_y: 点击Y轴随机偏移范围（像素）。
            click_wait_min: 点击后最短等待时间（秒）。
            click_wait_max: 点击后最长等待时间（秒）。
            action_wait_min: 操作间最短等待时间（秒）。
            action_wait_max: 操作间最长等待时间（秒）。
            tween_function: 鼠标移动插值函数名称。
        """
        self.move_duration_min = max(0.05, move_duration_min)
        self.move_duration_max = max(self.move_duration_min, move_duration_max)
        self.click_offset_x = max(0, click_offset_x)
        self.click_offset_y = max(0, click_offset_y)
        self.click_wait_min = max(0.1, click_wait_min)
        self.click_wait_max = max(self.click_wait_min, click_wait_max)
        self.action_wait_min = max(0.1, action_wait_min)
        self.action_wait_max = max(self.action_wait_min, action_wait_max)

        self.tween = _TWEEN_FUNCTIONS.get(tween_function, pyautogui.easeInOutQuad)

        # 获取屏幕尺寸用于安全检查
        self._screen_width, self._screen_height = pyautogui.size()

        logger.info(
            "人类化操作器初始化: 移动时长=%.1f~%.1fs, 偏移=±%d/±%dpx, "
            "点击延迟=%.1f~%.1fs, 操作间隔=%.1f~%.1fs",
            self.move_duration_min,
            self.move_duration_max,
            self.click_offset_x,
            self.click_offset_y,
            self.click_wait_min,
            self.click_wait_max,
            self.action_wait_min,
            self.action_wait_max,
        )

    def _is_safe_position(self, x: int, y: int) -> bool:
        """检查坐标是否在屏幕安全范围内.

        Args:
            x: X 坐标。
            y: Y 坐标。

        Returns:
            坐标是否在屏幕范围内。
        """
        safe = 0 <= x < self._screen_width and 0 <= y < self._screen_height
        if not safe:
            logger.warning(
                "目标坐标 (%d, %d) 超出屏幕范围 (%d x %d)",
                x, y, self._screen_width, self._screen_height,
            )
        return safe

    def _add_offset(self, x: int, y: int) -> Tuple[int, int]:
        """为坐标添加随机偏移.

        Args:
            x: 原始 X 坐标。
            y: 原始 Y 坐标。

        Returns:
            添加偏移后的坐标元组。
        """
        offset_x = random.randint(-self.click_offset_x, self.click_offset_x)
        offset_y = random.randint(-self.click_offset_y, self.click_offset_y)
        new_x = x + offset_x
        new_y = y + offset_y
        # 确保偏移后仍在屏幕内
        new_x = max(0, min(new_x, self._screen_width - 1))
        new_y = max(0, min(new_y, self._screen_height - 1))
        return new_x, new_y

    def move_to(self, x: int, y: int, with_offset: bool = True) -> bool:
        """人类化移动鼠标到指定位置.

        Args:
            x: 目标 X 坐标。
            y: 目标 Y 坐标。
            with_offset: 是否添加随机偏移。

        Returns:
            操作是否成功。
        """
        if with_offset:
            x, y = self._add_offset(x, y)

        if not self._is_safe_position(x, y):
            return False

        duration = random.uniform(self.move_duration_min, self.move_duration_max)

        try:
            pyautogui.moveTo(x, y, duration=duration, tween=self.tween)
            logger.debug("鼠标移动到 (%d, %d), 耗时 %.2fs", x, y, duration)
            return True
        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe 触发，操作中止")
            return False
        except Exception as e:
            logger.error("鼠标移动失败: %s", e)
            return False

    def click(self, x: int, y: int, with_offset: bool = True) -> bool:
        """人类化点击指定位置.

        先移动到目标位置，随机延时后点击。

        Args:
            x: 目标 X 坐标。
            y: 目标 Y 坐标。
            with_offset: 是否添加随机偏移。

        Returns:
            操作是否成功。
        """
        if with_offset:
            x, y = self._add_offset(x, y)

        if not self._is_safe_position(x, y):
            return False

        duration = random.uniform(self.move_duration_min, self.move_duration_max)

        try:
            # 移动鼠标
            pyautogui.moveTo(x, y, duration=duration, tween=self.tween)

            # 随机短暂停顿后点击（模拟人类反应时间）
            pre_click_wait = random.uniform(0.05, 0.15)
            time.sleep(pre_click_wait)

            pyautogui.click(x, y)
            logger.info("点击位置 (%d, %d)", x, y)

            # 点击后等待
            wait = random.uniform(self.click_wait_min, self.click_wait_max)
            time.sleep(wait)
            logger.debug("点击后等待 %.2fs", wait)

            return True

        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe 触发，操作中止")
            return False
        except Exception as e:
            logger.error("点击操作失败: %s", e)
            return False

    def press_key(self, key: str) -> bool:
        """按下指定按键.

        Args:
            key: 按键名称（如 'escape', 'enter'）。

        Returns:
            操作是否成功。
        """
        try:
            # 按键前短暂延时
            wait = random.uniform(0.1, 0.3)
            time.sleep(wait)

            pyautogui.press(key)
            logger.info("按下按键: %s", key)
            return True

        except pyautogui.FailSafeException:
            logger.warning("PyAutoGUI FailSafe 触发，操作中止")
            return False
        except Exception as e:
            logger.error("按键操作失败: %s", e)
            return False

    def random_wait(self) -> float:
        """执行一次随机等待.

        Returns:
            实际等待的时间（秒）。
        """
        wait = random.uniform(self.action_wait_min, self.action_wait_max)
        logger.debug("随机等待 %.2fs", wait)
        time.sleep(wait)
        return wait
