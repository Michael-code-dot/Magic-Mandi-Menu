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
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        category VARCHAR(100),
        description TEXT,
        price DECIMAL(10,2),
        image VARCHAR(255)
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
        try:
            database = get_db()
            cursor = database.cursor(dictionary=True)
            cursor.execute("SELECT id, name, category, description, price, image FROM menu")
            menu = cursor.fetchall()
            cursor.close()
        except Exception as e:
            print("DATABASE ERROR IN INDEX ROUTE:", str(e))
            menu = []

        MENU_CACHE["data"] = menu
        MENU_CACHE["timestamp"] = current_time

    return render_template("index.html", menu=menu, table=table)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        entered_password = request.form.get('password', '').strip()
        if entered_password == ADMIN_PASSWORD:
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

    return render_template("admin.html")

@app.route("/manage_menu")
def manage_menu():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    menu = []
    try:
        database = get_db()
        cursor = database.cursor(dictionary=True)
        cursor.execute("SELECT * FROM menu")
        menu = cursor.fetchall()
        cursor.close()

        if not menu:
            ins_cursor = database.cursor()
            ins_cursor.execute("""
                INSERT INTO menu (name, category, description, price, image) VALUES 
                ('Grilled Chicken', 'Main Meal', 'Delicious grilled chicken served with fries.', 700.00, 'images/chicken.jpg'),
                ('Cheese Pizza', 'Fast Food', 'Fresh pizza prepared with cheese.', 900.00, 'images/pizza.jpg'),
                ('Fresh Juice', 'Drinks', 'Fresh passion and orange juice.', 250.00, 'images/juice.jpg')
            """)
            database.commit()
            ins_cursor.close()

            fetch_cursor = database.cursor(dictionary=True)
            fetch_cursor.execute("SELECT * FROM menu")
            menu = fetch_cursor.fetchall()
            fetch_cursor.close()
    except Exception as e:
        print("DATABASE ERROR IN MANAGE_MENU:", str(e))
        menu = [
            {'id': 1, 'name': 'Grilled Chicken', 'category': 'Main Meal', 'price': 700.00},
            {'id': 2, 'name': 'Cheese Pizza', 'category': 'Fast Food', 'price': 900.00},
            {'id': 3, 'name': 'Fresh Juice', 'category': 'Drinks', 'price': 250.00}
        ]

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
        description = request.form.get("description", "")
        price = request.form["price"]
        image = request.form.get("image", "")

        cursor = database.cursor()
        cursor.execute("""
            INSERT INTO menu (name, category, description, price, image)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, category, description, price, image))
        database.commit()
        cursor.close()

        MENU_CACHE["data"] = None
        return redirect(url_for("manage_menu"))

    return render_template("add_menu.html")

@app.route("/edit_menu/<int:item_id>", methods=["GET", "POST"])
def edit_menu(item_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    global MENU_CACHE
    database = get_db()
    cursor = database.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]

        cursor.execute("UPDATE menu SET name=%s, price=%s WHERE id=%s", (name, price, item_id))
        database.commit()
        cursor.close()

        MENU_CACHE["data"] = None
        return redirect(url_for("manage_menu"))

    cursor.execute("SELECT * FROM menu WHERE id=%s", (item_id,))
    item = cursor.fetchone()
    cursor.close()

    if not item:
        item = {'id': item_id, 'name': 'Sample Dish', 'price': 500.00}

    return render_template("edit_menu.html", item=item)

@app.route("/delete_menu/<int:item_id>")
def delete_menu(item_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    global MENU_CACHE
    try:
        database = get_db()
        cursor = database.cursor()
        cursor.execute("DELETE FROM menu WHERE id=%s", (item_id,))
        database.commit()
        cursor.close()
        MENU_CACHE["data"] = None
    except Exception as e:
        print("DELETE ERROR:", str(e))

    return redirect(url_for("manage_menu"))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)