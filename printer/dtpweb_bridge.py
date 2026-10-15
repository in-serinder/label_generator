"""dtpweb 原生打印通道。

德佟（DothanTech）标签打印机配套了一个本地的「dtpweb 打印助手」，
它在本机监听 HTTP 端口，浏览器中的 dtpweb.js 通过 HTTP 与之通信。
Python（tkinter）无法直接调用浏览器 JS，因此这里采用如下桥接方式：

    1. 把打印任务写成 job.json，和 print.html 一起放进临时目录；
    2. 启动一个临时 HTTP 服务托管该目录；
    3. 用 Chrome/Edge 打开 print.html，页面调用 dtpweb 接口完成打印；
    4. 页面把打印结果 POST 回 /__result，Python 端拿到结果后收尾。

相比位图打印，该通道直接向打印机下发矢量文本与二维码，清晰度更高、
速度更快，也不依赖系统打印驱动的图像缩放。
"""

import functools
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .chrome_bitmap import find_chrome

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# 打印助手同一时刻通常只允许一个会话，因此把所有浏览器任务串行化，
# 避免「查询打印机列表」与「打印」并发时互相抢占打印机。
_BRIDGE_LOCK = threading.Lock()


class DTPWebPrintError(Exception):
    """dtpweb 打印通道异常。"""


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ResultHandler(SimpleHTTPRequestHandler):
    """托管打印页面，并接收页面回传的打印结果。"""

    def __init__(self, *args, directory=None, result_box=None, **kwargs):
        self._result_box = result_box
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):  # 静默访问日志
        pass

    def do_POST(self):
        if self.path != "/__result":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"ok": False, "code": -1, "message": raw or "结果解析失败"}

        body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        if self._result_box is not None:
            self._result_box["result"] = data
            self._result_box["event"].set()


def _prepare_workdir(job):
    """创建临时目录，写入 job.json 并复制打印页面资源。"""
    tmp_dir = tempfile.mkdtemp(prefix="label_dtpweb_")
    with open(os.path.join(tmp_dir, "job.json"), "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False)
    shutil.copy(os.path.join(WEB_DIR, "print.html"), tmp_dir)
    src_lib = os.path.join(WEB_DIR, "lib")
    if os.path.isdir(src_lib):
        shutil.copytree(src_lib, os.path.join(tmp_dir, "lib"))
    return tmp_dir


def _terminate(proc):
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_browser_job(job, action="print", timeout=30, headless=True):
    """在浏览器中执行一次 dtpweb 任务，等待并返回页面上报的结果。

    :param job: 打印任务配置字典
    :param action: print（打印）或 printers（仅查询打印机列表）
    :param timeout: 等待结果的最大秒数
    :param headless: 是否以无窗口模式运行浏览器
    :return: 页面上报的结果字典
    :raises DTPWebPrintError: 浏览器缺失或等待结果超时
    """
    browser = find_chrome()
    if not browser:
        raise DTPWebPrintError("未找到 Chrome 或 Edge 浏览器，无法拉起 dtpweb 打印页面")

    if not os.path.isfile(os.path.join(WEB_DIR, "print.html")):
        raise DTPWebPrintError(f"打印页面缺失：{os.path.join(WEB_DIR, 'print.html')}")

    with _BRIDGE_LOCK:
        return _run_browser_job_locked(job, action, timeout, headless, browser)


def _run_browser_job_locked(job, action, timeout, headless, browser):
    tmp_dir = _prepare_workdir(job)
    result_box = {"result": None, "event": threading.Event()}
    port = _free_port()

    handler = functools.partial(_ResultHandler, directory=tmp_dir, result_box=result_box)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/print.html?action={action}"
    args = [browser, "--new-window", "--no-first-run", "--no-default-browser-check",
            f"--user-data-dir={os.path.join(tmp_dir, 'profile')}"]
    if headless:
        args.append("--headless=new")
    args.append(url)

    proc = None
    try:
        proc = subprocess.Popen(args)
        if not result_box["event"].wait(timeout):
            raise DTPWebPrintError(
                "等待打印结果超时。请确认已安装「dtpweb 打印助手」（Windows 上安装德佟打印机驱动即可内置），"
                "且打印机已连接。"
            )
        return result_box["result"] or {"ok": False, "code": -1, "message": "未收到打印结果"}
    finally:
        _terminate(proc)
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            httpd.server_close()
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)


def build_job(layout, printer_name=None, copies=1, rotate=False,
              gap_type=255, darkness=255, speed=255, job_name="LabelGenerator"):
    """把布局转换为 dtpweb 打印任务配置。

    :param layout: LabelGenerator.build_layout() 的结果
    :param printer_name: 目标打印机名称，为空表示使用默认打印机
    :param copies: 打印份数
    :param rotate: 是否顺时针旋转 90 度（竖式标签纸）
    """
    width_mm = layout["width"]
    height_mm = layout["height"]
    # 旋转时标签纸的宽高需要对调，内容坐标系保持不变
    paper_w, paper_h = (height_mm, width_mm) if rotate else (width_mm, height_mm)
    return {
        "printerName": printer_name or "",
        "paperWidth": round(paper_w, 2),
        "paperHeight": round(paper_h, 2),
        "orientation": 90 if rotate else 0,
        "copies": copies,
        "gapType": gap_type,
        "darkness": darkness,
        "speed": speed,
        "jobName": job_name,
        "items": layout["items"],
    }


def print_via_dtpweb(layout, printer_name=None, copies=1, rotate=False,
                     gap_type=255, darkness=255, speed=255, timeout=30,
                     headless=True):
    """通过 dtpweb 原生接口打印一张标签。"""
    job = build_job(layout, printer_name, copies, rotate, gap_type, darkness, speed)
    return run_browser_job(job, action="print", timeout=timeout, headless=headless)


def get_printers_via_dtpweb(timeout=15):
    """查询 dtpweb 打印助手识别到的打印机列表。

    :return: (成功与否, 打印机列表或错误信息)
    """
    result = run_browser_job({}, action="printers", timeout=timeout, headless=True)
    if result.get("ok"):
        return True, result.get("printers", [])
    return False, result.get("message", "查询失败")
