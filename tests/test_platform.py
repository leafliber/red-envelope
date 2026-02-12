"""平台抽象基类单元测试."""

from src.platform.base import PlatformWindow, WindowInfo


class TestWindowInfo:
    """测试 WindowInfo 数据类."""

    def test_create_window_info(self):
        """创建窗口信息."""
        info = WindowInfo(
            window_id=123,
            title="Test Window",
            x=100,
            y=200,
            width=800,
            height=600,
        )
        assert info.window_id == 123
        assert info.title == "Test Window"
        assert info.x == 100
        assert info.y == 200
        assert info.width == 800
        assert info.height == 600
        assert info.is_visible is True  # 默认值
        assert info.pid == 0  # 默认值

    def test_window_info_with_all_fields(self):
        """所有字段均指定."""
        info = WindowInfo(
            window_id=456,
            title="QQ Chat",
            x=0,
            y=0,
            width=1920,
            height=1080,
            is_visible=False,
            pid=9999,
        )
        assert info.is_visible is False
        assert info.pid == 9999

    def test_platform_window_is_abstract(self):
        """PlatformWindow 不能直接实例化."""
        import pytest

        with pytest.raises(TypeError):
            PlatformWindow()
