import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import win32print
import base64
import tempfile
import subprocess
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator.label import LabelGenerator


class LabelGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Material Label Generator")
        self.root.geometry("610x700")
        # self.root.maxsize(610, 700)
        self.root.resizable(True, True)

        self.label_generator = LabelGenerator()
        self.preview_image = None
        self.current_printer = None
        self.silent_print_var = tk.BooleanVar(value=False)

        self.create_widgets()
        self.load_printers()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.LabelFrame(main_frame, text="Label Information", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar()
        type_combo = ttk.Combobox(input_frame, textvariable=self.type_var, width=30)
        type_combo["values"] = ("Resistor", "Capacitor", "Inductor", "Diode", "Transistor", "IC", "LED", "Fuse")
        type_combo.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(input_frame, text="Package:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.package_var = tk.StringVar()
        package_combo = ttk.Combobox(input_frame, textvariable=self.package_var, width=30)
        package_combo["values"] = ("0402", "0603", "0805", "1206", "SOT-23", "SOT-223", "QFP-32", "DIP-8", "DIP-16", "SOP-8", "SOP-16")
        package_combo.grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(input_frame, text="Value Range:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.value_var = tk.StringVar()
        value_entry = ttk.Entry(input_frame, textvariable=self.value_var, width=32)
        value_entry.grid(row=2, column=1, pady=5, padx=5)

        size_frame = ttk.LabelFrame(main_frame, text="Print Size", padding="10")
        size_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(size_frame, text="Width (mm):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.width_var = tk.StringVar(value="50")
        ttk.Entry(size_frame, textvariable=self.width_var, width=15).grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(size_frame, text="Height (mm):").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        self.height_var = tk.StringVar(value="25")
        ttk.Entry(size_frame, textvariable=self.height_var, width=15).grid(row=0, column=3, pady=5, padx=5)

        printer_frame = ttk.LabelFrame(main_frame, text="Printer", padding="10")
        printer_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(printer_frame, text="Select Printer:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(printer_frame, textvariable=self.printer_var, width=40)
        self.printer_combo.grid(row=0, column=1, pady=5, padx=5)

        self.print_date_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(printer_frame, text="Print Date", variable=self.print_date_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Checkbutton(printer_frame, text="Silent print (no dialog)", variable=self.silent_print_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

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

    def load_printers(self):
        try:
            printers = [p[2] for p in win32print.EnumPrinters(2)]
            self.printer_combo["values"] = printers
            if printers:
                self.printer_combo.current(0)
                self.current_printer = printers[0]
        except Exception as e:
            self.printer_combo["values"] = ["Default Printer"]
            self.current_printer = "Default Printer"

    def generate_preview(self):
        label_type = self.type_var.get()
        package = self.package_var.get()
        value_range = self.value_var.get()

        if not label_type or not package or not value_range:
            messagebox.showwarning("Warning", "Please fill in all fields!")
            return

        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            if width <= 0 or height <= 0:
                raise ValueError()
            if width > 70 or height > 70:
                messagebox.showwarning("Warning", "Size cannot exceed 70mm x 70mm!")
                return
        except ValueError:
            messagebox.showwarning("Warning", "Please enter valid width and height!")
            return

        self.label_generator.set_label_data(label_type, package, value_range)
        self.label_generator.set_print_date(self.print_date_var.get())
        self.label_generator.set_size(width * 8, height * 8)

        img = self.label_generator.generate_label_image()
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

    CHROME_PATHS = [
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe"),
    ]

    def _find_chrome(self):
        for path in self.CHROME_PATHS:
            if os.path.exists(path):
                return path
        return None

    def _image_to_base64_png(self, img):
        buf = io.BytesIO()
        img.save(buf, format="PNG", dpi=(203, 203))
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")

    def print_label(self):
        if self.preview_image is None:
            messagebox.showwarning("Warning", "Please generate preview first!")
            return

        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
        except ValueError:
            messagebox.showwarning("Warning", "Please enter valid width and height!")
            return

        chrome = self._find_chrome()
        if chrome is None:
            messagebox.showerror("Error", "Google Chrome not found on this system.")
            return

        try:
            # 以 203dpi 生成清晰图像
            self.label_generator.set_size(width * 8, height * 8)
            img = self.label_generator.generate_label_image()
            img_b64 = self._image_to_base64_png(img)

            silent = self.silent_print_var.get()

            html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ size: {width}mm {height}mm; margin: 0; }}
  html, body {{ margin: 0; padding: 0; }}
  img {{ display: block; width: {width}mm; height: {height}mm; }}
</style>
</head>
<body>
  <img src="data:image/png;base64,{img_b64}" />
  <script>window.onload = function() {{ window.print(); }};</script>
</body>
</html>"""

            tmp_dir = tempfile.mkdtemp(prefix="label_print_")
            html_path = os.path.join(tmp_dir, "label.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            args = [chrome]
            if silent:
                args.append("--kiosk-printing")
            args.append("--new-window")
            args.append("file:///" + html_path.replace(chr(92), "/"))

            subprocess.Popen(args)
        except Exception as e:
            messagebox.showerror("Error", f"Print failed: {str(e)}")
