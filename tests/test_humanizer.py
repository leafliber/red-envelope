"""Humanizer 单元测试."""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.humanizer import Humanizer


@pytest.fixture
def humanizer():
    """创建 Humanizer 实例（mock pyautogui）."""
    with patch("src.humanizer.pyautogui") as mock_pag:
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.05
        mock_pag.easeInOutQuad = lambda x: x
        mock_pag.easeOutQuad = lambda x: x
        mock_pag.linear = lambda x: x
        mock_pag.easeInQuad = lambda x: x
        mock_pag.FailSafeException = Exception

        h = Humanizer(
            move_duration_min=0.01,
            move_duration_max=0.02,
            click_offset_x=5,
            click_offset_y=5,
            click_wait_min=0.01,
            click_wait_max=0.02,
            action_wait_min=0.01,
            action_wait_max=0.02,
        )
        h._pag = mock_pag
        yield h, mock_pag


class TestHumanizerInit:
    """测试 Humanizer 初始化."""

    def test_init_defaults(self, humanizer):
        """默认参数初始化."""
        h, _ = humanizer
        assert h.move_duration_min >= 0.01
        assert h.move_duration_max >= h.move_duration_min
        assert h.click_offset_x >= 0
        assert h.click_offset_y >= 0

    def test_init_clamps_values(self):
        """参数约束检查."""
        with patch("src.humanizer.pyautogui") as mock_pag:
            mock_pag.size.return_value = (1920, 1080)
            mock_pag.easeInOutQuad = lambda x: x
            h = Humanizer(
                move_duration_min=-1.0,
                move_duration_max=0.01,
                click_offset_x=-5,
                click_offset_y=-5,
                click_wait_min=-1.0,
                click_wait_max=0.01,
                action_wait_min=-1.0,
                action_wait_max=0.01,
            )
            assert h.move_duration_min >= 0.05  # 最小值限制
            assert h.click_offset_x == 0  # 负值被截断为0
            assert h.click_wait_min >= 0.1


class TestHumanizerSafety:
    """测试安全检查."""

    def test_safe_position(self, humanizer):
        """屏幕内坐标."""
        h, _ = humanizer
        assert h._is_safe_position(100, 100) is True
        assert h._is_safe_position(0, 0) is True

    def test_unsafe_position(self, humanizer):
        """屏幕外坐标."""
        h, _ = humanizer
        assert h._is_safe_position(-1, 100) is False
        assert h._is_safe_position(100, -1) is False
        assert h._is_safe_position(2000, 100) is False
        assert h._is_safe_position(100, 1200) is False

    def test_add_offset_stays_in_bounds(self, humanizer):
        """偏移后仍在屏幕内."""
        h, _ = humanizer
        for _ in range(100):
            x, y = h._add_offset(960, 540)
            assert 0 <= x < 1920
            assert 0 <= y < 1080

    def test_add_offset_edge_cases(self, humanizer):
        """边缘坐标偏移不越界."""
        h, _ = humanizer
        for _ in range(100):
            x, y = h._add_offset(0, 0)
            assert x >= 0
            assert y >= 0
            x, y = h._add_offset(1919, 1079)
            assert x < 1920
            assert y < 1080


class TestHumanizerActions:
    """测试操作方法."""

    def test_move_to(self, humanizer):
        """鼠标移动."""
        h, mock_pag = humanizer
        result = h.move_to(500, 500, with_offset=False)
        assert result is True
        mock_pag.moveTo.assert_called_once()

    def test_move_to_unsafe(self, humanizer):
        """移动到屏幕外."""
        h, mock_pag = humanizer
        result = h.move_to(-100, -100, with_offset=False)
        assert result is False
        mock_pag.moveTo.assert_not_called()

    def test_click(self, humanizer):
        """点击操作."""
        h, mock_pag = humanizer
        result = h.click(500, 500, with_offset=False)
        assert result is True
        mock_pag.moveTo.assert_called_once()
        mock_pag.click.assert_called_once()

    def test_click_unsafe(self, humanizer):
        """点击屏幕外."""
        h, mock_pag = humanizer
        result = h.click(-100, -100, with_offset=False)
        assert result is False

    def test_press_key(self, humanizer):
        """按键操作."""
        h, mock_pag = humanizer
        result = h.press_key("escape")
        assert result is True
        mock_pag.press.assert_called_once_with("escape")

    def test_random_wait(self, humanizer):
        """随机等待."""
        h, _ = humanizer
        start = time.time()
        wait_time = h.random_wait()
        elapsed = time.time() - start
        assert wait_time >= h.action_wait_min
        assert wait_time <= h.action_wait_max
