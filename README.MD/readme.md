# 🏨 Magic Mandi & Grill - Digital QR Menu

A light, fast, and responsive view-only digital menu system for **Magic Mandi & Grill**. Customers scan a QR code at their table to view the real-time menu directly on their smartphones.

---

## 📌 Project Overview

- **View-Only Experience:** Designed for seamless menu browsing without requiring app downloads or login setups.
- **Dynamic Content:** Menu categories, items, prices, and descriptions are powered dynamically via MySQL.
- **Table-Specific QR Codes:** Includes a custom Python script that automatically generates 54 clean, printable QR codes mapped to individual table redirect parameters.

---

## 🛠️ Tech Stack

- **Backend:** Python (Flask)
- **Database:** MySQL
- **Frontend:** HTML5, CSS3, JavaScript
- **Utilities:** `qrcode`, `Pillow` (PIL) for automated image generation

---

## 📂 Project Structure

```text
HotelQRmenu/
│
├── qrcodes/
│   ├── magic_mandi_clean_qrs/  # Generated PNG sticker files (Tables 1-54)
│   └── generate_qr.py           # Automated QR code generator script
│
├── static/
│   ├── css/                    # Custom stylesheets
│   ├── images/                 # Dish & background imagery
│   └── js/                     # Client-side scripts
│
├── templates/
│   ├── index.html              # Main landing view
│   ├── menu.html               # Digital menu interface
│   └── manage_menu.html        # Menu management dashboard
│
├── app.py                      # Flask application server
└── README.md                   # Project documentation