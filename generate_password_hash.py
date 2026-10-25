"""
Generates a password hash for ADMIN_PASSWORD_HASH or DEBASA_ADMIN_PASSWORD_HASH.

app.py no longer stores or compares plaintext passwords — it checks a hash
instead. Run this once per password, then paste the output into your .env
file (or your host's environment variable settings).

Usage:
    python generate_password_hash.py
"""
import getpass
from werkzeug.security import generate_password_hash

password = getpass.getpass("Password to hash: ")
confirm = getpass.getpass("Confirm password: ")

if password != confirm:
    raise SystemExit("Passwords did not match. Nothing was generated.")

if len(password) < 8:
    print("Warning: that's a short password for an admin account.")

print("\nAdd this line to your .env file (replace the matching variable):\n")
print(generate_password_hash(password))
print()
