"""系统托盘应用 - 使用 pystray 实现跨平台系统托盘."""

import logging
import sys
from typing import TYPE_CHECKING, Any, Optional

import pystray

from .controller import BotState, GUIController
from .icons import create_icon

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pystray._base import Icon as TrayIcon
    from pystray._base import Menu as TrayMenu
    from pystray._base import MenuItem as TrayMenuItem
else:
    TrayIcon = Any
    TrayMenu = Any
    TrayMenuItem = Any


class TrayApp:
    """系统托盘应用.

    提供系统托盘图标和右键菜单，控制后台 RedEnvelopeBot。
    菜单项的启用/禁用状态随机器人状态动态更新。
    """

    def __init__(self) -> None:
        self.controller = GUIController(on_state_change=self._on_state_change)
        self._icon: Optional[TrayIcon] = None

    # ── 菜单构建 ──────────────────────────────────────────────

    def _build_menu(self) -> TrayMenu:
        """构建托盘右键菜单.

        使用 lambda 实现动态启用/禁用，每次打开菜单时自动重新计算。
        """
        return pystray.Menu(
            # 状态显示（不可点击）
            pystray.MenuItem(
                lambda item: f"状态: {self.controller.state.value}",
                action=None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            # 启动 - 仅停止时可用
            pystray.MenuItem(
                "▶ 启动",
                self._on_start,
                enabled=lambda item: self.controller.state == BotState.STOPPED,
            ),
            # 暂停 - 仅运行中可用
            pystray.MenuItem(
                "⏸ 暂停",
                self._on_pause,
                enabled=lambda item: self.controller.state == BotState.RUNNING,
            ),
            # 继续 - 仅暂停时可用
            pystray.MenuItem(
                "⏵ 继续",
                self._on_resume,
                enabled=lambda item: self.controller.state == BotState.PAUSED,
            ),
            # 停止 - 非停止状态可用
            pystray.MenuItem(
                "⏹ 停止",
                self._on_stop,
                enabled=lambda item: self.controller.state != BotState.STOPPED,
            ),
            pystray.Menu.SEPARATOR,
            # 退出
            pystray.MenuItem("✕ 退出", self._on_quit),
        )

    # ── 菜单回调 ──────────────────────────────────────────────

    def _on_start(self, icon: TrayIcon, item: TrayMenuItem) -> None:
        self.controller.start()

    def _on_stop(self, icon: TrayIcon, item: TrayMenuItem) -> None:
        self.controller.stop()

    def _on_pause(self, icon: TrayIcon, item: TrayMenuItem) -> None:
        self.controller.pause()

    def _on_resume(self, icon: TrayIcon, item: TrayMenuItem) -> None:
        self.controller.resume()

    def _on_quit(self, icon: TrayIcon, item: TrayMenuItem) -> None:
        """退出前停止机器人."""
        logger.info("用户请求退出")
        self.controller.stop()
        icon.stop()

    # ── 状态变更 ──────────────────────────────────────────────

    def _on_state_change(self, new_state: BotState) -> None:
        """响应机器人状态变化，更新托盘图标."""
        if self._icon:
            try:
                self._icon.icon = create_icon(new_state)
                # pystray 在每次菜单打开时重新计算 lambda，无需手动刷新
            except Exception as e:
                logger.error("更新托盘图标失败: %s", e)

    # ── 启动 ──────────────────────────────────────────────────

    def run(self) -> None:
        """启动托盘应用（阻塞主线程）."""
        self._icon = pystray.Icon(
            name="red-envelope-qq",
            icon=create_icon(BotState.STOPPED),
            title="QQ红包助手",
            menu=self._build_menu(),
        )

        logger.info("=" * 50)
        logger.info("QQ红包助手 - 系统托盘应用已启动")
        logger.info("右键点击托盘图标查看菜单")
        logger.info("=" * 50)

        self._icon.run()


def main() -> None:
    """GUI 入口函数."""
    # 配置基础日志（机器人启动时会重新配置）
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    try:
        app = TrayApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("收到键盘中断，退出")
    except Exception as e:
        logger.critical("托盘应用启动失败: %s", e, exc_info=True)
        sys.exit(1)
