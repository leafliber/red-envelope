"""GUI 控制器和图标生成的单元测试."""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.gui.controller import BotState, GUIController
from src.gui.icons import ICON_SIZE, create_icon


# ─── BotState 测试 ───────────────────────────────────────────


class TestBotState:
    """测试 BotState 枚举."""

    def test_state_values(self):
        assert BotState.STOPPED.value == "已停止"
        assert BotState.RUNNING.value == "运行中"
        assert BotState.PAUSED.value == "已暂停"

    def test_all_states_exist(self):
        assert len(BotState) == 3


# ─── GUIController 测试 ──────────────────────────────────────


class TestGUIControllerInit:
    """测试控制器初始化."""

    def test_initial_state_is_stopped(self):
        ctrl = GUIController()
        assert ctrl.state == BotState.STOPPED

    def test_callback_is_stored(self):
        cb = MagicMock()
        ctrl = GUIController(on_state_change=cb)
        assert ctrl._on_state_change is cb


class TestGUIControllerStateChange:
    """测试状态变更和回调."""

    def test_set_state_triggers_callback(self):
        cb = MagicMock()
        ctrl = GUIController(on_state_change=cb)
        ctrl._set_state(BotState.RUNNING)
        cb.assert_called_once_with(BotState.RUNNING)
        assert ctrl.state == BotState.RUNNING

    def test_set_state_no_callback(self):
        ctrl = GUIController()
        ctrl._set_state(BotState.RUNNING)
        assert ctrl.state == BotState.RUNNING

    def test_callback_error_does_not_crash(self):
        cb = MagicMock(side_effect=RuntimeError("boom"))
        ctrl = GUIController(on_state_change=cb)
        # Should not raise
        ctrl._set_state(BotState.RUNNING)
        assert ctrl.state == BotState.RUNNING


class TestGUIControllerStart:
    """测试启动机器人."""

    @patch("src.gui.controller.GUIController._run_bot")
    def test_start_launches_thread(self, mock_run):
        ctrl = GUIController()
        with patch("src.gui.controller.logger"):
            # Mock the imports inside start()
            with patch("src.main.load_config", return_value={}):
                with patch("src.main.setup_logging"):
                    with patch("src.main.RedEnvelopeBot"):
                        ctrl.start()
                        assert ctrl.state == BotState.RUNNING
                        assert ctrl._thread is not None

    def test_start_ignores_if_already_running(self):
        ctrl = GUIController()
        ctrl._state = BotState.RUNNING
        ctrl.start()
        # No thread should be created
        assert ctrl._thread is None


class TestGUIControllerStop:
    """测试停止机器人."""

    def test_stop_from_running(self):
        cb = MagicMock()
        ctrl = GUIController(on_state_change=cb)
        ctrl._state = BotState.RUNNING
        ctrl._bot = MagicMock()
        ctrl.stop()
        ctrl._bot.stop.assert_called_once()
        assert ctrl.state == BotState.STOPPED

    def test_stop_from_paused(self):
        ctrl = GUIController()
        ctrl._state = BotState.PAUSED
        ctrl._bot = MagicMock()
        ctrl.stop()
        ctrl._bot.stop.assert_called_once()
        assert ctrl.state == BotState.STOPPED

    def test_stop_when_already_stopped(self):
        ctrl = GUIController()
        ctrl.stop()
        assert ctrl.state == BotState.STOPPED


class TestGUIControllerPauseResume:
    """测试暂停和继续."""

    def test_pause_from_running(self):
        ctrl = GUIController()
        ctrl._state = BotState.RUNNING
        ctrl._bot = MagicMock()
        ctrl.pause()
        ctrl._bot.set_paused.assert_called_once_with(True)

    def test_pause_ignored_if_not_running(self):
        ctrl = GUIController()
        ctrl._state = BotState.STOPPED
        ctrl.pause()
        assert ctrl.state == BotState.STOPPED

    def test_resume_from_paused(self):
        ctrl = GUIController()
        ctrl._state = BotState.PAUSED
        ctrl._bot = MagicMock()
        ctrl.resume()
        ctrl._bot.set_paused.assert_called_once_with(False)

    def test_resume_ignored_if_not_paused(self):
        ctrl = GUIController()
        ctrl._state = BotState.RUNNING
        ctrl._bot = MagicMock()
        ctrl.resume()
        # State should not change
        assert ctrl.state == BotState.RUNNING


class TestGUIControllerHotkeySync:
    """测试快捷键触发的暂停状态同步."""

    def test_hotkey_pause_updates_state(self):
        ctrl = GUIController()
        ctrl._state = BotState.RUNNING

        ctrl._handle_bot_pause_change(True)
        assert ctrl.state == BotState.PAUSED

    def test_hotkey_resume_updates_state(self):
        ctrl = GUIController()
        ctrl._state = BotState.PAUSED

        ctrl._handle_bot_pause_change(False)
        assert ctrl.state == BotState.RUNNING

    def test_hotkey_change_ignored_when_stopped(self):
        ctrl = GUIController()
        ctrl._state = BotState.STOPPED

        ctrl._handle_bot_pause_change(True)
        assert ctrl.state == BotState.STOPPED


# ─── 图标生成测试 ─────────────────────────────────────────────


class TestIconGeneration:
    """测试托盘图标生成."""

    def test_create_icon_returns_image(self):
        img = create_icon(BotState.STOPPED)
        assert isinstance(img, Image.Image)

    def test_icon_size(self):
        img = create_icon(BotState.RUNNING)
        assert img.size == (ICON_SIZE, ICON_SIZE)

    def test_icon_mode_is_rgba(self):
        img = create_icon(BotState.PAUSED)
        assert img.mode == "RGBA"

    @pytest.mark.parametrize("state", list(BotState))
    def test_all_states_produce_valid_icon(self, state):
        img = create_icon(state)
        assert isinstance(img, Image.Image)
        assert img.size == (ICON_SIZE, ICON_SIZE)

    def test_different_states_produce_different_icons(self):
        """不同状态的图标应该有不同的像素内容."""
        running = create_icon(BotState.RUNNING)
        stopped = create_icon(BotState.STOPPED)
        paused = create_icon(BotState.PAUSED)

        # 比较像素数据
        assert running.tobytes() != stopped.tobytes()
        assert running.tobytes() != paused.tobytes()
        assert stopped.tobytes() != paused.tobytes()
