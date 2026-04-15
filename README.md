# Daxxi140 Café Ordering System – Project A MVP

## Overview
This Flask + SQLite application has been updated to align more closely with the Project A scope, Jira backlog, and Confluence documentation.

### Current MVP features
- QR entry point represented by the public `/menu` route
- Customer menu browsing from a database-backed menu
- Customer order placement from a selected menu item
- Customer order tracking using an order code
- Staff order queue with status updates
- Simple management dashboard for order metrics
- Responsive UI for mobile-first usage

## Technology stack
- Python 3.11+
- Flask 3.0.2
- SQLite
- HTML / CSS / Jinja templates

## Project structure
- `app.py` – Flask routes and business logic
- `init_db.py` – database setup and menu seeding
- `templates/` – customer and staff pages
- `static/style.css` – styling
- `database.db` – SQLite database

## Setup instructions
1. Create a virtual environment:
   `py -m venv .venv`
2. Activate the environment:
   `.venv\Scripts\Activate.ps1`
3. Install dependencies:
   `python -m pip install -r requirements.txt`
4. Initialize the database:
   `python init_db.py`
5. Run the application:
   `python app.py`
6. Open the browser:
   `http://127.0.0.1:5000`

## Suggested demo flow
1. Open `/menu` as the customer entry point.
2. Select an item and place an order.
3. Save the generated order code.
4. Open `/track` and search by the order code.
5. Open `/orders` as staff and update the status.
6. Refresh `/track/<order_code>` to show the changed status.
7. Open `/dashboard` to show summary metrics.

## Jira / Confluence alignment
This MVP now supports these core backlog themes:
- Customer ordering experience
- QR access and low-friction entry
- Staff order management
- Order tracking
- Technical foundation for later admin features

## Known future enhancements
- Admin authentication
- Menu management UI
- Notifications
- Feedback collection
- QR image generation
