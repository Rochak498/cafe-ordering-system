# Daxxi140 Cafe Ordering System — Iteration 2

## Overview
This is the Iteration 2 product for ISYS3008 Project B. It extends the Iteration 1 MVP by adding role-based staff access, menu administration, order editing/cancellation, enhanced reporting, and better operational controls.

## Main Features

### Customer Facing Feature
- Customer home page
- Customer menu browsing
- Menu item images and descriptions
- Category filtering and keyword search
- QR-code menu access page
- Customer order placement
- Table number or takeaway selection
- Unique order code generation
- Order tracking by order code
- Estimated preparation time and status messages

### Staff/owner features
- Staff login and logout
- Protected staff queue, dashboard, CSV export, and menu admin pages
- Order search and status filter
- Order status updates
- Edit order details including customer name, table number, quantity, notes, and status
- Cancel orders while keeping records for traceability
- Add menu item with category, name, price, description, and image path/URL
- Hide/show menu items without deleting records
- CSV export of order records

### Dashboard features
- Total orders
- Total revenue
- Average order value
- Status counts
- Top-selling items
- Category sales
- Daily revenue summary
- Orders by hour
- Active table slots
- Recent orders

## Demo Accounts
- Username: `staff` / Password: `staff123`
- Username: `admin` / Password: `admin123`

## Technologies
- Python 3.x
- Flask 3.0.2
- qrcode[pil] 7.4.2
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
## Important Database Note
If you have an old database from Iteration 1 or earlier Iteration 2 work, delete `database.db` first, then run:
```bash
python init_db.py
```

## QR Code Note
The QR page is available at:
```text
http://127.0.0.1:5000/qr
```
It generates a QR code that links to the customer menu. For a real deployment, host the app online or run it on a shared local network so customer devices can access the same URL.

## Iteration Tag
Tag the final commit as:
```text
iteration-2
```

