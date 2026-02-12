"""平台抽象基类 - 定义跨平台窗口操作接口."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class WindowInfo:
    """窗口信息数据类."""

    window_id: int  # 窗口句柄(Windows)或窗口ID(macOS)
    title: str  # 窗口标题
    x: int  # 窗口左上角X坐标
    y: int  # 窗口左上角Y坐标
    width: int  # 窗口宽度
    height: int  # 窗口高度
    is_visible: bool = True  # 窗口是否可见
    pid: int = 0  # 所属进程ID


class PlatformWindow(ABC):
    """跨平台窗口操作抽象基类.

    定义窗口枚举、截图、激活等操作的统一接口,
    由各平台子类提供具体实现。
    """

    @abstractmethod
    def enumerate_windows(self, title_keywords: List[str]) -> List[WindowInfo]:
        """枚举所有匹配关键词的窗口.

        Args:
            title_keywords: 窗口标题关键词列表，匹配任意一个即返回。

        Returns:
            匹配到的窗口信息列表。
        """

    @abstractmethod
    def capture_window(self, window: WindowInfo) -> Optional[np.ndarray]:
        """后台截取指定窗口的内容（不需要窗口在最前）.

        Args:
            window: 目标窗口信息。

        Returns:
            窗口截图的numpy数组(BGR格式)，失败返回None。
        """

    @abstractmethod
    def activate_window(self, window: WindowInfo) -> bool:
        """将指定窗口激活并置顶到最前.

        Args:
            window: 目标窗口信息。

        Returns:
            是否成功激活。
        """

    @abstractmethod
    def is_window_valid(self, window: WindowInfo) -> bool:
        """检查窗口句柄是否仍然有效.

        Args:
            window: 目标窗口信息。

        Returns:
            窗口是否有效。
        """

    @abstractmethod
    def get_window_rect(self, window: WindowInfo) -> Optional[tuple]:
        """获取窗口在屏幕上的实际位置和大小.

        Args:
            window: 目标窗口信息。

        Returns:
            (x, y, width, height) 元组，失败返回None。
        """
