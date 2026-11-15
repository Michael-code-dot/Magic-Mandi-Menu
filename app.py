import os
import re
import io
import csv
import json
import gzip
import base64
import time
import atexit
import secrets
import threading
import calendar
from functools import wraps, lru_cache
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask, render_template, request, redirect, g, session, url_for,
    make_response, Response, jsonify
)
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
import mysql.connector
from mysql.connector import pooling

app = Flask(__name__)
# Live template reloading only on your own computer (Render sets RENDER=true).
app.config["TEMPLATES_AUTO_RELOAD"] = os.getenv("RENDER") is None
app.config["MAX_CONTENT_LENGTH"] = 14 * 1024 * 1024     # reject uploads bigger than this
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

# ---------------------------------------------------------------------------
# Caches. Most scans are served straight from memory and never touch the
# database. Run gunicorn with ONE worker (several threads) so these caches
# are shared by every request and disabling the menu takes effect instantly.
# ---------------------------------------------------------------------------
MENU_CACHE = {"data": None, "timestamp": 0}
CACHE_DURATION = 60

SETTINGS_CACHE = {"data": None, "timestamp": 0}
SETTINGS_CACHE_SECONDS = 10

PAGE_CACHE = {}            # table key -> (timestamp, finished html)
PAGE_CACHE_SECONDS = 30
PAGE_CACHE_MAX = 200
CACHE_LOCK = threading.Lock()


def invalidate_caches():
    """Call after any change to the menu or to the menu on/off switch."""
    MENU_CACHE["data"] = None
    SETTINGS_CACHE["data"] = None
    PAGE_CACHE.clear()

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

    # DEBASA QR: anonymous QR-scan log (no names, phone numbers or IPs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_scans (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            scanned_at DATETIME NOT NULL,
            table_no VARCHAR(10) NULL,
            visitor_id CHAR(16) NOT NULL,
            is_new TINYINT(1) NOT NULL DEFAULT 1,
            device VARCHAR(20) NULL,
            os VARCHAR(20) NULL,
            browser VARCHAR(20) NULL,
            INDEX idx_scanned_at (scanned_at),
            INDEX idx_visitor (visitor_id)
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
    pool_size=10,
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
# Scan analytics. Each visit is put in a small in-memory buffer (no database
# work during the request) and written to MySQL in one batch every 15 seconds.
# Nothing personal is stored: no names, no phone numbers, no IP addresses --
# only the time, table number, device type and a random anonymous visitor id
# kept in a cookie.
#
# Only scans that come from a table QR code (the link has ?table=N) are
# recorded. Opening the plain menu link -- for example you testing on your
# own laptop or phone -- is NOT counted.
# ---------------------------------------------------------------------------
KENYA_TZ = timezone(timedelta(hours=3))      # East Africa Time, no daylight saving


def now_local():
    return datetime.now(KENYA_TZ).replace(tzinfo=None)


BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|uptime|monitor|curl|wget|python-requests|"
    r"httpclient|headless|facebookexternalhit|lighthouse",
    re.I,
)

SCAN_BUFFER = []
SCAN_BUFFER_MAX = 5000
SCAN_LOCK = threading.Lock()
LAST_SEEN = {}
SCAN_DEDUPE_SECONDS = 1800    # the same phone refreshing within 30 min = one scan


def parse_user_agent(ua):
    if re.search(r"iPad|Tablet", ua) or (
        "Android" in ua and "Mobi" not in ua
    ):
        device = "Tablet"
    elif re.search(r"Mobi|iPhone|iPod|Android", ua):
        device = "Mobile"
    else:
        device = "Desktop"

    if re.search(r"iPhone|iPad|iPod", ua):
        os_name = "iOS"
    elif "Android" in ua:
        os_name = "Android"
    elif "Windows" in ua:
        os_name = "Windows"
    elif re.search(r"Macintosh|Mac OS X", ua):
        os_name = "macOS"
    elif "CrOS" in ua:
        os_name = "ChromeOS"
    elif "Linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Other"

    if "Instagram" in ua:
        browser = "Instagram"
    elif re.search(r"FBAN|FBAV", ua):
        browser = "Facebook"
    elif re.search(r"musical_ly|Bytedance|TikTok", ua):
        browser = "TikTok"
    elif "SamsungBrowser" in ua:
        browser = "Samsung"
    elif re.search(r"EdgA|Edg/|EdgiOS", ua):
        browser = "Edge"
    elif re.search(r"OPR/|Opera", ua):
        browser = "Opera"
    elif re.search(r"Firefox|FxiOS", ua):
        browser = "Firefox"
    elif re.search(r"CriOS|Chrome", ua):
        browser = "Chrome"
    elif "Safari" in ua:
        browser = "Safari"
    else:
        browser = "Other"

    return device, os_name, browser


def get_visitor():
    vid = request.cookies.get("mm_vid", "")
    if re.fullmatch(r"[0-9a-f]{16}", vid):
        return vid, False
    return secrets.token_hex(8), True


def track_scan(table, vid, is_new):
    try:
        ua = request.headers.get("User-Agent", "")
        if not ua or BOT_RE.search(ua):
            return

        # not a real guest view: browser prefetch, HEAD checks, or the owner logged in
        if request.method != "GET" or session.get("debasa_admin_logged_in"):
            return
        purpose = (request.headers.get("Sec-Purpose", "") + request.headers.get("Purpose", "")
                   + request.headers.get("X-Moz", "")).lower()
        if "prefetch" in purpose or "prerender" in purpose:
            return

        table_no = table if (table and table.isalnum() and len(table) <= 10) else None

        # Only real table-QR scans count. The plain menu link (no ?table=N) is
        # what you open when testing on your own laptop/phone, so it is ignored.
        if table_no is None:
            return

        now = time.time()
        key = (vid, table_no)

        with SCAN_LOCK:
            last = LAST_SEEN.get(key)
            if last and now - last < SCAN_DEDUPE_SECONDS:
                return
            LAST_SEEN[key] = now

            if len(LAST_SEEN) > 5000:
                cutoff = now - SCAN_DEDUPE_SECONDS
                for k in [k for k, v in LAST_SEEN.items() if v < cutoff]:
                    del LAST_SEEN[k]
                if len(LAST_SEEN) > 20000:
                    LAST_SEEN.clear()

            if len(SCAN_BUFFER) < SCAN_BUFFER_MAX:
                device, os_name, browser = parse_user_agent(ua)
                SCAN_BUFFER.append(
                    (now_local(), table_no, vid, 1 if is_new else 0,
                     device, os_name, browser)
                )
    except Exception:
        app.logger.exception("SCAN TRACKING FAILED")


def flush_scans():
    with SCAN_LOCK:
        rows = SCAN_BUFFER[:]
        del SCAN_BUFFER[:]

    if not rows:
        return

    conn = None
    try:
        conn = db_pool.get_connection()
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO menu_scans
                (scanned_at, table_no, visitor_id, is_new, device, os, browser)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )
        conn.commit()
        cur.close()
    except Exception:
        app.logger.exception("SCAN FLUSH FAILED")
        with SCAN_LOCK:
            SCAN_BUFFER[:0] = rows[:SCAN_BUFFER_MAX]
    finally:
        if conn is not None:
            conn.close()


def _flush_loop():
    while True:
        time.sleep(15)
        try:
            flush_scans()
        except Exception:
            app.logger.exception("SCAN FLUSH LOOP ERROR")


def seed_last_seen():
    """After a restart, remember who scanned in the last 30 minutes so the
    same phone is not counted twice just because the server restarted."""
    conn = None
    try:
        conn = db_pool.get_connection()
        cur = conn.cursor()
        now_dt = now_local()
        cur.execute(
            "SELECT visitor_id, table_no, MAX(scanned_at) FROM menu_scans "
            "WHERE scanned_at >= %s GROUP BY visitor_id, table_no",
            (now_dt - timedelta(seconds=SCAN_DEDUPE_SECONDS),),
        )
        t_now = time.time()
        with SCAN_LOCK:
            for vid_, tbl_, seen_ in cur.fetchall():
                LAST_SEEN[(vid_, tbl_ or "")] = t_now - (now_dt - seen_).total_seconds()
        cur.close()
    except Exception:
        app.logger.exception("SCAN SEED FAILED")
    finally:
        if conn is not None:
            conn.close()


seed_last_seen()
threading.Thread(target=_flush_loop, daemon=True).start()
atexit.register(flush_scans)


# Friendly anonymous names, so you can recognise a returning guest at a glance
# ("Golden Falcon #7F") without storing anything personal.
_ADJ = ["Golden", "Silver", "Crimson", "Amber", "Jade", "Royal", "Swift", "Brave",
        "Sunny", "Misty", "Cosmic", "Velvet", "Coral", "Ivory", "Ember", "Azure",
        "Lucky", "Noble", "Gentle", "Bright", "Wild", "Calm", "Bold", "Spicy"]
_ANIMAL = ["Falcon", "Lion", "Leopard", "Zebra", "Eagle", "Gazelle", "Cheetah", "Giraffe",
           "Rhino", "Flamingo", "Hippo", "Antelope", "Heron", "Panther", "Ibis", "Oryx",
           "Buffalo", "Hawk", "Crane", "Jackal", "Meerkat", "Parrot", "Lynx", "Tortoise"]


GUEST_NUM = {}


def refresh_guest_numbers():
    """Guest 1 is the first phone ever recorded, Guest 2 the next, and so on."""
    try:
        cur = get_db().cursor()
        try:
            cur.execute("SELECT visitor_id FROM menu_scans GROUP BY visitor_id ORDER BY MIN(id)")
            GUEST_NUM.clear()
            for i, (v,) in enumerate(cur.fetchall(), 1):
                GUEST_NUM[v] = i
        finally:
            cur.close()
    except Exception:
        app.logger.exception("GUEST NUMBERS FAILED")


def guest_name(vid):
    n = GUEST_NUM.get(vid)
    if n is None:
        try:
            n = int(vid[:4], 16) % 900 + 100
        except Exception:
            return "Guest"
    return f"Guest {n}"


@lru_cache(maxsize=32)
def gzip_html(html):
    """Compress a page once; the cached page is the same string every time."""
    return gzip.compress(html.encode("utf-8"), compresslevel=6)


# ---------------------------------------------------------------------------
# Payment page shown to the HOTEL STAFF (never to guests) whenever the menu is
# switched off. Your bank / M-Pesa details live in Render's Environment tab, not
# in the code, so they never end up in GitHub. All of these are optional:
#   PAY_BANK_NAME  PAY_BANK_BRANCH  PAY_BANK_ACCOUNT_NAME  PAY_BANK_ACCOUNT_NUMBER
#   PAY_BUSINESS_NUMBER   (defaults below are Stanbic Bank / 600100 / 0100017448007)
#   CONTACT_PHONE (defaults to 0759971119 if not set)
# ---------------------------------------------------------------------------
def render_payment_required():
    restaurant_name = "Your hotel"
    sub = None

    try:
        settings = get_menu_settings()
        if settings:
            restaurant_name = settings["restaurant_name"]

        cursor = get_db().cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT monthly_fee, expiry_date, grace_days, status
                FROM debasa_subscription
                ORDER BY expiry_date DESC, id DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
        finally:
            cursor.close()

        if row:
            expired = row["expiry_date"] < date.today()
            status = (row["status"] or "pending").lower()
            if status == "pending":
                label = "Awaiting payment"
            elif expired:
                label = "Expired"
            else:
                label = status.capitalize()
            sub = {
                "monthly_fee": row["monthly_fee"],
                "expiry_date": row["expiry_date"],
                "expired": expired,
                "status_label": label,
            }
    except Exception:
        app.logger.exception("PAYMENT PAGE DATA FAILED")

    env = os.getenv
    pay = {
        "bank_name": env("PAY_BANK_NAME", "Stanbic Bank").strip(),
        "bank_branch": env("PAY_BANK_BRANCH", "").strip(),
        "bank_account_name": env("PAY_BANK_ACCOUNT_NAME", "").strip(),
        "bank_number": env("PAY_BANK_ACCOUNT_NUMBER", "0100017448007").strip(),
        "business_number": env("PAY_BUSINESS_NUMBER", "600100").strip(),
    }
    contact_phone = env("CONTACT_PHONE", "0759971119").strip()

    return render_template(
        "subscription_required.html",
        restaurant_name=restaurant_name,
        sub=sub,
        pay=pay,
        contact_phone=contact_phone,
    ), 403


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


def get_menu_settings():
    now = time.time()
    if (
        SETTINGS_CACHE["data"] is not None
        and now - SETTINGS_CACHE["timestamp"] < SETTINGS_CACHE_SECONDS
    ):
        return SETTINGS_CACHE["data"]

    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT restaurant_name, menu_enabled
            FROM debasa_qr_settings
            WHERE id = 1
        """)
        settings = cursor.fetchone()
    finally:
        cursor.close()

    SETTINGS_CACHE["data"] = settings
    SETTINGS_CACHE["timestamp"] = now
    return settings


def get_menu():
    now = time.time()
    if (
        MENU_CACHE["data"] is not None
        and now - MENU_CACHE["timestamp"] < CACHE_DURATION
    ):
        return MENU_CACHE["data"]

    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, name, category, description, price, image
            FROM menu
        """)
        menu = cursor.fetchall()
    finally:
        cursor.close()

    MENU_CACHE["data"] = menu
    MENU_CACHE["timestamp"] = now
    return menu


@app.route("/health")
def health():
    # Lightweight, no database. Point an uptime monitor here (see notes).
    return "ok", 200


@app.route('/')
def index():
    table = request.args.get("table")
    vid, is_new = get_visitor()

    result = build_menu_page(table)

    # count it only when the real menu was shown (not the "menu off" page)
    if getattr(g, "menu_shown", False):
        track_scan(table, vid, is_new)

    if isinstance(result, str) and "gzip" in request.headers.get("Accept-Encoding", ""):
        response = make_response(gzip_html(result))
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    else:
        response = make_response(result)

    response.headers["Vary"] = "Accept-Encoding"

    if is_new:
        response.set_cookie(
            "mm_vid", vid, max_age=60 * 60 * 24 * 365,
            httponly=True, samesite="Lax", secure=request.is_secure
        )

    return response


def build_menu_page(table):
    # Only cache sane table values so nobody can fill the cache with junk.
    cacheable = table is None or (table.isalnum() and len(table) <= 6)
    key = table or ""

    if cacheable:
        hit = PAGE_CACHE.get(key)
        if hit and time.time() - hit[0] < PAGE_CACHE_SECONDS:
            g.menu_shown = True
            return hit[1]

    # One thread rebuilds the page; the others wait and then reuse it.
    with CACHE_LOCK:
        if cacheable:
            hit = PAGE_CACHE.get(key)
            if hit and time.time() - hit[0] < PAGE_CACHE_SECONDS:
                g.menu_shown = True
                return hit[1]

        try:
            settings = get_menu_settings()

            if settings and not settings["menu_enabled"]:
                return render_template(
                    "menu_unavailable.html",
                    restaurant_name=settings["restaurant_name"]
                )

            menu = get_menu()

        except Exception:
            app.logger.exception("MENU PAGE FAILED")
            return "Menu temporarily unavailable. Please try again later.", 503

        html = render_template("index.html", menu=menu, table=table)
        g.menu_shown = True

        if cacheable and len(PAGE_CACHE) < PAGE_CACHE_MAX:
            PAGE_CACHE[key] = (time.time(), html)

        return html


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
    if not restaurant_menu_is_enabled():
        return render_payment_required()
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
        invalidate_caches()

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


ANALYTICS_RANGES = {
    "today": "Today", "yesterday": "Yesterday", "7": "Last 7 days",
    "30": "Last 30 days", "month": "This month", "all": "All time",
}


def analytics_data(range_key="30", table_f=None, guest_f=None):
    """Everything the analytics page shows, computed from the menu_scans table."""
    if range_key not in ANALYTICS_RANGES:
        range_key = "30"
    flush_scans()                       # include scans still waiting in memory
    refresh_guest_numbers()

    now = now_local()
    d0 = datetime.combine(now.date(), datetime.min.time())
    yesterday0 = d0 - timedelta(days=1)
    week0 = d0 - timedelta(days=d0.weekday())          # this Monday
    month0 = d0.replace(day=1)
    year0 = d0.replace(month=1, day=1)
    last30 = d0 - timedelta(days=29)
    five_min = now - timedelta(minutes=5)
    one_hour = now - timedelta(hours=1)

    # the period used by the charts, the lists and the latest-scans table
    far_future = datetime(2100, 1, 1)
    if range_key == "today":
        r_from, r_to = d0, far_future
    elif range_key == "yesterday":
        r_from, r_to = yesterday0, d0
    elif range_key == "7":
        r_from, r_to = d0 - timedelta(days=6), far_future
    elif range_key == "month":
        r_from, r_to = month0, far_future
    elif range_key == "all":
        r_from, r_to = datetime(2000, 1, 1), far_future
    else:
        r_from, r_to = last30, far_future

    cur = get_db().cursor(dictionary=True)
    try:
        def one(sql, params=()):
            cur.execute(sql, params)
            return cur.fetchone() or {}

        def many(sql, params=()):
            cur.execute(sql, params)
            return cur.fetchall()

        def num(value):
            return int(value or 0)

        k = one(
            """
            SELECT COUNT(*) AS total,
                   COUNT(DISTINCT visitor_id) AS visitors,
                   SUM(scanned_at >= %s) AS today,
                   SUM(scanned_at >= %s AND scanned_at < %s) AS yesterday,
                   SUM(scanned_at >= %s) AS week,
                   SUM(scanned_at >= %s) AS month,
                   SUM(scanned_at >= %s) AS year,
                   SUM(scanned_at >= %s) AS last5,
                   SUM(scanned_at >= %s) AS last_hour,
                   SUM(is_new = 0) AS returning_scans,
                   SUM(scanned_at >= %s) AS last30
            FROM menu_scans
            """,
            (d0, yesterday0, d0, week0, month0, year0,
             five_min, one_hour, last30),
        )

        def uniq(since):
            r = one(
                "SELECT COUNT(DISTINCT visitor_id) AS c FROM menu_scans "
                "WHERE scanned_at >= %s", (since,)
            )
            return num(r.get("c"))

        total = num(k.get("total"))
        last30_total = num(k.get("last30"))

        # ---- trend series ------------------------------------------------
        def series(rows, keys, labels):
            by_key = {r["k"]: r for r in rows}
            return {
                "labels": labels,
                "scans": [num(by_key.get(x, {}).get("s")) for x in keys],
                "visitors": [num(by_key.get(x, {}).get("u")) for x in keys],
            }

        day_keys = [(last30 + timedelta(days=i)).date() for i in range(30)]
        day_rows = many(
            """
            SELECT DATE(scanned_at) AS k, COUNT(*) AS s,
                   COUNT(DISTINCT visitor_id) AS u
            FROM menu_scans WHERE scanned_at >= %s
            GROUP BY DATE(scanned_at)
            """, (last30,))
        days = series(day_rows, day_keys, [d.strftime("%d %b") for d in day_keys])

        week_keys = [(week0 + timedelta(weeks=i - 11)).date() for i in range(12)]
        week_rows = many(
            """
            SELECT DATE_SUB(DATE(scanned_at),
                            INTERVAL WEEKDAY(scanned_at) DAY) AS k,
                   COUNT(*) AS s, COUNT(DISTINCT visitor_id) AS u
            FROM menu_scans WHERE scanned_at >= %s
            GROUP BY k
            """, (week0 - timedelta(weeks=11),))
        weeks = series(week_rows, week_keys, [d.strftime("%d %b") for d in week_keys])

        month_keys = []
        y, m = now.year, now.month
        for _ in range(12):
            month_keys.append(y * 100 + m)
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        month_keys.reverse()
        first_month = date(month_keys[0] // 100, month_keys[0] % 100, 1)
        month_rows = many(
            """
            SELECT YEAR(scanned_at) * 100 + MONTH(scanned_at) AS k,
                   COUNT(*) AS s, COUNT(DISTINCT visitor_id) AS u
            FROM menu_scans WHERE scanned_at >= %s
            GROUP BY k
            """, (datetime.combine(first_month, datetime.min.time()),))
        months = series(
            month_rows, month_keys,
            [date(x // 100, x % 100, 1).strftime("%b %Y") for x in month_keys],
        )

        year_rows = many(
            """
            SELECT YEAR(scanned_at) AS k, COUNT(*) AS s,
                   COUNT(DISTINCT visitor_id) AS u
            FROM menu_scans GROUP BY YEAR(scanned_at)
            """)
        first_year = min([r["k"] for r in year_rows] + [now.year])
        year_keys = list(range(first_year, now.year + 1))
        years = series(year_rows, year_keys, [str(x) for x in year_keys])

        # ---- patterns (last 30 days) --------------------------------------
        hour_rows = {
            r["k"]: num(r["c"]) for r in many(
                "SELECT HOUR(scanned_at) AS k, COUNT(*) AS c FROM menu_scans "
                "WHERE scanned_at >= %s AND scanned_at < %s GROUP BY k", (r_from, r_to))
        }
        hours = [hour_rows.get(h, 0) for h in range(24)]

        wd_rows = {
            r["k"]: num(r["c"]) for r in many(
                "SELECT WEEKDAY(scanned_at) AS k, COUNT(*) AS c FROM menu_scans "
                "WHERE scanned_at >= %s AND scanned_at < %s GROUP BY k", (r_from, r_to))
        }
        weekdays = [wd_rows.get(i, 0) for i in range(7)]

        def breakdown(column):
            rows = many(
                f"SELECT COALESCE({column}, 'Unknown') AS k, COUNT(*) AS c "
                "FROM menu_scans WHERE scanned_at >= %s AND scanned_at < %s "
                "GROUP BY k ORDER BY c DESC LIMIT 8", (r_from, r_to))
            return {"labels": [r["k"] for r in rows],
                    "values": [num(r["c"]) for r in rows]}

        tables_rows = many(
            "SELECT table_no AS k, COUNT(*) AS c FROM menu_scans "
            "WHERE table_no IS NOT NULL AND scanned_at >= %s AND scanned_at < %s "
            "GROUP BY table_no ORDER BY c DESC LIMIT 15", (r_from, r_to))
        tables = {"labels": ["Table " + str(r["k"]) for r in tables_rows],
                  "values": [num(r["c"]) for r in tables_rows]}
        no_table = num(one(
            "SELECT COUNT(*) AS c FROM menu_scans "
            "WHERE table_no IS NULL AND scanned_at >= %s AND scanned_at < %s", (r_from, r_to)
        ).get("c"))

        best = one(
            "SELECT DATE(scanned_at) AS d, COUNT(*) AS c FROM menu_scans "
            "GROUP BY DATE(scanned_at) ORDER BY c DESC LIMIT 1")

        extra, extra_p = "", []
        if table_f:
            extra += " AND table_no = %s"; extra_p.append(table_f)
        if guest_f:
            extra += " AND visitor_id = %s"; extra_p.append(guest_f)

        recent_rows = many(
            "SELECT scanned_at, table_no, visitor_id, is_new, device, os, browser "
            "FROM menu_scans WHERE scanned_at >= %s AND scanned_at < %s" + extra +
            " ORDER BY id DESC LIMIT 100", tuple([r_from, r_to] + extra_p))

        guest_rows = many(
            "SELECT visitor_id, COUNT(*) AS scans, MIN(scanned_at) AS first_seen, "
            "MAX(scanned_at) AS last_seen, SUM(is_new = 0) AS back, "
            "GROUP_CONCAT(DISTINCT table_no ORDER BY table_no SEPARATOR ', ') AS tbls, "
            "MAX(device) AS device, MAX(os) AS os, MAX(browser) AS browser "
            "FROM menu_scans WHERE scanned_at >= %s AND scanned_at < %s "
            "GROUP BY visitor_id ORDER BY last_seen DESC LIMIT 40", (r_from, r_to))

        tstat_rows = many(
            "SELECT table_no, COUNT(*) AS scans, COUNT(DISTINCT visitor_id) AS guests, "
            "MAX(scanned_at) AS last_seen FROM menu_scans "
            "WHERE table_no IS NOT NULL AND scanned_at >= %s AND scanned_at < %s "
            "GROUP BY table_no ORDER BY scans DESC LIMIT 30", (r_from, r_to))
        thour_rows = many(
            "SELECT table_no, HOUR(scanned_at) AS h, COUNT(*) AS c FROM menu_scans "
            "WHERE table_no IS NOT NULL AND scanned_at >= %s AND scanned_at < %s "
            "GROUP BY table_no, h", (r_from, r_to))

        # these also need the cursor, so they must run before it is closed
        visitors_today = uniq(d0)
        visitors_week = uniq(week0)
        visitors_month = uniq(month0)
        devices = breakdown("device")
        systems = breakdown("os")
        browsers = breakdown("browser")
    finally:
        cur.close()

    peak_hour = None
    if any(hours):
        h = hours.index(max(hours))
        peak_hour = f"{h:02d}:00 - {(h + 1) % 24:02d}:00"

    best_hour = {}
    for r in thour_rows:
        t = r["table_no"]
        if t not in best_hour or r["c"] > best_hour[t][1]:
            best_hour[t] = (r["h"], r["c"])

    table_stats = [{
        "table": r["table_no"],
        "scans": num(r["scans"]),
        "guests": num(r["guests"]),
        "last": r["last_seen"].strftime("%d %b, %H:%M"),
        "busy": (f"{best_hour[r['table_no']][0]:02d}:00" if r["table_no"] in best_hour else "-"),
    } for r in tstat_rows]

    guests = [{
        "id": r["visitor_id"],
        "name": guest_name(r["visitor_id"]),
        "scans": num(r["scans"]),
        "first": r["first_seen"].strftime("%d %b, %H:%M"),
        "last": r["last_seen"].strftime("%d %b, %H:%M"),
        "returning": num(r["back"]) > 0,
        "tables": r["tbls"] or "-",
        "phone": " · ".join(x for x in (r["device"], r["os"], r["browser"]) if x) or "-",
    } for r in guest_rows]

    recent = [{
        "time": r["scanned_at"].strftime("%d %b, %H:%M"),
        "table": r["table_no"] or "-",
        "visitor": (r["visitor_id"] or "")[:6].upper(),
        "id": r["visitor_id"],
        "name": guest_name(r["visitor_id"]),
        "returning": not r["is_new"],
        "device": r["device"] or "-",
        "os": r["os"] or "-",
        "browser": r["browser"] or "-",
    } for r in recent_rows]

    return {
        "generated": now.strftime("%d %b %Y, %H:%M"),
        "table_stats": table_stats,
        "guests": guests,
        "filter_table": table_f,
        "filter_guest": guest_name(guest_f) if guest_f else None,
        "filter_guest_id": guest_f,
        "range": range_key,
        "range_label": ANALYTICS_RANGES[range_key],
        "ranges": ANALYTICS_RANGES,
        "kpi": {
            "total": total,
            "today": num(k.get("today")),
            "yesterday": num(k.get("yesterday")),
            "week": num(k.get("week")),
            "month": num(k.get("month")),
            "year": num(k.get("year")),
            "last5": num(k.get("last5")),
            "last_hour": num(k.get("last_hour")),
            "visitors_all": num(k.get("visitors")),
            "visitors_today": visitors_today,
            "visitors_week": visitors_week,
            "visitors_month": visitors_month,
            "returning_pct": round(100 * num(k.get("returning_scans")) / total) if total else 0,
            "avg_per_day": round(last30_total / 30, 1),
            "peak_hour": peak_hour or "-",
            "best_day": (
                f"{best['d'].strftime('%d %b %Y')} ({num(best['c'])})"
                if best else "-"
            ),
        },
        "trend": {"days": days, "weeks": weeks, "months": months, "years": years},
        "hours": hours,
        "weekdays": weekdays,
        "tables": tables,
        "no_table": no_table,
        "devices": devices,
        "systems": systems,
        "browsers": browsers,
        "recent": recent,
    }


@app.route("/debasa-admin/analytics")
@debasa_admin_required
def debasa_analytics():
    try:
        tf = request.args.get("table", "").strip()
        gf = request.args.get("guest", "").strip().lower()
        data = analytics_data(
            request.args.get("range", "30"),
            tf if (tf.isalnum() and len(tf) <= 10) else None,
            gf if re.fullmatch(r"[0-9a-f]{16}", gf) else None,
        )
    except Exception:
        app.logger.exception("ANALYTICS ERROR")
        return "Unable to load analytics. Check the server logs.", 500

    restaurant_name = "Magic Mandi and Grill Hotel"
    try:
        settings = get_menu_settings()
        if settings:
            restaurant_name = settings["restaurant_name"]
    except Exception:
        pass

    return render_template(
        "analytics.html", data=data, restaurant_name=restaurant_name
    )


@app.route("/debasa-admin/analytics.json")
@debasa_admin_required
def debasa_analytics_json():
    """Live numbers for the dashboard, so it can update without reloading."""
    try:
        tf = request.args.get("table", "").strip()
        gf = request.args.get("guest", "").strip().lower()
        data = analytics_data(
            request.args.get("range", "30"),
            tf if (tf.isalnum() and len(tf) <= 10) else None,
            gf if re.fullmatch(r"[0-9a-f]{16}", gf) else None,
        )
    except Exception:
        app.logger.exception("ANALYTICS JSON ERROR")
        return jsonify(error=True), 500

    response = jsonify(data)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/debasa-admin/analytics/reset", methods=["POST"])
@debasa_admin_required
def debasa_analytics_reset():
    """Wipe every recorded scan (after the owner types RESET)."""
    if request.form.get("confirm", "").strip().upper() != "RESET":
        return redirect(url_for("debasa_analytics", msg="noreset"))

    with SCAN_LOCK:
        del SCAN_BUFFER[:]
        LAST_SEEN.clear()

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM menu_scans")
        db.commit()
    finally:
        cur.close()
    return redirect(url_for("debasa_analytics", msg="reset"))


@app.route("/debasa-admin/analytics/clean-notable", methods=["POST"])
@debasa_admin_required
def debasa_analytics_clean_notable():
    """Remove old scans that have no table number (your own testing)."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM menu_scans WHERE table_no IS NULL")
        db.commit()
    finally:
        cur.close()
    return redirect(url_for("debasa_analytics", msg="cleaned"))


@app.route("/debasa-admin/analytics.csv")
@debasa_admin_required
def debasa_analytics_csv():
    flush_scans()
    refresh_guest_numbers()

    cur = get_db().cursor()
    try:
        cur.execute(
            "SELECT scanned_at, table_no, visitor_id, is_new, device, os, browser "
            "FROM menu_scans ORDER BY id DESC LIMIT 100000"
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["scanned_at", "table", "guest", "visitor_id", "new_visitor",
                     "device", "os", "browser"])
    for r in rows:
        writer.writerow([r[0], r[1] or "", guest_name(r[2]), r[2], "yes" if r[3] else "no",
                         r[4] or "", r[5] or "", r[6] or ""])

    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=menu-scans.csv"},
    )


# ---------------------------------------------------------------------------
# Owner tools: better dish descriptions, menu backup, printable table QR codes
# ---------------------------------------------------------------------------
from descriptions_data import DESCRIPTIONS

_GENERIC_DESC = re.compile(r"^\s*(delicious|tasty|freshly)\b.*\bfreshly prepared\.?\s*$", re.I)


def _desc_key(row):
    """The key used in descriptions_data.py: the photo file name, or the dish name."""
    img = (row.get("image") or "").strip().split("?")[0].rsplit("/", 1)[-1]
    stem = img.rsplit(".", 1)[0].lower() if img else ""
    name = re.sub(r"[^a-z0-9()]+", "_", (row.get("name") or "").lower()).strip("_")
    for k in (stem, name):
        if k and k in DESCRIPTIONS:
            return k
    return None


def _description_plan(replace_all=False):
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, description, image FROM menu ORDER BY category, name")
        rows = cur.fetchall()
    finally:
        cur.close()
    plan = []
    for r in rows:
        k = _desc_key(r)
        new = DESCRIPTIONS.get(k) if k else None
        old = (r["description"] or "").strip()
        generic = (not old) or bool(_GENERIC_DESC.match(old))
        plan.append({
            "id": r["id"], "name": r["name"], "old": old, "new": new,
            "apply": bool(new) and new != old and (generic or replace_all),
            "kept": bool(new) and new != old and not generic and not replace_all,
        })
    return plan


@app.route("/debasa-admin/descriptions", methods=["GET", "POST"])
@debasa_admin_required
def debasa_descriptions():
    replace_all = request.values.get("replace_all") == "1"
    plan = _description_plan(replace_all)

    if request.method == "POST":
        todo = [(x["new"], x["id"]) for x in plan if x["apply"]]
        if todo:
            db = get_db()
            cur = db.cursor()
            try:
                cur.executemany("UPDATE menu SET description=%s WHERE id=%s", todo)
                db.commit()
            finally:
                cur.close()
            invalidate_caches()
        return redirect(url_for("debasa_descriptions", done=len(todo)))

    return render_template(
        "descriptions.html", plan=plan, replace_all=replace_all,
        n_apply=sum(1 for x in plan if x["apply"]),
        n_kept=sum(1 for x in plan if x["kept"]),
        n_none=sum(1 for x in plan if not x["new"]),
        done=request.args.get("done"),
    )


@app.route("/debasa-admin/backup.csv")
@debasa_admin_required
def debasa_backup_csv():
    cur = get_db().cursor()
    try:
        cur.execute("SELECT id, name, category, description, price, image FROM menu ORDER BY id")
        rows = cur.fetchall()
    finally:
        cur.close()
    out = io.StringIO()
    out.write("\ufeff")                       # so Excel shows special characters correctly
    w = csv.writer(out)
    w.writerow(["id", "name", "category", "description", "price", "image"])
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    stamp = now_local().strftime("%Y-%m-%d")
    return Response(
        out.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=menu-backup-{stamp}.csv"},
    )


@app.route("/debasa-admin/qr")
@debasa_admin_required
def debasa_qr():
    name = "Magic Mandi and Grill Hotel"
    try:
        settings = get_menu_settings()
        if settings:
            name = settings["restaurant_name"]
    except Exception:
        pass
    return render_template("qr_tables.html", restaurant_name=name)


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
            return render_payment_required()
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


# ---------------------------------------------------------------------------
# GitHub photo picker. Add Menu / Edit Menu show the photos that are already in
# your GitHub "image" folder, so you pick one instead of typing its file name.
# The list is cached for 10 minutes (GitHub limits anonymous requests). The
# "Refresh" button in the picker forces a fresh list right after you upload.
# Optional: set GITHUB_TOKEN in Render to raise GitHub's limit (not required).
# ---------------------------------------------------------------------------
GITHUB_IMAGE_REPO = "Michael-code-dot/hotel-qr-redirect"
GITHUB_IMAGE_RAW = (
    f"https://raw.githubusercontent.com/{GITHUB_IMAGE_REPO}/refs/heads/main/image/"
)
PHOTO_LIST_CACHE = {"names": [], "timestamp": 0}
PHOTO_LIST_SECONDS = 600
PHOTO_LIST_LOCK = threading.Lock()


def github_photo_names():
    now = time.time()
    if (
        PHOTO_LIST_CACHE["names"]
        and now - PHOTO_LIST_CACHE["timestamp"] < PHOTO_LIST_SECONDS
    ):
        return PHOTO_LIST_CACHE["names"]

    with PHOTO_LIST_LOCK:
        now = time.time()
        if (
            PHOTO_LIST_CACHE["names"]
            and now - PHOTO_LIST_CACHE["timestamp"] < PHOTO_LIST_SECONDS
        ):
            return PHOTO_LIST_CACHE["names"]

        headers = {
            "User-Agent": "magic-mandi-menu",
            "Accept": "application/vnd.github+json",
        }
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = "Bearer " + token

        try:
            request_obj = Request(
                f"https://api.github.com/repos/{GITHUB_IMAGE_REPO}/contents/image",
                headers=headers,
            )
            with urlopen(request_obj, timeout=8) as response:
                items = json.load(response)

            PHOTO_LIST_CACHE["names"] = sorted(
                i["name"] for i in items
                if i.get("type") == "file"
                and i["name"].lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            )
            PHOTO_LIST_CACHE["timestamp"] = time.time()
        except Exception:
            app.logger.exception("GITHUB PHOTO LIST FAILED")
            # keep showing the last good list; try again in about a minute
            PHOTO_LIST_CACHE["timestamp"] = time.time() - PHOTO_LIST_SECONDS + 60

        return PHOTO_LIST_CACHE["names"]


@app.route("/admin/photos.json")
@admin_required
def admin_photo_list():
    if request.args.get("refresh"):
        PHOTO_LIST_CACHE["timestamp"] = 0
    return jsonify(names=github_photo_names(), base=GITHUB_IMAGE_RAW)


# ---------------------------------------------------------------------------
# Upload a photo straight to GitHub. In Add Menu / Edit Menu press "Upload new
# photo": the photo is shrunk (about 1000 px wide, under ~220 KB, still sharp)
# and saved into your GitHub image folder for you, so you no longer open GitHub.
# Needs GITHUB_TOKEN in Render (a fine-grained token limited to the photo repo
# with "Contents: Read and write"). Needs Pillow in requirements.txt.
# ---------------------------------------------------------------------------
class PhotoError(Exception):
    pass


def photo_upload_enabled():
    return bool(os.getenv("GITHUB_TOKEN", "").strip())


def photo_slug(text):
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:60] or "photo"


def prepare_photo(file_storage):
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise PhotoError(
            "Photo upload needs Pillow. Add the line  Pillow  to requirements.txt and redeploy."
        )

    Image.MAX_IMAGE_PIXELS = 60_000_000
    raw = file_storage.read()
    if not raw:
        raise PhotoError("No photo was received. Please choose a photo.")

    try:
        img = Image.open(io.BytesIO(raw))
        if img.format == "JPEG":
            img.draft("RGB", (2000, 2000))      # decode small: saves memory
        img.load()
    except Exception:
        raise PhotoError("That file is not a photo we can read. Use a JPG or PNG.")

    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    else:
        img = img.convert("RGB")

    img.thumbnail((1000, 1000), Image.LANCZOS)

    data = b""
    for size_limit in (1000, 900, 800):
        if max(img.size) > size_limit:
            img.thumbnail((size_limit, size_limit), Image.LANCZOS)
        for quality in (86, 82, 78, 74, 70, 65):
            out = io.BytesIO()
            img.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
            data = out.getvalue()
            if len(data) <= 220_000:
                return data
    return data


def github_save_photo(name, data):
    token = os.getenv("GITHUB_TOKEN", "").strip()
    body = json.dumps({
        "message": f"Add menu photo {name}",
        "content": base64.b64encode(data).decode("ascii"),
        "branch": "main",
    }).encode("utf-8")

    request_obj = Request(
        f"https://api.github.com/repos/{GITHUB_IMAGE_REPO}/contents/image/{quote(name)}",
        data=body,
        method="PUT",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "magic-mandi-menu",
        },
    )

    try:
        with urlopen(request_obj, timeout=30):
            pass
    except HTTPError as exc:
        app.logger.error("GITHUB UPLOAD HTTP %s: %s", exc.code, exc.read()[:300])
        if exc.code == 401:
            raise PhotoError("GitHub rejected the token. It may be wrong or expired. Make a new one and update GITHUB_TOKEN in Render.")
        if exc.code in (403, 404):
            raise PhotoError("GitHub says the token cannot write to the photo repository. It needs access to hotel-qr-redirect with Contents: Read and write.")
        if exc.code == 422:
            raise PhotoError("A photo with that name already exists. Try again.")
        raise PhotoError("GitHub could not save the photo. Please try again in a minute.")
    except Exception:
        app.logger.exception("GITHUB UPLOAD FAILED")
        raise PhotoError("Could not reach GitHub. Check your internet and try again.")


@app.route("/admin/upload-photo", methods=["POST"])
@admin_required
def admin_upload_photo():
    if not photo_upload_enabled():
        return jsonify(ok=False, error="Photo upload is not set up yet. Add GITHUB_TOKEN in Render."), 503
    if not restaurant_menu_is_enabled():
        return jsonify(ok=False, error="Menu management is paused. Please contact DEBASA Systems."), 403

    file = request.files.get("photo")
    if file is None or not file.filename:
        return jsonify(ok=False, error="Please choose a photo."), 400

    dish = request.form.get("dish", "").strip()
    stem = photo_slug(dish or os.path.splitext(file.filename)[0])

    try:
        data = prepare_photo(file)

        existing = {n.lower() for n in github_photo_names()}
        name = stem + ".jpg"
        counter = 2
        while name.lower() in existing:
            name = f"{stem}_{counter}.jpg"
            counter += 1

        github_save_photo(name, data)
    except PhotoError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    except Exception:
        app.logger.exception("PHOTO UPLOAD FAILED")
        return jsonify(ok=False, error="Something went wrong while saving the photo."), 500

    with PHOTO_LIST_LOCK:
        if name not in PHOTO_LIST_CACHE["names"]:
            PHOTO_LIST_CACHE["names"] = sorted(PHOTO_LIST_CACHE["names"] + [name])

    return jsonify(ok=True, name=name, kb=round(len(data) / 1024))


@app.errorhandler(413)
def upload_too_large(_error):
    if request.path == "/admin/upload-photo":
        return jsonify(ok=False, error="That photo is too big. Choose one under 14 MB."), 413
    return "That upload is too large.", 413


@app.route("/add_menu", methods=["GET", "POST"])
@admin_required
def add_menu():
    if not restaurant_menu_is_enabled():
        return render_payment_required()

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

            invalidate_caches()
            return redirect(url_for("manage_menu"))

    return render_template("add_menu.html", error=error, photo_base=GITHUB_IMAGE_RAW, upload_enabled=photo_upload_enabled())


@app.route("/edit_menu/<int:item_id>", methods=["GET", "POST"])
@admin_required
def edit_menu(item_id):
    if not restaurant_menu_is_enabled():
        return render_payment_required()

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
            # name and price always change; category, description and image only
            # when the form sends them (older forms that don't are left alone).
            fields = ["name=%s", "price=%s"]
            values = [name, price]
            for column in ("category", "description", "image"):
                value = request.form.get(column)
                if value is not None:
                    fields.append(column + "=%s")
                    values.append(value.strip())
            values.append(item_id)
            cursor.execute(
                "UPDATE menu SET " + ", ".join(fields) + " WHERE id=%s",
                tuple(values)
            )
            database.commit()
            cursor.close()

            invalidate_caches()
            return redirect(url_for("manage_menu"))

    cursor.execute("SELECT * FROM menu WHERE id=%s", (item_id,))
    item = cursor.fetchone()
    cursor.close()

    if not item:
        item = {'id': item_id, 'name': 'Sample Dish', 'price': 500.00}

    return render_template("edit_menu.html", item=item, error=error, photo_base=GITHUB_IMAGE_RAW, upload_enabled=photo_upload_enabled())


@app.route("/delete_menu/<int:item_id>", methods=["POST"])
@admin_required
def delete_menu(item_id):
    if not restaurant_menu_is_enabled():
        return render_payment_required()

    try:
        database = get_db()
        cursor = database.cursor()
        cursor.execute("DELETE FROM menu WHERE id=%s", (item_id,))
        database.commit()
        cursor.close()
        invalidate_caches()
    except Exception:
        app.logger.exception("DELETE MENU ITEM FAILED")

    return redirect(url_for("manage_menu"))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)