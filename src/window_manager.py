"""窗口管理模块 - 封装窗口扫描、缓存和操作."""

import logging
import time
from typing import Dict, List, Optional

from .platform import PlatformWindow, WindowInfo, get_platform

logger = logging.getLogger(__name__)


class WindowManager:
    """窗口管理器.

    负责窗口扫描、缓存管理和窗口操作的协调。
    使用缓存减少重复的窗口枚举开销。
    """

    def __init__(
        self,
        title_keywords: Optional[List[str]] = None,
        cache_ttl: float = 5.0,
        platform: Optional[PlatformWindow] = None,
    ) -> None:
        """初始化窗口管理器.

        Args:
            title_keywords: 窗口标题匹配关键词，默认 ["QQ"]。
            cache_ttl: 窗口列表缓存过期时间（秒）。
            platform: 平台实现实例，为 None 时自动检测。
        """
        self.title_keywords = title_keywords or ["QQ"]
        self.cache_ttl = cache_ttl
        self.platform = platform or get_platform()

        # 缓存
        self._window_cache: List[WindowInfo] = []
        self._cache_timestamp: float = 0.0

    @property
    def _cache_valid(self) -> bool:
        """检查缓存是否仍在有效期内."""
        return (time.time() - self._cache_timestamp) < self.cache_ttl

    def scan_windows(self, force_refresh: bool = False) -> List[WindowInfo]:
        """扫描匹配的QQ窗口列表.

        Args:
            force_refresh: 是否强制刷新缓存。

        Returns:
            匹配到的窗口信息列表。
        """
        if not force_refresh and self._cache_valid and self._window_cache:
            logger.debug("使用缓存的窗口列表 (%d 个窗口)", len(self._window_cache))
            return self._window_cache

        try:
            windows = self.platform.enumerate_windows(self.title_keywords)
            # 过滤无效窗口
            valid_windows = [
                w for w in windows if self.platform.is_window_valid(w)
            ]
            self._window_cache = valid_windows
            self._cache_timestamp = time.time()
            logger.debug(
                "窗口扫描完成，发现 %d 个有效QQ窗口", len(valid_windows)
            )
            return valid_windows

        except Exception as e:
            logger.error("窗口扫描失败: %s", e)
            return self._window_cache  # 失败时返回旧缓存

    def capture_window(self, window: WindowInfo) -> Optional["numpy.ndarray"]:
        """后台截取指定窗口.

        Args:
            window: 目标窗口。

        Returns:
            截图 numpy 数组（BGR格式），失败返回 None。
        """
        if not self.platform.is_window_valid(window):
            logger.warning(
                "窗口 '%s' (ID=%d) 已失效，从缓存中移除",
                window.title,
                window.window_id,
            )
            self._remove_from_cache(window)
            return None

        return self.platform.capture_window(window)

    def activate_window(self, window: WindowInfo) -> bool:
        """激活指定窗口并置顶.

        Args:
            window: 目标窗口。

        Returns:
            是否成功激活。
        """
        if not self.platform.is_window_valid(window):
            logger.warning("窗口 '%s' 已失效，无法激活", window.title)
            self._remove_from_cache(window)
            return False

        return self.platform.activate_window(window)

    def get_window_screen_pos(self, window: WindowInfo) -> Optional[tuple]:
        """获取窗口在屏幕上的绝对位置.

        Args:
            window: 目标窗口。

        Returns:
            (x, y, width, height) 元组。
        """
        return self.platform.get_window_rect(window)

    def invalidate_cache(self) -> None:
        """手动使缓存失效."""
        self._cache_timestamp = 0.0
        logger.debug("窗口缓存已失效")

    def _remove_from_cache(self, window: WindowInfo) -> None:
        """从缓存中移除指定窗口."""
        self._window_cache = [
            w for w in self._window_cache if w.window_id != window.window_id
        ]
