"""生成 Briefcase 打包所需的应用图标文件."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw


def generate_app_icon(output_dir: Path) -> None:
    """生成多尺寸应用图标.

    Briefcase 需要不同尺寸的 PNG 图标用于不同平台：
    - macOS: 16, 32, 64, 128, 256, 512, 1024
    - Windows: 16, 32, 48, 64, 256
    """
    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    output_dir.mkdir(parents=True, exist_ok=True)

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = max(1, size // 16)
        body_top = int(size * 0.25)
        body_bottom = size - margin
        radius = max(1, size // 16)

        body_color = (220, 53, 69)
        flap_color = (185, 43, 56)
        coin_color = (255, 215, 0)

        # 信封主体
        draw.rounded_rectangle(
            [margin, body_top, size - margin, body_bottom],
            radius=radius,
            fill=body_color,
        )
        # 信封盖子
        flap_peak = int(size * 0.55)
        draw.polygon(
            [(margin, body_top), (size // 2, flap_peak), (size - margin, body_top)],
            fill=flap_color,
        )
        # 金币
        coin_r = max(1, int(size * 0.12))
        cx, cy = size // 2, int(size * 0.55)
        draw.ellipse(
            [cx - coin_r, cy - coin_r, cx + coin_r, cy + coin_r],
            fill=coin_color,
        )

        # Briefcase 期望的命名格式: icon-{size}.png
        img.save(output_dir / f"icon-{size}.png")
        print(f"  生成 icon-{size}.png")

    # 同时保存一个通用的 icon.png（使用 256px）
    img_256 = Image.open(output_dir / "icon-256.png")
    img_256.save(output_dir / "icon.png")
    print("  生成 icon.png")

    # 生成 .ico 文件（Windows 需要）
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)]
    ico_images = []
    for w, h in ico_sizes:
        ico_img = Image.open(output_dir / f"icon-{w}.png")
        ico_images.append(ico_img)
    ico_images[0].save(
        output_dir / "icon.ico",
        format="ICO",
        sizes=ico_sizes,
        append_images=ico_images[1:],
    )
    print("  生成 icon.ico")

    # 生成 .icns 所需的源图（macOS - Briefcase 会自动处理）
    print(f"\n图标已生成到: {output_dir}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    output = project_root / "src" / "gui" / "resources"
    print("正在生成应用图标...")
    generate_app_icon(output)
    print("完成！")
