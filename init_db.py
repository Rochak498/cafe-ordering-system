import sqlite3

DB_PATH = "database.db"

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
    ("staff", "staff123", "Staff Member", "staff"),
    ("admin", "admin123", "Cafe Owner", "admin"),
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

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT UNIQUE,
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
        payment_method TEXT NOT NULL DEFAULT 'Pay at Counter',
        payment_status TEXT NOT NULL DEFAULT 'Unpaid',
        payment_reference TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)

existing_order_columns = column_names(conn, "orders")
if "order_code" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN order_code TEXT")
if  "requested_time" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN requested_time TEXT NOT NULL DEFAULT 'ASAP'")
if "promo_code" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN promo_code TEXT NOT NULL DEFAULT ''")
if "discount_amount" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0")
if "notes" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN notes TEXT")
if "table_number" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN table_number TEXT NOT NULL DEFAULT 'Takeaway'")
if "customer_phone" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN customer_phone TEXT NOT NULL DEFAULT ''")
if "payment_method" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'Pay at Counter'")
if "payment_status" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'Unpaid'")
if "size_option" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN size_option TEXT NOT NULL DEFAULT 'Regular'")
if "milk_option" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN milk_option TEXT NOT NULL DEFAULT 'Full Cream'")
if "extras" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN extras TEXT NOT NULL DEFAULT ''")
if "modifiers_total" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN modifiers_total REAL NOT NULL DEFAULT 0")
if "subtotal" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN subtotal REAL NOT NULL DEFAULT 0")
if "service_fee" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN service_fee REAL NOT NULL DEFAULT 0")
if "gst_amount" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN gst_amount REAL NOT NULL DEFAULT 0")
if "payment_reference" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN payment_reference TEXT NOT NULL DEFAULT ''")
if "Payment_provider" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN payment_provider TEXT NOT NULL DEFAULT ''")
if "payment_last4" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN payment_last4 TEXT NOT NULL DEFAULT ''")
if "payment_authorisation" not in existing_order_columns:
    cur.execute("ALTER TABLE orders ADD COLUMN payment_authorisation TEXT NOT NULL DEFAULT ''")


cur.execute(
    """
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
    """
)

existing_menu_columns = column_names(conn, "menu_items")
if "description" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN description TEXT NOT NULL DEFAULT ''")
if "image_url" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN image_url TEXT NOT NULL DEFAULT 'images/fallback.jpg'")
if "is_available" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN is_available INTEGER NOT NULL DEFAULT 1")
if "dietary_tags" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN dietary_tags TEXT NOT NULL DEFAULT ''")
if "prep_minutes" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN prep_minutes INTEGER NOT NULL DEFAULT 8")
if "stock_count" not in existing_menu_columns:
    cur.execute("ALTER TABLE menu_items ADD COLUMN stock_count INTEGER NOT NULL DEFAULT 20")

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
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cur.execute(
    """
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
    """
)

cur.execute("""
CREATE TABLE IF NOT EXISTS promo_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    discount_rate REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
)
""")

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

cur.execute("UPDATE orders SET subtotal = total_price WHERE subtotal = 0")
cur.execute("UPDATE orders SET gst_amount = ROUND(total_price / 11, 2) WHERE gst_amount = 0")
cur.execute("UPDATE orders SET status = 'Pending' WHERE status = 'pending'")
cur.execute("UPDATE orders SET payment_method = 'Credit/Debit Card' WHERE payment_method IN ('Pay at Counter', 'Cash', 'EFTPOS/Card')")
cur.execute("UPDATE orders SET payment_status = 'Paid' WHERE payment_status = 'Unpaid'")

conn.commit()
conn.close()

print("Database initialized successfully.")
