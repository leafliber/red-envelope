"""GUI 控制器 - 管理 RedEnvelopeBot 后台线程."""

import enum
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class BotState(enum.Enum):
    """机器人运行状态."""

    STOPPED = "已停止"
    RUNNING = "运行中"
    PAUSED = "已暂停"


class GUIController:
    """GUI 控制器，在后台线程中管理 RedEnvelopeBot.

    通过回调通知 GUI 层状态变更，所有操作线程安全。
    """

    def __init__(
        self, on_state_change: Optional[Callable[[BotState], None]] = None
    ) -> None:
        """初始化控制器.

        Args:
            on_state_change: 状态变更回调函数，接收新状态参数。
        """
        self._state = BotState.STOPPED
        self._bot = None
        self._thread: Optional[threading.Thread] = None
        self._on_state_change = on_state_change
        self._lock = threading.Lock()

    @property
    def state(self) -> BotState:
        """当前机器人状态."""
        return self._state

    def _set_state(self, new_state: BotState) -> None:
        """更新状态并触发回调."""
        self._state = new_state
        if self._on_state_change:
            try:
                self._on_state_change(new_state)
            except Exception as e:
                logger.error("状态回调执行失败: %s", e)

    def start(self) -> None:
        """启动机器人（后台线程）."""
        with self._lock:
            if self._state != BotState.STOPPED:
                logger.warning("机器人已在运行中，忽略启动请求")
                return

            try:
                from ..main import RedEnvelopeBot, load_config, setup_logging

                config = load_config()
                setup_logging(config)
                self._bot = RedEnvelopeBot(config)
                self._thread = threading.Thread(
                    target=self._run_bot, name="bot-worker", daemon=True
                )
                self._thread.start()
                self._set_state(BotState.RUNNING)
                logger.info("机器人已通过 GUI 启动")
            except Exception as e:
                logger.error("启动机器人失败: %s", e, exc_info=True)
                self._set_state(BotState.STOPPED)

    def _run_bot(self) -> None:
        """运行机器人主循环（在后台线程中调用）."""
        try:
            if self._bot:
                self._bot.run()
        except Exception as e:
            logger.error("机器人线程异常: %s", e, exc_info=True)
        finally:
            # 线程结束时重置状态
            self._set_state(BotState.STOPPED)
            self._bot = None

    def stop(self) -> None:
        """停止机器人."""
        with self._lock:
            if self._bot and self._state != BotState.STOPPED:
                self._bot.stop()
                self._set_state(BotState.STOPPED)
                logger.info("机器人已通过 GUI 停止")

    def pause(self) -> None:
        """暂停机器人."""
        with self._lock:
            if self._bot and self._state == BotState.RUNNING:
                self._bot._paused = True
                self._set_state(BotState.PAUSED)
                logger.info("机器人已通过 GUI 暂停")

    def resume(self) -> None:
        """继续运行机器人."""
        with self._lock:
            if self._bot and self._state == BotState.PAUSED:
                self._bot._paused = False
                self._set_state(BotState.RUNNING)
                logger.info("机器人已通过 GUI 继续运行")
