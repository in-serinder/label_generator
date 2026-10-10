from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
from datetime import datetime


class LabelGenerator:
    def __init__(self):
        self.width = 400
        self.height = 200
        self.label_data = {
            "type": "",
            "package": "",
            "value_range": ""
        }
        self.print_date = False

    def set_label_data(self, label_type, package, value_range):
        self.label_data["type"] = label_type
        self.label_data["package"] = package
        self.label_data["value_range"] = value_range

    def set_size(self, width, height):
        self.width = width
        self.height = height

    def set_print_date(self, value):
        self.print_date = value

    def _load_font(self, size):
        # 优先使用常见中文字体，保证中文/常规字符都能渲染
        for name in ("msyh.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def generate_qr_code(self, size=50):
        qr_content = f"TYPE:{self.label_data['type']}|PKG:{self.label_data['package']}|RNG:{self.label_data['value_range']}"
        qr = qrcode.QRCode(version=None, box_size=10, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        return qr_img.resize((size, size), Image.NEAREST)

    def generate_label_image(self):
        W, H = self.width, self.height
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)

        margin = max(4, int(H * 0.06))

        # 字体按图像高度等比缩放
        f_title = self._load_font(max(8, int(H * 0.11)))
        f_value = self._load_font(max(10, int(H * 0.20)))
        f_small = self._load_font(max(8, int(H * 0.10)))

        # 右侧二维码区域：约占宽度 38%，且不超过高度
        qr_size = min(int(W * 0.38), H - 2 * margin)
        qr_size = max(qr_size, 20)
        qr_img = self.generate_qr_code(size=qr_size)

        # 左侧文本区域
        left_x = margin
        left_right = W - qr_size - margin * 2
        left_width = left_right - left_x

        # 二维码水平靠右居中，垂直居中
        qr_x = W - qr_size - margin
        qr_y = (H - qr_size) // 2

        def text_w(text, font):
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0]

        def clamp_font(text, font, max_w):
            # 若文字超宽则缩小字号
            size = font.size
            while size > 6 and text_w(text, font) > max_w:
                size -= 1
                font = self._load_font(size)
            return font

        # 垂直布局：TYPE / 值 / PKG / RNG / (日期)
        rows = []
        rows.append(("TYPE:", f_title))
        rows.append((self.label_data["type"], f_value))
        rows.append(("PKG: " + self.label_data["package"], f_small))
        rows.append(("RNG: " + self.label_data["value_range"], f_small))
        if self.print_date:
            rows.append((datetime.now().strftime("%Y-%m-%d %H:%M"), f_small))

        # 计算每行高度并按间距均匀分布
        heights = []
        for text, font in rows:
            bbox = draw.textbbox((0, 0), text, font=font)
            heights.append(bbox[3] - bbox[1])
        total_text_h = sum(heights)
        gap = max(2, (H - 2 * margin - total_text_h) // (len(rows) + 1))

        y = margin + gap
        for (text, font), lh in zip(rows, heights):
            font = clamp_font(text, font, left_width)
            draw.text((left_x, y), text, font=font, fill="black")
            y += lh + gap

        img.paste(qr_img, (qr_x, qr_y))
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
