#!/usr/bin/env python3
"""把作品集 PPT 转成「可浏览 + 可下载」的三种形态，供展示站使用。

输入：C:\\Users\\cjz\\Desktop\\求职\\崔金周STM32H750-智能家居终端-作品集.pptx
输出：
  assets/portfolio-STM32H750.pptx    原文件（可下载）
  assets/portfolio-STM32H750.pdf     转出的 PDF（跨平台、体积小、排版不变）
  images/portfolio/slide-NN.png      逐页预览图（供 README / docs 内嵌浏览）

依赖：
  - PowerPoint（Windows COM，用于 pptx → pdf；也可手动导出 PDF 后跳过该步）
  - pymupdf（pdf → png）
用法：python build_portfolio.py
"""
import os
import shutil
import subprocess
import sys

SRC = r"C:\Users\cjz\Desktop\求职\崔金周STM32H750-智能家居终端-作品集.pptx"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SLIDES = os.path.join(ROOT, "images", "portfolio")
PPTX_OUT = os.path.join(ASSETS, "portfolio-STM32H750.pptx")
PDF_OUT = os.path.join(ASSETS, "portfolio-STM32H750.pdf")
SLIDE_W = 1440  # 预览图宽度（16:9 ⇒ 810 高）


def pptx_to_pdf(src, dst):
    """Windows 下用 PowerPoint COM 导出 PDF。"""
    ps = f'''
$ErrorActionPreference = "Stop"
$ppt = New-Object -ComObject PowerPoint.Application
try {{
  $pres = $ppt.Presentations.Open("{src}", $true, $false, $false)
  $pres.SaveAs("{dst}", 32)   # 32 = ppSaveAsPDF
  $pres.Close()
}} finally {{
  $ppt.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
}}
'''
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.exists(dst):
        sys.exit(f"PowerPoint 导出失败（可手动导出 PDF 放到 {dst}）:\n{r.stderr[-800:]}")


def pdf_to_slides(pdf, outdir):
    import pymupdf
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith(".png"):
            os.remove(os.path.join(outdir, f))
    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc, 1):
        zoom = SLIDE_W / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        pix.save(os.path.join(outdir, f"slide-{i:02d}.png"))
    n = len(doc)
    doc.close()
    return n


def main():
    if not os.path.exists(SRC):
        sys.exit(f"源 PPT 不存在: {SRC}")
    os.makedirs(ASSETS, exist_ok=True)

    shutil.copy2(SRC, PPTX_OUT)
    print(f"  pptx -> {os.path.relpath(PPTX_OUT, ROOT)}  ({os.path.getsize(PPTX_OUT)/1048576:.2f} MB)")

    if not os.path.exists(PDF_OUT):
        print("  导出 PDF（PowerPoint COM）…")
        pptx_to_pdf(SRC, PDF_OUT)
    print(f"  pdf  -> {os.path.relpath(PDF_OUT, ROOT)}  ({os.path.getsize(PDF_OUT)/1048576:.2f} MB)")

    n = pdf_to_slides(PDF_OUT, SLIDES)
    total = sum(os.path.getsize(os.path.join(SLIDES, f)) for f in os.listdir(SLIDES))
    print(f"  slides -> images/portfolio/  共 {n} 页, {total/1048576:.2f} MB")
    print("完成。")


if __name__ == "__main__":
    main()
