"""托盘图标生成 - 使用 Pillow 绘制不同状态的红包图标."""

import logging
from typing import Tuple

from PIL import Image, ImageDraw

from .controller import BotState

logger = logging.getLogger(__name__)

# 图标尺寸（像素）
ICON_SIZE = 64


def _draw_envelope(
    draw: ImageDraw.ImageDraw,
    size: int,
    body_color: Tuple[int, int, int],
    flap_color: Tuple[int, int, int],
    coin_color: Tuple[int, int, int],
    border_color: Tuple[int, int, int, int] = (0, 0, 0, 0),
) -> None:
    """绘制红包信封图形.

    Args:
        draw: Pillow ImageDraw 对象。
        size: 图标尺寸。
        body_color: 信封主体颜色。
        flap_color: 信封盖子颜色。
        coin_color: 中心金币颜色。
        border_color: 描边颜色。
    """
    margin = 4
    body_top = int(size * 0.28)
    body_bottom = size - margin

    # 信封主体（圆角矩形）
    draw.rounded_rectangle(
        [margin, body_top, size - margin, body_bottom],
        radius=4,
        fill=body_color,
        outline=border_color,
    )

    # 信封盖子（三角形）
    flap_peak = int(size * 0.55)
    draw.polygon(
        [
            (margin, body_top),
            (size // 2, flap_peak),
            (size - margin, body_top),
        ],
        fill=flap_color,
    )

    # 中心金币
    coin_r = int(size * 0.12)
    cx, cy = size // 2, int(size * 0.55)
    draw.ellipse(
        [cx - coin_r, cy - coin_r, cx + coin_r, cy + coin_r],
        fill=coin_color,
    )


# 各状态颜色方案
_STATE_COLORS = {
    BotState.RUNNING: {
        "body_color": (220, 53, 69),       # 鲜红
        "flap_color": (185, 43, 56),       # 深红
        "coin_color": (255, 215, 0),       # 金色
    },
    BotState.PAUSED: {
        "body_color": (230, 162, 60),      # 橙黄
        "flap_color": (200, 140, 50),      # 深橙
        "coin_color": (255, 235, 150),     # 浅金
    },
    BotState.STOPPED: {
        "body_color": (130, 130, 130),     # 灰色
        "flap_color": (100, 100, 100),     # 深灰
        "coin_color": (180, 180, 180),     # 浅灰
    },
}


def create_icon(state: BotState) -> Image.Image:
    """根据机器人状态生成托盘图标.

    Args:
        state: 当前机器人状态。

    Returns:
        64x64 RGBA 图标。
    """
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    colors = _STATE_COLORS.get(state, _STATE_COLORS[BotState.STOPPED])
    _draw_envelope(draw, ICON_SIZE, **colors)

    return img
