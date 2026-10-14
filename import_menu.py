
import os
import pandas as pd
import mysql.connector

# Exact filename matching your file explorer
excel_file = "Product (product.template) (1) (1).xlsx"
df = pd.read_excel(excel_file)
print(f"Loaded {len(df)} items from Excel spreadsheet.")

def connect_to_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST", "localhost"),
        user=os.getenv("MYSQLUSER", "root"),
        password=os.getenv("MYSQLPASSWORD", "5002"),
        database=os.getenv("MYSQLDATABASE", "hotelqr"),
        port=int(os.getenv("MYSQLPORT", 3306)),
        ssl_disabled=False
    )

db = connect_to_db()
cursor = db.cursor()

# Clear old entries to prevent duplicates
cursor.execute("TRUNCATE TABLE menu")

# Loop through and insert all items safely
for index, row in df.iterrows():
    name = str(row['Name']).strip()
    
    category = str(row['Product Category']).replace('Finished Goods / ', '').strip()
    if 'Mojito' in category or 'Mocktail' in category:
        category = 'Mocktails'
    elif 'Juice' in category:
        category = 'Juices'
    elif 'Pasta' in category:
        category = 'Pastas'
    elif 'Pizza' in category:
        category = 'Pizzas'
    elif 'Coffee' in category:
        category = 'Coffee'
    elif 'Ice Cream' in category:
        category = 'Ice Cream'

    description = f"Delicious {name} freshly prepared."
    price = float(row['Sales Price'])
    image = "default.jpg"

    cursor.execute("""
        INSERT INTO menu (name, category, description, price, image)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, category, description, price, image))

db.commit()
cursor.close()
db.close()

print(f"✅ Success! All {len(df)} menu items imported into MySQL database.")