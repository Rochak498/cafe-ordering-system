from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from contextlib import closing

app = Flask(__name__)
app.secret_key = "replace_this_with_a_secure_key"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create_order", methods=["GET", "POST"])
def create_order():
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        item_name = request.form.get("item_name", "").strip()
        quantity = request.form.get("quantity", "").strip()
        unit_price = request.form.get("unit_price", "").strip()

        if not customer_name or not item_name or not quantity or not unit_price:
            flash("All fields are required.", "error")
            return redirect(url_for("create_order"))

        try:
            quantity = int(quantity)
            unit_price = float(unit_price)

            if quantity <= 0 or unit_price < 0:
                flash("Quantity must be greater than 0 and price must not be negative.", "error")
                return redirect(url_for("create_order"))

            total_price = quantity * unit_price

            with closing(get_db_connection()) as conn:
                conn.execute("""
                    INSERT INTO orders (customer_name, item_name, quantity, unit_price, total_price, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (customer_name, item_name, quantity, unit_price, total_price, "Pending"))
                conn.commit()

            flash("Order created successfully.", "success")
            return redirect(url_for("orders"))

        except ValueError:
            flash("Quantity must be a whole number and price must be numeric.", "error")
            return redirect(url_for("create_order"))

    return render_template("index.html")


@app.route("/orders")
def orders():
    with closing(get_db_connection()) as conn:
        orders = conn.execute("""
            SELECT * FROM orders ORDER BY created_at DESC
        """).fetchall()
    return render_template("orders.html", orders=orders)


@app.route("/update_status/<int:order_id>", methods=["POST"])
def update_status(order_id):
    new_status = request.form.get("status", "Pending")

    valid_statuses = {"Pending", "Preparing", "Ready", "Completed"}
    if new_status not in valid_statuses:
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
        total_revenue = conn.execute("SELECT COALESCE(SUM(total_price), 0) AS revenue FROM orders").fetchone()["revenue"]
        pending_orders = conn.execute("SELECT COUNT(*) AS count FROM orders WHERE status = 'Pending'").fetchone()["count"]
        ready_orders = conn.execute("SELECT COUNT(*) AS count FROM orders WHERE status = 'Ready'").fetchone()["count"]

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        total_revenue=round(total_revenue, 2),
        pending_orders=pending_orders,
        ready_orders=ready_orders
    )


if __name__ == "__main__":
    app.run(debug=True)