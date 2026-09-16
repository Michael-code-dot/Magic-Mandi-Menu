# Magic Mandi Menu (Hotel QR Menu)

Simple Flask-based menu and ordering system intended for QR-driven menus in restaurants/hotels. This repository contains a small Flask app (app.py) that serves menu pages, accepts orders, and provides waiter/kitchen/admin views.

This README provides a quickstart for local development, required environment variables, a brief description of the database schema, and recommended next steps.

---

## Quickstart (Windows)

1. Create and activate a virtual environment:

   python -m venv venv
   venv\Scripts\activate

2. Install dependencies:

   pip install -r requirements.txt

3. Set required environment variables (PowerShell example):

   $env:MYSQLHOST = "localhost"
   $env:MYSQLUSER = "root"
   $env:MYSQLPASSWORD = "your_mysql_password"
   $env:MYSQLDATABASE = "hotelqr"
   $env:MYSQLPORT = "3306"
   $env:PORT = "5000"
   # Optional: enable debug mode
   $env:FLASK_DEBUG = "1"

4. Run the app:

   python app.py

   Then open http://localhost:5000 in a browser.

Notes: In production, do not enable Flask debug mode and do not store credentials in environment variables in plaintext.

---

## Required environment variables

- MYSQLHOST (default: localhost)
- MYSQLUSER (default: root)
- MYSQLPASSWORD (no safe default — set this)
- MYSQLDATABASE (default: hotelqr)
- MYSQLPORT (default: 3306)
- PORT (default: 5000)
- FLASK_DEBUG (optional; set to "1" to enable)

Consider using a .env file locally with a tool like python-dotenv or a secrets manager in production.

---

## Expected Database Schema (high-level)

The app expects these tables (column names shown by usage in app.py):

- menu
  - id (PK)
  - name
  - category
  - description
  - price
  - image

- orders
  - id (PK)
  - customer_name
  - table_number
  - total
  - waiter_id (FK -> waiters.id)
  - status (e.g., Preparing, Completed, Printed)
  - created_at (timestamp)

- order_items
  - id (PK)
  - order_id (FK -> orders.id)
  - menu_name
  - quantity
  - price

- waiters
  - id (PK)
  - name

- table_assignments
  - id (PK)
  - table_number
  - waiter_id (FK -> waiters.id)

This README does not include CREATE TABLE SQL; add schema DDL appropriate to your MySQL server before running.

---

## Important notes and known issue

- There is a known syntax/connection problem in `connect_to_db()` inside `app.py` that will prevent the app from starting. The line that assigns the password is currently malformed.

  Recommended fix (example):

  Replace the broken line with:

  ```python
  password = os.getenv("MYSQLPASSWORD")
  ```

  or include a safe default only for local development. Prefer failing early if the password is not set in production.

- The app currently stores routing, DB access, and templates in a single `app.py` file. For maintainability consider splitting logic into modules/Blueprints and using an ORM or a DB abstraction layer.

- Admin and waiter pages are currently unprotected. Add authentication and CSRF protection before public or production deployment.

---

## Developer suggestions / next steps

- Fix the DB connection line in `app.py` so the app can start.
- Add a `.env.example` file showing required env vars and values used for local testing.
- Add a `README` section with database DDL or provide a `schema.sql` migration file.
- Add tests (pytest) and a CI workflow to run tests on PRs.
- Pin dependency versions in `requirements.txt` and consider adding a `constraints.txt` for reproducible installs.
- Add basic authentication for admin/waiter views and server-side validation for inputs.

---

## Contact / Attribution

Maintainer: repository owner

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
