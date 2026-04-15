from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from contextlib import closing
import secrets

app = Flask(__name__)
app.secret_key = "change_this_before_production"
DB_PATH = "database.db"
VALID_STATUSES = ("Pending", "Preparing", "Ready", "Completed")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_order_code(length: int = 8) -> str:
    return secrets.token_hex(length // 2).upper()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/menu")
def menu():
    with closing(get_db_connection()) as conn:
        menu_items = conn.execute(
            "SELECT * FROM menu_items WHERE is_available = 1 ORDER BY category, name"
        ).fetchall()
    return render_template("menu.html", menu_items=menu_items)


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

        try:
            quantity = int(quantity_raw)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a whole number greater than 0.", "error")
            return redirect(url_for("create_order", item_id=item_id))

        order_code = generate_order_code()
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

    return render_template("track.html", order=order, order_code=searched_code)


@app.route("/orders")
def orders():
    status_filter = request.args.get("status", "All")
    query = "SELECT * FROM orders"
    params = []

    if status_filter in VALID_STATUSES:
        query += " WHERE status = ?"
        params.append(status_filter)

    query += " ORDER BY created_at DESC"

    with closing(get_db_connection()) as conn:
        orders = conn.execute(query, params).fetchall()

    return render_template(
        "orders.html",
        orders=orders,
        valid_statuses=VALID_STATUSES,
        status_filter=status_filter,
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

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        total_revenue=round(total_revenue, 2),
        pending_orders=pending_orders,
        preparing_orders=preparing_orders,
        ready_orders=ready_orders,
        completed_orders=completed_orders,
    )


if __name__ == "__main__":
    app.run(debug=True)
