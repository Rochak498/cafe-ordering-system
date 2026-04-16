from flask import Flask, render_template, request, redirect, url_for, flash, Response
import csv
import io
import os
import sqlite3
from contextlib import closing
import secrets

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_this_before_production")
DB_PATH = "database.db"
VALID_STATUSES = ("Pending", "Preparing", "Ready", "Completed")
STATUS_HELP_TEXT = {
    "Pending": "Your order has been received and is waiting to be prepared.",
    "Preparing": "Our staff are currently preparing your order.",
    "Ready": "Your order is ready for collection.",
    "Completed": "Your order has been completed. Thank you for visiting Daxxi140 Café.",
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


@app.route("/")
def home():
    with closing(get_db_connection()) as conn:
        available_items = conn.execute(
            "SELECT COUNT(*) AS count FROM menu_items WHERE is_available = 1"
        ).fetchone()["count"]
        total_orders = conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"]
    return render_template(
        "home.html", available_items=available_items, total_orders=total_orders
    )


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
        categories = conn.execute(
            "SELECT DISTINCT category FROM menu_items WHERE is_available = 1 ORDER BY category"
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

        order_code = build_unique_order_code()
        total_price = float(item["price"]) * quantity

        with closing(get_db_connection()) as conn:
            conn.execute(
                """
                INSERT INTO orders (
                    order_code, customer_name, item_name, quantity,
                    unit_price, total_price, notes, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_code,
                    customer_name,
                    item["name"],
                    quantity,
                    float(item["price"]),
                    total_price,
                    notes,
                    "Pending",
                ),
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
            order = conn.execute(
                "SELECT * FROM orders WHERE order_code = ?", (searched_code,)
            ).fetchone()

        if order is None and request.method == "POST":
            flash("No order found for that order code.", "error")
        elif order is not None:
            order = prepare_order_rows([order])[0]

    return render_template("track.html", order=order, order_code=searched_code)


@app.route("/orders")
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

    orders = prepare_order_rows(orders)

    return render_template(
        "orders.html",
        orders=orders,
        valid_statuses=VALID_STATUSES,
        status_filter=status_filter,
        search=search,
    )


@app.route("/update_status/<int:order_id>", methods=["POST"])
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


@app.route("/orders/export")
def export_orders():
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            "SELECT order_code, customer_name, item_name, quantity, unit_price, total_price, status, created_at FROM orders ORDER BY created_at DESC"
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order Code",
        "Customer Name",
        "Item Name",
        "Quantity",
        "Unit Price",
        "Total Price",
        "Status",
        "Created At",
    ])

    for row in rows:
        writer.writerow([
            row["order_code"],
            row["customer_name"],
            row["item_name"],
            row["quantity"],
            row["unit_price"],
            row["total_price"],
            row["status"],
            row["created_at"],
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=orders_export.csv"
    return response


@app.route("/dashboard")
def dashboard():
    with closing(get_db_connection()) as conn:
        total_orders = conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"]
        total_revenue = conn.execute(
            "SELECT COALESCE(SUM(total_price), 0) AS revenue FROM orders"
        ).fetchone()["revenue"]
        pending_orders = conn.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE status = 'Pending'"
        ).fetchone()["count"]
        preparing_orders = conn.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE status = 'Preparing'"
        ).fetchone()["count"]
        ready_orders = conn.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE status = 'Ready'"
        ).fetchone()["count"]
        completed_orders = conn.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE status = 'Completed'"
        ).fetchone()["count"]
        average_order_value = conn.execute(
            "SELECT COALESCE(AVG(total_price), 0) AS avg_value FROM orders"
        ).fetchone()["avg_value"]
        top_items = conn.execute(
            """
            SELECT item_name, SUM(quantity) AS total_quantity, SUM(total_price) AS sales
            FROM orders
            GROUP BY item_name
            ORDER BY total_quantity DESC, sales DESC
            LIMIT 5
            """
        ).fetchall()
        recent_orders = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

    recent_orders = prepare_order_rows(recent_orders)

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        total_revenue=round(total_revenue, 2),
        pending_orders=pending_orders,
        preparing_orders=preparing_orders,
        ready_orders=ready_orders,
        completed_orders=completed_orders,
        average_order_value=round(average_order_value or 0, 2),
        top_items=top_items,
        recent_orders=recent_orders,
    )


if __name__ == "__main__":
    app.run(debug=True)
