# Daxxi140 Cafe Ordering System — Iteration 3 Final Product

This is the final Iteration 3 version of the Daxxi140 Cafe Ordering System for ISYS3008 Project B.

## Final Product Features

### Customer-facing features
- Browse menu with images, descriptions, categories, and prices
- Search and filter menu items
- Scan QR code to open the customer menu
- Select table number or takeaway
- Add order notes
- Select payment method
- Receive unique order code
- Track order status
- View printable digital receipt
- Submit customer feedback/rating
- View table availability

### Staff/owner features
- Staff/admin login
- Protected staff pages
- Staff order queue
- Search/filter orders by code, customer, item, status, or table
- Update order status
- Edit orders
- Cancel orders while keeping traceability
- Kitchen display screen
- Menu administration with item image/description
- Add/hide/show menu items
- Dashboard analytics
- CSV export
- Feedback summary
- Loyalty points summary
- Active table slot visibility

## Technologies
- Python 3.x
- Flask 3.0.2
- SQLite
- HTML5
- CSS3
- qrcode 7.4.2

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Initialise/reset database:

```bash
python init_db.py
```

3. Run the application:

```bash
python app.py
```

4. Open:

```text
http://127.0.0.1:5000
```

## Demo accounts

```text
staff / staff123
admin / admin123
```

## Suggested demo flow
1. Show QR code page
2. Open customer menu
3. Browse item images/descriptions
4. Check table availability
5. Place dine-in order with table number and payment method
6. Track order
7. View receipt
8. Login as staff
9. Open kitchen display
10. Update/edit/cancel order
11. Add/hide menu item
12. Show dashboard analytics, feedback, and loyalty
13. Export CSV

## Iteration tag
Tag final commit as:

```text
iteration-3-final
```

## Iteration 3 realism upgrades

This final version includes realistic café/POS features:

- item images and descriptions
- table number or takeaway selection
- size options
- milk/dietary options with surcharges
- extras/modifiers such as extra shot and syrups
- payment methods: Pay at Counter, Cash, EFTPOS/Card, Apple Pay / Google Pay
- simulated transaction records for paid orders
- card/mobile surcharge calculation
- subtotal, GST included, surcharge and total calculation
- transaction register for staff/owner
- improved staff queue with payment and modifier details
- improved dashboard with payment method and modifier revenue summaries

Demo recommendation: create a large coffee order with oat milk, extra shot, and EFTPOS/Card payment to demonstrate realistic café pricing and transactions.
