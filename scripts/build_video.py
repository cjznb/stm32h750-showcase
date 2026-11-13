#!/usr/bin/env python3
"""把手势演示视频转成 README 友好格式：GIF（直接内嵌）+ 压缩 MP4（可下载）。

用法：python build_video.py
源：  C:\\Users\\cjz\\Desktop\\求职\\项目截图\\demo-gesture.mp4
出：  ../images/demo-gesture.gif   (800px 宽, ~12 fps, 调色板优化)
      ../images/demo-gesture.mp4   (1280px 宽, 无音轨, faststart)

依赖：ffmpeg（本机 E:\\Anaconda3\\Library\\bin\\ffmpeg.exe 或 PATH）
"""
import os
import shutil
import subprocess
import sys

SRC = r"C:\Users\cjz\Desktop\求职\项目截图\demo-gesture.mp4"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))
os.makedirs(OUT, exist_ok=True)

CANDIDATES = [
    r"E:\Anaconda3\Library\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    "ffmpeg",
]


def find_ffmpeg():
    for c in CANDIDATES:
        if c == "ffmpeg":
            if shutil.which("ffmpeg"):
                return "ffmpeg"
        elif os.path.exists(c):
            return c
    sys.exit("找不到 ffmpeg")


def run(args):
    print("  $", " ".join(os.path.basename(a) if i == 0 else a for i, a in enumerate(args)))
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print(p.stderr[-1500:])
        raise SystemExit(f"ffmpeg 失败: {args[0]}")


def mb(path):
    return os.path.getsize(path) / 1024 / 1024


def main():
    if not os.path.exists(SRC):
        sys.exit(f"源视频不存在: {SRC}")
    ff = find_ffmpeg()
    print(f"ffmpeg: {ff}")

    gif = os.path.join(OUT, "demo-gesture.gif")
    mp4 = os.path.join(OUT, "demo-gesture.mp4")
    poster = os.path.join(OUT, "demo-gesture-poster.jpg")

    # 裁掉手机边框/背景，只留屏幕（拍屏视频的摩尔纹会让 GIF 体积暴涨，裁 + 降色最有效）
    CROP = "crop=1500:820:270:160"

    # 1) 封面帧：README 里做"可点击播放"的缩略图
    run([ff, "-y", "-v", "error", "-ss", "1.2", "-i", SRC,
         "-vf", f"{CROP},scale=1000:-1", "-frames:v", "1", "-q:v", "3", poster])
    print(f"  poster      -> {mb(poster):.2f} MB")

    # 2) GIF：直接内嵌（目标 <= 3 MB）
    for scale, fps, colors in ((620, 8, 64), (560, 8, 48), (480, 6, 48)):
        vf = (f"{CROP},fps={fps},scale={scale}:-1:flags=lanczos,"
              f"split[s0][s1];[s0]palettegen=max_colors={colors}:stats_mode=diff[p];"
              f"[s1][p]paletteuse=dither=none:diff_mode=rectangle")
        run([ff, "-y", "-v", "error", "-i", SRC, "-vf", vf, "-loop", "0", gif])
        print(f"  GIF {scale}px@{fps}fps {colors}c -> {mb(gif):.2f} MB")
        if mb(gif) <= 3.0:
            break

    # 3) MP4：给想看原速的人下载（无音轨、faststart）
    run([ff, "-y", "-v", "error", "-i", SRC,
         "-vf", f"{CROP},scale=1200:-2", "-c:v", "libx264", "-crf", "26",
         "-preset", "slow", "-pix_fmt", "yuv420p", "-an",
         "-movflags", "+faststart", mp4])
    print(f"  MP4 1200px crf26 -> {mb(mp4):.2f} MB")

    print("\nimages/ 合计 %.1f MB" % (
        sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1024 / 1024))


if __name__ == "__main__":
    main()
