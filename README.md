# Daxxi140 Café Ordering System – Iteration 1 MVP

## Project Overview
This web application was developed for ISYS3007 Project A Assessment 2. It delivers the first usable product increment for the Daxxi140 Café project.

## Implemented Features
- Customer menu browsing with category and search filters
- Order placement with generated order code
- Customer order tracking page
- Staff order queue with search and status filtering
- Order status updates
- Dashboard with summary metrics, top items, and recent orders
- CSV export for order records

## Technology Stack
- Python 3.x
- Flask 3.0.2
- SQLite
- HTML5
- CSS3

## How to Run
1. Create a virtual environment if desired.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Initialise the database:
   ```bash
   python init_db.py
   ```
4. Start the application:
   ```bash
   python app.py
   ```
5. Open the browser at:
   `http://127.0.0.1:5000`

## Suggested Demo Flow
1. Open home page
2. Browse menu
3. Place an order
4. Track the order using the order code
5. Open staff queue and update status
6. Open dashboard and review metrics
7. Export order records to CSV

## Iteration Tag
Tag this version in Git as:
`iteration-1`
