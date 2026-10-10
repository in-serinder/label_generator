from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
from datetime import datetime


class LabelGenerator:
    def __init__(self):
        self.width = 200
        self.height = 100
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

    def generate_qr_code(self, size=50):
        qr_content = f"TYPE:{self.label_data['type']}|PKG:{self.label_data['package']}|RNG:{self.label_data['value_range']}"
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data(qr_content)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        return qr_img.resize((size, size), Image.LANCZOS)

    def set_print_date(self, value):
        self.print_date = value

    def generate_label_image(self):
        img = Image.new("RGB", (self.width, self.height), "white")
        draw = ImageDraw.Draw(img)

        try:
            font_label = ImageFont.truetype("arial.ttf", 10)
            font_value = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 9)
        except:
            font_label = ImageFont.load_default()
            font_value = ImageFont.load_default()
            font_small = ImageFont.load_default()

        left_width = self.width * 65 // 100
        right_width = self.width - left_width

        draw.text((8, 5), "TYPE:", font=font_label, fill="black")
        draw.text((8, 18), self.label_data["type"], font=font_value, fill="black")
        draw.text((8, 40), "PKG:", font=font_small, fill="black")
        draw.text((35, 40), self.label_data["package"], font=font_small, fill="black")
        draw.text((8, 55), "RNG:", font=font_small, fill="black")
        draw.text((35, 55), self.label_data["value_range"], font=font_small, fill="black")

        if self.print_date:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            draw.text((8, 70), current_time, font=font_small, fill="black")

        qr_img = self.generate_qr_code(size=min(right_width - 6, self.height - 6))
        qr_x = left_width + (right_width - qr_img.width) // 2
        qr_y = (self.height - qr_img.height) // 2
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