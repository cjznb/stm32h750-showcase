#!/usr/bin/env python3
"""生成展示用图表（数据全部来自仓库内可复核的记录）。

用法：python build_charts.py
输出：../images/chart-*.png
数据来源：
  - FPS 阶梯：agent/memory.md:88-95（操作员 B 基准对比表）
  - Empty screen：agent/logs/2026-08-09-显示触摸优化与缓存一致性排查.md:116-117
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))
os.makedirs(OUT, exist_ok=True)

for _f in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
    if os.path.exists(_f):
        font_manager.fontManager.addfont(_f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=_f).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

INK = "#e6e9ef"
DIM = "#8b95a5"
ACC = "#4cc2ff"
ACC2 = "#ffb454"
BG = "#11141a"


def style(ax):
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_color("#2a3140")
    ax.tick_params(colors=DIM, labelsize=11)
    ax.grid(axis="y", color="#232a36", linewidth=0.8)
    ax.set_axisbelow(True)


def chart_fps():
    """逐配置帧率演进：每一步都是一个真实提交/配置。"""
    labels = [
        "初始基线\n(2×PARTIAL + MDMA 拷贝)",
        "+ ITCM 热链\n(712f6c1)",
        "+ 三缓冲 + vblank 换页\n(2801c64)",
        "DMA2D 开 + 异步\n(连崩 2 次，弃用)",
        "DMA2D 开 + 同步\n(移植上游补丁)",
        "最终：DMA2D 关\n+ AXI 堆可缓存",
    ]
    fps = [42, 47, 47, 46, 45, 52]
    ms = [21, 15, 18, None, None, 11]
    colors = [DIM, ACC2, ACC2, "#6b7280", "#6b7280", ACC]

    fig, ax = plt.subplots(figsize=(11.5, 5.2), dpi=160)
    fig.patch.set_facecolor(BG)
    style(ax)
    bars = ax.bar(range(len(fps)), fps, color=colors, width=0.62, zorder=3)
    for i, (b, v) in enumerate(zip(bars, fps)):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.9, f"{v} fps",
                ha="center", color=INK, fontsize=13, fontweight="bold")
        if ms[i]:
            ax.text(b.get_x() + b.get_width() / 2, v / 2, f"{ms[i]} ms",
                    ha="center", color="#0d1117", fontsize=11, fontweight="bold")
    ax.set_xticks(range(len(fps)))
    ax.set_xticklabels(labels, fontsize=9.5, color=DIM)
    ax.set_ylim(0, 62)
    ax.set_ylabel("平均帧率 (fps)", color=DIM, fontsize=11)
    ax.set_title("STM32H750 · LVGL 渲染优化：平均 42 → 52 fps（帧耗时 21 → 11 ms）",
                 color=INK, fontsize=13, pad=14, loc="left")
    ax.axhline(62, color=ACC, linewidth=1, linestyle=(0, (4, 4)), alpha=.55, zorder=2)
    ax.text(len(fps) - 0.45, 62.6, "面板刷新率上限 62 Hz（空场景已跑满）",
            ha="right", color=ACC, fontsize=9.5)
    fig.tight_layout()
    dst = os.path.join(OUT, "chart-fps.png")
    fig.savefig(dst, facecolor=BG)
    plt.close(fig)
    print("  chart-fps.png")


def chart_dma2d():
    """DMA2D 判别实验：开关它，帧率不变；但显示损坏/崩溃只在开启时出现。"""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.2), dpi=160,
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    fig.patch.set_facecolor(BG)

    style(a1)
    a1.bar(["DMA2D 开", "DMA2D 关"], [47, 47], color=["#6b7280", ACC], width=0.55, zorder=3)
    for i, v in enumerate([47, 47]):
        a1.text(i, v + 0.8, f"{v} fps", ha="center", color=INK, fontsize=13, fontweight="bold")
    a1.set_ylim(0, 56)
    a1.set_title("帧率：开/关完全一致 → 零收益", color=INK, fontsize=11.5, loc="left")
    a1.set_ylabel("平均帧率 (fps)", color=DIM, fontsize=10)

    style(a2)
    a2.axis("off")
    rows = [
        ("随机显示损坏", "有（文本/图形边缘）", "无", ACC),
        ("偶发 HardFault", "有", "无", ACC),
        ("基准帧率", "47 fps", "47 fps", DIM),
    ]
    a2.text(0.02, 1.02, "判别实验结果", color=INK, fontsize=12, fontweight="bold")
    a2.text(0.02, 0.90, "现象", color=DIM, fontsize=10)
    a2.text(0.52, 0.90, "DMA2D 开", color=DIM, fontsize=10)
    a2.text(0.80, 0.90, "DMA2D 关", color=DIM, fontsize=10)
    y = 0.74
    for name, on, off, c in rows:
        a2.text(0.02, y, name, color=INK, fontsize=10.5)
        a2.text(0.52, y, on, color="#ff7b72" if on not in ("47 fps",) else DIM, fontsize=10.5)
        a2.text(0.80, y, off, color=c if off == "无" else DIM, fontsize=10.5)
        a2.plot([0.0, 0.98], [y - 0.06, y - 0.06], color="#232a36", linewidth=0.8)
        y -= 0.24
    a2.text(0.02, y - 0.02,
            "结论：DMA2D 在本平台零帧率收益，却引入缓存一致性问题\n"
            "（真因为 LVGL 9.5 上游 open bug #10021 / #10022）→ 弃用",
            color=ACC, fontsize=10.5, linespacing=1.6)
    fig.tight_layout()
    dst = os.path.join(OUT, "chart-dma2d.png")
    fig.savefig(dst, facecolor=BG)
    plt.close(fig)
    print("  chart-dma2d.png")


def chart_timeline():
    """4 个月里程碑（全部对应真实提交/交付）。"""
    events = [
        ("08-09", "工程初始化\n显示三缓冲/ITCM/触摸 DMA", ACC2),
        ("08-11", "ESP32-C6 桥接\nUSART6 + 帧协议 v1.1", DIM),
        ("08-17", "UI 框架重构\n业务/主题/i18n 分层", DIM),
        ("08-23", "TLSF 堆接管\n--wrap 全量替换 newlib", DIM),
        ("09-16", "SD 卡 IDMA 根因\n中转缓冲落 AXI 专用段", ACC),
        ("09-20", "统一 VFS + POSIX\nFatFs + littlefs 双盘", ACC),
        ("09-29", "OTA 阶段 C\n双槽 + staging 契约", ACC),
        ("10-08", "SPI1 读截断根因\nCS 窗口内一次传输", ACC),
        ("10-13", "OTA 失败真因\n坏值跨总线写入", ACC),
        ("10-14", "P1 撕裂定案\nDVFS × SDRAM 刷新", ACC),
        ("10-17", "触摸 I2C 自愈\nbit-bang + 重挂链", DIM),
        ("10-29", "v1.7 合并主线\n455 提交 / CI 绿", ACC),
    ]
    fig, ax = plt.subplots(figsize=(13, 3.6), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(-0.6, len(events) - 0.4)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")
    ax.plot([0, len(events) - 1], [0, 0], color="#2a3140", linewidth=2, zorder=1)
    for i, (d, t, c) in enumerate(events):
        up = i % 2 == 0
        y = 0.28 if up else -0.28
        ax.plot([i, i], [0, y], color="#2a3140", linewidth=1, zorder=1)
        ax.scatter([i], [0], s=70, color=c, zorder=3, edgecolors=BG, linewidths=1.5)
        ax.text(i, y + (0.10 if up else -0.10), d, ha="center",
                va="bottom" if up else "top", color=c, fontsize=9.5, fontweight="bold")
        ax.text(i, y + (0.30 if up else -0.30), t, ha="center",
                va="bottom" if up else "top", color=INK, fontsize=7.8, linespacing=1.4)
    fig.tight_layout()
    dst = os.path.join(OUT, "chart-timeline.png")
    fig.savefig(dst, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print("  chart-timeline.png")


if __name__ == "__main__":
    print("生成图表 ->", OUT)
    chart_fps()
    chart_dma2d()
    chart_timeline()
