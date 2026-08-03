import qrcode

base_url = "http://127.0.0.1:5000"

for table in range(1, 21):

    url = f"{base_url}/?table={table}"

    qr = qrcode.make(url)

    qr.save(f"qrcodes/Table_{table}.png")

print("✅ QR Codes Generated Successfully!")