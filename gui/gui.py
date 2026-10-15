import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import threading
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator.label import LabelGenerator, MODE_MATERIAL, MODE_CABLE
from config import get_history_list, add_to_history, get_last_size, save_last_size
from printer import (
    DTPWebPrintError,
    find_chrome,
    get_printers_via_dtpweb,
    image_to_base64_png,
    print_bitmap_via_chrome,
    print_via_dtpweb,
)

try:
    import win32print
except ImportError:  # pywin32 缺失时不阻断位图打印
    win32print = None

# 打印通道常量
MODE_DTPWEB = "dtpweb"
MODE_BITMAP = "bitmap"

# 打印机下拉框的占位文案（异步检测期间/检测失败时显示）
PRINTER_STATUS_DETECTING = "正在检测打印机…"
PRINTER_STATUS_NONE = "未检测到打印机"
INVALID_PRINTER_NAMES = (PRINTER_STATUS_DETECTING, PRINTER_STATUS_NONE)

# 电缆线标签在 history.ini 中的历史记录字段名
HIST_CABLE_NAMES = "cablenames"
HIST_CABLE_NOTES = "cablenotes"


class LabelGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Label Generator")
        self.root.geometry("610x760")
        # self.root.maxsize(610, 700)
        self.root.resizable(True, True)

        self.label_generator = LabelGenerator()
        self.preview_image = None
        self.current_printer = None
        self.silent_print_var = tk.BooleanVar(value=False)
        self.rotate_var = tk.BooleanVar(value=False)
        self.print_mode_var = tk.StringVar(value=MODE_DTPWEB)
        self.copies_var = tk.StringVar(value="1")
        self.darkness_var = tk.StringVar(value="255")
        self.speed_var = tk.StringVar(value="255")
        self.gap_type_var = tk.StringVar(value="255")
        self.text_scale_var = tk.StringVar(value="100")
        self.printing = False
        self.size_list = [
            "30*10", "30*15", "30*25", "30*80", "30*90", "32*25",
            "35*10", "35*12", "35*15", "35*30", "35*35", "40*10",
            "40*25", "40*30", "20*10", "20*15", "20*20", "25*10",
            "25*15", "50*20", "30*40", "30*50", "30*55", "30*60",
            "30*70", "40*15", "40*20", "50*15", "50*25", "50*30",
            "50*35", "50*40", "50*54", "40*40", "40*50", "40*60",
            "40*70", "40*80", "50*50"
        ]

        self.create_widgets()
        self.load_printers()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标签类型以分页形式呈现：物料标签 / 电缆线标签
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.X, pady=(0, 10))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # ---------- 物料标签 ----------
        input_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(input_frame, text="Material Label")

        ttk.Label(input_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar()
        type_values = ["Resistor", "Capacitor", "Inductor", "Diode", "Transistor", "IC", "LED", "Fuse"]
        type_values = type_values + get_history_list("types")
        type_combo = ttk.Combobox(input_frame, textvariable=self.type_var, width=30)
        type_combo["values"] = type_values
        type_combo.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(input_frame, text="Package:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.package_var = tk.StringVar()
        package_values = ["0402", "0603", "0805", "1206", "SOT-23", "SOT-223", "QFP-32", "DIP-8", "DIP-16", "SOP-8", "SOP-16"]
        package_values = package_values + get_history_list("packages")
        package_combo = ttk.Combobox(input_frame, textvariable=self.package_var, width=30)
        package_combo["values"] = package_values
        package_combo.grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(input_frame, text="Value Range:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.value_var = tk.StringVar()
        value_values = get_history_list("values")
        value_entry = ttk.Combobox(input_frame, textvariable=self.value_var, width=32)
        value_entry["values"] = value_values
        value_entry.grid(row=2, column=1, pady=5, padx=5)

        # ---------- 电缆线标签 ----------
        cable_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(cable_frame, text="Cable Label")

        ttk.Label(cable_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cable_name_var = tk.StringVar()
        cable_name_combo = ttk.Combobox(cable_frame, textvariable=self.cable_name_var, width=32)
        cable_name_combo["values"] = get_history_list(HIST_CABLE_NAMES)
        cable_name_combo.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(cable_frame, text="Note:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.cable_note_var = tk.StringVar()
        cable_note_combo = ttk.Combobox(cable_frame, textvariable=self.cable_note_var, width=32)
        cable_note_combo["values"] = get_history_list(HIST_CABLE_NOTES)
        cable_note_combo.grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(cable_frame, text="(Name 为大字，Note 为下方小字备注，可留空)",
                  foreground="#6b7785").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        size_frame = ttk.LabelFrame(main_frame, text="Print Size", padding="10")
        size_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(size_frame, text="Label Size (mm):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.size_var = tk.StringVar(value=get_last_size())
        size_combo = ttk.Combobox(size_frame, textvariable=self.size_var, width=15, values=self.size_list)
        size_combo.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(size_frame, text="(Width*Height)").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))

        printer_frame = ttk.LabelFrame(main_frame, text="Printer", padding="10")
        printer_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(printer_frame, text="Print via:").grid(row=0, column=0, sticky=tk.W, pady=5)
        mode_combo = ttk.Combobox(
            printer_frame, textvariable=self.print_mode_var, width=40, state="readonly",
            values=[MODE_DTPWEB, MODE_BITMAP]
        )
        mode_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        mode_combo.bind("<<ComboboxSelected>>",
                        lambda e: self.load_printers(notify=True))

        ttk.Label(printer_frame, text="Select Printer:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(printer_frame, textvariable=self.printer_var, width=40)
        self.printer_combo.grid(row=1, column=1, pady=5, padx=5)
        ttk.Button(printer_frame, text="Refresh", width=8,
                   command=lambda: self.load_printers(notify=True)).grid(row=1, column=2, padx=5)

        ttk.Label(printer_frame, text="Copies:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(printer_frame, from_=1, to=99, width=5, textvariable=self.copies_var).grid(
            row=2, column=1, sticky=tk.W, padx=5)

        ttk.Label(printer_frame, text="Darkness / Speed / Gap:").grid(row=3, column=0, sticky=tk.W, pady=5)
        param_frame = ttk.Frame(printer_frame)
        param_frame.grid(row=3, column=1, sticky=tk.W, padx=5)
        ttk.Combobox(param_frame, width=10, state="readonly", textvariable=self.darkness_var,
                     values=["255", "8", "10", "12", "14"]).pack(side=tk.LEFT)
        ttk.Combobox(param_frame, width=10, state="readonly", textvariable=self.speed_var,
                     values=["255", "2", "3", "4"]).pack(side=tk.LEFT, padx=5)
        ttk.Combobox(param_frame, width=10, state="readonly", textvariable=self.gap_type_var,
                     values=["255", "0", "2"]).pack(side=tk.LEFT)

        ttk.Label(printer_frame, text="Text Size (%):").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(printer_frame, from_=50, to=200, increment=5, width=5,
                    textvariable=self.text_scale_var,
                    command=self.generate_preview).grid(row=4, column=1, sticky=tk.W, padx=5)

        self.print_date_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(printer_frame, text="Print Date", variable=self.print_date_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Checkbutton(printer_frame, text="Silent print (no dialog)", variable=self.silent_print_var).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Checkbutton(printer_frame, text="Rotate 90 (for vertical label)", variable=self.rotate_var).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.preview_label = ttk.Label(preview_frame, text="No preview available")
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Generate Preview", command=self.generate_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save Image", command=self.save_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Print", command=self.print_label).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.root.quit).pack(side=tk.RIGHT, padx=5)

    def load_printers(self, notify=False):
        """按当前打印通道刷新打印机列表。

        :param notify: 查询失败时是否弹窗提示。程序启动时静默，
                       用户手动点击刷新或切换通道时提示。
        """
        if self.print_mode_var.get() == MODE_DTPWEB:
            threading.Thread(target=self._load_dtpweb_printers, args=(notify,), daemon=True).start()
        else:
            self._load_system_printers()

    def _load_system_printers(self):
        printers = []
        if win32print is not None:
            try:
                printers = [p[2] for p in win32print.EnumPrinters(2)]
            except Exception:
                printers = []
        self._apply_printer_list(printers)

    def _ui(self, func):
        """把任务投递到 Tk 主线程执行；主线程未运行事件循环时静默跳过。"""
        try:
            self.root.after(0, func)
        except Exception:
            pass

    def _load_dtpweb_printers(self, notify=False):
        self._ui(lambda: self._set_printer_status(PRINTER_STATUS_DETECTING))
        try:
            ok, data = get_printers_via_dtpweb(timeout=15)
        except Exception as e:
            ok, data = False, str(e)
        if ok:
            names = []
            for item in data or []:
                name = item.get("name") or item.get("deviceName") or ""
                if not name:
                    continue
                # 局域网打印机显示 IP，便于区分
                names.append(name if item.get("isLocal", True) or not item.get("ip")
                             else f"{name}@{item.get('ip')}")
            self._ui(lambda: self._apply_printer_list(names))
            return
        self._ui(lambda: self._apply_printer_list([]))
        if notify:
            self._ui(lambda msg=str(data): messagebox.showwarning(
                "dtpweb",
                f"未获取到打印机列表：{msg}\n\n"
                "请确认已安装「dtpweb 打印助手」（Windows 下安装德佟打印机驱动即内置），"
                "打印机已连接，必要时可切换为 Chrome 位图打印。"))

    def _get_printer_name(self):
        """读取目标打印机名称；占位文案视为未指定（由打印页自动选择）。"""
        name = (self.printer_var.get() or "").strip()
        if not name or name in INVALID_PRINTER_NAMES:
            return ""
        return name

    def _set_printer_status(self, text):
        self.printer_combo["values"] = [text]
        self.printer_combo.set(text)
        self.current_printer = None

    def _apply_printer_list(self, printers):
        previous = self.printer_var.get()
        self.printer_combo["values"] = printers
        if printers:
            if previous in printers:
                self.printer_combo.set(previous)
            else:
                self.printer_combo.current(0)
            self.current_printer = self.printer_var.get()
        else:
            self.printer_combo.set(PRINTER_STATUS_NONE)
            self.current_printer = None

    def _apply_rotation(self, img):
        """勾选旋转时，把图像顺时针旋转 90 度（适配竖式标签纸）。"""
        if self.rotate_var.get():
                        return img.rotate(-90, expand=True)
        return img

    def _get_size_mm(self):
        """从下拉框解析 "宽*高"，返回 (width, height) 或 None。"""
        raw = self.size_var.get().strip()
        raw = raw.replace("x", "*").replace("X", "*").replace("×", "*")
        try:
            parts = [p for p in raw.split("*") if p.strip()]
            width = int(parts[0])
            height = int(parts[1])
        except (ValueError, IndexError):
            messagebox.showwarning("Warning", "Invalid size. Please select from the list (e.g. 50*25).")
            return None
        if width <= 0 or height <= 0:
            messagebox.showwarning("Warning", "Invalid size. Please select from the list (e.g. 50*25).")
            return None
        if width > 100 or height > 100:
            messagebox.showwarning("Warning", "Size cannot exceed 100mm x 100mm!")
            return None
        return width, height

    def generate_preview(self):
        if not self._apply_label_data():
            return

        size = self._get_size_mm()
        if size is None:
            return
        width, height = size

        self.label_generator.set_print_date(self.print_date_var.get())
        self.label_generator.set_size_mm(width, height)
        self.label_generator.set_text_scale(self._get_text_scale())

        img = self.label_generator.generate_label_image()
        img = self._apply_rotation(img)
        preview_w = min(560, img.width)
        preview_h = int(img.height * preview_w / img.width)
        img = img.resize((preview_w, preview_h), Image.LANCZOS)

        self.preview_image = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self.preview_image, text="")

    def save_image(self):
        if self.preview_image is None:
            messagebox.showwarning("Warning", "Please generate preview first!")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filepath:
            self.label_generator.save_image(filepath)
            messagebox.showinfo("Success", f"Image saved to {filepath}")

    def _image_to_tspl_bitmap_hex(self, img):
        bw = img.convert("L").point(lambda p: 0 if p < 128 else 255, "1")
        width, height = bw.size
        width_bytes = (width + 7) // 8
        pixels = bw.load()

        data = bytearray()
        for y in range(height):
            for xb in range(width_bytes):
                byte = 0
                for bit in range(8):
                    x = xb * 8 + bit
                    if x < width and pixels[x, y] == 0:
                        byte |= (0x80 >> bit)
                data.append(byte)

        return width_bytes, height, data.hex().upper()


    def _find_chrome(self):
        """兼容旧调用：委托给 printer 模块的浏览器查找。"""
        return find_chrome()

    def _image_to_base64_png(self, img):
        """兼容旧调用：把 PIL 图像转成 base64 PNG。"""
        return image_to_base64_png(img)

    def _get_copies(self):
        try:
            copies = int(str(self.copies_var.get()).strip())
        except (ValueError, TypeError):
            copies = 1
        return max(1, min(99, copies))

    def _get_int_param(self, var, default=255):
        try:
            return int(str(var.get()).strip())
        except (ValueError, TypeError):
            return default

    def _get_text_scale(self):
        """读取字号缩放百分比并转成系数（0.5 ~ 2.0）。"""
        try:
            percent = float(str(self.text_scale_var.get()).strip())
        except (ValueError, TypeError):
            percent = 100.0
        return max(0.5, min(2.0, percent / 100.0))

    def _is_cable_mode(self):
        """当前是否为电缆线标签分页。"""
        try:
            return self.notebook.index(self.notebook.select()) == 1
        except Exception:
            return False

    def _on_tab_changed(self, event=None):
        """切换标签类型后清空预览，避免误用上一类型的布局。"""
        self.preview_image = None
        self.preview_label.configure(image="", text="No preview available")

    def _apply_label_data(self):
        """按当前标签类型把界面字段写入生成器。

        :return: 字段填写完整返回 True，否则弹窗提示并返回 False
        """
        if self._is_cable_mode():
            name = self.cable_name_var.get().strip()
            note = self.cable_note_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please fill in the cable name!")
                return False
            add_to_history(HIST_CABLE_NAMES, name)
            if note:
                add_to_history(HIST_CABLE_NOTES, note)
            self.label_generator.set_mode(MODE_CABLE)
            self.label_generator.set_cable_data(name, note)
        else:
            label_type = self.type_var.get().strip()
            package = self.package_var.get().strip()
            value_range = self.value_var.get().strip()
            if not label_type or not package or not value_range:
                messagebox.showwarning("Warning", "Please fill in all fields!")
                return False
            add_to_history("types", label_type)
            add_to_history("packages", package)
            add_to_history("values", value_range)
            self.label_generator.set_mode(MODE_MATERIAL)
            self.label_generator.set_label_data(label_type, package, value_range)
        return True

    def print_label(self):
        if self.printing:
            return

        if self.preview_image is None:
            messagebox.showwarning("Warning", "Please generate preview first!")
            return

        size = self._get_size_mm()
        if size is None:
            return
        width, height = size
        # 记录本次打印尺寸，下次启动自动回填
        save_last_size(f"{width}*{height}")

        if not self._apply_label_data():
            return

        # 布局与位图在主线程算好，避免多线程访问 PIL/Tk 资源
        self.label_generator.set_print_date(self.print_date_var.get())
        self.label_generator.set_size_mm(width, height)
        self.label_generator.set_text_scale(self._get_text_scale())
        layout = self.label_generator.build_layout()

        printer_name = self._get_printer_name()
        copies = self._get_copies()
        rotate = self.rotate_var.get()
        silent = self.silent_print_var.get()

        if self.print_mode_var.get() == MODE_DTPWEB:
            self.printing = True
            params = (
                layout,
                printer_name,
                copies,
                rotate,
                self._get_int_param(self.gap_type_var),
                self._get_int_param(self.darkness_var),
                self._get_int_param(self.speed_var),
                silent,
            )
            threading.Thread(target=self._print_dtpweb, args=params, daemon=True).start()
        else:
            img = self.label_generator.generate_label_image()
            img = self._apply_rotation(img)
            paper_w, paper_h = (height, width) if rotate else (width, height)
            try:
                print_bitmap_via_chrome(img, paper_w, paper_h, silent=silent)
            except Exception as e:
                messagebox.showerror("Error", f"Print failed: {str(e)}")

    def _print_dtpweb(self, layout, printer_name, copies, rotate, gap_type, darkness, speed, silent):
        """后台线程：调用 dtpweb 打印接口。"""
        try:
            result = print_via_dtpweb(
                layout,
                printer_name=printer_name,
                copies=copies,
                rotate=rotate,
                gap_type=gap_type,
                darkness=darkness,
                speed=speed,
                headless=silent,
                timeout=30,
            )
        except DTPWebPrintError as e:
            self._ui(lambda msg=str(e): messagebox.showerror("dtpweb", msg))
            return
        except Exception as e:
            self._ui(lambda msg=str(e): messagebox.showerror("Error", f"Print failed: {msg}"))
            return
        finally:
            self.printing = False

        if result.get("ok"):
            self._ui(lambda: messagebox.showinfo("Success", "标签已发送到打印机。"))
        else:
            message = result.get("message", "未知错误")
            steps = [s for s in (result.get("steps") or []) if isinstance(s, str)]
            if steps:
                message = f"{message}\n\n已完成步骤：\n- " + "\n- ".join(steps)
            self._ui(lambda m=message: messagebox.showerror("dtpweb", f"打印失败：{m}"))