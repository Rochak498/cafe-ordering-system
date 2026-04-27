from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
import csv
import io
import os
import sqlite3
from contextlib import closing
from functools import wraps
import secrets

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_this_before_production")
DB_PATH = "database.db"
VALID_STATUSES = ("Pending", "Preparing", "Ready", "Completed", "Cancelled")
STAFF_STATUSES = ("Pending", "Preparing", "Ready", "Completed")
STATUS_HELP_TEXT = {
    "Pending": "Your order has been received and is waiting to be prepared.",
    "Preparing": "Our staff are currently preparing your order.",
    "Ready": "Your order is ready for collection.",
    "Completed": "Your order has been completed. Thank you for visiting Daxxi140 Café.",
    "Cancelled": "This order has been cancelled. Please speak with staff if this was unexpected.",
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


def generate_order_code(length: int = 8) -> str:
    return secrets.token_hex(length // 2).upper()


def build_unique_order_code() -> str:
    while True:
        code = generate_order_code()
        with closing(get_db_connection()) as conn:
            existing = conn.execute("SELECT 1 FROM orders WHERE order_code = ?", (code,)).fetchone()
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


def prepare_order_rows(rows):
    prepared = []
    for row in rows:
        order = dict(row)
        order["status_help"] = STATUS_HELP_TEXT.get(order["status"], "")
        order["estimated_minutes"] = estimate_prep_time(order["quantity"], order["status"])
        prepared.append(order)
    return prepared


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/")
def home():
    with closing(get_db_connection()) as conn:
        available_items = conn.execute("SELECT COUNT(*) AS count FROM menu_items WHERE is_available = 1").fetchone()["count"]
        total_orders = conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"]
    return render_template("home.html", available_items=available_items, total_orders=total_orders)


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
    query = "SELECT * FROM menu_items WHERE is_available = 1"
    params = []
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (name LIKE ? OR category LIKE ?)"
        like_value = f"%{search}%"
        params.extend([like_value, like_value])
    query += " ORDER BY category, name"
    with closing(get_db_connection()) as conn:
        menu_items = conn.execute(query, params).fetchall()
        categories = conn.execute("SELECT DISTINCT category FROM menu_items WHERE is_available = 1 ORDER BY category").fetchall()
    return render_template("menu.html", menu_items=menu_items, categories=categories, selected_category=category, search=search)


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
        if not customer_name or not quantity_raw:
            flash("Customer name and quantity are required.", "error")
            return redirect(url_for("create_order", item_id=item_id))
        if len(customer_name) < 2:
            flash("Customer name must contain at least 2 characters.", "error")
            return redirect(url_for("create_order", item_id=item_id))
        try:
            quantity = int(quantity_raw)
            if quantity <= 0 or quantity > 50:
                raise ValueError
        except ValueError:
            flash("Quantity must be a whole number between 1 and 50.", "error")
            return redirect(url_for("create_order", item_id=item_id))
        order_code = build_unique_order_code()
        total_price = float(item["price"]) * quantity
        with closing(get_db_connection()) as conn:
            conn.execute(
                """
                INSERT INTO orders (order_code, customer_name, item_name, quantity, unit_price, total_price, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (order_code, customer_name, item["name"], quantity, float(item["price"]), total_price, notes, "Pending"),
            )
            conn.commit()
        flash(f"Order placed successfully. Your order code is {order_code}.", "success")
        return redirect(url_for("track_order", order_code=order_code))
    return render_template("create_order.html", item=item)


@app.route("/track", methods=["GET", "POST"])
@app.route("/track/<order_code>", methods=["GET"])
def track_order(order_code=None):
    searched_code = order_code
    order = None
    if request.method == "POST":
        searched_code = request.form.get("order_code", "").strip().upper()
    if searched_code:
        with closing(get_db_connection()) as conn:
            order = conn.execute("SELECT * FROM orders WHERE order_code = ?", (searched_code,)).fetchone()
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
        query += " AND (order_code LIKE ? OR customer_name LIKE ? OR item_name LIKE ?)"
        like_value = f"%{search}%"
        params.extend([like_value, like_value, like_value])
    query += " ORDER BY created_at DESC"
    with closing(get_db_connection()) as conn:
        orders = conn.execute(query, params).fetchall()
    return render_template("orders.html", orders=prepare_order_rows(orders), valid_statuses=STAFF_STATUSES, all_statuses=VALID_STATUSES, status_filter=status_filter, search=search)


@app.route("/update_status/<int:order_id>", methods=["POST"])
@login_required
def update_status(order_id):
    new_status = request.form.get("status", "Pending")
    if new_status not in STAFF_STATUSES:
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
        status = request.form.get("status", order["status"])
        if not customer_name or len(customer_name) < 2:
            flash("Customer name must contain at least 2 characters.", "error")
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
        total_price = float(order["unit_price"]) * quantity
        with closing(get_db_connection()) as conn:
            conn.execute(
                "UPDATE orders SET customer_name = ?, quantity = ?, total_price = ?, notes = ?, status = ? WHERE id = ?",
                (customer_name, quantity, total_price, notes, status, order_id),
            )
            conn.commit()
        flash("Order updated successfully.", "success")
        return redirect(url_for("orders"))
    return render_template("edit_order.html", order=order, valid_statuses=VALID_STATUSES)


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
            "SELECT order_code, customer_name, item_name, quantity, unit_price, total_price, status, created_at FROM orders ORDER BY created_at DESC"
        ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order Code", "Customer Name", "Item Name", "Quantity", "Unit Price", "Total Price", "Status", "Created At"])
    for row in rows:
        writer.writerow([row["order_code"], row["customer_name"], row["item_name"], row["quantity"], row["unit_price"], row["total_price"], row["status"], row["created_at"]])
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
        if not category or not name or not price_raw:
            flash("Category, name and price are required.", "error")
            return redirect(url_for("admin_menu"))
        try:
            price = float(price_raw)
            if price < 0:
                raise ValueError
        except ValueError:
            flash("Price must be a valid positive number.", "error")
            return redirect(url_for("admin_menu"))
        with closing(get_db_connection()) as conn:
            conn.execute("INSERT INTO menu_items (category, name, price, is_available) VALUES (?, ?, ?, 1)", (category, name, price))
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
        recent_orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5").fetchall()
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
    )


if __name__ == "__main__":
    app.run(debug=True)
