import qrcode

# Your permanent GitHub Pages URL (instead of Render directly)
base_url = "https://michael-code-dot.github.io/hotel-qr-redirect"

# Generates QR codes for Table 1 up to Table 54
for table in range(1, 55):
    url = f"{base_url}/?table={table}"
    
    qr = qrcode.make(url)
    qr.save(f"Table_{table}.png")

print("✅ All 54 Permanent QR Codes Generated Successfully!")