import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

# ==========================================================
# 🏨 MAGIC MANDI & GRILL - TIGHT LAYOUT (MINIMAL WHITE SPACE)
# ==========================================================
BASE_URL = "https://michael-code-dot.github.io/hotel-qr-redirect/"
OUTPUT_FOLDER = "magic_mandi_clean_qrs"

CANVAS_SIZE = 600  # Square canvas (600x600 px)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

for table_num in range(1, 55):
    # 1. Plain white square canvas
    img = Image.new('RGB', (CANVAS_SIZE, CANVAS_SIZE), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # 2. Generate QR code with border=0 to remove built-in margins
    table_url = f"{BASE_URL}?table={table_num}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=0,  # 👈 Removes built-in white border from QR generator
    )
    qr.add_data(table_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert('RGB')

    # 3. Scale QR Code to fill almost the entire width (490x490 px)
    qr_size = 490
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    qr_x = (CANVAS_SIZE - qr_size) // 2  # Tight side margins
    qr_y = 20                            # Very tight 20px top margin
    img.paste(qr_img, (qr_x, qr_y))

    # 4. Load Bold Font
    try:
        font_footer = ImageFont.truetype("arialbd.ttf", 50)
    except IOError:
        try:
            font_footer = ImageFont.truetype("arial.ttf", 50)
        except IOError:
            font_footer = ImageFont.load_default()

    # 5. Position "SCAN MENU" directly underneath with tight spacing
    draw.text(
        (CANVAS_SIZE // 2, qr_y + qr_size + 35),
        "SCAN MENU",
        fill="#000000",  # Bold Black Text
        font=font_footer,
        anchor="mm"
    )

    # 6. Save PNG image
    file_path = os.path.join(OUTPUT_FOLDER, f"Table_{table_num}.png")
    img.save(file_path, "PNG")

print(f"🎉 Done! Regenerated tight QRs with minimal white space in '{OUTPUT_FOLDER}'!")