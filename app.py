import os
import time
from flask import Flask, render_template, request, jsonify, redirect, g, session, url_for
import mysql.connector

app = Flask(__name__)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 604800 
app.secret_key = 'magic_mandi_super_secret_key_change_this'
ADMIN_PASSWORD = "mandi123_secure"

MENU_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_DURATION = 300

def connect_to_db():
    db = mysql.connector.connect(
        host=os.getenv("MYSQLHOST", "magic-mandi-db-lekantrevon-f36c.h.aivencloud.com"),
        user=os.getenv("MYSQLUSER", "avnadmin"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE", "defaultdb"),
        port=int(os.getenv("MYSQLPORT", 15691)),
        ssl_disabled=False
    )
    # Automatically initialize tables if they don't exist
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        category VARCHAR(100),
        description TEXT,
        price DECIMAL(10,2),
        image VARCHAR(255)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        customer_name VARCHAR(255),
        table_number INT,
        total DECIMAL(10,2),
        waiter_id INT,
        status VARCHAR(50) DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT,
        menu_name VARCHAR(255),
        quantity INT,
        price DECIMAL(10,2)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS waiters (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS table_assignments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        table_number INT,
        waiter_id INT
    )''')
    db.commit()
    cursor.close()
    return db

def get_db():
    if 'db' not in g:
        g.db = connect_to_db()
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

@app.route('/')
def index():
    table = request.args.get("table")
    current_time = time.time()

    if MENU_CACHE["data"] is not None and (current_time - MENU_CACHE["timestamp"] < CACHE_DURATION):
        menu = MENU_CACHE["data"]
    else:
        database = get_db()
        cursor = database.cursor(dictionary=True)
        cursor.execute("SELECT id, name, category, description, price, image FROM menu")
        menu = cursor.fetchall()
        cursor.close()

        MENU_CACHE["data"] = menu
        MENU_CACHE["timestamp"] = current_time

    return render_template("index.html", menu=menu, table=table)

@app.route("/place_order", methods=["POST"])
def place_order():
    database = get_db()
    data = request.get_json()

    customer_name = data["customer_name"]
    table_number = data["table_number"]
    cart = data["cart"]
    total = data["total"]

    cursor = database.cursor(dictionary=True)
    cursor.execute("SELECT waiter_id FROM table_assignments WHERE table_number=%s", (table_number,))
    assignment = cursor.fetchone()

    waiter_id = assignment["waiter_id"] if assignment else 1

    cursor.execute("""
        INSERT INTO orders (customer_name, table_number, total, waiter_id)
        VALUES (%s, %s, %s, %s)
    """, (customer_name, table_number, total, waiter_id))

    order_id = cursor.lastrowid

    for item in cart:
        cursor.execute("""
            INSERT INTO order_items (order_id, menu_name, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, item["name"], item["quantity"], item["price"]))

    database.commit()
    cursor.close()

    return jsonify({"message": "Order placed successfully!", "order_id": order_id})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Incorrect Password. Please try again.'
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route("/admin")
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    database = get_db()
    cursor = database.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM orders")
    total_orders = cursor.fetchone()["total"]

    cursor.execute("SELECT SUM(total) AS revenue FROM orders")
    result = cursor.fetchone()
    revenue = result["revenue"] if result["revenue"] and result["revenue"] else 0

    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Preparing'")
    preparing = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Completed'")
    completed = cursor.fetchone()["total"]
    cursor.close()

    return render_template(
        "admin.html",
        total_orders=total_orders,
        revenue=revenue,
        preparing=preparing,
        completed=completed
    )

@app.route("/manage_menu")
def manage_menu():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    database = get_db()
    cursor = database.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu")
    menu = cursor.fetchall()
    cursor.close()
    return render_template("manage_menu.html", menu=menu)

@app.route("/add_menu", methods=["GET", "POST"])
def add_menu():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    global MENU_CACHE
    database = get_db()
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        description = request.form["description"]
        price = request.form["price"]
        image = request.form["image"]

        cursor = database.cursor()
        cursor.execute("""
            INSERT INTO menu (name, category, description, price, image)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, category, description, price, image))
        database.commit()
        cursor.close()

        MENU_CACHE["data"] = None
        return redirect("/admin")

    return render_template("add_menu.html")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)