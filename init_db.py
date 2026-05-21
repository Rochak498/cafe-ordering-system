import sqlite3

DB_PATH = "database.db"

MENU_SEED = [
    ("Coffee", "Latte", 5.50, "Smooth espresso with steamed milk and a light foam finish.", "images/latte.jpg", 1),
    ("Coffee", "Cappuccino", 5.20, "Classic espresso topped with thick foam and cocoa dusting.", "images/cappucino.jpg", 1),
    ("Coffee", "Flat White", 5.30, "Rich espresso blended with velvety microfoam.", "images/flat_white.jpg", 1),
    ("Cold Drinks", "Iced Coffee", 6.00, "Chilled espresso over ice with milk and optional sweetness.", "images/ice-coffee.jpg", 1),
    ("Cold Drinks", "Iced Chocolate", 6.20, "Cold chocolate drink served over ice with creamy texture.", "images/ice-choclate.jpg", 1),
    ("Food", "Chicken Wrap", 9.50, "Grilled chicken, fresh salad and sauce wrapped for quick lunch.", "images/chicken_wrap.jpg", 1),
    ("Food", "Veggie Toastie", 8.50, "Toasted sandwich with vegetables, cheese and savoury filling.", "images/veggie-toastie.jpg", 1),
    ("Food", "Banana Bread", 4.80, "Moist banana bread slice, ideal with coffee.", "images/banana_bread.jpg", 1),
    ("Dessert", "Blueberry Muffin", 4.50, "Soft muffin with blueberry pieces and a lightly sweet finish.", "images/blueberry-muffin.jpg", 1),
    ("Dessert", "Chocolate Brownie", 5.00, "Dense chocolate brownie with a rich cocoa flavour.", "images/brownie.jpg", 1),
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
        table_number TEXT NOT NULL DEFAULT 'Takeaway',
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
if "table_number" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN table_number TEXT NOT NULL DEFAULT 'Takeaway'")

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        image_url TEXT NOT NULL DEFAULT 'images/fallback.svg',
        is_available INTEGER NOT NULL DEFAULT 1
    )
    """
)

existing_menu_columns = column_names(conn, "menu_items")
if "description" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN description TEXT NOT NULL DEFAULT 'image_url TEXT NOT NULL DEFAULT 'images/fallback.svg', is_available INTEGER NOT NULL DEFAULT 1'")
if "image_url" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN image_url TEXT NOT NULL DEFAULT 'images/fallback.svg'")

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
    cur.executemany(
        "INSERT INTO menu_items (category, name, price, description, image_url, is_available) VALUES (?, ?, ?, ?, ?, ?)",
        MENU_SEED,
    )
else:
    for category, name, price, description, image_url, is_available in MENU_SEED:
        cur.execute(
            """
            UPDATE menu_items
           SET description = ?,
           image_url = ?
           WHERE name = ?
            """,
            (description, image_url, name),
        )

if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    cur.executemany("INSERT INTO users (username, password, display_name, role) VALUES (?, ?, ?, ?)", USER_SEED)

conn.commit()
conn.close()

print("Database initialized successfully.")
