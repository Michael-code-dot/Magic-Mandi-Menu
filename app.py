import os
import time
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, g, session, url_for
import mysql.connector

app = Flask(__name__)

# Force browser to cache static images/CSS locally for 7 days
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 604800 

# Security configuration for admin session login
app.secret_key = 'magic_mandi_super_secret_key_change_this'
ADMIN_PASSWORD = "mandi123_secure"


# ==========================================================
# ⚡ IN-MEMORY CACHE CONFIGURATION
# ==========================================================
MENU_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_DURATION = 300  # 300 seconds = 5 Minutes


# Get a database connection with automatic fallback to SQLite if MySQL fails
def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=os.getenv("MYSQLHOST", "magic-mandi-db-lekantrevon-f36c.h.aivencloud.com"),
                user=os.getenv("MYSQLUSER", "avnadmin"),
                password=os.getenv("MYSQLPASSWORD"),
                database=os.getenv("MYSQLDATABASE", "defaultdb"),
                port=int(os.getenv("MYSQLPORT", 15691)),
                ssl_disabled=False
            )
            g.db_type = 'mysql'
        except Exception as e:
            print(f"⚠️ MySQL connection failed: {e}. Falling back to SQLite.")
            g.db = sqlite3.connect('menu.db')
            g.db.row_factory = sqlite3.Row
            g.db_type = 'sqlite'
            g.db.execute('''CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                category TEXT,
                description TEXT,
                price REAL,
                image TEXT
            )''')
            g.db.commit()
    return g.db

# Automatically close the database connection when the request completes
@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            if hasattr(db, 'is_connected') and db.is_connected():
                db.close()
            else:
                db.close()
        except Exception:
            pass


# ==========================================================
# 🏨 CUSTOMER MENU ROUTE (CACHED FOR 200+ SCANS)
# ==========================================================
@app.route('/')
def index():
    table = request.args.get("table")
    current_time = time.time()

    # 1. SERVE FROM RAM CACHE IF VALID
    if MENU_CACHE["data"] is not None and (current_time - MENU_CACHE["timestamp"] < CACHE_DURATION):
        seconds_left = int(CACHE_DURATION - (current_time - MENU_CACHE["timestamp"]))
        print(f"⚡ [CACHE HIT] Serving menu from RAM in 0.001s! (Cache updates in {seconds_left}s)")
        menu = MENU_CACHE["data"]

    # 2. CACHE EXPIRED OR FIRST RUN -> QUERY DATABASE
    else:
        print("🐢 [CACHE EXPIRED/MISS] Querying database...")
        database = get_db()
        
        if getattr(g, 'db_type', 'mysql') == 'mysql':
            cursor = database.cursor(dictionary=True)
            cursor.execute("SELECT id, name, category, description, price, image FROM menu")
            menu = cursor.fetchall()
            cursor.close()
        else:
            cursor = database.execute("SELECT id, name, category, description, price, image FROM menu")
            menu = [dict(row) for row in cursor.fetchall()]

        # 3. SAVE FRESH DATA TO RAM CACHE
        MENU_CACHE["data"] = menu
        MENU_CACHE["timestamp"] = current_time
        print("✅ [CACHE UPDATED] Fresh menu saved to server memory!")

    return render_template(
        "index.html",
        menu=menu,
        table=table
    )


@app.route("/place_order", methods=["POST"])
def place_order():
    database = get_db()
    data = request.get_json()

    customer_name = data["customer_name"]
    table_number = data["table_number"]
    cart = data["cart"]
    total = data["total"]

    if getattr(g, 'db_type', 'mysql') == 'mysql':
        cursor = database.cursor(dictionary=True)
        cursor.execute("SELECT waiter_id FROM table_assignments WHERE table_number=%s", (table_number,))
        assignment = cursor.fetchone()

        if assignment is None:
            return jsonify({"message": "No waiter assigned to this table."}), 400

        waiter_id = assignment["waiter_id"]

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
    else:
        # SQLite fallback execution
        cursor = database.cursor()
        cursor.execute("""
            INSERT INTO orders (customer_name, table_number, total, waiter_id)
            VALUES (?, ?, ?, ?)
        """, (customer_name, table_number, total, 1))
        order_id = cursor.lastrowid
        database.commit()

    return jsonify({
        "message": "Order placed successfully!",
        "order_id": order_id
    })


@app.route("/waiter")
def waiter():
    database = get_db()
    if getattr(g, 'db_type', 'mysql') == 'mysql':
        cursor = database.cursor(dictionary=True)
        cursor.execute("SELECT orders.*, waiters.name AS waiter_name FROM orders LEFT JOIN waiters ON orders.waiter_id = waiters.id ORDER BY orders.created_at DESC")
        orders = cursor.fetchall()
        for order in orders:
            cursor.execute("SELECT menu_name, quantity, price FROM order_items WHERE order_id=%s", (order["id"],))
            order["items"] = cursor.fetchall()
    else:
        orders = []
    return render_template("waiter.html", orders=orders)


@app.route("/kitchen_data")
def kitchen_data():
    database = get_db()
    if getattr(g, 'db_type', 'mysql') == 'mysql':
        cursor = database.cursor(dictionary=True)
        cursor.execute("SELECT orders.*, waiters.name AS waiter_name FROM orders LEFT JOIN waiters ON orders.waiter_id = waiters.id ORDER BY orders.created_at DESC")
        orders = cursor.fetchall()
        for order in orders:
            cursor.execute("SELECT menu_name, quantity, price FROM order_items WHERE order_id=%s", (order["id"],))
            order["items"] = cursor.fetchall()
    else:
        orders = []
    return jsonify(orders)


@app.route("/complete/<int:order_id>")
def complete_order(order_id):
    database = get_db()
    cursor = database.cursor() if getattr(g, 'db_type', 'mysql') == 'mysql' else database
    cursor.execute("UPDATE orders SET status='Completed' WHERE id=?", (order_id,) if getattr(g, 'db_type', 'mysql') != 'mysql' else "UPDATE orders SET status='Completed%s'")
    database.commit()
    return redirect("/kitchen")


@app.route("/preparing/<int:order_id>")
def preparing_order(order_id):
    database = get_db()
    database.commit()
    return redirect("/kitchen")


# ==========================================================
# 🔐 ADMIN AUTHENTICATION ROUTES
# ==========================================================
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


# ==========================================================
# 🛠️ PROTECTED ADMIN & MENU MANAGEMENT ROUTES
# ==========================================================
@app.route("/admin")
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template("admin.html", total_orders=0, revenue=0, preparing=0, completed=0)


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

        if getattr(g, 'db_type', 'mysql') == 'mysql':
            cursor = database.cursor()
            cursor.execute("INSERT INTO menu (name, category, description, price, image) VALUES (%s, %s, %s, %s, %s)", (name, category, description, price, image))
            database.commit()
        else:
            database.execute("INSERT INTO menu (name, category, description, price, image) VALUES (?, ?, ?, ?, ?)", (name, category, description, price, image))
            database.commit()

        MENU_CACHE["data"] = None
        return redirect("/admin")

    return render_template("add_menu.html")


@app.route("/manage_menu")
def manage_menu():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    database = get_db()
    if getattr(g, 'db_type', 'mysql') == 'mysql':
        cursor = database.cursor(dictionary=True)
        cursor.execute("SELECT * FROM menu")
        menu = cursor.fetchall()
    else:
        cursor = database.execute("SELECT * FROM menu")
        menu = [dict(row) for row in cursor.fetchall()]
    return render_template("manage_menu.html", menu=menu)


@app.route("/edit_menu/<int:item_id>", methods=["GET", "POST"])
def edit_menu(item_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    global MENU_CACHE
    database = get_db()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        if getattr(g, 'db_type', 'mysql') == 'mysql':
            cursor = database.cursor()
            cursor.execute("UPDATE menu SET name=%s, price=%s WHERE id=%s", (name, price, item_id))
            database.commit()
        MENU_CACHE["data"] = None
        return redirect("/manage_menu")

    if getattr(g, 'db_type', 'mysql') == 'mysql':
        cursor = database.cursor(dictionary=True)
        cursor.execute("SELECT * FROM menu WHERE id=%s", (item_id,))
        item = cursor.fetchone()
    else:
        item = {"name": "", "price": 0}
    return render_template("edit_menu.html", item=item)


@app.route("/delete_menu/<int:item_id>")
def delete_menu(item_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    global MENU_CACHE
    database = get_db()
    if getattr(g, 'db_type', 'mysql') == 'mysql':
        cursor = database.cursor()
        cursor.execute("DELETE FROM menu WHERE id=%s", (item_id,))
        database.commit()

    MENU_CACHE["data"] = None
    return redirect("/manage_menu")


@app.route("/track/<int:order_id>")
def track_order(order_id):
    return render_template("track_order.html", order={"id": order_id, "status": "Pending"})


@app.route("/receipt/<int:order_id>")
def receipt(order_id):
    return render_template("receipt.html", order={"id": order_id}, items=[])


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)