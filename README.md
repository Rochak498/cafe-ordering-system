# Daxxi140 Cafe Ordering System — Iteration 2

## Overview
This is the Iteration 2 product for ISYS3008 Project B. It extends the Iteration 1 MVP by adding role-based staff access, menu administration, order editing/cancellation, enhanced reporting, and better operational controls.

## Main Features
- Customer menu browsing with search and category filter
- Customer order placement with unique order code generation
- Customer order tracking
- Staff login for protected operational pages
- Staff order queue with search/status filtering
- Order status updates
- Edit order details
- Cancel orders
- Menu administration: add items and toggle availability
- Dashboard: total orders, revenue, average value, status counts, category sales, daily summary, hourly summary, recent orders
- CSV order export

## Demo Accounts
- Username: `staff` / Password: `staff123`
- Username: `admin` / Password: `admin123`

## Technologies
- Python 3.x
- Flask
- SQLite
- HTML5
- CSS3

## Setup
```bash
pip install -r requirements.txt
python init_db.py
python app.py
```

Open:
```text
http://127.0.0.1:5000
```

## Iteration Tag
Tag the final commit as:
```text
iteration-2
```

## Notes for Tutor
Run `init_db.py` before running the app. If using an old database from Iteration 1, delete `database.db` and run `init_db.py` again for a clean Iteration 2 demo database.
