import os
import sqlite3
from werkzeug.security import generate_password_hash

# Same DB path as app.py, useful when deployed with a persistent disk later.
DB_PATH = os.getenv("DATABASE_PATH", "database.db")


def ensure_db_directory_exists(path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def is_password_hash(value: str) -> bool:
    return value.startswith("pbkdf2:") or value.startswith("scrypt:")


ensure_db_directory_exists(DB_PATH)

MENU_SEED = [
    ("Coffee", "Latte", 5.50, "Smooth espresso with steamed milk and a light foam finish.", "images/latte.jpg", "Vegetarian", 7, 30, 1),
    ("Coffee", "Cappuccino", 5.20, "Classic espresso topped with thick foam and cocoa dusting.", "images/cappucino.jpg", "Vegetarian", 7, 30, 1),
    ("Coffee", "Flat White", 5.30, "Rich espresso blended with velvety microfoam.", "images/flat_white.jpg", "Vegetarian", 6, 30, 1),
    ("Cold Drinks", "Iced Coffee", 6.00, "Chilled espresso over ice with milk and optional sweetness.", "images/ice-coffee.jpg", "Vegetarian", 8, 25, 1),
    ("Cold Drinks", "Iced Chocolate", 6.20, "Cold chocolate drink served over ice with creamy texture.", "images/ice-choclate.jpg", "Vegetarian", 6, 25, 1),
    ("Food", "Chicken Wrap", 9.50, "Grilled chicken, fresh salad and sauce wrapped for quick lunch.", "images/chicken_wrap.jpg", "Contains gluten", 12, 18, 1),
    ("Food", "Veggie Toastie", 8.50, "Toasted sandwich with vegetables, cheese and savoury filling.", "images/veggie-toastie.jpg", "Vegetarian, contains gluten", 10, 18, 1),
    ("Food", "Banana Bread", 4.80, "Moist banana bread slice, ideal with coffee.", "images/banana_bread.jpg", "Vegetarian", 4, 20, 1),
    ("Dessert", "Blueberry Muffin", 4.50, "Soft muffin with blueberry pieces and a lightly sweet finish.", "images/blueberry-muffin.jpg", "Vegetarian", 3, 20, 1),
    ("Dessert", "Chocolate Brownie", 5.00, "Dense chocolate brownie with a rich cocoa flavour.", "images/brownie.jpg", "Vegetarian", 3, 20, 1),
]

USER_SEED = [
    ("staff", generate_password_hash("staff123"), "Staff Member", "staff"),
    ("admin", generate_password_hash("admin123"), "Cafe Owner", "admin"),
]

PROMO_SEED = [
    ("WELCOME10", "Welcome 10% discount", 0.10, 1),
    ("STUDENT10", "Student 10% discount", 0.10, 1),
    ("COFFEE5", "Coffee lover 5% discount", 0.05, 1),
]


def column_names(conn, table_name):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def add_column_if_missing(conn, table, column, definition):
    if column not in column_names(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code TEXT UNIQUE,
    order_group TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL DEFAULT '',
    table_number TEXT NOT NULL DEFAULT 'Takeaway',
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    size_option TEXT NOT NULL DEFAULT 'Regular',
    milk_option TEXT NOT NULL DEFAULT 'Full Cream',
    extras TEXT NOT NULL DEFAULT '',
    modifiers_total REAL NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL DEFAULT 0,
    discount_amount REAL NOT NULL DEFAULT 0,
    service_fee REAL NOT NULL DEFAULT 0,
    gst_amount REAL NOT NULL DEFAULT 0,
    total_price REAL NOT NULL,
    notes TEXT,
    requested_time TEXT NOT NULL DEFAULT 'ASAP',
    promo_code TEXT NOT NULL DEFAULT '',
    payment_method TEXT NOT NULL DEFAULT 'Credit/Debit Card',
    payment_status TEXT NOT NULL DEFAULT 'Unpaid',
    payment_reference TEXT NOT NULL DEFAULT '',
    payment_provider TEXT NOT NULL DEFAULT '',
    payment_last4 TEXT NOT NULL DEFAULT '',
    payment_authorisation TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


add_column_if_missing(conn, "orders", "order_code", "TEXT")
add_column_if_missing(conn, "orders", "order_group", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "orders", "customer_phone", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "orders", "table_number", "TEXT NOT NULL DEFAULT 'Takeaway'")
add_column_if_missing(conn, "orders", "size_option", "TEXT NOT NULL DEFAULT 'Regular'")
add_column_if_missing(conn, "orders", "milk_option", "TEXT NOT NULL DEFAULT 'Full Cream'")
add_column_if_missing(conn, "orders", "extras", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "orders", "modifiers_total", "REAL NOT NULL DEFAULT 0")
add_column_if_missing(conn, "orders", "subtotal", "REAL NOT NULL DEFAULT 0")
add_column_if_missing(conn, "orders", "discount_amount", "REAL NOT NULL DEFAULT 0")
add_column_if_missing(conn, "orders", "service_fee", "REAL NOT NULL DEFAULT 0")
add_column_if_missing(conn, "orders", "gst_amount", "REAL NOT NULL DEFAULT 0")
add_column_if_missing(conn, "orders", "notes", "TEXT")
add_column_if_missing(conn, "orders", "requested_time", "TEXT NOT NULL DEFAULT 'ASAP'")
add_column_if_missing(conn, "orders", "promo_code", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "orders", "payment_method", "TEXT NOT NULL DEFAULT 'Pay at Counter'")
add_column_if_missing(conn, "orders", "payment_status", "TEXT NOT NULL DEFAULT 'Unpaid'")
add_column_if_missing(conn, "orders", "payment_reference", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "orders", "payment_provider", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "orders", "payment_last4", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "orders", "payment_authorisation", "TEXT NOT NULL DEFAULT ''")

cur.execute("""
CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    image_url TEXT NOT NULL DEFAULT 'images/fallback.jpg',
    dietary_tags TEXT NOT NULL DEFAULT '',
    prep_minutes INTEGER NOT NULL DEFAULT 8,
    stock_count INTEGER NOT NULL DEFAULT 20,
    is_available INTEGER NOT NULL DEFAULT 1
)
""")
add_column_if_missing(conn, "menu_items", "description", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "menu_items", "image_url", "TEXT NOT NULL DEFAULT 'images/fallback.jpg'")
add_column_if_missing(conn, "menu_items", "dietary_tags", "TEXT NOT NULL DEFAULT ''")
add_column_if_missing(conn, "menu_items", "prep_minutes", "INTEGER NOT NULL DEFAULT 8")
add_column_if_missing(conn, "menu_items", "stock_count", "INTEGER NOT NULL DEFAULT 20")
add_column_if_missing(conn, "menu_items", "is_available", "INTEGER NOT NULL DEFAULT 1")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code TEXT NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_ref TEXT UNIQUE NOT NULL,
    order_code TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    amount REAL NOT NULL,
    surcharge_amount REAL NOT NULL DEFAULT 0,
    payment_status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    discount_rate REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
)
""")

# Seed/update menu data
if cur.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0] == 0:
    cur.executemany(
        "INSERT INTO menu_items (category, name, price, description, image_url, dietary_tags, prep_minutes, stock_count, is_available) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        MENU_SEED,
    )
else:
    for category, name, price, description, image_url, dietary_tags, prep_minutes, stock_count, is_available in MENU_SEED:
        cur.execute("""
            UPDATE menu_items
            SET description = ?, image_url = ?, dietary_tags = ?, prep_minutes = ?
            WHERE name = ?
        """, (description, image_url, dietary_tags, prep_minutes, name))

if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    cur.executemany("INSERT INTO users (username, password, display_name, role) VALUES (?, ?, ?, ?)", USER_SEED)

if cur.execute("SELECT COUNT(*) FROM promo_codes").fetchone()[0] == 0:
    cur.executemany("INSERT INTO promo_codes (code, description, discount_rate, is_active) VALUES (?, ?, ?, ?)", PROMO_SEED)

# Migrate any legacy plaintext user passwords to hashed values.
for user_row in cur.execute("SELECT id, password FROM users").fetchall():
    if user_row[1] and not is_password_hash(user_row[1]):
        cur.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(user_row[1]), user_row[0]))

cur.execute("UPDATE orders SET subtotal = total_price WHERE subtotal = 0")
cur.execute("UPDATE orders SET gst_amount = ROUND(total_price / 11, 2) WHERE gst_amount = 0")
cur.execute("UPDATE orders SET status = 'Pending' WHERE status = 'pending'")
cur.execute("UPDATE orders SET payment_method = 'Credit/Debit Card' WHERE payment_method IN ('Pay at Counter', 'Cash', 'EFTPOS/Card')")
cur.execute("UPDATE orders SET payment_status = 'Paid' WHERE payment_status = 'Unpaid'")

conn.commit()
conn.close()

print("Database initialized successfully.")
