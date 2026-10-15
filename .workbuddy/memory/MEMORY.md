# 长期记忆

## 项目：label_generator（物料标签生成器）

Python + tkinter 桌面程序，生成带二维码的物料标签（TYPE / PKG / RNG）。

### 打印通道（2026-10-15 重构）
两条通道，GUI 上用 **Print via** 下拉框切换：

- `dtpweb`：德佟（DothanTech）原生接口。Python 无法直接调 JS，采用
  「临时 HTTP 服务 + Chrome/Edge 打开 `printer/web/print.html` + 页面 POST 结果回 `/__result`」的桥接方案。
  文本与二维码以原生对象下发，不走位图。
- `bitmap`：Pillow 渲染 PNG → Chrome/Edge 按 `@page size` 打印，兜底，适配任意 Windows 打印机。

关键约束：
- **打印助手同一时刻只允许一个会话**，所有浏览器任务必须用 `printer/dtpweb_bridge.py`
  中的 `_BRIDGE_LOCK` 串行化，否则后启动的会话 `openPrinter` 会失败。
- `openPrinter` 必须传打印助手返回的**完整设备对象**（含 ip/port/type），
  只传 `{name}` 会失败。页面里先 `getPrinters({onlyLocal:false})` 再按名称匹配。
- 打印机下拉框在异步检测期间显示占位文案，取名字时要过滤掉（见 `gui/gui.py::_get_printer_name`）。

### 布局
`generator/label.py::build_layout()` 统一以**毫米**计算布局，位图通道与 dtpweb 通道共用，
保证预览与打印一致。位图按 8 px/mm（≈203 dpi）渲染。
**字体换算关键**：dtpweb `drawText.fontHeight` 单位是毫米；PIL `truetype(size)` 单位是
**像素（em）**，绝不能按 mm×72/25.4 当磅值传。用探针字「国」实测比例换算：
`_font_size_px(mm) = mm × 8 / ratio`（本机 ratio ≈ 0.91）。行距 = 字高 × 0.28，
内容垂直居中；GUI 有 Text Size (%) 整体缩放（set_text_scale）。
垂直还有空余时，PKG/RNG 两行小字再放大 1~4px 并统一字号。
标签尺寸持久化在 `history.ini` 的 `[size] last`（config.get_last_size / save_last_size）。

### 标签模式（2026-10-15）
GUI 用 ttk.Notebook 两个分页切换，`set_mode()` + `_apply_label_data()`（gui）统一起效：
- `MODE_MATERIAL`：TYPE / PKG / RNG 四行，QR 内容 `TYPE:x|PKG:y|RNG:z`。
- `MODE_CABLE`：大字命名 + 下方备注（备注**自动折行** `_wrap_text`/`_fit_wrapped_lines`，
  先缩到放得下再逐 px 放大），QR 内容 `NAME:x|NOTE:y`。
  层次约束：备注块 ≤ 可用高 55%，备注字高 ≤ 命名字高 80%。
  cable 历史存 history.ini 的 `cablenames` / `cablenotes`。

### 已知坑
- `config.py` 用 `configparser` 存历史记录，必须 `ConfigParser(interpolation=None)`，
  否则历史值含 `%`（如 "10K 1%"）会在写入时抛 `ValueError: invalid interpolation syntax`。
- `generator/_init_.py`、`gui/_init_.py` 文件名是单下划线（非 `__init__.py`），
  靠 Python 3 命名空间包导入；`printer/__init__.py` 用的是标准双下划线命名。

## 用户偏好
- 交流用中文。
- 倾向于先把需求确认清楚再动手（本次通过选项确认了「改造项目用 dtpweb 打印」+「纯浏览器/本地 HTML」）。
