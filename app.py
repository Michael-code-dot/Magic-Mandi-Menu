import os
import time
import calendar
from functools import wraps
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, g, session, url_for
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
import mysql.connector
from mysql.connector import pooling

app = Flask(__name__)
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 604800

# ---------------------------------------------------------------------------
# Required configuration. The app refuses to start if any of these are
# missing, instead of silently falling back to something insecure.
#
# ADMIN_PASSWORD_HASH / DEBASA_ADMIN_PASSWORD_HASH are password HASHES, not
# plaintext passwords. Generate them with generate_password_hash.py and put
# the output in your .env file / host's environment variable settings.
# ---------------------------------------------------------------------------
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is not set. Generate one with:\n"
        '  python -c "import secrets; print(secrets.token_hex(32))"'
    )

ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH:
    raise RuntimeError(
        "ADMIN_PASSWORD_HASH is not set. Generate it with generate_password_hash.py"
    )

DEBASA_ADMIN_PASSWORD_HASH = os.getenv("DEBASA_ADMIN_PASSWORD_HASH")
if not DEBASA_ADMIN_PASSWORD_HASH:
    raise RuntimeError(
        "DEBASA_ADMIN_PASSWORD_HASH is not set. Generate it with generate_password_hash.py"
    )

# CSRF protection on every POST/PUT/PATCH/DELETE form. Every <form> in the
# templates needs: <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
csrf = CSRFProtect(app)

# Rate limiting, keyed by IP. No global default — applied explicitly to the
# two login routes below so brute-forcing the password is no longer free.
limiter = Limiter(get_remote_address, app=app, default_limits=[])

MENU_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_DURATION = 300

DB_CONFIG = {
    "host": os.getenv("MYSQLHOST", "magic-mandi-db-lekantrevon-f36c.h.aivencloud.com"),
    "user": os.getenv("MYSQLUSER", "avnadmin"),
    "password": os.getenv("MYSQLPASSWORD"),
    "database": os.getenv("MYSQLDATABASE", "defaultdb"),
    "port": int(os.getenv("MYSQLPORT", 15691)),
    "ssl_disabled": False,
}


def init_db():
    """Create tables if they don't exist. Runs once at startup, not per request."""
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    # Existing menu table — preserve existing menu data
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        category VARCHAR(100),
        description TEXT,
        price DECIMAL(10,2),
        image VARCHAR(255)
    )''')

    # DEBASA QR: Restaurant menu access control
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS debasa_qr_settings (
            id INT PRIMARY KEY,
            restaurant_name VARCHAR(255) NOT NULL,
            menu_enabled BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)

    cursor.execute("""
        INSERT IGNORE INTO debasa_qr_settings
            (id, restaurant_name, menu_enabled)
        VALUES (1, 'Magic Mandi and Grill Hotel', TRUE)
    """)

    # DEBASA QR: Hotel subscription records
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debasa_subscription (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            monthly_fee DECIMAL(10,2) NOT NULL DEFAULT 1000.00,
            start_date DATE NOT NULL,
            expiry_date DATE NOT NULL,
            grace_days INT NOT NULL DEFAULT 7,
            status VARCHAR(30) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
        )
    ''')

    # DEBASA QR: Subscription payment history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debasa_subscription_payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subscription_id INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_date DATE NOT NULL,
            payment_reference VARCHAR(150) NOT NULL,
            confirmed_by VARCHAR(100) NOT NULL DEFAULT 'admin',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT fk_debasa_subscription_payment
                FOREIGN KEY (subscription_id)
                REFERENCES debasa_subscription(id)
                ON DELETE RESTRICT,

            UNIQUE KEY unique_payment_reference (payment_reference)
        )
    ''')

    db.commit()
    cursor.close()
    db.close()


init_db()

# Connection pool instead of opening/closing a fresh MySQL connection on
# every single request.
db_pool = pooling.MySQLConnectionPool(
    pool_name="magic_mandi_pool",
    pool_size=5,
    **DB_CONFIG
)


def get_db():
    if 'db' not in g:
        g.db = db_pool.get_connection()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()


# ---------------------------------------------------------------------------
# Auth decorators — replace the repeated "if not session.get(...)" checks
# that were copy-pasted at the top of every protected route.
# ---------------------------------------------------------------------------
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return view(*args, **kwargs)
    return wrapped


def debasa_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('debasa_admin_logged_in'):
            return redirect(url_for('debasa_admin_login'))
        return view(*args, **kwargs)
    return wrapped


@app.route('/')
def index():
    table = request.args.get("table")

    try:
        database = get_db()
        cursor = database.cursor(dictionary=True)

        cursor.execute("""
            SELECT restaurant_name, menu_enabled
            FROM debasa_qr_settings
            WHERE id = 1
        """)

        settings = cursor.fetchone()
        cursor.close()

        if settings and not settings["menu_enabled"]:
            return render_template(
                "menu_unavailable.html",
                restaurant_name=settings["restaurant_name"]
            )

    except Exception:
        app.logger.exception("MENU ACCESS CHECK FAILED")
        return "Menu temporarily unavailable. Please try again later.", 503

    current_time = time.time()

    if (
        MENU_CACHE["data"] is not None
        and current_time - MENU_CACHE["timestamp"] < CACHE_DURATION
    ):
        menu = MENU_CACHE["data"]

    else:
        try:
            database = get_db()
            cursor = database.cursor(dictionary=True)

            cursor.execute("""
                SELECT id, name, category, description, price, image
                FROM menu
            """)

            menu = cursor.fetchall()
            cursor.close()

        except Exception:
            app.logger.exception("DATABASE ERROR IN INDEX ROUTE")
            menu = []

        MENU_CACHE["data"] = menu
        MENU_CACHE["timestamp"] = current_time

    return render_template("index.html", menu=menu, table=table)


@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def admin_login():
    error = None
    if request.method == 'POST':
        entered_password = request.form.get('password', '').strip()
        if check_password_hash(ADMIN_PASSWORD_HASH, entered_password):
            session.clear()
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Incorrect password. Please try again.'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route("/debasa-admin/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def debasa_admin_login():
    error = None

    if request.method == "POST":
        entered_password = request.form.get("password", "").strip()

        if check_password_hash(DEBASA_ADMIN_PASSWORD_HASH, entered_password):
            session.clear()
            session["debasa_admin_logged_in"] = True
            return redirect(url_for("debasa_subscription"))

        error = "Incorrect DEBASA admin password. Please try again."

    return render_template("debasa_admin_login.html", error=error)


@app.route("/debasa-admin/logout")
def debasa_admin_logout():
    session.pop("debasa_admin_logged_in", None)
    return redirect(url_for("debasa_admin_login"))


@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html")


@app.route("/debasa-admin/subscriptions")
@debasa_admin_required
def debasa_subscription():
    subscriptions = []
    total_subscriptions = 0
    active_subscriptions = 0
    renewals_due = 0
    database_error = False

    today = date.today()
    renewal_cutoff = today + timedelta(days=7)

    cursor = None

    try:
        database = get_db()
        cursor = database.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                customer_name,
                monthly_fee,
                start_date,
                expiry_date,
                grace_days,
                status,
                created_at
            FROM debasa_subscription
            ORDER BY expiry_date ASC, id DESC
        """)

        rows = cursor.fetchall()

        for item in rows:
            start_date = item["start_date"]
            expiry_date = item["expiry_date"]
            grace_days = int(item.get("grace_days") or 0)
            grace_end_date = expiry_date + timedelta(days=grace_days)

            subscription_status = (item.get("status") or "pending").lower()

            if subscription_status == "pending":
                display_status = "pending"
            elif subscription_status != "active":
                display_status = subscription_status
            elif today < start_date:
                display_status = "upcoming"
            elif today > grace_end_date:
                display_status = "expired"
            elif today > expiry_date:
                display_status = "grace_period"
            elif expiry_date <= renewal_cutoff:
                display_status = "expiring_soon"
            else:
                display_status = "active"

            item["display_status"] = display_status
            subscriptions.append(item)

            if display_status == "active":
                active_subscriptions += 1

            if display_status in ("expiring_soon", "grace_period"):
                renewals_due += 1

        total_subscriptions = len(subscriptions)

    except Exception:
        app.logger.exception("DEBASA SUBSCRIPTION DASHBOARD ERROR")
        database_error = True

    finally:
        if cursor is not None:
            cursor.close()

    menu_enabled = True
    restaurant_name = "Magic Mandi and Grill Hotel"

    try:
        settings_cursor = get_db().cursor(dictionary=True)
        settings_cursor.execute("""
            SELECT restaurant_name, menu_enabled
            FROM debasa_qr_settings
            WHERE id = 1
        """)
        menu_settings = settings_cursor.fetchone()
        settings_cursor.close()

        if menu_settings:
            menu_enabled = bool(menu_settings["menu_enabled"])
            restaurant_name = menu_settings["restaurant_name"]

    except Exception:
        app.logger.exception("Unable to load restaurant menu status")

    return render_template(
        "subscription.html",
        subscriptions=subscriptions,
        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions,
        renewals_due=renewals_due,
        database_error=database_error,
        menu_enabled=menu_enabled,
        restaurant_name=restaurant_name
    )


@app.route("/debasa-admin/menu-control", methods=["POST"])
@debasa_admin_required
def toggle_debasa_menu():
    database = get_db()
    cursor = database.cursor()

    try:
        cursor.execute("""
            SELECT menu_enabled
            FROM debasa_qr_settings
            WHERE id = 1
        """)

        settings = cursor.fetchone()

        if settings is None:
            return "Restaurant settings not found.", 404

        new_status = not bool(settings[0])

        cursor.execute("""
            UPDATE debasa_qr_settings
            SET menu_enabled = %s
            WHERE id = 1
        """, (new_status,))

        database.commit()

    except Exception:
        database.rollback()
        app.logger.exception("Menu control update failed")
        return "Unable to update menu status.", 500

    finally:
        cursor.close()

    return redirect(url_for("debasa_subscription"))


@app.route(
    "/debasa-admin/subscriptions/<int:subscription_id>/activate",
    methods=["POST"]
)
@debasa_admin_required
def activate_debasa_subscription(subscription_id):
    database = get_db()
    cursor = database.cursor()

    try:
        # Activate only a subscription that is currently pending.
        cursor.execute(
            """
            UPDATE debasa_subscription
            SET status = 'active'
            WHERE id = %s
              AND status = 'pending'
            """,
            (subscription_id,)
        )

        if cursor.rowcount == 0:
            database.rollback()
            return (
                "Subscription not found or is not pending. "
                "Refresh the dashboard and try again."
            ), 400

        database.commit()

    except Exception:
        database.rollback()
        app.logger.exception("Subscription activation failed")
        return "Unable to activate the subscription.", 500

    finally:
        cursor.close()

    return redirect(url_for("debasa_subscription"))


@app.route(
    "/debasa-admin/subscriptions/<int:subscription_id>/renew",
    methods=["GET", "POST"]
)
@debasa_admin_required
def renew_debasa_subscription(subscription_id):
    cursor = None

    try:
        database = get_db()
        cursor = database.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, customer_name, expiry_date
            FROM debasa_subscription
            WHERE id = %s
            """,
            (subscription_id,)
        )

        subscription = cursor.fetchone()

        if subscription is None:
            return "Subscription not found.", 404

        error = None

        if request.method == "POST":
            try:
                months = int(request.form.get("months", ""))

                if months not in (1, 3, 6, 12):
                    raise ValueError

            except (ValueError, TypeError):
                error = "Please select a valid renewal period."

            if error is None:
                current_expiry = subscription["expiry_date"]
                today = date.today()

                # Preserve any remaining subscription time.
                renewal_start = max(today, current_expiry)

                month_index = renewal_start.month - 1 + months
                new_year = renewal_start.year + month_index // 12
                new_month = month_index % 12 + 1

                last_day = calendar.monthrange(new_year, new_month)[1]
                new_day = min(renewal_start.day, last_day)

                new_expiry = date(new_year, new_month, new_day)

                cursor.execute(
                    """
                    UPDATE debasa_subscription
                    SET expiry_date = %s
                    WHERE id = %s
                    """,
                    (new_expiry, subscription_id)
                )

                database.commit()

                return redirect(url_for("debasa_subscription"))

        return render_template(
            "subscription_renew.html",
            subscription=subscription,
            error=error
        )

    except Exception:
        if 'database' in locals():
            database.rollback()

        app.logger.exception("DEBASA SUBSCRIPTION RENEWAL ERROR")

        return (
            "Unable to process the renewal. Check the server logs for details."
        ), 500

    finally:
        if cursor:
            cursor.close()


@app.route("/debasa-admin/subscriptions/new", methods=["GET", "POST"])
@debasa_admin_required
def create_debasa_subscription():
    error = None

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        start_date_text = request.form.get("start_date", "").strip()
        expiry_date_text = request.form.get("expiry_date", "").strip()

        try:
            monthly_fee = Decimal(request.form.get("monthly_fee", ""))
            grace_days = int(request.form.get("grace_days", "7"))

            start_date = date.fromisoformat(start_date_text)
            expiry_date = date.fromisoformat(expiry_date_text)

            if not customer_name:
                raise ValueError("Enter a hotel or restaurant name.")

            if not monthly_fee.is_finite() or monthly_fee <= 0:
                raise ValueError("Monthly fee must be greater than zero.")

            if monthly_fee > Decimal("99999999.99"):
                raise ValueError("Monthly fee is too high.")

            if not 0 <= grace_days <= 90:
                raise ValueError("Grace period must be between 0 and 90 days.")

            if expiry_date <= start_date:
                raise ValueError("Expiry date must be after start date.")

            database = get_db()
            cursor = database.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO debasa_subscription
                    (
                        customer_name,
                        monthly_fee,
                        start_date,
                        expiry_date,
                        grace_days,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        customer_name,
                        monthly_fee,
                        start_date,
                        expiry_date,
                        grace_days,
                        "pending"
                    )
                )

                database.commit()

            except Exception:
                database.rollback()
                raise

            finally:
                cursor.close()

            return redirect(url_for("debasa_subscription"))

        except (ValueError, InvalidOperation):
            error = (
                "Please check the hotel name, monthly fee, dates, "
                "and grace period. The expiry date must be after "
                "the start date."
            )

        except Exception:
            app.logger.exception("DEBASA SUBSCRIPTION CREATE ERROR")
            error = (
                "Unable to save the subscription. Check the database "
                "connection and confirm the subscription tables exist."
            )

    return render_template("subscription_form.html", error=error)


@app.route(
    "/debasa-admin/subscriptions/<int:subscription_id>/edit",
    methods=["GET", "POST"]
)
@debasa_admin_required
def edit_debasa_subscription(subscription_id):
    cursor = None
    error = None

    try:
        database = get_db()
        cursor = database.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, customer_name, monthly_fee, start_date,
                   expiry_date, grace_days
            FROM debasa_subscription
            WHERE id = %s
            """,
            (subscription_id,)
        )
        subscription = cursor.fetchone()

        if not subscription:
            return "Subscription not found.", 404

        if request.method == "POST":
            customer_name = request.form.get("customer_name", "").strip()

            try:
                monthly_fee = Decimal(request.form.get("monthly_fee", ""))
                grace_days = int(request.form.get("grace_days", "7"))
                start_date = date.fromisoformat(request.form.get("start_date", ""))
                expiry_date = date.fromisoformat(request.form.get("expiry_date", ""))

                if not customer_name:
                    raise ValueError("Enter a hotel or restaurant name.")

                if not monthly_fee.is_finite() or monthly_fee <= 0:
                    raise ValueError("Monthly fee must be greater than zero.")

                if monthly_fee > Decimal("99999999.99"):
                    raise ValueError("Monthly fee is too high.")

                if not 0 <= grace_days <= 90:
                    raise ValueError("Grace period must be between 0 and 90 days.")

                if expiry_date <= start_date:
                    raise ValueError("Expiry date must be after start date.")

            except (ValueError, InvalidOperation):
                error = (
                    "Check the hotel name, monthly fee, dates, "
                    "and grace period. Expiry must be after start."
                )

            if not error:
                cursor.execute(
                    """
                    UPDATE debasa_subscription
                    SET customer_name = %s,
                        monthly_fee = %s,
                        start_date = %s,
                        expiry_date = %s,
                        grace_days = %s
                    WHERE id = %s
                    """,
                    (
                        customer_name,
                        monthly_fee,
                        start_date,
                        expiry_date,
                        grace_days,
                        subscription_id
                    )
                )

                database.commit()
                return redirect(url_for("debasa_subscription"))

        return render_template(
            "subscription_edit.html",
            subscription=subscription,
            error=error
        )

    except Exception:
        if 'database' in locals():
            database.rollback()

        app.logger.exception("DEBASA SUBSCRIPTION EDIT ERROR")
        return (
            "Unable to process the subscription. Check the server logs for details."
        ), 500

    finally:
        if cursor:
            cursor.close()


@app.route(
    "/debasa-admin/subscriptions/<int:subscription_id>/delete",
    methods=["POST"]
)
@debasa_admin_required
def delete_debasa_subscription(subscription_id):
    database = get_db()
    cursor = database.cursor()

    try:
        cursor.execute(
            "SELECT id FROM debasa_subscription WHERE id = %s",
            (subscription_id,)
        )

        if cursor.fetchone() is None:
            return "Subscription not found.", 404

        cursor.execute(
            "DELETE FROM debasa_subscription WHERE id = %s",
            (subscription_id,)
        )

        database.commit()

    except Exception:
        database.rollback()
        app.logger.exception("Subscription deletion failed")
        return "Unable to delete this subscription.", 500

    finally:
        cursor.close()

    return redirect(url_for("debasa_subscription"))


def restaurant_menu_is_enabled():
    database = get_db()
    cursor = database.cursor()

    try:
        cursor.execute("""
            SELECT menu_enabled
            FROM debasa_qr_settings
            WHERE id = 1
        """)
        settings = cursor.fetchone()

        return settings is not None and bool(settings[0])

    finally:
        cursor.close()


@app.route("/manage_menu")
@admin_required
def manage_menu():
    database = get_db()
    cursor = database.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT menu_enabled
            FROM debasa_qr_settings
            WHERE id = 1
        """)
        settings = cursor.fetchone()

        if not settings or not settings["menu_enabled"]:
            return (
                "YOUR SUBSCRIPTION HAS EXPIRED. RENEW TO ENABLE MENU MANAGEMENT. "
                " MENU IS DISABLED<S. "
                "Contact DEBASA."
                "<strong>PAY YOUR SUBSCRIPTION FEE OF 1000.00 THROUGH  BANK AC:0100017448007.</strong>"
            ), 403
    finally:
        cursor.close()

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
    except Exception:
        app.logger.exception("DATABASE ERROR IN MANAGE_MENU")
        menu = [
            {'id': 1, 'name': 'Grilled Chicken', 'category': 'Main Meal', 'price': 700.00},
            {'id': 2, 'name': 'Cheese Pizza', 'category': 'Fast Food', 'price': 900.00},
            {'id': 3, 'name': 'Fresh Juice', 'category': 'Drinks', 'price': 250.00}
        ]

    return render_template("manage_menu.html", menu=menu)


@app.route("/add_menu", methods=["GET", "POST"])
@admin_required
def add_menu():
    if not restaurant_menu_is_enabled():
        return "Menu management is temporarily disabled.", 403

    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        image = request.form.get("image", "").strip()

        try:
            price = Decimal(request.form.get("price", ""))
            if not price.is_finite() or price <= 0:
                raise ValueError
            if not name or not category:
                raise ValueError
        except (InvalidOperation, ValueError):
            error = "Enter a name, category, and a price greater than zero."

        if not error:
            database = get_db()
            cursor = database.cursor()
            cursor.execute("""
                INSERT INTO menu (name, category, description, price, image)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, category, description, price, image))
            database.commit()
            cursor.close()

            MENU_CACHE["data"] = None
            return redirect(url_for("manage_menu"))

    return render_template("add_menu.html", error=error)


@app.route("/edit_menu/<int:item_id>", methods=["GET", "POST"])
@admin_required
def edit_menu(item_id):
    if not restaurant_menu_is_enabled():
        return "Menu management is temporarily disabled.", 403

    database = get_db()
    cursor = database.cursor(dictionary=True)
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        try:
            price = Decimal(request.form.get("price", ""))
            if not price.is_finite() or price <= 0 or not name:
                raise ValueError
        except (InvalidOperation, ValueError):
            error = "Enter a name and a price greater than zero."

        if not error:
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

    return render_template("edit_menu.html", item=item, error=error)


@app.route("/delete_menu/<int:item_id>", methods=["POST"])
@admin_required
def delete_menu(item_id):
    if not restaurant_menu_is_enabled():
        return "Menu management is temporarily disabled.", 403

    try:
        database = get_db()
        cursor = database.cursor()
        cursor.execute("DELETE FROM menu WHERE id=%s", (item_id,))
        database.commit()
        cursor.close()
        MENU_CACHE["data"] = None
    except Exception:
        app.logger.exception("DELETE MENU ITEM FAILED")

    return redirect(url_for("manage_menu"))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)