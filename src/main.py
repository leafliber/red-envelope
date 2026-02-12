"""主控制器 - 协调窗口扫描、图像识别和自动点击的主循环."""

import logging
import logging.handlers
import os
import random
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pynput import keyboard

from .humanizer import Humanizer
from .image_detector import ImageDetector, MatchResult
from .window_manager import WindowManager

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录."""
    return Path(__file__).resolve().parent.parent


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载 YAML 配置文件.

    Args:
        config_path: 配置文件路径，为 None 时使用默认路径。

    Returns:
        配置字典。
    """
    if config_path is None:
        config_path = str(_get_project_root() / "config" / "config.yaml")

    if not os.path.isfile(config_path):
        logger.warning("配置文件不存在: %s，使用默认配置", config_path)
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info("已加载配置文件: %s", config_path)
    return config or {}


def setup_logging(config: Dict[str, Any]) -> None:
    """配置日志系统.

    同时输出到控制台和文件（如配置了文件路径）。

    Args:
        config: 日志配置字典。
    """
    log_cfg = config.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    fmt = log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler（避免重复添加）
    root_logger.handlers.clear()

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(fmt))
    root_logger.addHandler(console_handler)

    # 文件输出
    log_file = log_cfg.get("file")
    if log_file:
        log_path = _get_project_root() / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        max_bytes = log_cfg.get("max_size_mb", 10) * 1024 * 1024
        backup_count = log_cfg.get("backup_count", 5)

        file_handler = logging.handlers.RotatingFileHandler(
            str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(fmt))
        root_logger.addHandler(file_handler)

        logger.info("日志文件: %s", log_path)


class RedEnvelopeBot:
    """QQ红包自动点击机器人.

    主控制器，协调窗口扫描 → 图像识别 → 自动点击的完整流程。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """初始化红包机器人.

        Args:
            config: 配置字典，为 None 时从默认路径加载。
        """
        if config is None:
            config = load_config()
        self.config = config
        self._running = False
        self._paused = False
        self._hotkey_listener = None

        # 初始化各模块
        self._init_modules()

    def _init_modules(self) -> None:
        """根据配置初始化各功能模块."""
        win_cfg = self.config.get("window", {})
        det_cfg = self.config.get("detection", {})
        hum_cfg = self.config.get("humanizer", {})

        # 窗口管理器
        self.window_manager = WindowManager(
            title_keywords=win_cfg.get("title_keywords", ["QQ"]),
            cache_ttl=win_cfg.get("cache_ttl", 5.0),
        )

        # 扫描间隔
        self.scan_interval_min = win_cfg.get("scan_interval_min", 1.0)
        self.scan_interval_max = win_cfg.get("scan_interval_max", 3.0)

        # 图像识别器
        template_path = det_cfg.get("template_path", "img/redbag.png")
        if not os.path.isabs(template_path):
            template_path = str(_get_project_root() / template_path)

        self.detector = ImageDetector(
            template_path=template_path,
            threshold=det_cfg.get("match_threshold", 0.8),
            method=det_cfg.get("match_method", "TM_CCOEFF_NORMED"),
            grayscale=det_cfg.get("grayscale", True),
        )

        # 人类化操作器
        self.humanizer = Humanizer(
            move_duration_min=hum_cfg.get("move_duration_min", 0.2),
            move_duration_max=hum_cfg.get("move_duration_max", 0.5),
            click_offset_x=hum_cfg.get("click_offset_x", 5),
            click_offset_y=hum_cfg.get("click_offset_y", 5),
            click_wait_min=hum_cfg.get("click_wait_min", 0.3),
            click_wait_max=hum_cfg.get("click_wait_max", 0.8),
            action_wait_min=hum_cfg.get("action_wait_min", 0.5),
            action_wait_max=hum_cfg.get("action_wait_max", 1.5),
            tween_function=hum_cfg.get("tween_function", "easeInOutQuad"),
        )

        # 快捷键配置
        hotkey_cfg = self.config.get("hotkey", {})
        self._pause_hotkey = hotkey_cfg.get(
            "pause_resume", "<ctrl>+<shift>+p"
        )

        logger.info("所有模块初始化完成")

    def _handle_red_envelope(
        self, window, match: MatchResult, screenshot
    ) -> bool:
        """处理检测到的红包.

        流程: 激活窗口 → 计算屏幕坐标 → 人类化点击 → 按ESC关闭。

        Args:
            window: 红包所在的窗口。
            match: 模板匹配结果。
            screenshot: 窗口截图（用于计算 Retina 缩放比例）。

        Returns:
            是否成功处理。
        """
        logger.info(
            "开始处理红包 - 窗口: '%s', 位置: (%d, %d), 置信度: %.4f",
            window.title,
            match.center_x,
            match.center_y,
            match.confidence,
        )

        # 1. 激活窗口
        if not self.window_manager.activate_window(window):
            logger.error("激活窗口失败，放弃本次操作")
            return False

        # 等待窗口完全激活
        time.sleep(0.3)

        # 2. 获取窗口在屏幕上的实际位置
        rect = self.window_manager.get_window_screen_pos(window)
        if rect is None:
            logger.error("获取窗口位置失败，放弃本次操作")
            return False

        win_x, win_y, win_w, win_h = rect

        # 3. 计算红包在屏幕上的绝对坐标
        # Retina 屏幕修正：截图为原始像素分辨率，窗口坐标为逻辑点。
        # 将匹配坐标从像素空间转换到逻辑空间。
        img_h, img_w = screenshot.shape[:2]
        scale_x = img_w / win_w if win_w > 0 else 1.0
        scale_y = img_h / win_h if win_h > 0 else 1.0

        logical_cx = match.center_x / scale_x
        logical_cy = match.center_y / scale_y

        screen_x = int(win_x + logical_cx)
        screen_y = int(win_y + logical_cy)

        logger.info(
            "红包屏幕坐标: (%d, %d) "
            "(匹配像素=(%d,%d), 缩放=%.2fx%.2f, 逻辑偏移=(%.0f,%.0f))",
            screen_x, screen_y,
            match.center_x, match.center_y,
            scale_x, scale_y,
            logical_cx, logical_cy,
        )

        # 4. 人类化点击红包
        if not self.humanizer.click(screen_x, screen_y, with_offset=True):
            logger.error("点击红包失败")
            return False

        # 5. 随机等待
        self.humanizer.random_wait()

        # 6. 按 ESC 关闭窗口
        if not self.humanizer.press_key("escape"):
            logger.warning("按ESC失败，尝试继续")

        logger.info("红包处理完成 ✓")
        return True

    def _scan_once(self) -> bool:
        """执行一轮完整的扫描和检测.

        Returns:
            本轮是否检测到并处理了红包。
        """
        # 1. 扫描窗口
        windows = self.window_manager.scan_windows()
        if not windows:
            logger.debug("未发现QQ窗口")
            return False

        # 2. 逐个窗口截图并检测
        for window in windows:
            screenshot = self.window_manager.capture_window(window)
            if screenshot is None:
                continue

            match = self.detector.detect(screenshot)
            if match.found:
                return self._handle_red_envelope(window, match, screenshot)

        return False

    def _toggle_pause(self) -> None:
        """切换暂停/继续状态."""
        self._paused = not self._paused
        state = "已暂停" if self._paused else "已继续"
        logger.info("监控状态切换: %s (快捷键: %s)", state, self._pause_hotkey)

    def _start_hotkey_listener(self) -> None:
        """启动全局快捷键监听."""
        try:
            hotkey = keyboard.HotKey(
                keyboard.HotKey.parse(self._pause_hotkey),
                self._toggle_pause,
            )

            def _on_press(key):
                try:
                    hotkey.press(key)
                except Exception:
                    pass

            def _on_release(key):
                try:
                    hotkey.release(key)
                except Exception:
                    pass

            self._hotkey_listener = keyboard.Listener(
                on_press=_on_press,
                on_release=_on_release,
            )
            self._hotkey_listener.daemon = True
            self._hotkey_listener.start()
            logger.info(
                "全局快捷键已注册: %s (暂停/继续)", self._pause_hotkey
            )
        except Exception as e:
            logger.warning("注册全局快捷键失败: %s (程序将继续运行)", e)

    def _stop_hotkey_listener(self) -> None:
        """停止全局快捷键监听."""
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None
            logger.debug("全局快捷键监听已停止")

    def run(self) -> None:
        """启动主循环.

        持续扫描QQ窗口并检测红包，直到收到中断信号。
        """
        self._running = True
        self._paused = False

        # 注册信号处理（仅主线程可注册信号）
        def _signal_handler(signum, frame):
            logger.info("收到中断信号 (%s)，正在停止...", signal.Signals(signum).name)
            self._running = False

        try:
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        except ValueError:
            # 在非主线程中运行时（如 GUI 模式），跳过信号注册
            logger.debug("信号处理跳过（非主线程）")

        # 启动全局快捷键监听
        self._start_hotkey_listener()

        logger.info("=" * 60)
        logger.info("QQ红包自动点击系统已启动")
        logger.info("按 %s 暂停/继续监控", self._pause_hotkey)
        logger.info("按 Ctrl+C 停止运行")
        logger.info("=" * 60)

        cycle_count = 0

        try:
            while self._running:
                # 暂停状态：等待恢复
                if self._paused:
                    time.sleep(0.5)
                    continue

                cycle_count += 1
                logger.debug("--- 扫描轮次 #%d ---", cycle_count)

                found = self._scan_once()

                if found:
                    # 找到红包后短暂等待再继续
                    wait = random.uniform(0.5, 1.0)
                else:
                    # 正常轮询间隔
                    wait = random.uniform(
                        self.scan_interval_min, self.scan_interval_max
                    )

                logger.debug("下次扫描等待 %.2fs", wait)
                time.sleep(wait)

        except Exception as e:
            logger.critical("主循环异常退出: %s", e, exc_info=True)
        finally:
            self._running = False
            self._stop_hotkey_listener()
            logger.info("QQ红包自动点击系统已停止 (共运行 %d 轮)", cycle_count)

    def stop(self) -> None:
        """停止主循环."""
        self._running = False
        self._stop_hotkey_listener()
        logger.info("收到停止请求")

    @property
    def paused(self) -> bool:
        """当前是否处于暂停状态."""
        return self._paused


def main(config_path: Optional[str] = None, verbose: bool = False) -> None:
    """程序入口函数.

    Args:
        config_path: 配置文件路径。
        verbose: 是否开启详细日志（DEBUG级别）。
    """
    config = load_config(config_path)

    if verbose:
        config.setdefault("logging", {})["level"] = "DEBUG"

    setup_logging(config)

    try:
        bot = RedEnvelopeBot(config)
        bot.run()
    except FileNotFoundError as e:
        logger.error("文件缺失: %s", e)
        sys.exit(1)
    except ImportError as e:
        logger.error("缺少依赖: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.critical("启动失败: %s", e, exc_info=True)
        sys.exit(1)
