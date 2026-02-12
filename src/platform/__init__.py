"""平台模块 - 根据当前操作系统自动选择平台实现."""

import platform
import logging
from typing import Optional

from .base import PlatformWindow, WindowInfo

logger = logging.getLogger(__name__)

__all__ = ["PlatformWindow", "WindowInfo", "get_platform"]


def get_platform() -> PlatformWindow:
    """根据当前操作系统返回对应的平台实现.

    Returns:
        当前平台的 PlatformWindow 实现实例。

    Raises:
        OSError: 不支持的操作系统。
    """
    system = platform.system()

    if system == "Windows":
        from .windows import WindowsPlatform
        logger.info("检测到 Windows 平台")
        return WindowsPlatform()
    elif system == "Darwin":
        from .macos import MacOSPlatform
        logger.info("检测到 macOS 平台")
        return MacOSPlatform()
    else:
        raise OSError(f"不支持的操作系统: {system}，仅支持 Windows 和 macOS")
