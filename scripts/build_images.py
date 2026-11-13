#!/usr/bin/env python3
"""为展示仓库准备图片：复制 + 缩放 + 去 EXIF + 合成 UI 拼图。

用法：python build_images.py
源目录：C:\\Users\\cjz\\Desktop\\求职\\项目截图
输出：  ../images/
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

SRC = r"C:\Users\cjz\Desktop\求职\项目截图"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))
os.makedirs(OUT, exist_ok=True)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]

# 源文件名 -> 输出名, 目标最大宽度
MAP = {
    # —— 真机实拍（屏幕照片，转 JPEG 省体积）——
    "real-home.png": ("real-home.jpg", 1600),
    "real-control-center.png": ("real-control-center.jpg", 1400),
    # —— Renode 仿真渲染帧（原生 800x480，保持 PNG）——
    "Home页（Renode截图）.png": ("ui-home.png", 800),
    "控制中心页（Renode截图）.png": ("ui-control-center.png", 800),
    "wifi页（Renode截图）.png": ("ui-wifi.png", 800),
    # —— 硬件实拍 ——
    "实拍图.jpg": ("hardware-whole.jpg", 1600),
    "主控-QSPI_FLASH-SDRAM实拍.png": ("hardware-mcu.jpg", 1400),
    "SD接口实拍.png": ("hardware-sd.jpg", 1000),
    "stm32从设备（包含C6及传感器，存储器）EP32C6.jpg": ("hardware-slave.jpg", 1600),
    # —— 工具 / 日志 ——
    "主项目Bootloader与APP部分启动日志.png": ("logs-boot.png", 1400),
    "SerialHub项目截图（含H750部分日志）.png": ("tool-serialhub.png", 1600),
    "以opencode为例的agent通过serialhub查看串口内容.png": ("tool-agent-serialhub.png", 1600),
}


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def clean_save(img, dst, max_w=None, quality=86):
    if max_w and img.width > max_w:
        h = round(img.height * max_w / img.width)
        img = img.resize((max_w, h), Image.LANCZOS)
    if img.mode in ("P", "RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        conv = img.convert("RGBA")
        bg.paste(conv, mask=conv.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if dst.lower().endswith(".png"):
        img.save(dst, "PNG", optimize=True)
    else:
        img.save(dst, "JPEG", quality=quality, optimize=True, progressive=True,
                 comment=b"")  # comment 置空，PIL 顺带丢掉原 EXIF
    return img.size


def build_hero():
    """把三张 800x480 的 UI 截图拼成一张 hero 图。"""
    names = [("ui-home.png", "Home"), ("ui-control-center.png", "控制中心"), ("ui-wifi.png", "Wi-Fi 管理")]
    imgs = []
    for fn, label in names:
        p = os.path.join(OUT, fn)
        if os.path.exists(p):
            imgs.append((Image.open(p).convert("RGB"), label))
    if len(imgs) < 2:
        print("  hero: 跳过（可用 UI 截图不足）")
        return
    pad, lab_h, gap = 16, 34, 12
    w = sum(i.width for i, _ in imgs) + gap * (len(imgs) - 1) + pad * 2
    h = max(i.height for i, _ in imgs) + lab_h + pad * 2
    canvas = Image.new("RGB", (w, h), (17, 20, 26))
    draw = ImageDraw.Draw(canvas)
    font = load_font(20)
    x = pad
    for im, label in imgs:
        canvas.paste(im, (x, pad))
        draw.text((x + 2, pad + im.height + 8), label, fill=(200, 210, 225), font=font)
        x += im.width + gap
    dst = os.path.join(OUT, "hero-ui.png")
    clean_save(canvas, dst, max_w=1600)
    print(f"  hero-ui.png  {canvas.size[0]}x{canvas.size[1]} -> {dst}")


def main():
    if not os.path.isdir(SRC):
        sys.exit(f"源目录不存在: {SRC}")
    print(f"源: {SRC}\n出: {OUT}\n")
    missing = []
    for src_name, (dst_name, max_w) in MAP.items():
        sp = os.path.join(SRC, src_name)
        if not os.path.exists(sp):
            missing.append(src_name)
            continue
        img = Image.open(sp)
        # 强制丢掉 EXIF/GPS：只保留像素
        img = Image.frombytes(img.mode, img.size, img.tobytes())
        dst = os.path.join(OUT, dst_name)
        size = clean_save(img, dst, max_w)
        kb = os.path.getsize(dst) / 1024
        print(f"  {src_name[:34]:<36} -> {dst_name:<24} {size[0]}x{size[1]}  {kb:6.0f} KB")
    if missing:
        print("\n缺失源文件：")
        for m in missing:
            print("  -", m)
    build_hero()
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1024 / 1024
    print(f"\nimages/ 合计 {total:.1f} MB")


if __name__ == "__main__":
    main()
