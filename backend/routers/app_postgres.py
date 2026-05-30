from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ============================================
# DATABASE CONFIG
# ============================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'M1l02025')
}

def get_db():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise

# ============================================
# ORDERS ENDPOINTS
# ============================================

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders with customer and product info"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT 
                o.order_id,
                o.customer_id,
                c.name as customer_name,
                c.email as customer_email,
                o.product_id,
                p.product_name,
                o.quantity,
                o.unit_price,
                o.total_price,
                o.status,
                o.notes,
                o.created_at,
                o.updated_at
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN products p ON o.product_id = p.product_id
            ORDER BY o.created_at DESC
        ''')
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert datetime objects to strings
        orders = [dict(row) for row in orders]
        for order in orders:
            if order['created_at']:
                order['created_at'] = order['created_at'].isoformat()
            if order['updated_at']:
                order['updated_at'] = order['updated_at'].isoformat()
        
        return jsonify({'success': True, 'data': orders, 'count': len(orders)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """Get single order by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT 
                o.order_id,
                o.customer_id,
                c.name as customer_name,
                o.product_id,
                p.product_name,
                o.quantity,
                o.unit_price,
                o.total_price,
                o.status,
                o.notes,
                o.created_at,
                o.updated_at
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN products p ON o.product_id = p.product_id
            WHERE o.order_id = %s
        ''', (order_id,))
        order = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        order = dict(order)
        if order['created_at']:
            order['created_at'] = order['created_at'].isoformat()
        if order['updated_at']:
            order['updated_at'] = order['updated_at'].isoformat()
        
        return jsonify({'success': True, 'data': order})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create new order"""
    data = request.get_json()
    
    # Validations
    errors = []
    
    if not data.get('customer_id') or int(data.get('customer_id', 0)) < 1:
        errors.append('Invalid customer ID')
    
    if not data.get('product_id') or int(data.get('product_id', 0)) < 1:
        errors.append('Invalid product ID')
    
    if not data.get('quantity') or int(data.get('quantity', 0)) < 1:
        errors.append('Quantity must be at least 1')
    
    if not data.get('unit_price') or float(data.get('unit_price', 0)) <= 0:
        errors.append('Unit price must be greater than 0')
    
    if not data.get('status') or data.get('status') not in ['pending', 'processing', 'completed', 'cancelled']:
        errors.append('Invalid status')
    
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        customer_id = int(data['customer_id'])
        product_id = int(data['product_id'])
        quantity = int(data['quantity'])
        unit_price = float(data['unit_price'])
        status = data['status']
        notes = data.get('notes', None)
        
        total_price = quantity * unit_price
        
        cursor.execute('''
            INSERT INTO orders (customer_id, product_id, quantity, unit_price, total_price, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id
        ''', (customer_id, product_id, quantity, unit_price, total_price, status, notes))
        
        order_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'data': {'order_id': order_id}
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    """Update order quantity and/or status"""
    data = request.get_json()
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get current order
        cursor.execute('SELECT * FROM orders WHERE order_id = %s', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        order = dict(order)
        
        # Update fields if provided
        quantity = int(data.get('quantity', order['quantity']))
        status = data.get('status', order['status'])
        notes = data.get('notes', order['notes'])
        
        if quantity < 1:
            return jsonify({'success': False, 'error': 'Quantity must be at least 1'}), 400
        
        total_price = quantity * order['unit_price']
        
        cursor.execute('''
            UPDATE orders 
            SET quantity = %s, total_price = %s, status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s
        ''', (quantity, total_price, status, notes, order_id))
        
        # Log status change in history
        if status != order['status']:
            cursor.execute('''
                INSERT INTO order_history (order_id, old_status, new_status, changed_by)
                VALUES (%s, %s, %s, %s)
            ''', (order_id, order['status'], status, 'API'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'data': {'order_id': order_id, 'updated': True}})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete order"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM orders WHERE order_id = %s', (order_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        cursor.execute('DELETE FROM orders WHERE order_id = %s', (order_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'deleted': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# CUSTOMERS ENDPOINTS
# ============================================

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Get all customers"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM customers ORDER BY name')
        customers = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'data': customers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# PRODUCTS ENDPOINTS
# ============================================

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM products ORDER BY product_name')
        products = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'data': products})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# REPORTS ENDPOINTS
# ============================================

@app.route('/api/reports/sales-by-customer', methods=['GET'])
def sales_by_customer():
    """Get total sales by customer"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT 
                c.customer_id,
                c.name,
                c.email,
                COUNT(o.order_id) as total_orders,
                SUM(o.total_price) as total_spent,
                AVG(o.total_price) as avg_order_value
            FROM customers c
            LEFT JOIN orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_id, c.name, c.email
            ORDER BY total_spent DESC NULLS LAST
        ''')
        data = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/orders-by-status', methods=['GET'])
def orders_by_status():
    """Get orders grouped by status"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count,
                SUM(total_price) as total_amount,
                AVG(total_price) as avg_amount
            FROM orders
            GROUP BY status
            ORDER BY count DESC
        ''')
        data = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/api/health', methods=['GET'])
def health():
    """Check API and database health"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        return jsonify({
            'status': 'healthy',
            'service': 'Order Management API',
            'database': 'PostgreSQL',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Order Management API - PostgreSQL Edition")
    print("="*60)
    print(f"✓ Database Host: {DB_CONFIG['host']}")
    print(f"✓ Database Port: {DB_CONFIG['port']}")
    print(f"✓ Database Name: {DB_CONFIG['database']}")
    print(f"✓ Server: http://localhost:5000")
    print(f"✓ CORS: Enabled")
    
    print("\nEndpoints:")
    print("  GET    /api/orders")
    print("  POST   /api/orders")
    print("  GET    /api/orders/<id>")
    print("  PUT    /api/orders/<id>")
    print("  DELETE /api/orders/<id>")
    print("  GET    /api/customers")
    print("  GET    /api/products")
    print("  GET    /api/reports/sales-by-customer")
    print("  GET    /api/reports/orders-by-status")
    print("  GET    /api/health")
    
    print("\nStarting server...\n")
    print("="*60)
    
    app.run(debug=True, port=5000)
