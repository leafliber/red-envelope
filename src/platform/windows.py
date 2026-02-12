"""Windows 平台实现 - 基于 pywin32 的窗口操作."""

import ctypes
import logging
from typing import List, Optional

import numpy as np

from .base import PlatformWindow, WindowInfo

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32con
    import win32ui
    import win32process

    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
    logger.debug("pywin32 未安装，Windows 平台功能不可用")


class WindowsPlatform(PlatformWindow):
    """Windows 平台窗口操作实现.

    使用 pywin32 (win32gui, win32con, win32ui) 进行窗口枚举、
    后台截图 (PrintWindow) 和窗口激活。
    """

    def __init__(self) -> None:
        if not _HAS_WIN32:
            raise ImportError(
                "Windows 平台需要安装 pywin32: pip install pywin32"
            )
        # 设置 DPI 感知，避免截图缩放问题
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            logger.warning("设置 DPI 感知失败，截图可能存在缩放问题")

    def enumerate_windows(self, title_keywords: List[str]) -> List[WindowInfo]:
        """枚举所有匹配关键词的窗口."""
        matched: List[WindowInfo] = []

        def _enum_callback(hwnd: int, _extra: object) -> None:
            if not win32gui.IsWindow(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            # 检查标题是否包含任意关键词（不区分大小写）
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in title_keywords):
                return

            is_visible = bool(win32gui.IsWindowVisible(hwnd))
            try:
                rect = win32gui.GetWindowRect(hwnd)
                x, y = rect[0], rect[1]
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
            except Exception:
                x = y = width = height = 0

            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                pid = 0

            # 过滤无效窗口（宽高为0）
            if width > 0 and height > 0:
                info = WindowInfo(
                    window_id=hwnd,
                    title=title,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    is_visible=is_visible,
                    pid=pid,
                )
                matched.append(info)

        win32gui.EnumWindows(_enum_callback, None)
        logger.debug("扫描到 %d 个匹配窗口", len(matched))
        return matched

    def capture_window(self, window: WindowInfo) -> Optional[np.ndarray]:
        """使用 PrintWindow 后台截取窗口内容."""
        hwnd = window.window_id
        if not self.is_window_valid(window):
            logger.warning("窗口句柄 %d 无效，跳过截图", hwnd)
            return None

        try:
            # 获取窗口实际尺寸
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            if width <= 0 or height <= 0:
                logger.warning("窗口 %d 尺寸异常: %dx%d", hwnd, width, height)
                return None

            # 创建设备上下文和位图
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            # 使用 PrintWindow 截取后台窗口
            # PW_RENDERFULLCONTENT = 2, 用于截取完整内容
            result = ctypes.windll.user32.PrintWindow(
                hwnd, save_dc.GetSafeHdc(), 2
            )

            if result == 0:
                # 回退到不带标志的 PrintWindow
                result = ctypes.windll.user32.PrintWindow(
                    hwnd, save_dc.GetSafeHdc(), 0
                )

            # 读取位图数据
            bmp_info = bitmap.GetInfo()
            bmp_data = bitmap.GetBitmapBits(True)

            img = np.frombuffer(bmp_data, dtype=np.uint8)
            img = img.reshape(
                (bmp_info["bmHeight"], bmp_info["bmWidth"], 4)
            )
            # BGRA -> BGR
            img = img[:, :, :3]

            # 清理资源
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            win32gui.DeleteObject(bitmap.GetHandle())

            logger.debug("成功截取窗口 '%s' (%dx%d)", window.title, width, height)
            return img.copy()

        except Exception as e:
            logger.error("截取窗口 '%s' 失败: %s", window.title, e)
            return None

    def activate_window(self, window: WindowInfo) -> bool:
        """将窗口激活并置顶."""
        hwnd = window.window_id
        if not self.is_window_valid(window):
            logger.warning("窗口句柄 %d 无效，无法激活", hwnd)
            return False

        try:
            # 如果窗口最小化，先恢复
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # 将窗口置顶
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            )
            # 取消置顶（只是拉到最前，不始终置顶）
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            )
            logger.info("已激活窗口: '%s'", window.title)
            return True

        except Exception as e:
            logger.error("激活窗口 '%s' 失败: %s", window.title, e)
            return False

    def is_window_valid(self, window: WindowInfo) -> bool:
        """检查窗口句柄是否仍然有效."""
        return bool(win32gui.IsWindow(window.window_id))

    def get_window_rect(self, window: WindowInfo) -> Optional[tuple]:
        """获取窗口在屏幕上的位置和大小."""
        if not self.is_window_valid(window):
            return None
        try:
            rect = win32gui.GetWindowRect(window.window_id)
            return (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
        except Exception as e:
            logger.error("获取窗口 '%s' 位置失败: %s", window.title, e)
            return None
