"""主控制器单元测试."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.main import RedEnvelopeBot, load_config, setup_logging


class TestLoadConfig:
    """测试配置加载."""

    def test_load_valid_config(self, tmp_path):
        """加载有效配置文件."""
        config_data = {
            "window": {"title_keywords": ["QQ"], "scan_interval_min": 1.0},
            "detection": {"match_threshold": 0.8},
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        config = load_config(str(config_file))
        assert config["window"]["title_keywords"] == ["QQ"]
        assert config["detection"]["match_threshold"] == 0.8

    def test_load_missing_config(self):
        """配置文件不存在返回空字典."""
        config = load_config("/nonexistent/config.yaml")
        assert config == {}

    def test_load_empty_config(self, tmp_path):
        """空配置文件返回空字典."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("", encoding="utf-8")
        config = load_config(str(config_file))
        assert config == {}


class TestSetupLogging:
    """测试日志配置."""

    def test_setup_console_logging(self):
        """仅控制台日志."""
        config = {"logging": {"level": "INFO"}}
        setup_logging(config)

    def test_setup_file_logging(self, tmp_path):
        """文件日志."""
        log_file = str(tmp_path / "test.log")
        config = {
            "logging": {
                "level": "DEBUG",
                "file": log_file,
                "max_size_mb": 1,
                "backup_count": 2,
            }
        }
        with patch("src.main._get_project_root", return_value=tmp_path):
            setup_logging(config)

    def test_setup_default_logging(self):
        """无日志配置使用默认."""
        setup_logging({})


class TestPlatformDetection:
    """测试平台自动检测."""

    def test_get_platform_returns_instance(self):
        """get_platform 返回平台实例."""
        from src.platform import get_platform

        platform = get_platform()
        assert platform is not None

    @patch("platform.system", return_value="Linux")
    def test_unsupported_platform(self, mock_system):
        """不支持的平台抛出异常."""
        from src.platform import get_platform

        with pytest.raises(OSError, match="不支持的操作系统"):
            get_platform()


class TestRedEnvelopeBotPause:
    """测试暂停/继续功能."""

    def test_initial_state_not_paused(self):
        """初始状态未暂停."""
        with patch("src.main.ImageDetector"), \
             patch("src.main.WindowManager"), \
             patch("src.main.Humanizer"):
            bot = RedEnvelopeBot(config={
                "detection": {"template_path": "/dev/null"},
            })
            assert bot.paused is False

    def test_toggle_pause(self):
        """切换暂停状态."""
        with patch("src.main.ImageDetector"), \
             patch("src.main.WindowManager"), \
             patch("src.main.Humanizer"):
            bot = RedEnvelopeBot(config={
                "detection": {"template_path": "/dev/null"},
            })
            assert bot.paused is False
            bot._toggle_pause()
            assert bot.paused is True
            bot._toggle_pause()
            assert bot.paused is False

    def test_hotkey_config_default(self):
        """默认快捷键配置."""
        with patch("src.main.ImageDetector"), \
             patch("src.main.WindowManager"), \
             patch("src.main.Humanizer"):
            bot = RedEnvelopeBot(config={
                "detection": {"template_path": "/dev/null"},
            })
            assert bot._pause_hotkey == "<ctrl>+<shift>+p"

    def test_hotkey_config_custom(self):
        """自定义快捷键配置."""
        with patch("src.main.ImageDetector"), \
             patch("src.main.WindowManager"), \
             patch("src.main.Humanizer"):
            bot = RedEnvelopeBot(config={
                "detection": {"template_path": "/dev/null"},
                "hotkey": {"pause_resume": "<cmd>+<shift>+p"},
            })
            assert bot._pause_hotkey == "<cmd>+<shift>+p"
