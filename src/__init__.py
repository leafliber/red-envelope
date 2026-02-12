"""QQ红包自动点击系统.

基于 Python 开发的跨平台 QQ 红包自动点击工具，
通过图像识别检测红包窗口，模拟人类鼠标操作完成自动抢红包。
支持 Windows 和 macOS 双平台。
"""

__version__ = "1.0.0"
__author__ = "red-envelope-qq"

from .main import RedEnvelopeBot, load_config, main

__all__ = ["RedEnvelopeBot", "load_config", "main"]
