import os
from flask import Flask, render_template, request, jsonify, redirect
import mysql.connector

app = Flask(__name__)

# Dynamic Database Connection (Reads from Render Environment Variables)
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

def get_db():
    global db
    try:
        if not db.is_connected():
            db.reconnect(attempts=3, delay=2)
    except Exception:
        db = connect_to_db()
    return db


@app.route('/')
def index():
    database = get_db()
    table = request.args.get("table")

    cursor = database.cursor(dictionary=True)

    cursor.execute("""
        SELECT id,name,category,description,price,image
        FROM menu
    """)

    menu = cursor.fetchall()

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

    cursor = database.cursor(dictionary=True)

    # Find the waiter assigned to this table
    cursor.execute("""
        SELECT waiter_id
        FROM table_assignments
        WHERE table_number=%s
    """, (table_number,))

    assignment = cursor.fetchone()

    if assignment is None:
        return jsonify({"message": "No waiter assigned to this table."}), 400

    waiter_id = assignment["waiter_id"]

    # Save the order
    cursor.execute("""
        INSERT INTO orders
        (customer_name, table_number, total, waiter_id)
        VALUES (%s, %s, %s, %s)
    """, (
        customer_name,
        table_number,
        total,
        waiter_id
    ))

    order_id = cursor.lastrowid

    # Save ordered items
    for item in cart:
        cursor.execute("""
            INSERT INTO order_items
            (order_id, menu_name, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (
            order_id,
            item["name"],
            item["quantity"],
            item["price"]
        ))

    database.commit()

    return jsonify({
        "message": "Order placed successfully!",
        "order_id": order_id
    })


@app.route("/waiter")
def waiter():
    database = get_db()
    cursor = database.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            orders.*,
            waiters.name AS waiter_name
        FROM orders
        LEFT JOIN waiters
        ON orders.waiter_id = waiters.id
        ORDER BY orders.created_at DESC
    """)

    orders = cursor.fetchall()

    for order in orders:
        cursor.execute("""
            SELECT menu_name, quantity, price
            FROM order_items
            WHERE order_id=%s
        """, (order["id"],))

        order["items"] = cursor.fetchall()

    return render_template(
        "waiter.html",
        orders=orders
    )


@app.route("/kitchen_data")
def kitchen_data():
    database = get_db()
    cursor = database.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            orders.*,
            waiters.name AS waiter_name
        FROM orders
        LEFT JOIN waiters
        ON orders.waiter_id = waiters.id
        ORDER BY orders.created_at DESC
    """)

    orders = cursor.fetchall()

    for order in orders:
        cursor.execute("""
            SELECT menu_name, quantity, price
            FROM order_items
            WHERE order_id=%s
        """, (order["id"],))

        order["items"] = cursor.fetchall()

    return jsonify(orders)


@app.route("/complete/<int:order_id>")
def complete_order(order_id):
    database = get_db()
    cursor = database.cursor()
    cursor.execute("UPDATE orders SET status='Completed' WHERE id=%s", (order_id,))
    database.commit()
    return redirect("/kitchen")


@app.route("/preparing/<int:order_id>")
def preparing_order(order_id):
    database = get_db()
    cursor = database.cursor()
    cursor.execute("UPDATE orders SET status='Preparing' WHERE id=%s", (order_id,))
    database.commit()
    return redirect("/kitchen")


@app.route("/admin")
def admin():
    database = get_db()
    cursor = database.cursor(dictionary=True)

    # Total orders
    cursor.execute("SELECT COUNT(*) AS total FROM orders")
    total_orders = cursor.fetchone()["total"]

    # Total revenue
    cursor.execute("SELECT SUM(total) AS revenue FROM orders")
    result = cursor.fetchone()
    revenue = result["revenue"] if result["revenue"] else 0

    # Preparing orders
    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Preparing'")
    preparing = cursor.fetchone()["total"]

    # Completed orders
    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Completed'")
    completed = cursor.fetchone()["total"]

    return render_template(
        "admin.html",
        total_orders=total_orders,
        revenue=revenue,
        preparing=preparing,
        completed=completed
    )


@app.route("/add_menu", methods=["GET", "POST"])
def add_menu():
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
        return redirect("/admin")

    return render_template("add_menu.html")


@app.route("/manage_menu")
def manage_menu():
    database = get_db()
    cursor = database.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu")
    menu = cursor.fetchall()
    return render_template("manage_menu.html", menu=menu)


@app.route("/edit_menu/<int:item_id>", methods=["GET", "POST"])
def edit_menu(item_id):
    database = get_db()
    cursor = database.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]

        cursor.execute("""
            UPDATE menu SET name=%s, price=%s WHERE id=%s
        """, (name, price, item_id))
        database.commit()
        return redirect("/manage_menu")

    cursor.execute("SELECT * FROM menu WHERE id=%s", (item_id,))
    item = cursor.fetchone()
    return render_template("edit_menu.html", item=item)


@app.route("/delete_menu/<int:item_id>")
def delete_menu(item_id):
    database = get_db()
    cursor = database.cursor()

    # Delete related order items first (if any)
    cursor.execute("""
        DELETE FROM order_items 
        WHERE menu_name = (SELECT name FROM menu WHERE id=%s)
    """, (item_id,))

    # Delete the menu item
    cursor.execute("DELETE FROM menu WHERE id=%s", (item_id,))
    database.commit()

    return redirect("/manage_menu")


@app.route("/track/<int:order_id>")
def track_order(order_id):
    database = get_db()
    cursor = database.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            orders.*,
            waiters.name AS waiter_name
        FROM orders
        LEFT JOIN waiters
        ON orders.waiter_id = waiters.id
        WHERE orders.id=%s
    """, (order_id,))

    order = cursor.fetchone()

    return render_template(
        "track_order.html",
        order=order
    )


@app.route("/receipt/<int:order_id>")
def receipt(order_id):
    database = get_db()
    cursor = database.cursor(dictionary=True)

    # Automatically mark the order as Printed
    cursor.execute("""
        UPDATE orders
        SET status='Printed'
        WHERE id=%s
    """, (order_id,))
    database.commit()

    # Get order details
    cursor.execute("""
        SELECT
            orders.*,
            waiters.name AS waiter_name
        FROM orders
        LEFT JOIN waiters
        ON orders.waiter_id = waiters.id
        WHERE orders.id=%s
    """, (order_id,))

    order = cursor.fetchone()

    # Get ordered items
    cursor.execute("""
        SELECT *
        FROM order_items
        WHERE order_id=%s
    """, (order_id,))

    items = cursor.fetchall()

    return render_template(
        "receipt.html",
        order=order,
        items=items
    )


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)