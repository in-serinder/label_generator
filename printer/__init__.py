"""打印通道：dtpweb 原生接口 + Chrome 位图兜底。"""

from .chrome_bitmap import (
    CHROME_PATHS,
    EDGE_PATHS,
    build_print_html,
    find_chrome,
    image_to_base64_png,
    print_bitmap_via_chrome,
)
from .dtpweb_bridge import (
    DTPWebPrintError,
    build_job,
    get_printers_via_dtpweb,
    print_via_dtpweb,
    run_browser_job,
)

__all__ = [
    "CHROME_PATHS",
    "EDGE_PATHS",
    "build_print_html",
    "find_chrome",
    "image_to_base64_png",
    "print_bitmap_via_chrome",
    "DTPWebPrintError",
    "build_job",
    "get_printers_via_dtpweb",
    "print_via_dtpweb",
    "run_browser_job",
]
