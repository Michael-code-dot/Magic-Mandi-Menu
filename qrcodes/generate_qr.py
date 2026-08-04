import qrcode

# Your live Render website URL
base_url = "https://magic-mandi-menu.onrender.com"

# Generates QR codes for Table 1 up to Table 54
for table in range(1, 55):
    url = f"{base_url}/?table={table}"
    
    qr = qrcode.make(url)
    qr.save(f"Table_{table}.png")

print("✅ All 54 QR Codes Generated Successfully!")