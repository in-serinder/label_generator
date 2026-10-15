from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
from datetime import datetime

# 标签位图渲染分辨率：8 px/mm ≈ 203 dpi，与主流标签打印机一致。
PX_PER_MM = 8

# 行距系数：行与行之间的空白 = 字高 × LINE_GAP_RATIO。
# 用固定比例而不是「把剩余空间均分」，避免标签越高、行距越松散。
LINE_GAP_RATIO = 0.28
# 文本超出可用宽度时自动缩小的下限（毫米）
MIN_FONT_HEIGHT_MM = 0.7
# 自动缩小字号的最大迭代次数
MAX_SHRINK_STEPS = 60
# 可用宽度的安全系数。打印机内置字体的宽度与 PC 预览字体不完全一致，
# 留一点余量避免文字压到二维码上。
TEXT_SAFE_RATIO = 0.96
# 垂直方向还有空余时，下方小字（PKG / RNG）允许额外放大的范围（位图像素）。
# 位图为 8 px/mm，即 0.125mm ~ 0.5mm。
GROW_MIN_PX = 1.0
GROW_MAX_PX = 4.0

# 标签模式
MODE_MATERIAL = "material"   # 物料标签：TYPE / PKG / RNG
MODE_CABLE = "cable"         # 电缆线标签：大字命名 + 下方备注

# 电缆线标签的字号比例（相对标签高度）
CABLE_TITLE_RATIO = 0.32
CABLE_NOTE_RATIO = 0.18
# 备注块最多占用的可用高度比例，避免备注把命名挤没
CABLE_NOTE_MAX_RATIO = 0.55
# 备注字高上限（相对命名字高），保证「大字命名 + 下方小字备注」的层次
CABLE_NOTE_MAX_FONT_RATIO = 0.8


class LabelGenerator:
    """标签生成器。

    布局统一以「毫米」为单位计算（build_layout），位图通道和 dtpweb
    原生通道共用同一份布局，保证预览效果与打印效果一致。
    """

    def __init__(self):
        self.width_mm = 50.0
        self.height_mm = 25.0
        self.label_data = {
            "type": "",
            "package": "",
            "value_range": ""
        }
        self.cable_data = {
            "name": "",
            "note": ""
        }
        self.mode = MODE_MATERIAL
        self.print_date = False
        self.font_name = "黑体"
        # 整体字号缩放系数，1.0 为默认比例
        self.text_scale = 1.0
        self._font_ratio = None

    def set_mode(self, mode):
        """设置标签模式：MODE_MATERIAL 或 MODE_CABLE。"""
        self.mode = mode if mode in (MODE_MATERIAL, MODE_CABLE) else MODE_MATERIAL

    def set_label_data(self, label_type, package, value_range):
        self.label_data["type"] = label_type
        self.label_data["package"] = package
        self.label_data["value_range"] = value_range

    def set_cable_data(self, name, note):
        """设置电缆线标签内容：命名（大字）与备注（小字）。"""
        self.cable_data["name"] = name or ""
        self.cable_data["note"] = note or ""

    def set_size_mm(self, width_mm, height_mm):
        """以毫米为单位设置标签尺寸。"""
        self.width_mm = float(width_mm)
        self.height_mm = float(height_mm)

    def set_print_date(self, value):
        self.print_date = value

    def set_font_name(self, name):
        self.font_name = name
        self._font_ratio = None

    def set_text_scale(self, scale):
        """设置整体字号缩放系数（0.5 ~ 2.0）。"""
        try:
            scale = float(scale)
        except (ValueError, TypeError):
            scale = 1.0
        self.text_scale = max(0.5, min(2.0, scale))

    def get_qr_content(self):
        if self.mode == MODE_CABLE:
            return f"NAME:{self.cable_data['name']}|NOTE:{self.cable_data['note']}"
        return (
            f"TYPE:{self.label_data['type']}|"
            f"PKG:{self.label_data['package']}|"
            f"RNG:{self.label_data['value_range']}"
        )

    def _load_font(self, size_pt):
        # 优先使用常见中文字体，保证中文/常规字符都能渲染
        for name in ("msyh.ttc", "simhei.ttf", "simsun.ttc", "arial.tt"):
            try:
                return ImageFont.truetype(name, size_pt)
            except Exception:
                continue
        return ImageFont.load_default()

    def _font_height_ratio(self):
        """实测「PIL 字体 size → 实际字符高度（像素）」的线性比例。

        PIL 的 ImageFont.truetype(size) 单位是**像素**（em 尺寸），
        不是物理磅值。dtpweb 的 drawText(fontHeight) 单位是**毫米**，
        若按 mm × 72/25.4 当成磅值直接喂给 PIL，字会只有正确尺寸的 35%，
        看起来就是「文字过小」。这里用探针字测出真实比例再换算。
        """
        if self._font_ratio is None:
            probe = self._load_font(100)
            ratio = 0.0
            try:
                bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), "国", font=probe)
                ratio = (bbox[3] - bbox[1]) / 100.0
            except Exception:
                ratio = 0.0
            # 兜底：常见中文字体的字面高度约占 em 的 0.85~0.9
            self._font_ratio = ratio if ratio > 0.1 else 0.88
        return self._font_ratio

    def _font_size_px(self, font_height_mm):
        """把「字高（毫米）」换算成 PIL 的字体 size（像素）。"""
        target_px = font_height_mm * PX_PER_MM
        return max(1, int(round(target_px / self._font_height_ratio())))

    def _text_width_mm(self, text, font_height_mm):
        """估算指定字高下文本的显示宽度（毫米）。"""
        if not text:
            return 0.0
        probe = self._load_font(100)
        bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=probe)
        width_per_size = (bbox[2] - bbox[0]) / 100.0
        return width_per_size * self._font_size_px(font_height_mm) / PX_PER_MM

    def _fit_font_height(self, text, font_height_mm, max_width_mm):
        """把字高收敛到「文本宽度不超过 max_width_mm」，超宽时每次缩 6%。"""
        h = font_height_mm
        steps = 0
        while (h > MIN_FONT_HEIGHT_MM and steps < MAX_SHRINK_STEPS
               and self._text_width_mm(text, h) > max_width_mm):
            h *= 0.94
            steps += 1
        return round(h, 2)

    def _wrap_text(self, text, font_height_mm, max_width_mm):
        """按可用宽度把文本折成多行。

        西文按空格分词，超长单词或中文再逐字断开，尽量保持可读。
        """
        if not text:
            return [""]
        lines = []
        current = ""
        for token in text.split(" "):
            piece = token
            while piece:
                candidate = piece if not current else current + " " + piece
                if self._text_width_mm(candidate, font_height_mm) <= max_width_mm:
                    current = candidate
                    break
                if current:
                    lines.append(current)
                    current = ""
                    continue
                # 单个词就超宽：逐字切到能放下为止（至少保留一个字符）
                cut = len(piece)
                while cut > 1 and self._text_width_mm(piece[:cut], font_height_mm) > max_width_mm:
                    cut -= 1
                lines.append(piece[:cut])
                piece = piece[cut:]
        if current:
            lines.append(current)
        return lines or [""]

    def _fit_wrapped_lines(self, text, base_h_mm, max_width_mm, max_height_mm,
                           max_font_h_mm=None):
        """折行并尽量用满可用高度。

        先缩小字高直到折行后的总高度放得下，再逐像素尝试放大
        （上限 GROW_MAX_PX），只要不折出新行、不越界就继续放大。

        :return: (最终字高mm, 折行后的文本列表)
        """
        if not text:
            return base_h_mm, [""]
        h = base_h_mm
        if max_font_h_mm is not None:
            h = min(h, max_font_h_mm)
        for _ in range(MAX_SHRINK_STEPS):
            lines = self._wrap_text(text, h, max_width_mm)
            if (len(lines) * h * (1.0 + LINE_GAP_RATIO) <= max_height_mm
                    or h <= MIN_FONT_HEIGHT_MM):
                break
            h *= 0.94
        lines = self._wrap_text(text, h, max_width_mm)

        # 还有余量就继续放大，直到折出新行或顶到放大上限
        step = 1.0 / PX_PER_MM
        while h + step - base_h_mm <= GROW_MAX_PX / PX_PER_MM + 1e-9:
            candidate = h + step
            if max_font_h_mm is not None and candidate > max_font_h_mm:
                break
            cand_lines = self._wrap_text(text, candidate, max_width_mm)
            if len(cand_lines) > len(lines):
                break
            if len(cand_lines) * candidate * (1.0 + LINE_GAP_RATIO) > max_height_mm:
                break
            h, lines = candidate, cand_lines
        return round(h, 2), lines

    def generate_qr_code(self, size=50):
        qr = qrcode.QRCode(version=None, box_size=10, border=1)
        qr.add_data(self.get_qr_content())
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        return qr_img.resize((size, size), Image.NEAREST)

    def build_layout(self):
        """生成以毫米为单位的标签布局。

        返回 {"width", "height", "items": [...]}，
        items 中元素形如：
          {"type": "text", "text", "x", "y", "fontHeight", "fontStyle", "fontName"}
          {"type": "qrcode", "text", "x", "y", "size"}
        """
        W, H = self.width_mm, self.height_mm
        margin = max(0.8, H * 0.06)

        # 右侧二维码：约占宽度 38%，且不超过标签高度
        qr_size = min(W * 0.38, H - 2 * margin)
        qr_size = max(qr_size, 5.0)

        left_x = margin
        left_width = max(4.0, W - qr_size - margin * 2) * TEXT_SAFE_RATIO

        # 每行格式：(文本, 字高mm, 是否参与余量放大, 是否允许折行)
        if self.mode == MODE_CABLE:
            # 电缆线标签：左侧只有两行——大字命名 + 下方备注
            name = self.cable_data["name"]
            note = self.cable_data["note"]
            # 备注留空时，命名可以占满整块高度
            rows = [(name, max(1.5, H * CABLE_TITLE_RATIO), not note, False)]
            if note:
                rows.append((note, max(1.0, H * CABLE_NOTE_RATIO), False, True))
        else:
            title_h = max(1.0, H * 0.11)
            value_h = max(1.2, H * 0.20)
            small_h = max(1.0, H * 0.10)
            rows = [
                ("TYPE:", title_h, False, False),
                (self.label_data["type"], value_h, False, False),
                ("PKG: " + self.label_data["package"], small_h, True, False),
                ("RNG: " + self.label_data["value_range"], small_h, True, False),
            ]
        if self.print_date:
            date_h = max(1.0, H * (CABLE_NOTE_RATIO if self.mode == MODE_CABLE else 0.10))
            rows.append((datetime.now().strftime("%Y-%m-%d %H:%M"), date_h, False, False))

        # 先按可用宽度收敛不折行的各行（超宽时每次缩 6%，比固定步长更平滑）
        fixed = [[text, self._fit_font_height(text, font_h * self.text_scale, left_width), growable]
                 for text, font_h, growable, wrap in rows if not wrap]
        # 折行行可用的高度 = 标签可用高度 - 其余各行已占高度
        avail_h = H - 2 * margin
        wrap_budget = avail_h - sum(h * (1.0 + LINE_GAP_RATIO) for _, h, _ in fixed)
        # 命名行（cable 模式下即第一行）的字高，用于限制备注不要盖过命名
        title_fitted_h = fixed[0][1] if fixed else 0.0

        fitted = []
        fixed_iter = iter(fixed)
        for text, font_h, growable, wrap in rows:
            if not wrap:
                fitted.append(next(fixed_iter))
                continue
            # 备注允许折成多行，并尽量用满剩余高度，但不能盖过命名
            budget = min(max(1.0, wrap_budget), avail_h * CABLE_NOTE_MAX_RATIO)
            line_h, lines = self._fit_wrapped_lines(
                text, font_h * self.text_scale, left_width, budget,
                max_font_h_mm=title_fitted_h * CABLE_NOTE_MAX_FONT_RATIO if title_fitted_h else None)
            for line in lines:
                fitted.append([line, line_h, growable])

        # 垂直方向还有空余时，把下方小字再放大 1~4 像素（不超宽、不越界）
        growable_idx = [i for i, row in enumerate(fitted) if row[2]]
        free_mm = (H - 2 * margin) - sum(h * (1.0 + LINE_GAP_RATIO) for _, h, _ in fitted)
        if growable_idx and free_mm > 0:
            per_row_px = free_mm * PX_PER_MM / (len(growable_idx) * (1.0 + LINE_GAP_RATIO))
            grow_px = min(GROW_MAX_PX, per_row_px)
            if grow_px >= GROW_MIN_PX:
                grown = {}
                for i in growable_idx:
                    text, h, _ = fitted[i]
                    # 放大后若因超宽被缩回去，就保持原字号
                    grown[i] = max(h, self._fit_font_height(
                        text, h + grow_px / PX_PER_MM, left_width))
                # 两行小字取同一个字号，避免长短行大小不一
                uniform = min(grown.values())
                for i, h in grown.items():
                    fitted[i][1] = uniform

        # 行距 = 字高 × LINE_GAP_RATIO，内容整体在标签内垂直居中
        line_heights = [h * (1.0 + LINE_GAP_RATIO) for _, h, _ in fitted]
        content_h = sum(line_heights)
        top = max(margin, (H - content_h) / 2.0)

        items = []
        y = top
        for (text, font_h, _), lh in zip(fitted, line_heights):
            items.append({
                "type": "text",
                "text": text,
                "x": round(left_x, 2),
                "y": round(y, 2),
                "fontHeight": font_h,
                "fontStyle": 0,
                "fontName": self.font_name,
            })
            y += lh

        items.append({
            "type": "qrcode",
            "text": self.get_qr_content(),
            "x": round(W - qr_size - margin, 2),
            "y": round((H - qr_size) / 2, 2),
            "size": round(qr_size, 2),
        })

        return {"width": W, "height": H, "items": items}

    def generate_label_image(self):
        layout = self.build_layout()
        W_px = max(1, int(round(layout["width"] * PX_PER_MM)))
        H_px = max(1, int(round(layout["height"] * PX_PER_MM)))
        img = Image.new("RGB", (W_px, H_px), "white")
        draw = ImageDraw.Draw(img)

        for item in layout["items"]:
            if item["type"] == "text":
                font = self._load_font(self._font_size_px(item["fontHeight"]))
                draw.text((item["x"] * PX_PER_MM, item["y"] * PX_PER_MM),
                          item["text"], font=font, fill="black")
            elif item["type"] == "qrcode":
                qr_px = max(1, int(round(item["size"] * PX_PER_MM)))
                qr_img = self.generate_qr_code(size=qr_px)
                img.paste(qr_img, (int(round(item["x"] * PX_PER_MM)),
                                   int(round(item["y"] * PX_PER_MM))))
        return img

    def save_image(self, filepath):
        img = self.generate_label_image()
        img.save(filepath)

    def get_image_bytes(self):
        img = self.generate_label_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()
