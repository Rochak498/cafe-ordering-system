import sqlite3

DB_PATH = "database.db"

MENU_SEED = [
    ("Coffee", "Latte", 5.50, 1),
    ("Coffee", "Cappuccino", 5.20, 1),
    ("Coffee", "Flat White", 5.30, 1),
    ("Cold Drinks", "Iced Coffee", 6.00, 1),
    ("Cold Drinks", "Iced Chocolate", 6.20, 1),
    ("Food", "Chicken Wrap", 9.50, 1),
    ("Food", "Veggie Toastie", 8.50, 1),
    ("Food", "Banana Bread", 4.80, 1),
    ("Dessert", "Blueberry Muffin", 4.50, 1),
    ("Dessert", "Chocolate Brownie", 5.00, 1),
]

USER_SEED = [
    ("staff", "staff123", "Staff Member", "staff"),
    ("admin", "admin123", "Cafe Owner", "admin"),
]


def column_names(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT UNIQUE,
        customer_name TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        notes TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)

existing_order_columns = column_names(conn, "orders")
if "order_code" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN order_code TEXT")
if "notes" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN notes TEXT")

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        is_available INTEGER NOT NULL DEFAULT 1
    )
    """
)

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """
)

if cur.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0] == 0:
    cur.executemany("INSERT INTO menu_items (category, name, price, is_available) VALUES (?, ?, ?, ?)", MENU_SEED)

if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    cur.executemany("INSERT INTO users (username, password, display_name, role) VALUES (?, ?, ?, ?)", USER_SEED)

conn.commit()
conn.close()

print("Database initialized successfully.")
