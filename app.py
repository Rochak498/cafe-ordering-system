from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
import csv
import io
import os
import sqlite3
from contextlib import closing
from functools import wraps
import secrets
from urllib.parse import urlparse
import qrcode
from qrcode.image.svg import SvgImage


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_this_before_production")
DB_PATH = "database.db"
VALID_STATUSES = ("Pending", "Preparing", "Ready", "Completed", "Cancelled")
STAFF_STATUSES = ("Pending", "Preparing", "Ready", "Completed")
STATUS_HELP_TEXT = {
    "Pending": "Your order has been received and is waiting to be prepared.",
    "Preparing": "Our staff are currently preparing your order.",
    "Ready": "Your order is ready for collection.",
    "Completed": "Your order has been completed. Thank you for visiting Daxxi140 Cafe.",
    "Cancelled": "This order has been cancelled. Please speak with staff if this was unexpected.",
}

MILK_OPTIONS = {
    "Full Cream": 0.00,
    "Skim": 0.00,
    "Soy": 0.80,
    "Oat": 0.80,
    "Lactose Free": 0.80,
    "Almond": 0.80,
    "None / Not Applicable": 0.00,
}

SIZE_OPTIONS = {
    "Small": -0.50,
    "Regular": 0.00,
    "Large": 1.00,
}

EXTRA_OPTIONS = {
    "Extra Shot": 1.00,
    "Vanilla Syrup": 0.50,
    "Caramel Syrup": 0.50,
    "Hazelnut Syrup": 0.50,
    "Whipped Cream": 0.50,
    "Gluten Free Bread": 2.00,
}

DRINK_CATEGORIES = {"Coffee", "Cold Drinks"}
FOOD_CATEGORIES = {"Food"}

DRINK_EXTRA_OPTIONS = {
    "Extra Shot": EXTRA_OPTIONS["Extra Shot"],
    "Vanilla Syrup": EXTRA_OPTIONS["Vanilla Syrup"],
    "Caramel Syrup": EXTRA_OPTIONS["Caramel Syrup"],
    "Hazelnut Syrup": EXTRA_OPTIONS["Hazelnut Syrup"],
    "Whipped Cream": EXTRA_OPTIONS["Whipped Cream"],
}

FOOD_EXTRA_OPTIONS = {
    "Gluten Free Bread": EXTRA_OPTIONS["Gluten Free Bread"],
}

NO_SIZE_OPTIONS = {"Regular": 0.00}
NO_MILK_OPTIONS = {"None / Not Applicable": 0.00}

def get_modifier_options(category: str):
    """Return only the modifiers that make sense for the selected menu category."""
    if category in DRINK_CATEGORIES:
        return {
            "show_size": True,
            "show_milk": True,
            "size_options": SIZE_OPTIONS,
            "milk_options": MILK_OPTIONS,
            "extra_options": DRINK_EXTRA_OPTIONS,
            "note": "Choose drink size, milk, and optional coffee extras.",
        }
    if category in FOOD_CATEGORIES:
        return {
            "show_size": False,
            "show_milk": False,
            "size_options": NO_SIZE_OPTIONS,
            "milk_options": NO_MILK_OPTIONS,
            "extra_options": FOOD_EXTRA_OPTIONS,
            "note": "Food items only show realistic food modifiers.",
        }
    return {
        "show_size": False,
        "show_milk": False,
        "size_options": NO_SIZE_OPTIONS,
        "milk_options": NO_MILK_OPTIONS,
        "extra_options": {},
        "note": "No drink modifiers apply to this item.",
    }


def clean_modifiers_for_category(category: str, size_option: str, milk_option: str, selected_extras):
    """Ignore size, milk and extras that do not apply to the menu category."""
    options = get_modifier_options(category)
    if not options["show_size"]:
        size_option = "Regular"
    elif size_option not in options["size_options"]:
        size_option = "Regular"

    if not options["show_milk"]:
        milk_option = "None / Not Applicable"
    elif milk_option not in options["milk_options"]:
        milk_option = "Full Cream"

    allowed_extras = options["extra_options"]
    valid_extras = [extra for extra in selected_extras if extra in allowed_extras]
    return size_option, milk_option, valid_extras, ", ".join(valid_extras), options

PAYMENT_METHODS = {
    # Online-only payment options for the customer ordering flow.
    # No full card details are stored; only safe receipt metadata such as last 4 digits.
    "Credit/Debit Card": {"surcharge_rate": 0.015, "paid_immediately": True},
    "Apple Pay / Google Pay": {"surcharge_rate": 0.012, "paid_immediately": True},
}

CARD_BRAND_PREFIXES = {
    "4": "Visa",
    "5": "Mastercard",
    "3": "American Express",
}

PROMO_CODES = {
    "WELCOME10": {"discount_rate": 0.10, "label": "Welcome 10% discount"},
    "STUDENT10": {"discount_rate": 0.10, "label": "Student 10% discount"},
    "COFFEE5": {"discount_rate": 0.05, "label": "Coffee lover 5% discount"},
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            flash("Please log in with a staff account to access this page.", "error")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped_view

def current_user():
    return session.get("user")

def menu_image_src(image_url: str) -> str:
    """Return a usable image URL for menu cards. Supports external URLs and static image paths."""
    if not image_url:
        return url_for("static", filename="images/fallback.jpg")
    parsed = urlparse(image_url)
    if parsed.scheme in {"http", "https"}:
        return image_url
    return url_for("static", filename=image_url.lstrip("/"))

@app.context_processor
def inject_helpers():
    return {
        "menu_image_src": menu_image_src,
        "milk_options": MILK_OPTIONS,
        "size_options": SIZE_OPTIONS,
        "extra_options": EXTRA_OPTIONS,
        "payment_methods": PAYMENT_METHODS,
        "promo_codes": PROMO_CODES,
        }

def generate_order_code(length: int = 8) -> str:
    return secrets.token_hex(length // 2).upper()


def build_unique_order_code() -> str:
    while True:
        code = generate_order_code()
        with closing(get_db_connection()) as conn:
            existing = conn.execute(
                "SELECT 1 FROM orders WHERE order_code = ?", (code,)
            ).fetchone()
        if existing is None:
            return code


def estimate_prep_time(quantity: int, status: str) -> int:
    base = 5 + max(quantity - 1, 0) * 2
    adjustments = {
        "Pending": base + 5,
        "Preparing": max(base, 4),
        "Ready": 0,
        "Completed": 0,
        "Cancelled": 0,
    }
    return adjustments.get(status, base)

def normalise_extras(selected_extras):
    """Return valid extras as a clean list and comma-separated label."""
    if not selected_extras:
        return [], ""
    valid = [extra for extra in selected_extras if extra in EXTRA_OPTIONS]
    return valid, ", ".join(valid)


def normalise_promo_code(promo_code: str) -> str:
    return (promo_code or "").strip().upper()


def get_promo_discount_rate(promo_code: str) -> float:
    promo_code = normalise_promo_code(promo_code)
    return PROMO_CODES.get(promo_code, {}).get("discount_rate", 0.0)


def only_digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def detect_card_brand(card_number: str) -> str:
    digits = only_digits(card_number)
    if digits.startswith("34") or digits.startswith("37"):
        return "American Express"
    return CARD_BRAND_PREFIXES.get(digits[:1], "Card")


def luhn_valid(card_number: str) -> bool:
    """Validate a card number using the Luhn checksum. This is a simulation, not a real payment gateway."""
    digits = only_digits(card_number)
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for index, char in enumerate(reverse_digits):
        number = int(char)
        if index % 2 == 1:
            number *= 2
            if number > 9:
                number -= 9
        checksum += number
    return checksum % 10 == 0


def expiry_valid(expiry: str) -> bool:
    """Validate MM/YY format without storing it."""
    expiry = (expiry or "").strip()
    if "/" not in expiry:
        return False
    month_text, year_text = expiry.split("/", 1)
    if not (month_text.isdigit() and year_text.isdigit()):
        return False
    month = int(month_text)
    year = int(year_text)
    if month < 1 or month > 12:
        return False
    # Academic demo rule: accept current/future year in 20YY format.
    return year >= 26


def validate_online_payment(form, payment_method: str):
    """Return safe payment metadata after validating online-only payment input."""
    if payment_method not in PAYMENT_METHODS:
        return False, "Please choose a valid online payment method.", {}

    if payment_method == "Credit/Debit Card":
        cardholder = form.get("cardholder_name", "").strip()
        card_number = form.get("card_number", "").strip()
        expiry = form.get("card_expiry", "").strip()
        cvv = only_digits(form.get("card_cvv", ""))
        digits = only_digits(card_number)

        if len(cardholder) < 2:
            return False, "Cardholder name is required for card payments.", {}
        if not luhn_valid(digits):
            return False, "Please enter a valid credit/debit card number.", {}
        if not expiry_valid(expiry):
            return False, "Please enter a valid expiry date in MM/YY format.", {}
        if len(cvv) not in (3, 4):
            return False, "Please enter a valid CVV.", {}

        return True, "", {
            "payment_provider": detect_card_brand(digits),
            "payment_last4": digits[-4:],
            "payment_authorisation": "AUTH-" + secrets.token_hex(3).upper(),
        }

    if payment_method == "Apple Pay / Google Pay":
        wallet_name = form.get("wallet_name", "Apple Pay").strip() or "Apple Pay"
        wallet_confirmed = form.get("wallet_confirmed") == "yes"
        if wallet_name not in {"Apple Pay", "Google Pay"}:
            return False, "Please select Apple Pay or Google Pay.", {}
        if not wallet_confirmed:
            return False, "Please confirm the mobile wallet payment authorisation.", {}
        return True, "", {
            "payment_provider": wallet_name,
            "payment_last4": "WALLET",
            "payment_authorisation": "WALLET-" + secrets.token_hex(3).upper(),
        }

    return False, "Unsupported online payment method.", {}


def calculate_order_pricing(base_price: float, quantity: int, size_option: str, milk_option: str, extras_list, payment_method: str, promo_code: str = ""):
    """Calculate realistic café order pricing including modifiers, promotions, GST and payment surcharges."""
    size_surcharge = SIZE_OPTIONS.get(size_option, 0.00)
    milk_surcharge = MILK_OPTIONS.get(milk_option, 0.00)
    extras_surcharge = sum(EXTRA_OPTIONS.get(extra, 0.00) for extra in extras_list)
    modifiers_per_item = size_surcharge + milk_surcharge + extras_surcharge
    item_price = max(float(base_price) + modifiers_per_item, 0)
    subtotal_before_discount = round(item_price * quantity, 2)
    promo_code = normalise_promo_code(promo_code)
    discount_rate = get_promo_discount_rate(promo_code)
    discount_amount = round(subtotal_before_discount * discount_rate, 2) if promo_code else 0.0
    discounted_subtotal = round(max(subtotal_before_discount - discount_amount, 0), 2)
    surcharge_rate = PAYMENT_METHODS.get(payment_method, next(iter(PAYMENT_METHODS.values())))["surcharge_rate"]
    service_fee = round(discounted_subtotal * surcharge_rate, 2)
    total_price = round(discounted_subtotal + service_fee, 2)
    gst_amount = round(total_price / 11, 2)  # GST is included in consumer prices.
    return {
        "modifiers_total": round(modifiers_per_item * quantity, 2),
        "subtotal": subtotal_before_discount,
        "discount_amount": discount_amount,
        "discounted_subtotal": discounted_subtotal,
        "service_fee": service_fee,
        "total_price": total_price,
        "gst_amount": gst_amount,
    }


def create_transaction(order_code: str, payment_method: str, amount: float, surcharge: float, payment_status: str):
    if payment_status != "Paid":
        return ""
    ref = "TXN-" + secrets.token_hex(4).upper()
    with closing(get_db_connection()) as conn:
        conn.execute(
            """
            INSERT INTO transactions (transaction_ref, order_code, payment_method, amount, surcharge_amount, payment_status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ref, order_code, payment_method, amount, surcharge, payment_status),
        )
        conn.commit()
    return ref


def prepare_order_rows(rows):
    prepared = []
    for row in rows:
        order = dict(row)
        order["status_help"] = STATUS_HELP_TEXT.get(order["status"], "")
        order["estimated_minutes"] = estimate_prep_time(order["quantity"], order["status"])
        order["service_type"] = "Takeaway" if order.get("table_number") == "Takeaway" else f"Table {order.get('table_number')}"
        order["extras_list"] = [x.strip() for x in (order.get("extras") or "").split(",") if x.strip()]
        prepared.append(order)
    return prepared


@app.context_processor
def inject_user():
    return {"current_user": current_user()}

def calculate_loyalty_points(total_spend: float) -> int:
    """Simple loyalty rule for final sprint: 1 point per full dollar spent."""
    return int(max(total_spend or 0, 0))


def customer_total_spend(phone: str) -> float:
    if not phone:
        return 0.0
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(total_price), 0) AS spend FROM orders WHERE customer_phone = ? AND status != 'Cancelled'",
            (phone,),
        ).fetchone()
    return float(row["spend"] or 0)


def get_menu_category_for_item(item_name: str) -> str:
    with closing(get_db_connection()) as conn:
        row = conn.execute("SELECT category FROM menu_items WHERE name = ?", (item_name,)).fetchone()
    return row["category"] if row else "Coffee"

@app.route("/")
def home():
    with closing(get_db_connection()) as conn:
        available_items = conn.execute("SELECT COUNT(*) AS count FROM menu_items WHERE is_available = 1").fetchone()["count"]
        total_orders = conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"]
        low_stock = conn.execute("SELECT COUNT(*) AS count FROM menu_items WHERE stock_count <= 5").fetchone()["count"]
        active_tables = conn.execute("SELECT COUNT(DISTINCT table_number) AS count FROM orders WHERE table_number != 'Takeaway' AND status IN ('Pending','Preparing','Ready')").fetchone()["count"]
    return render_template("home.html", available_items=available_items, total_orders=total_orders, low_stock=low_stock, active_tables=active_tables)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        with closing(get_db_connection()) as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()
        if user:
            session["user"] = {"username": user["username"], "role": user["role"], "display_name": user["display_name"]}
            flash(f"Welcome, {user['display_name']}.", "success")
            return redirect(request.args.get("next") or url_for("orders"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/menu")
def menu():
    category = request.args.get("category", "All")
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM menu_items WHERE is_available = 1 AND stock_count > 0"
    params = []

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (name LIKE ? OR category LIKE ? OR description LIKE ?)"
        like_value = f"%{search}%"
        params.extend([like_value, like_value, like_value])

    query += " ORDER BY category, name"

    with closing(get_db_connection()) as conn:
        menu_items = conn.execute(query, params).fetchall()
        categories = conn.execute(
            "SELECT DISTINCT category FROM menu_items WHERE is_available = 1 AND stock_count > 0 ORDER BY category"
        ).fetchall()

    return render_template(
        "menu.html",
        menu_items=menu_items,
        categories=categories,
        selected_category=category,
        search=search,
    )


@app.route("/order/<int:item_id>", methods=["GET", "POST"])
def create_order(item_id):
    with closing(get_db_connection()) as conn:
        item = conn.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()

    if item is None or item["is_available"] == 0:
        flash("Selected menu item is not available.", "error")
        return redirect(url_for("menu"))

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        quantity_raw = request.form.get("quantity", "").strip()
        notes = request.form.get("notes", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        payment_method = request.form.get("payment_method", "Credit/Debit Card").strip() or "Credit/Debit Card"
        payment_ok, payment_error, payment_meta = validate_online_payment(request.form, payment_method)
        if not payment_ok:
            flash(payment_error, "error")
            return redirect(url_for("create_order", item_id=item_id))
        promo_code = normalise_promo_code(request.form.get("promo_code", ""))
        requested_time = request.form.get("requested_time", "ASAP").strip() or "ASAP"
        table_number = request.form.get("table_number", "Takeaway").strip() or "Takeaway"
        size_option = request.form.get("size_option", "Regular").strip() or "Regular"
        milk_option = request.form.get("milk_option", "Full Cream").strip() or "Full Cream"
        selected_extras = request.form.getlist("extras")
        size_option, milk_option, selected_extras, extras_label, modifier_options = clean_modifiers_for_category(
            item["category"], size_option, milk_option, selected_extras
        )
        valid_tables = {"Takeaway"} | {str(i) for i in range(1, 21)}

        if table_number not in valid_tables:
            flash("Please select a valid table number or takeaway option.", "error")
            return redirect(url_for("create_order", item_id=item_id))

        if not customer_name or not quantity_raw:
            flash("Customer name and quantity are required.", "error")
            return redirect(url_for("create_order", item_id=item_id))

        if promo_code and promo_code not in PROMO_CODES:
            flash("Invalid promo code. Try WELCOME10, STUDENT10 or leave it blank.", "error")
            return redirect(url_for("create_order", item_id=item_id))
        
        if size_option not in SIZE_OPTIONS or milk_option not in MILK_OPTIONS:
            flash("Please select valid size and milk options.", "error")
            return redirect(url_for("create_order", item_id=item_id))
        
        if not customer_name or not quantity_raw:
            flash("Customer name and quantity are required.", "error")
            return redirect(url_for("create_order", item_id=item_id))

        if len(customer_name) < 2:
            flash("Customer name must contain at least 2 characters.", "error")
            return redirect(url_for("create_order", item_id=item_id))

        try:
            quantity = int(quantity_raw)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a whole number greater than 0.", "error")
            return redirect(url_for("create_order", item_id=item_id))

        if item["stock_count"] is not None and int(item["stock_count"]) < quantity:
            flash(f"Only {item['stock_count']} left for {item['name']}. Please reduce quantity or choose another item.", "error")
            return redirect(url_for("create_order", item_id=item_id))

        order_code = build_unique_order_code()
        pricing = calculate_order_pricing(
           float(item["price"]),
           quantity,
           size_option,
           milk_option,
           selected_extras,
           payment_method,
           promo_code
        )
        payment_status = "Paid" if PAYMENT_METHODS[payment_method]["paid_immediately"] else "Unpaid"
        transaction_ref = ""

        with closing(get_db_connection()) as conn:
            conn.execute(
                """
                INSERT INTO orders (
                    order_code, customer_name, customer_phone, table_number, item_name, quantity, unit_price, size_option,
                    milk_option, extras, modifiers_total, subtotal, discount_amount, service_fee, gst_amount, total_price, notes, requested_time, promo_code, status,
                    payment_method, payment_status, payment_reference, payment_provider, payment_last4, payment_authorisation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_code,
                    customer_name,
                    customer_phone,
                    table_number,
                    item["name"],
                    quantity,
                    float(item["price"]),
                    size_option,
                    milk_option,
                    extras_label,
                    pricing["modifiers_total"],
                    pricing["subtotal"],
                    pricing["discount_amount"],
                    pricing["service_fee"],
                    pricing["gst_amount"],
                    pricing["total_price"],
                    notes,
                    requested_time,
                    promo_code,
                    "Pending",
                    payment_method,
                    payment_status,
                    transaction_ref,
                    payment_meta["payment_provider"],
                    payment_meta["payment_last4"],
                    payment_meta["payment_authorisation"],
                ),
            )
            conn.execute("UPDATE menu_items SET stock_count = MAX(stock_count - ?, 0) WHERE id = ?", (quantity, item_id))
            conn.commit()

            transaction_ref = create_transaction(order_code, payment_method, pricing["total_price"], pricing["service_fee"], payment_status)
        if transaction_ref:
            with closing(get_db_connection()) as conn:
                conn.execute("UPDATE orders SET payment_reference = ? WHERE order_code = ?", (transaction_ref, order_code))
                conn.commit()

        flash(f"Order placed successfully. Your order code is {order_code}.", "success")
        return redirect(url_for("track_order", order_code=order_code))

    return render_template(
    "create_order.html",
    item=item,
    modifier_options=get_modifier_options(item["category"])
    )


@app.route("/track", methods=["GET", "POST"])
@app.route("/track/<order_code>", methods=["GET"])
def track_order(order_code=None):
    searched_code = order_code
    order = None

    if request.method == "POST":
        searched_code = request.form.get("order_code", "").strip().upper()

    if searched_code:
        with closing(get_db_connection()) as conn:
            order = conn.execute(
                "SELECT * FROM orders WHERE order_code = ?", (searched_code,)
            ).fetchone()

        if order is None and request.method == "POST":
            flash("No order found for that order code.", "error")
        elif order is not None:
            order = prepare_order_rows([order])[0]

    return render_template("track.html", order=order, order_code=searched_code)


@app.route("/orders")
@login_required
def orders():
    status_filter = request.args.get("status", "All")
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if status_filter in VALID_STATUSES:
        query += " AND status = ?"
        params.append(status_filter)

    if search:
        query += " AND (order_code LIKE ? OR customer_name LIKE ? OR item_name LIKE ? OR table_number LIKE ?)"
        like_value = f"%{search}%"
        params.extend([like_value, like_value, like_value, like_value])

    query += " ORDER BY created_at DESC"

    with closing(get_db_connection()) as conn:
        orders = conn.execute(query, params).fetchall()
    return render_template("orders.html", orders=prepare_order_rows(orders), valid_statuses=STAFF_STATUSES, all_statuses=VALID_STATUSES, status_filter=status_filter, search=search)
        



@app.route("/update_status/<int:order_id>", methods=["POST"])
@login_required
def update_status(order_id):
    new_status = request.form.get("status", "Pending")

    if new_status not in VALID_STATUSES:
        flash("Invalid status selected.", "error")
        return redirect(url_for("orders"))

    with closing(get_db_connection()) as conn:
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()

    flash("Order status updated successfully.", "success")
    return redirect(url_for("orders"))


@app.route("/orders/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def edit_order(order_id):
    with closing(get_db_connection()) as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        quantity_raw = request.form.get("quantity", "").strip()
        notes = request.form.get("notes", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        payment_status = request.form.get("payment_status", order["payment_status"] if "payment_status" in order.keys() else "Paid")
        payment_method = request.form.get("payment_method", order["payment_method"] if "payment_method" in order.keys() else "Credit/Debit Card")
        promo_code = normalise_promo_code(request.form.get("promo_code", order["promo_code"] if "promo_code" in order.keys() else ""))
        requested_time = request.form.get("requested_time", order["requested_time"] if "requested_time" in order.keys() else "ASAP").strip() or "ASAP"
        table_number = request.form.get("table_number", order["table_number"]).strip() or "Takeaway"
        size_option = request.form.get("size_option", order["size_option"] if "size_option" in order.keys() else "Regular")
        milk_option = request.form.get("milk_option", order["milk_option"] if "milk_option" in order.keys() else "Full Cream")
        item_category = get_menu_category_for_item(order["item_name"])
        size_option, milk_option, selected_extras, extras_label, modifier_options = clean_modifiers_for_category(
            item_category, size_option, milk_option, request.form.getlist("extras")
        )
        table_number = request.form.get("table_number", order["table_number"]).strip() or "Takeaway"
        valid_tables = {"Takeaway"} | {str(i) for i in range(1, 21)}

        if table_number not in valid_tables:
            flash("Please select a valid table number or takeaway option.", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        
        if promo_code and promo_code not in PROMO_CODES:
            flash("Invalid promo code selected.", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        if payment_method not in PAYMENT_METHODS or size_option not in SIZE_OPTIONS or milk_option not in MILK_OPTIONS:
            flash("Please select valid payment, size and milk options.", "error")
            return redirect(url_for("edit_order", order_id=order_id))

        status = request.form.get("status", order["status"])
        if not customer_name or len(customer_name) < 2:
            flash("Customer name must contain at least 2 characters.", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        if payment_status not in {"Paid", "Refunded"}:
            flash("Invalid online payment status selected.", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        if status not in VALID_STATUSES:
            flash("Invalid status selected.", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        try:
            quantity = int(quantity_raw)
            if quantity <= 0 or quantity > 50:
                raise ValueError
        except ValueError:
            flash("Quantity must be between 1 and 50.", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        pricing = calculate_order_pricing(float(order["unit_price"]), quantity, size_option, milk_option, selected_extras, payment_method, promo_code)
        with closing(get_db_connection()) as conn:
            conn.execute(
                "UPDATE orders SET customer_name = ?, customer_phone = ?, table_number = ?, quantity = ?, size_option = ?, milk_option = ?, extras = ?, modifiers_total = ?, subtotal = ?, discount_amount = ?, service_fee = ?, gst_amount = ?, total_price = ?, notes = ?, requested_time = ?, promo_code = ?, status = ?, payment_status = ?, payment_method = ? WHERE id = ?",
                (customer_name, customer_phone, table_number, quantity, size_option, milk_option, extras_label, pricing["modifiers_total"], pricing["subtotal"], pricing["discount_amount"], pricing["service_fee"], pricing["gst_amount"], pricing["total_price"], notes, requested_time, promo_code, status, payment_status, payment_method, order_id),
            )
            conn.commit()
        flash("Order updated successfully.", "success")
        return redirect(url_for("orders"))
    return render_template("edit_order.html", order=order, valid_statuses=VALID_STATUSES, modifier_options=get_modifier_options(get_menu_category_for_item(order["item_name"])))

@app.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    with closing(get_db_connection()) as conn:
        conn.execute("UPDATE orders SET status = 'Cancelled' WHERE id = ?", (order_id,))
        conn.commit()
    flash("Order cancelled successfully.", "success")
    return redirect(url_for("orders"))


@app.route("/orders/export")
@login_required
def export_orders():
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC"
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order Code",
        "Customer Name",
        "Phone",
        "Table/Service",
        "Item Name",
        "Size",
        "Milk",
        "Extras",
        "Quantity",
        "Unit Price",
        "Modifiers",
        "Subtotal",
        "Discount",
        "Promo Code",
        "Surcharge",  
        "GST Included",
        "Total Price",
        "Requested Time",
        "Payment Method",
        "Payment Provider",
        "Payment Last 4",
        "Authorisation",
        "Payment Status",
        "Payment Ref",
        "Status",
        "Created At",
    ])

    for row in rows:
        writer.writerow([
            row["order_code"],
            row["customer_name"],
            row["customer_phone"],
            row["table_number"],
            row["item_name"],
            row["size_option"],
            row["milk_option"],
            row["extras"],
            row["quantity"],
            row["unit_price"],
            row["modifiers_total"],
            row["subtotal"],
            row["discount_amount"],
            row["promo_code"],
            row["service_fee"],
            row["gst_amount"],  
            row["total_price"],
            row["requested_time"],
            row["payment_method"],
            row["payment_provider"] if "payment_provider" in row.keys() else "",
            row["payment_last4"] if "payment_last4" in row.keys() else "",
            row["payment_authorisation"] if "payment_authorisation" in row.keys() else "",
            row["payment_status"],
            row["payment_reference"],
            row["status"],
            row["created_at"],
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=orders_export.csv"
    return response

@app.route("/admin/menu", methods=["GET", "POST"])
@login_required
def admin_menu():
    if request.method == "POST":
        category = request.form.get("category", "").strip()
        name = request.form.get("name", "").strip()
        price_raw = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()
        image_url = request.form.get("image_url", "").strip() or "images/fallback.jpg"
        dietary_tags = request.form.get("dietary_tags", "").strip()
        prep_minutes_raw = request.form.get("prep_minutes", "8").strip() or "8"
        stock_count_raw = request.form.get("stock_count", "20").strip() or "20"
        if not category or not name or not price_raw or not description:
            flash("Category, name , price and description are required.", "error")
            return redirect(url_for("admin_menu"))
        try:
            price = float(price_raw)
            if price < 0:
                raise ValueError
            prep_minutes = int(prep_minutes_raw)
            stock_count = int(stock_count_raw)
            if prep_minutes < 1 or stock_count < 0:
                raise ValueError
        except ValueError:
            flash("Price, prep time and stock must be valid positive numbers.", "error")
            return redirect(url_for("admin_menu"))
        with closing(get_db_connection()) as conn:
            conn.execute("INSERT INTO menu_items (category, name, price, description, image_url, dietary_tags, prep_minutes, stock_count, is_available) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)", (category, name, price, description, image_url, dietary_tags, prep_minutes, stock_count))
            conn.commit()
        flash("Menu item added successfully.", "success")
        return redirect(url_for("admin_menu"))
    with closing(get_db_connection()) as conn:
        items = conn.execute("SELECT * FROM menu_items ORDER BY category, name").fetchall()
    return render_template("admin_menu.html", items=items)

@app.route("/admin/menu/<int:item_id>/toggle", methods=["POST"])
@login_required
def toggle_menu_item(item_id):
    with closing(get_db_connection()) as conn:
        item = conn.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()
        if item is None:
            flash("Menu item not found.", "error")
        else:
            new_value = 0 if item["is_available"] else 1
            conn.execute("UPDATE menu_items SET is_available = ? WHERE id = ?", (new_value, item_id))
            conn.commit()
            flash("Menu item availability updated.", "success")
    return redirect(url_for("admin_menu"))


@app.route("/admin/menu/<int:item_id>/stock", methods=["POST"])
@login_required
def update_menu_stock(item_id):
    try:
        stock_count = int(request.form.get("stock_count", "0"))
        if stock_count < 0:
            raise ValueError
    except ValueError:
        flash("Stock must be a whole number 0 or greater.", "error")
        return redirect(url_for("admin_menu"))
    with closing(get_db_connection()) as conn:
        conn.execute("UPDATE menu_items SET stock_count = ? WHERE id = ?", (stock_count, item_id))
        conn.commit()
    flash("Stock level updated.", "success")
    return redirect(url_for("admin_menu"))

@app.route("/qr")
def qr_page():
    app_url = request.url_root.rstrip("/") + url_for("menu")
    return render_template("qr.html", app_url=app_url)


@app.route("/qr/menu.svg")
def qr_menu_svg():
    app_url = request.url_root.rstrip("/") + url_for("menu")
    img = qrcode.make(app_url, image_factory=SvgImage)
    output = io.BytesIO()
    img.save(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")

@app.route("/receipt/<order_code>")
def receipt(order_code):
    with closing(get_db_connection()) as conn:
        order = conn.execute("SELECT * FROM orders WHERE order_code = ?", (order_code.upper(),)).fetchone()
    if order is None:
        flash("Receipt not found for that order code.", "error")
        return redirect(url_for("track_order"))
    order = prepare_order_rows([order])[0]
    loyalty_points = calculate_loyalty_points(order["total_price"])
    if order.get("customer_phone"):
        loyalty_points = calculate_loyalty_points(customer_total_spend(order["customer_phone"]))
    return render_template("receipt.html", order=order, loyalty_points=loyalty_points)


@app.route("/feedback/<order_code>", methods=["GET", "POST"])
def feedback(order_code):
    with closing(get_db_connection()) as conn:
        order = conn.execute("SELECT * FROM orders WHERE order_code = ?", (order_code.upper(),)).fetchone()
    if order is None:
        flash("Order not found for feedback.", "error")
        return redirect(url_for("track_order"))
    if request.method == "POST":
        try:
            rating = int(request.form.get("rating", "0"))
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash("Please select a rating between 1 and 5.", "error")
            return redirect(url_for("feedback", order_code=order_code))
        comment = request.form.get("comment", "").strip()
        with closing(get_db_connection()) as conn:
            conn.execute(
                "INSERT INTO feedback (order_code, rating, comment) VALUES (?, ?, ?)",
                (order_code.upper(), rating, comment),
            )
            conn.commit()
        flash("Thank you for your feedback. Your response helps improve café service.", "success")
        return redirect(url_for("track_order", order_code=order_code.upper()))
    return render_template("feedback.html", order=order)


@app.route("/kitchen")
@login_required
def kitchen_display():
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM orders
            WHERE status IN ('Pending', 'Preparing', 'Ready')
            ORDER BY CASE status WHEN 'Pending' THEN 1 WHEN 'Preparing' THEN 2 WHEN 'Ready' THEN 3 ELSE 4 END, created_at ASC
            """
        ).fetchall()
    grouped = {status: [] for status in ("Pending", "Preparing", "Ready")}
    for order in prepare_order_rows(rows):
        grouped.setdefault(order["status"], []).append(order)
    return render_template("kitchen.html", grouped=grouped)


@app.route("/tables")
def table_availability():
    with closing(get_db_connection()) as conn:
        active = conn.execute(
            """
            SELECT table_number, COUNT(*) AS order_count
            FROM orders
            WHERE table_number != 'Takeaway' AND status IN ('Pending', 'Preparing', 'Ready')
            GROUP BY table_number
            """
        ).fetchall()
    active_map = {str(row["table_number"]): row["order_count"] for row in active}
    tables = []
    for number in range(1, 21):
        count = active_map.get(str(number), 0)
        tables.append({"number": number, "active_orders": count, "available": count == 0})
    return render_template("tables.html", tables=tables)


@app.route("/transactions")
@login_required
def transactions():
    with closing(get_db_connection()) as conn:
        rows = conn.execute("""
            SELECT t.*, o.customer_name, o.table_number, o.item_name
            FROM transactions t
            LEFT JOIN orders o ON t.order_code = o.order_code
            ORDER BY t.created_at DESC
            LIMIT 100
        """).fetchall()
        totals = conn.execute("""
            SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS amount, COALESCE(SUM(surcharge_amount), 0) AS surcharge
            FROM transactions
            WHERE payment_status = 'Paid'
        """).fetchone()
    return render_template("transactions.html", transactions=rows, totals=totals)


@app.route("/dashboard")
@login_required
def dashboard():
    with closing(get_db_connection()) as conn:
        total_orders = conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"]
        total_revenue = conn.execute("SELECT COALESCE(SUM(total_price), 0) AS revenue FROM orders WHERE status != 'Cancelled'").fetchone()["revenue"]
        average_order_value = conn.execute("SELECT COALESCE(AVG(total_price), 0) AS avg_value FROM orders WHERE status != 'Cancelled'").fetchone()["avg_value"]
        status_counts = {status: conn.execute("SELECT COUNT(*) AS count FROM orders WHERE status = ?", (status,)).fetchone()["count"] for status in VALID_STATUSES}
        top_items = conn.execute(
            """
            SELECT item_name, SUM(quantity) AS total_quantity, SUM(total_price) AS sales
            FROM orders WHERE status != 'Cancelled'
            GROUP BY item_name
            ORDER BY total_quantity DESC, sales DESC
            LIMIT 5
            """
        ).fetchall()
        category_sales = conn.execute(
            """
            SELECT mi.category, SUM(o.quantity) AS total_quantity, SUM(o.total_price) AS sales
            FROM orders o
            LEFT JOIN menu_items mi ON o.item_name = mi.name
            WHERE o.status != 'Cancelled'
            GROUP BY mi.category
            ORDER BY sales DESC
            LIMIT 5
            """
        ).fetchall()
        daily_summary = conn.execute(
            """
            SELECT DATE(created_at) AS order_date, COUNT(*) AS order_count, COALESCE(SUM(total_price), 0) AS revenue
            FROM orders
            WHERE status != 'Cancelled'
            GROUP BY DATE(created_at)
            ORDER BY order_date DESC
            LIMIT 7
            """
        ).fetchall()
        hourly_summary = conn.execute(
            """
            SELECT STRFTIME('%H:00', created_at) AS hour_label, COUNT(*) AS order_count
            FROM orders
            GROUP BY STRFTIME('%H', created_at)
            ORDER BY hour_label
            LIMIT 12
            """
         ).fetchall()
        active_tables = conn.execute(
            """
            SELECT table_number, COUNT(*) AS order_count
            FROM orders
            WHERE table_number != 'Takeaway' AND status IN ('Pending', 'Preparing', 'Ready')
            GROUP BY table_number
            ORDER BY CAST(table_number AS INTEGER)
            """    
        ).fetchall()
        recent_orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5").fetchall()
        feedback_summary = conn.execute("SELECT COUNT(*) AS count, COALESCE(AVG(rating), 0) AS avg_rating FROM feedback").fetchone()
        latest_feedback = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 5").fetchall()
        loyalty_customers = conn.execute("""
            SELECT customer_name, customer_phone, COALESCE(SUM(total_price), 0) AS spend, COUNT(*) AS orders_count
            FROM orders
            WHERE customer_phone != '' AND status != 'Cancelled'
            GROUP BY customer_phone
            ORDER BY spend DESC
            LIMIT 5
        """).fetchall()
        payment_summary = conn.execute("""
            SELECT payment_method, COUNT(*) AS count, COALESCE(SUM(total_price), 0) AS amount
            FROM orders
            WHERE status != 'Cancelled'
            GROUP BY payment_method
            ORDER BY amount DESC
        """).fetchall()
        modifier_summary = conn.execute("""
            SELECT milk_option, COUNT(*) AS count, COALESCE(SUM(modifiers_total), 0) AS modifier_revenue
            FROM orders
            WHERE status != 'Cancelled' AND milk_option != ''
            GROUP BY milk_option
            ORDER BY modifier_revenue DESC
        """).fetchall()
        transaction_summary = conn.execute("""
            SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS amount, COALESCE(SUM(surcharge_amount), 0) AS surcharge
            FROM transactions
            WHERE payment_status = 'Paid'
        """).fetchone()
        low_stock_items = conn.execute("""
            SELECT name, category, stock_count
            FROM menu_items
            WHERE stock_count <= 5
            ORDER BY stock_count ASC, name
            LIMIT 8
        """).fetchall()
        promo_summary = conn.execute("""
            SELECT promo_code, COUNT(*) AS count, COALESCE(SUM(discount_amount), 0) AS discount_total
            FROM orders
            WHERE promo_code != ''
            GROUP BY promo_code
            ORDER BY discount_total DESC
        """).fetchall()
    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        total_revenue=round(total_revenue or 0, 2),
        average_order_value=round(average_order_value or 0, 2),
        status_counts=status_counts,
        top_items=top_items,
        category_sales=category_sales,
        daily_summary=daily_summary,
        hourly_summary=hourly_summary,
        recent_orders=prepare_order_rows(recent_orders),
        active_tables=active_tables,
        feedback_summary=feedback_summary,
        latest_feedback=latest_feedback,
        loyalty_customers=loyalty_customers,
        calculate_loyalty_points=calculate_loyalty_points,
        payment_summary=payment_summary,
        modifier_summary=modifier_summary,
        transaction_summary=transaction_summary,
        low_stock_items=low_stock_items,
        promo_summary=promo_summary,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)