"""QQ红包自动点击系统 - 命令行入口."""

import argparse
import sys


def _parse_args():
    """解析命令行参数."""
    parser = argparse.ArgumentParser(
        description="QQ红包自动点击系统 - 通过图像识别自动检测并点击QQ红包",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python -m src                     使用默认配置启动
  python -m src -c config.yaml      指定配置文件
  python -m src -v                  开启详细日志模式
""",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="配置文件路径 (默认: config/config.yaml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="开启详细日志 (DEBUG 级别)",
    )
    return parser.parse_args()


def _main():
    args = _parse_args()
    from .main import main
    main(config_path=args.config, verbose=args.verbose)


if __name__ == "__main__":
    _main()
