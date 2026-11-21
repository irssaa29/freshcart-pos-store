import os
from datetime import datetime, date
from decimal import Decimal
from flask import (
    Flask,
    request,
    jsonify,
    session,
    render_template
)
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg.errors import IntegrityError
from db import get_connection, fetch_all, fetch_one, execute_query

# ==========================================================
# APP CONFIGURATION
# ==========================================================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "temporary-development-secret")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
CORS(app, supports_credentials=True)

# ==========================================================
# BASIC ROUTES & HEALTH CHECK
# ==========================================================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        result = fetch_one("SELECT NOW() as server_time")
        return jsonify({
            "success": True,
            "message": "Database connection is working.",
            "data": {
                "server_time": result["server_time"].isoformat() if result else None
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Database connection failed: {str(e)}"
        }), 500

# ==========================================================
# CUSTOMER AUTHENTICATION ENDPOINTS
# ==========================================================
@app.route("/api/auth/register", methods=["POST"])
def customer_register():
    data = request.get_json() or {}
    name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone_number") or data.get("phone")
    address = data.get("address")

    if not name or not email or not password:
        return jsonify({"success": False, "message": "Missing required fields (full_name, email, password)."}), 400

    hashed_password = generate_password_hash(password)

    try:
        query = """
            INSERT INTO customers (full_name, email, password_hash, phone, address)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING customer_id
        """
        customer_id = execute_query(query, (name, email, hashed_password, phone, address), fetch_id=True)
        return jsonify({"success": True, "message": "Customer registered successfully.", "customer_id": customer_id}), 201
    except IntegrityError:
        return jsonify({"success": False, "message": "Email already exists."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/auth/login", methods=["POST"])
def customer_login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    customer = fetch_one("SELECT * FROM customers WHERE email = %s", (email,))
    if not customer or not check_password_hash(customer["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    session["customer_id"] = customer["customer_id"]
    session["customer_email"] = customer["email"]

    return jsonify({
        "success": True,
        "message": "Logged in successfully.",
        "customer": {
            "customer_id": customer["customer_id"],
            "full_name": customer["full_name"],
            "email": customer["email"]
        }
    })

@app.route("/api/auth/logout", methods=["POST"])
def customer_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})

# ==========================================================
# PRODUCTS & CATEGORIES
# ==========================================================
@app.route("/api/categories", methods=["GET"])
def get_categories():
    try:
        categories = fetch_all("SELECT * FROM categories ORDER BY category_name")
        return jsonify({"success": True, "data": categories})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/products", methods=["GET"])
def get_products():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    i.inventory_id,
                    p.product_id, 
                    p.product_name, 
                    p.price, 
                    i.quantity_available, 
                    i.expiry_date
                FROM inventory i
                JOIN products p ON i.product_id = p.product_id
                ORDER BY p.product_name ASC, i.expiry_date ASC NULLS LAST
            """)
            rows = cur.fetchall()
            # Format date to string so JSON serializes cleanly
            for r in rows:
                if r["expiry_date"]:
                    r["expiry_date"] = r["expiry_date"].strftime("%Y-%m-%d")
            return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

# ==========================================================
# CHECKOUT & TRANSACTION (ONLINE ORDERS)
# ==========================================================
@app.route("/api/orders/checkout", methods=["POST"])
def checkout():
    data = request.get_json() or {}
    customer_id = data.get("customer_id")
    items = data.get("items", [])
    payment_method = data.get("payment_method", "Cash on Delivery")
    delivery_address = data.get("delivery_address", "Multan, Pakistan")

    if not customer_id or not items:
        return jsonify({"success": False, "message": "Customer ID and items are required."}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            total_amount = Decimal('0.00')
            processed_items = []

            # 1. Verify and lock inventory rows
            for item in items:
                prod_id = item["product_id"]
                qty = int(item["quantity"])

                cur.execute("SELECT product_id, price FROM products WHERE product_id = %s", (prod_id,))
                prod = cur.fetchone()
                if not prod:
                    raise Exception(f"Product ID {prod_id} not found.")

                cur.execute("SELECT quantity_available FROM inventory WHERE product_id = %s FOR UPDATE", (prod_id,))
                inv = cur.fetchone()
                if not inv or inv["quantity_available"] < qty:
                    raise Exception(f"Insufficient stock for product ID {prod_id}.")

                subtotal = prod["price"] * qty
                total_amount += subtotal
                processed_items.append({"product_id": prod_id, "quantity": qty, "price": prod["price"]})

            # 2. Create Order
            cur.execute("""
                INSERT INTO orders (customer_id, order_date, order_status, total_amount)
                VALUES (%s, CURRENT_DATE, 'Pending', %s)
                RETURNING order_id
            """, (customer_id, total_amount))
            order_id = cur.fetchone()["order_id"]

            # 3. Create Order Details & Decrease Inventory
            for item in processed_items:
                cur.execute("""
                    INSERT INTO order_details (order_id, product_id, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, item["product_id"], item["quantity"], item["price"]))

                cur.execute("""
                    UPDATE inventory
                    SET quantity_available = quantity_available - %s
                    WHERE product_id = %s
                """, (item["quantity"], item["product_id"]))

            # 4. Create Payment Record
            cur.execute("""
                INSERT INTO payments (order_id, payment_method, amount, discount, payment_status, payment_date)
                VALUES (%s, %s, %s, 0.00, 'Pending', CURRENT_DATE)
            """, (order_id, payment_method, total_amount))

            # 5. Create Delivery Record
            cur.execute("""
                INSERT INTO deliveries (order_id, delivery_address, delivery_status, expected_date)
                VALUES (%s, %s, 'Pending', CURRENT_DATE + INTERVAL '3 days')
            """, (order_id, delivery_address))

            conn.commit()
            return jsonify({"success": True, "message": "Order placed successfully.", "order_id": order_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        conn.close()
# ==========================================================
# ADMIN DASHBOARD & STATISTICS
# ==========================================================
from flask import session, redirect, url_for, render_template

# Admin Login Page Route
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        username = data.get("username")
        password = data.get("password")
        
        # Query database to check if this approved admin exists
        admin_record = fetch_one(
            "SELECT * FROM admins WHERE username = %s AND password = %s", 
            (username, password)
        )
        
        if admin_record:
            session['is_admin'] = True
            session['admin_user'] = username
            if request.is_json:
                return jsonify({"success": True, "message": "Login successful!"})
            return redirect(url_for('admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({"success": False, "message": "Invalid credentials or unauthorized username."}), 401
            return render_template("admin_login.html", error="Invalid username or password")
            
    return render_template("admin_login.html")

# Admin Logout Route
@app.route("/admin/logout")
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

# Protect your existing /admin dashboard route
@app.route("/admin")
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    return render_template("admin.html")

@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    try:
        customers_count = fetch_one("SELECT COUNT(*) as count FROM customers")["count"]
        products_count = fetch_one("SELECT COUNT(*) as count FROM products")["count"]
        orders_count = fetch_one("SELECT COUNT(*) as count FROM orders")["count"]
        total_sales = fetch_one("SELECT SUM(total_amount) as total FROM orders WHERE order_status != 'Cancelled'")["total"] or 0

        return jsonify({
            "success": True,
            "data": {
                "total_customers": customers_count,
                "total_products": products_count,
                "total_orders": orders_count,
                "total_sales": float(total_sales)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

#admin restock
@app.route("/api/admin/restock", methods=["POST"])
def admin_restock():
    data = request.get_json() or {}
    is_new = data.get("is_new_product", False)
    product_id = data.get("product_id")
    quantity_added = int(data.get("quantity", 0))
    expiry_date = data.get("expiry_date")

    if quantity_added <= 0 or not expiry_date:
        return jsonify({"success": False, "message": "Valid quantity and expiry date are required."}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. If brand-new product, insert into products table first
            if is_new:
                name = (data.get("product_name") or "").strip()
                category = (data.get("category") or "General").strip()
                price = data.get("price")

                if not name or price is None or float(price) <= 0:
                    return jsonify({"success": False, "message": "New product requires a valid name and price."}), 400

                cur.execute("""
                    INSERT INTO products (product_name, category, price)
                    VALUES (%s, %s, %s)
                    RETURNING product_id
                """, (name, category, Decimal(str(price))))
                product_id = cur.fetchone()["product_id"]

            # 2. Check if a batch with the exact same product_id & expiry_date exists
            cur.execute("""
                SELECT inventory_id FROM inventory 
                WHERE product_id = %s AND expiry_date = %s
            """, (product_id, expiry_date))
            existing_batch = cur.fetchone()

            if existing_batch:
                cur.execute("""
                    UPDATE inventory 
                    SET quantity_available = quantity_available + %s
                    WHERE inventory_id = %s
                """, (quantity_added, existing_batch["inventory_id"]))
            else:
                cur.execute("""
                    INSERT INTO inventory (product_id, quantity_available, expiry_date, stock_status)
                    VALUES (%s, %s, %s, 'Available')
                """, (product_id, quantity_added, expiry_date))

            conn.commit()
            msg = "New product and initial batch added!" if is_new else "Batch stock updated successfully!"
            return jsonify({"success": True, "message": msg})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        conn.close()
# ==========================================================
# PHYSICAL POS CHECKOUT (In-Store Sale)
# ==========================================================
@app.route("/api/pos/checkout", methods=["POST"])
def pos_checkout():
    data = request.get_json() or {}
    items = data.get("items", [])
    payment_method = data.get("payment_method", "Cash")

    if not items:
        return jsonify({"success": False, "message": "No items provided for POS sale."}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            total_amount = Decimal('0.00')
            processed_items = []

            # 1. Validate stock and compute total
            for item in items:
                inv_id = item["inventory_id"]
                prod_id = item["product_id"]
                qty = int(item["quantity"])

                cur.execute("SELECT price FROM products WHERE product_id = %s", (prod_id,))
                prod = cur.fetchone()
                if not prod:
                    raise Exception(f"Product ID {prod_id} not found.")

                cur.execute("SELECT quantity_available FROM inventory WHERE inventory_id = %s FOR UPDATE", (inv_id,))
                inv = cur.fetchone()
                if not inv or inv["quantity_available"] < qty:
                    raise Exception(f"Insufficient stock in selected batch (Batch ID {inv_id}).")

                subtotal = prod["price"] * qty
                total_amount += subtotal
                processed_items.append({
                    "inventory_id": inv_id,
                    "product_id": prod_id,
                    "quantity": qty,
                    "price": prod["price"]
                })

            # 2. Create Order marked as Physical / Walk-in
            cur.execute("""
                INSERT INTO orders (customer_id, order_date, order_status, total_amount, order_type)
                VALUES (NULL, CURRENT_DATE, 'Delivered', %s, 'Physical')
                RETURNING order_id
            """, (total_amount,))
            order_id = cur.fetchone()["order_id"]

            # 3. Add order details & decrement shared inventory
            for item in processed_items:
                cur.execute("""
                    INSERT INTO order_details (order_id, product_id, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, item["product_id"], item["quantity"], item["price"]))

                cur.execute("""
                    UPDATE inventory
                    SET quantity_available = quantity_available - %s
                    WHERE inventory_id = %s
                """, (item["quantity"], item["inventory_id"]))

            # 4. Record Payment
            cur.execute("""
                INSERT INTO payments (order_id, payment_method, amount, discount, payment_status, payment_date)
                VALUES (%s, %s, %s, 0.00, 'Paid', CURRENT_DATE)
            """, (order_id, payment_method, total_amount))

            conn.commit()
        return jsonify({"success": True, "message": "POS sale completed successfully.", "order_id": order_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        conn.close()
@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

# ==========================================================
# ONLINE ORDERS & DELIVERY MANAGEMENT (ADMIN)
# ==========================================================
@app.route("/api/admin/online-orders", methods=["GET"])
def get_admin_online_orders():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    o.order_id,
                    o.order_date,
                    o.total_amount,
                    o.order_status,
                    c.full_name AS customer_name,
                    c.phone AS customer_phone,
                    d.delivery_id,
                    d.delivery_address,
                    d.delivery_status,
                    d.expected_date,
                    p.payment_method,
                    p.payment_status
                FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                LEFT JOIN deliveries d ON o.order_id = d.order_id
                LEFT JOIN payments p ON o.order_id = p.order_id
                WHERE o.customer_id IS NOT NULL
                ORDER BY 
                    CASE WHEN COALESCE(d.delivery_status, o.order_status) = 'Pending' THEN 0 ELSE 1 END,
                    o.order_id DESC
            """)
            orders = cur.fetchall()

            pending_count = 0
            for row in orders:
                if row["order_date"]:
                    row["order_date"] = row["order_date"].strftime("%Y-%m-%d")
                if row["expected_date"]:
                    row["expected_date"] = row["expected_date"].strftime("%Y-%m-%d")
                row["total_amount"] = float(row["total_amount"])

                status = row["delivery_status"] or row["order_status"] or "Pending"
                row["effective_status"] = status
                if status == "Pending":
                    pending_count += 1

            return jsonify({
                "success": True,
                "pending_count": pending_count,
                "data": orders
            })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/admin/orders/<int:order_id>/delivery-status", methods=["POST"])
def update_delivery_status(order_id):
    data = request.get_json() or {}
    new_status = data.get("delivery_status")

    if new_status not in ["Pending", "Out for Delivery", "Delivered", "Cancelled"]:
        return jsonify({"success": False, "message": "Invalid delivery status."}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Update deliveries table
            cur.execute("""
                UPDATE deliveries
                SET delivery_status = %s
                WHERE order_id = %s
            """, (new_status, order_id))

            # Sync orders table & mark COD payment as Paid when Delivered
            cur.execute("""
                UPDATE orders
                SET order_status = %s
                WHERE order_id = %s
            """, (new_status, order_id))

            if new_status == "Delivered":
                cur.execute("""
                    UPDATE payments
                    SET payment_status = 'Paid'
                    WHERE order_id = %s
                """, (order_id,))

            conn.commit()
            return jsonify({"success": True, "message": f"Order #{order_id} marked as {new_status}."})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        conn.close()
# ==========================================================
# RUN SERVER
# ==========================================================
if __name__ == "__main__":
    print("=======================================================")
    print(" ONLINE GROCERY STORE BACKEND                          ")
    print("=======================================================")
    print("Server: http://127.0.0.1:5000")
    print("Database: Neon PostgreSQL")
    print("=======================================================")
    app.run(debug=True, port=5000)
