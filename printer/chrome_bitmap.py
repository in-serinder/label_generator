"""通过 Chrome / Edge 把标签位图打印到系统打印机。

这是与打印机无关的通用兜底方案：先把标签渲染成 PNG，再交给浏览器
按指定纸张尺寸打印。适用于所有 Windows 打印机（含非德佟品牌）。
"""

import base64
import io
import os
import subprocess
import tempfile

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome(include_edge=True):
    """查找本机可用的 Chromium 内核浏览器，返回可执行文件路径。"""
    for path in CHROME_PATHS + (EDGE_PATHS if include_edge else []):
        if path and os.path.exists(path):
            return path
    return None


def image_to_base64_png(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(203, 203))
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def build_print_html(img, paper_w_mm, paper_h_mm):
    img_b64 = image_to_base64_png(img)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ size: {paper_w_mm}mm {paper_h_mm}mm; margin: 0; }}
  html, body {{ margin: 0; padding: 0; }}
  img {{ display: block; width: {paper_w_mm}mm; height: {paper_h_mm}mm; }}
</style>
</head>
<body>
  <img src="data:image/png;base64,{img_b64}" />
  <script>window.onload = function() {{ window.print(); }};</script>
</body>
</html>"""


def print_bitmap_via_chrome(img, paper_w_mm, paper_h_mm, silent=True, browser=None):
    """把 PIL 图像交给浏览器打印。

    :param img: PIL.Image 对象
    :param paper_w_mm: 纸张宽度，毫米
    :param paper_h_mm: 纸张高度，毫米
    :param silent: 为 True 时加 --kiosk-printing，跳过打印对话框
    :param browser: 指定浏览器路径，为 None 时自动查找
    :return: 启动的进程对象
    """
    chrome = browser or find_chrome()
    if not chrome:
        raise RuntimeError("未找到 Chrome 或 Edge 浏览器，无法完成打印")

    html = build_print_html(img, paper_w_mm, paper_h_mm)
    tmp_dir = tempfile.mkdtemp(prefix="label_print_")
    html_path = os.path.join(tmp_dir, "label.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    args = [chrome]
    if silent:
        args.append("--kiosk-printing")
    args.append("--new-window")
    args.append("file:///" + html_path.replace(chr(92), "/"))
    return subprocess.Popen(args)
