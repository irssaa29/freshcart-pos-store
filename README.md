# ⚡ FreshCart — Online Grocery Store & Physical POS System

A full-stack e-commerce and point-of-sale (POS) web application built with **Python Flask**, **Neon PostgreSQL**, and **Tailwind CSS**. Designed to synchronize in-store walk-in sales and online customer orders against a shared, batch-tracked central inventory.

## 🚀 Key Features

* **Dual-Channel Checkout (Online + Physical POS):** Both the customer storefront (`/`) and in-store POS register (`/admin`) deduct directly from the same PostgreSQL inventory in real time.
* **Batch-Level Expiry Tracking:** Supports multiple inventory batches per product (`inventory_id` + `expiry_date`), automatically highlighting low-stock (`< 10` units) and expiring-soon (`<= 7` days) batches.
* **Dynamic Inventory Restocking:** Admins can restock existing product batches or register brand-new products directly from the dashboard.
* **Online Order & Delivery Monitor:** Tracks pending deliveries, customer contact details, delivery addresses, and provides one-click status updates (`Pending` → `Out for Delivery` → `Delivered`), automatically marking COD payments as `Paid` upon delivery.
* **Role-Protected Admin Portal:** Session-based authentication (`/admin/login`) securing dashboard analytics, inventory controls, and POS operations.

## 🛠️ Tech Stack

* **Backend:** Python 3, Flask, Flask-CORS, Psycopg 3
* **Database:** Neon Serverless PostgreSQL
* **Frontend:** HTML5, Vanilla JavaScript (Fetch API), Tailwind CSS
* **Deployment:** Vercel

## ⚙️ Local Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt