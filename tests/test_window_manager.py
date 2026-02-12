"""WindowManager 单元测试."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.platform.base import PlatformWindow, WindowInfo
from src.window_manager import WindowManager


class MockPlatform(PlatformWindow):
    """测试用的 Mock 平台实现."""

    def __init__(self):
        self._windows = []
        self._screenshots = {}
        self._valid_ids = set()

    def set_windows(self, windows):
        self._windows = windows
        self._valid_ids = {w.window_id for w in windows}

    def set_screenshot(self, window_id, img):
        self._screenshots[window_id] = img

    def enumerate_windows(self, title_keywords):
        return [
            w
            for w in self._windows
            if any(kw.lower() in w.title.lower() for kw in title_keywords)
        ]

    def capture_window(self, window):
        return self._screenshots.get(window.window_id)

    def activate_window(self, window):
        return window.window_id in self._valid_ids

    def is_window_valid(self, window):
        return window.window_id in self._valid_ids

    def get_window_rect(self, window):
        if window.window_id in self._valid_ids:
            return (window.x, window.y, window.width, window.height)
        return None


@pytest.fixture
def mock_platform():
    """创建 Mock 平台."""
    return MockPlatform()


@pytest.fixture
def sample_windows():
    """创建示例窗口列表."""
    return [
        WindowInfo(
            window_id=1001,
            title="QQ - 聊天窗口",
            x=100,
            y=100,
            width=800,
            height=600,
            pid=1234,
        ),
        WindowInfo(
            window_id=1002,
            title="QQ - 群聊",
            x=200,
            y=200,
            width=800,
            height=600,
            pid=1234,
        ),
    ]


@pytest.fixture
def window_manager(mock_platform, sample_windows):
    """创建配置好的 WindowManager."""
    mock_platform.set_windows(sample_windows)
    return WindowManager(
        title_keywords=["QQ"],
        cache_ttl=5.0,
        platform=mock_platform,
    )


class TestWindowManagerScan:
    """测试窗口扫描."""

    def test_scan_finds_windows(self, window_manager):
        """扫描到QQ窗口."""
        windows = window_manager.scan_windows()
        assert len(windows) == 2

    def test_scan_empty(self, mock_platform):
        """无匹配窗口."""
        mock_platform.set_windows([])
        wm = WindowManager(
            title_keywords=["QQ"],
            platform=mock_platform,
        )
        windows = wm.scan_windows()
        assert len(windows) == 0

    def test_scan_uses_cache(self, window_manager, mock_platform):
        """缓存有效期内复用."""
        # 第一次扫描
        windows1 = window_manager.scan_windows()
        # 修改底层数据
        mock_platform.set_windows([])
        # 第二次应该返回缓存
        windows2 = window_manager.scan_windows()
        assert len(windows2) == 2

    def test_scan_force_refresh(self, window_manager, mock_platform):
        """强制刷新缓存."""
        window_manager.scan_windows()
        mock_platform.set_windows([])
        windows = window_manager.scan_windows(force_refresh=True)
        assert len(windows) == 0

    def test_invalidate_cache(self, window_manager, mock_platform):
        """手动缓存失效."""
        window_manager.scan_windows()
        mock_platform.set_windows([])
        window_manager.invalidate_cache()
        windows = window_manager.scan_windows()
        assert len(windows) == 0


class TestWindowManagerCapture:
    """测试窗口截图."""

    def test_capture_success(self, window_manager, mock_platform, sample_windows):
        """成功截图."""
        test_img = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_platform.set_screenshot(1001, test_img)

        result = window_manager.capture_window(sample_windows[0])
        assert result is not None
        assert result.shape == (600, 800, 3)

    def test_capture_no_screenshot(self, window_manager, sample_windows):
        """截图为 None."""
        result = window_manager.capture_window(sample_windows[0])
        assert result is None

    def test_capture_invalid_window(self, window_manager, mock_platform):
        """无效窗口截图."""
        invalid_win = WindowInfo(
            window_id=9999,
            title="Invalid",
            x=0,
            y=0,
            width=100,
            height=100,
        )
        result = window_manager.capture_window(invalid_win)
        assert result is None


class TestWindowManagerActivate:
    """测试窗口激活."""

    def test_activate_success(self, window_manager, sample_windows):
        """成功激活窗口."""
        result = window_manager.activate_window(sample_windows[0])
        assert result is True

    def test_activate_invalid_window(self, window_manager):
        """激活无效窗口."""
        invalid_win = WindowInfo(
            window_id=9999,
            title="Invalid",
            x=0,
            y=0,
            width=100,
            height=100,
        )
        result = window_manager.activate_window(invalid_win)
        assert result is False


class TestWindowManagerRect:
    """测试获取窗口位置."""

    def test_get_rect(self, window_manager, sample_windows):
        """获取窗口位置."""
        rect = window_manager.get_window_screen_pos(sample_windows[0])
        assert rect is not None
        assert rect == (100, 100, 800, 600)
