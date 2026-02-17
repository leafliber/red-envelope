"""macOS 平台实现 - 基于 pyobjc 的窗口操作."""

import logging
import subprocess
import time
from contextlib import nullcontext
from typing import List, Optional

import numpy as np

from .base import PlatformWindow, WindowInfo

logger = logging.getLogger(__name__)

try:
    import objc
    import Quartz
    from Quartz import (
        CGRectNull,
        CGWindowListCopyWindowInfo,
        CGWindowListCreateImage,
        kCGNullWindowID,
        kCGWindowImageDefault,
        kCGWindowListExcludeDesktopElements,
        kCGWindowListOptionAll,
        kCGWindowListOptionIncludingWindow,
    )
    from AppKit import (
        NSWorkspace,
        NSRunningApplication,
        NSApplicationActivateIgnoringOtherApps,
    )

    _HAS_PYOBJC = True
except ImportError:
    _HAS_PYOBJC = False
    objc = None
    logger.debug("pyobjc 未安装，macOS 平台功能不可用")


class MacOSPlatform(PlatformWindow):
    """macOS 平台窗口操作实现.

    使用 pyobjc (Quartz, AppKit) 进行窗口枚举、
    后台截图 (CGWindowListCreateImage) 和窗口激活。
    """

    def __init__(self) -> None:
        if not _HAS_PYOBJC:
            raise ImportError(
                "macOS 平台需要安装 pyobjc: pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa"
            )

    def _autorelease_pool(self):
        """返回 pyobjc 自动释放池上下文。

        在长时间循环线程中调用 Cocoa/Quartz API 时，
        自动释放池可及时回收 autoreleased 对象，避免内存持续增长。
        """
        if objc is None:
            return nullcontext()
        return objc.autorelease_pool()

    def enumerate_windows(self, title_keywords: List[str]) -> List[WindowInfo]:
        """枚举所有匹配关键词的窗口."""
        with self._autorelease_pool():
            matched: List[WindowInfo] = []

            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionAll | kCGWindowListExcludeDesktopElements,
                kCGNullWindowID,
            )

            if window_list is None:
                logger.warning("获取窗口列表失败")
                return matched

            for win in window_list:
                # 获取窗口所属应用名称和窗口标题
                owner_name = win.get("kCGWindowOwnerName", "")
                window_name = win.get("kCGWindowName", "")
                # 仅用应用名称（owner_name）匹配关键词，
                # 避免窗口标题中偶然包含关键词的无关窗口被匹配
                owner_lower = owner_name.lower()

                if not any(kw.lower() in owner_lower for kw in title_keywords):
                    continue

                # 过滤非正常窗口层级
                layer = win.get("kCGWindowLayer", 0)
                if layer != 0:
                    continue

                # 过滤不在屏幕上的窗口（如状态栏辅助窗口、弹出面板等）
                if not win.get("kCGWindowIsOnscreen", False):
                    continue

                window_id = win.get("kCGWindowNumber", 0)
                pid = win.get("kCGWindowOwnerPID", 0)

                bounds = win.get("kCGWindowBounds", {})
                x = int(bounds.get("X", 0))
                y = int(bounds.get("Y", 0))
                width = int(bounds.get("Width", 0))
                height = int(bounds.get("Height", 0))

                if width <= 0 or height <= 0:
                    continue

                # 窗口标题优先使用窗口名称，其次用应用名称
                title = window_name if window_name else owner_name

                info = WindowInfo(
                    window_id=window_id,
                    title=title,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    is_visible=True,
                    pid=pid,
                )
                matched.append(info)

            logger.debug("扫描到 %d 个匹配窗口", len(matched))
            return matched

    def capture_window(self, window: WindowInfo) -> Optional[np.ndarray]:
        """使用 CGWindowListCreateImage 后台截取窗口内容."""
        with self._autorelease_pool():
            if not self.is_window_valid(window):
                logger.warning("窗口 %d 无效，跳过截图", window.window_id)
                return None

            try:
                # 按窗口ID截取，不受其他窗口遮挡影响
                cg_image = CGWindowListCreateImage(
                    CGRectNull,
                    kCGWindowListOptionIncludingWindow,
                    window.window_id,
                    kCGWindowImageDefault,
                )

                if cg_image is None:
                    logger.debug("截取窗口 '%s' (ID=%d) 返回空图像，跳过", window.title, window.window_id)
                    return None

                # 获取图像尺寸
                width = Quartz.CGImageGetWidth(cg_image)
                height = Quartz.CGImageGetHeight(cg_image)

                if width == 0 or height == 0:
                    logger.warning("窗口 '%s' 截图尺寸为0", window.title)
                    return None

                # 获取像素数据
                data_provider = Quartz.CGImageGetDataProvider(cg_image)
                pixel_data = Quartz.CGDataProviderCopyData(data_provider)

                # 转换为 numpy 数组（BGRA 格式）
                img = np.frombuffer(pixel_data, dtype=np.uint8)
                bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image)
                img = img.reshape((height, bytes_per_row // 4, 4))
                # 裁剪到实际宽度（bytes_per_row 可能有填充）
                img = img[:, :width, :]
                # BGRA -> BGR
                img = img[:, :, [2, 1, 0]]

                logger.debug(
                    "成功截取窗口 '%s' (像素=%dx%d, 逻辑=%dx%d)",
                    window.title, width, height, window.width, window.height,
                )
                return img.copy()

            except Exception as e:
                logger.error("截取窗口 '%s' 失败: %s", window.title, e)
                return None

    def activate_window(self, window: WindowInfo) -> bool:
        """激活并置前指定窗口.

        先通过 NSRunningApplication 激活应用，再通过
        Accessibility API (AXUIElement) 拉起具体窗口，
        确保是红包所在的聊天窗口被置前而非其他QQ窗口。
        """
        with self._autorelease_pool():
            try:
                # Step 1: 激活应用
                workspace = NSWorkspace.sharedWorkspace()
                running_apps = workspace.runningApplications()

                target_app = None
                for app in running_apps:
                    if app.processIdentifier() == window.pid:
                        target_app = app
                        break

                if target_app is None:
                    logger.warning(
                        "未找到窗口 '%s' 对应的应用 (PID=%d)",
                        window.title,
                        window.pid,
                    )
                    return False

                target_app.activateWithOptions_(
                    NSApplicationActivateIgnoringOtherApps
                )

                # Step 2: 通过 Accessibility API 拉起具体窗口
                raised = self._raise_window_by_title(window)
                if raised:
                    logger.info("已激活并置前窗口: '%s'", window.title)
                else:
                    logger.warning(
                        "AX Raise 未成功，已激活应用但可能非目标窗口置前: '%s'",
                        window.title,
                    )

                return True

            except Exception as e:
                logger.error("激活窗口 '%s' 失败: %s", window.title, e)
                return False

    def _raise_window_by_title(self, window: WindowInfo) -> bool:
        """通过多种方式尝试拉起指定窗口.

        优先使用 AppleScript (System Events)，失败时回退到 AXUIElement。
        """
        # 方法1: AppleScript via System Events（最可靠）
        if self._raise_via_applescript(window):
            return True

        # 方法2: AXUIElement（需要 ApplicationServices）
        if self._raise_via_ax(window):
            return True

        return False

    def _raise_via_applescript(self, window: WindowInfo) -> bool:
        """通过 AppleScript + System Events 拉起指定窗口."""
        try:
            # 转义标题中的特殊字符
            escaped_title = window.title.replace('\\', '\\\\').replace('"', '\\"')

            script = f'''
tell application "System Events"
    set targetProc to first process whose unix id is {window.pid}
    set frontmost of targetProc to true
    set matched to false
    repeat with w in windows of targetProc
        try
            if name of w contains "{escaped_title}" then
                perform action "AXRaise" of w
                set matched to true
                exit repeat
            end if
        end try
    end repeat
    if not matched then
        -- 标题未精确匹配，拉起第一个窗口
        if (count of windows of targetProc) > 0 then
            perform action "AXRaise" of window 1 of targetProc
        end if
    end if
end tell
'''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.returncode == 0:
                logger.debug("AppleScript AXRaise 成功: '%s'", window.title)
                return True
            else:
                logger.debug(
                    "AppleScript AXRaise 失败 (rc=%d): %s",
                    result.returncode,
                    result.stderr.strip(),
                )
                return False

        except subprocess.TimeoutExpired:
            logger.debug("AppleScript 执行超时")
            return False
        except Exception as e:
            logger.debug("AppleScript 异常: %s", e)
            return False

    def _raise_via_ax(self, window: WindowInfo) -> bool:
        """通过 AXUIElement API 拉起指定窗口（备用方案）."""
        try:
            import ApplicationServices as AS

            app_ref = AS.AXUIElementCreateApplication(window.pid)
            err, ax_windows = AS.AXUIElementCopyAttributeValue(
                app_ref, "AXWindows", None
            )
            if err != 0 or ax_windows is None:
                logger.debug(
                    "AX 获取窗口列表失败 (err=%d), PID=%d",
                    err, window.pid,
                )
                return False

            for ax_win in ax_windows:
                err, title = AS.AXUIElementCopyAttributeValue(
                    ax_win, "AXTitle", None
                )
                if err != 0:
                    continue
                if title and window.title and window.title in str(title):
                    err = AS.AXUIElementPerformAction(ax_win, "AXRaise")
                    if err == 0:
                        logger.debug("AXUIElement AXRaise 成功: '%s'", title)
                        return True

            return False

        except ImportError:
            logger.debug("ApplicationServices 不可用，跳过 AXUIElement")
            return False
        except Exception as e:
            logger.debug("AXUIElement 异常: %s", e)
            return False

    def is_window_valid(self, window: WindowInfo) -> bool:
        """检查窗口是否仍然存在."""
        with self._autorelease_pool():
            try:
                window_list = CGWindowListCopyWindowInfo(
                    kCGWindowListOptionAll,
                    kCGNullWindowID,
                )
                if window_list is None:
                    return False
                return any(
                    w.get("kCGWindowNumber", 0) == window.window_id
                    for w in window_list
                )
            except Exception:
                return False

    def get_window_rect(self, window: WindowInfo) -> Optional[tuple]:
        """获取窗口在屏幕上的位置和大小."""
        with self._autorelease_pool():
            try:
                window_list = CGWindowListCopyWindowInfo(
                    kCGWindowListOptionAll,
                    kCGNullWindowID,
                )
                if window_list is None:
                    return None

                for w in window_list:
                    if w.get("kCGWindowNumber", 0) == window.window_id:
                        bounds = w.get("kCGWindowBounds", {})
                        return (
                            int(bounds.get("X", 0)),
                            int(bounds.get("Y", 0)),
                            int(bounds.get("Width", 0)),
                            int(bounds.get("Height", 0)),
                        )
                return None

            except Exception as e:
                logger.error("获取窗口 '%s' 位置失败: %s", window.title, e)
                return None
