import os
import pandas as pd
import mysql.connector

excel_file = "Product (product.template) (1) (1).xlsx"
df = pd.read_excel(excel_file)
print(f"Loaded {len(df)} items from Excel spreadsheet.")

def connect_to_db():
    return mysql.connector.connect(
        host="magic-mandi-db-lekantrevon-f36c.h.aivencloud.com",
        user="avnadmin",
        password=os.getenv("MYSQLPASSWORD"),
        database="defaultdb",
        port=15691,
        ssl_disabled=False
    )

db = connect_to_db()
cursor = db.cursor()

# Automatically create the menu table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        category VARCHAR(100),
        description TEXT,
        price DECIMAL(10, 2),
        image VARCHAR(255)
    )
""")

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

    clean_name = name . lower().replace(" ", "-").replace("/", "").replace("'", "").replace("(", "").replace(")", "").replace("&", "and")
    image = f"{clean_name}.jpg"

    
    cursor.execute("""
        INSERT INTO menu (name, category, description, price, image)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, category, description, price, image))

db.commit()
cursor.close()
db.close()

print(f"✅ Success! All {len(df)} menu items imported into Aiven MySQL database.")


