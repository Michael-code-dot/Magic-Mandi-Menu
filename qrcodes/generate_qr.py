import qrcode

base_url = "http://192.168.1.100:5000"

for table in range(1, 55):

    url = f"{base_url}/?table={table}"

    qr = qrcode.make(url)

    qr.save(f"Table_{table}.png")

print("✅ QR Codes Generated Successfully!")