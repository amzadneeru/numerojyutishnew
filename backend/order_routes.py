"""
Order, Order Items, and Invoice Management Routes
Handles the complete purchase process including order creation, retrieval, status updates, and invoice generation.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

order_bp = Blueprint('order', __name__)

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )


@order_bp.route('/api/orders', methods=['POST'])
def create_order():
    """
    Create a new order with associated order items.
    
    Expected JSON:
    {
        "user_id": 1,
        "country_code": "IN",
        "items": [
            {
                "product_id": 10,
                "quantity": 2,
                "unit_price": 299.00,
                "discount": 0,
                "tax_percent": 18,
                "tax_amount": 107.64
            }
        ],
        "subtotal": 598.00,
        "discount": 0,
        "taxable_amount": 598.00,
        "total_tax": 107.64,
        "total_amount": 705.64
    }
    
    Returns: order_id and order details on success
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(k in data for k in ['user_id', 'country_code', 'items', 'total_amount']):
            return jsonify(success=False, message='Missing required fields'), 400
        
        if not isinstance(data.get('items'), list) or len(data['items']) == 0:
            return jsonify(success=False, message='Items list is required and must not be empty'), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Validate country exists
        cur.execute("SELECT country_code FROM numerojyutishdb.countries WHERE country_code = %s", 
                   (data['country_code'],))
        if not cur.fetchone():
            conn.close()
            return jsonify(success=False, message='Invalid country code'), 400
        
        # Create order
        cur.execute("""
            INSERT INTO numerojyutishdb.orders 
            (user_id, country_code, subtotal, discount, taxable_amount, total_tax, total_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'CREATED')
            RETURNING order_id, created_at
        """, (
            data['user_id'],
            data['country_code'],
            data.get('subtotal', 0),
            data.get('discount', 0),
            data.get('taxable_amount', 0),
            data.get('total_tax', 0),
            data['total_amount']
        ))
        
        order = cur.fetchone()
        order_id, created_at = order[0], order[1]
        
        # Insert order items
        for item in data['items']:
            if not all(k in item for k in ['product_id', 'quantity', 'unit_price']):
                conn.rollback()
                conn.close()
                return jsonify(success=False, message='Missing required item fields'), 400
            
            # Validate product exists
            cur.execute("SELECT product_id FROM numerojyutishdb.products WHERE product_id = %s", 
                       (item['product_id'],))
            if not cur.fetchone():
                conn.rollback()
                conn.close()
                return jsonify(success=False, message=f"Product {item['product_id']} not found"), 404
            
            # Calculate total_amount if not provided
            item_total = item.get('total_amount', 
                                 item['quantity'] * item['unit_price'] + item.get('tax_amount', 0))
            
            cur.execute("""
                INSERT INTO numerojyutishdb.order_items
                (order_id, product_id, quantity, unit_price, discount, tax_percent, tax_amount, total_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING order_item_id
            """, (
                order_id,
                item['product_id'],
                item['quantity'],
                item['unit_price'],
                item.get('discount', 0),
                item.get('tax_percent', 0),
                item.get('tax_amount', 0),
                item_total
            ))
        
        # Create invoice for this order
        try:
            cur.execute("""
                INSERT INTO numerojyutishdb.invoices
                (order_id, invoice_number, subtotal, discount, tax_amount, total_amount, status, invoice_date)
                VALUES (%s, %s, %s, %s, %s, %s, 'DRAFT', CURRENT_TIMESTAMP)
                RETURNING invoice_id, invoice_number
            """, (
                order_id,
                f"INV-{order_id}-{datetime.now().strftime('%Y%m%d')}",
                data.get('subtotal', 0),
                data.get('discount', 0),
                data.get('total_tax', 0),
                data['total_amount']
            ))
            invoice_result = cur.fetchone()
            invoice_id, invoice_number = invoice_result[0], invoice_result[1]
            logging.info(f"Invoice {invoice_number} created for order {order_id}")
        except Exception as inv_err:
            logging.warning(f"Could not create invoice for order {order_id}: {inv_err}")
            invoice_id = None
            invoice_number = None
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Order {order_id} created successfully for user {data['user_id']}")
        return jsonify(
            success=True,
            message='Order created successfully',
            data={
                'order_id': order_id,
                'user_id': data['user_id'],
                'country_code': data['country_code'],
                'total_amount': float(data['total_amount']),
                'status': 'CREATED',
                'invoice_id': invoice_id,
                'invoice_number': invoice_number,
                'created_at': created_at.isoformat() if created_at else None
            }
        ), 201
    
    except Exception as e:
        logging.error(f"Error creating order: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating order: {str(e)}'), 500


@order_bp.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """
    Retrieve order details including all associated order items.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get order details
        cur.execute("""
            SELECT order_id, user_id, country_code, subtotal, discount, 
                   taxable_amount, total_tax, total_amount, status, created_at
            FROM numerojyutishdb.orders
            WHERE order_id = %s
        """, (order_id,))
        
        order = cur.fetchone()
        if not order:
            conn.close()
            return jsonify(success=False, message='Order not found'), 404
        
        # Get order items
        cur.execute("""
            SELECT oi.order_item_id, oi.product_id, p.product_name, oi.quantity, oi.unit_price,
                   oi.discount, oi.tax_percent, oi.tax_amount, oi.total_amount, oi.created_at
            FROM numerojyutishdb.order_items oi
            JOIN numerojyutishdb.products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
            ORDER BY oi.created_at
        """, (order_id,))
        
        items = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert items to list of dicts
        items_list = [dict(item) for item in items]
        
        return jsonify(
            success=True,
            data={
                'order': dict(order),
                'items': items_list
            }
        ), 200
    
    except Exception as e:
        logging.error(f"Error retrieving order {order_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving order: {str(e)}'), 500


@order_bp.route('/api/orders/user/<int:user_id>', methods=['GET'])
def get_user_orders(user_id):
    """
    Retrieve all orders for a specific user with pagination.
    Query params: page (default 1), limit (default 10)
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total count
        cur.execute("SELECT COUNT(*) FROM numerojyutishdb.orders WHERE user_id = %s", (user_id,))
        total = cur.fetchone()['count']
        
        # Get orders
        cur.execute("""
            SELECT order_id, user_id, country_code, subtotal, discount,
                   taxable_amount, total_tax, total_amount, status, created_at
            FROM numerojyutishdb.orders
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        orders = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(
            success=True,
            data={
                'orders': orders,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            }
        ), 200
    
    except Exception as e:
        logging.error(f"Error retrieving orders for user {user_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving orders: {str(e)}'), 500


@order_bp.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """
    Update order status (CREATED, CONFIRMED, SHIPPED, DELIVERED, CANCELLED).
    
    Expected JSON:
    {
        "status": "CONFIRMED"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify(success=False, message='Status field is required'), 400
        
        valid_statuses = ['CREATED', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED']
        if data['status'] not in valid_statuses:
            return jsonify(success=False, message=f'Invalid status. Must be one of: {", ".join(valid_statuses)}'), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE numerojyutishdb.orders
            SET status = %s
            WHERE order_id = %s
            RETURNING order_id, status
        """, (data['status'], order_id))
        
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify(success=False, message='Order not found'), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Order {order_id} status updated to {data['status']}")
        return jsonify(
            success=True,
            message=f'Order status updated to {data["status"]}',
            data={'order_id': order_id, 'status': data['status']}
        ), 200
    
    except Exception as e:
        logging.error(f"Error updating order {order_id} status: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating order status: {str(e)}'), 500


@order_bp.route('/api/orders/<int:order_id>', methods=['DELETE'])
def cancel_order(order_id):
    """
    Cancel an order (soft delete by setting status to CANCELLED).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if order exists and is cancellable
        cur.execute("SELECT status FROM numerojyutishdb.orders WHERE order_id = %s", (order_id,))
        order = cur.fetchone()
        
        if not order:
            conn.close()
            return jsonify(success=False, message='Order not found'), 404
        
        if order[0] == 'CANCELLED':
            conn.close()
            return jsonify(success=False, message='Order is already cancelled'), 400
        
        if order[0] in ['SHIPPED', 'DELIVERED']:
            conn.close()
            return jsonify(success=False, message='Cannot cancel shipped/delivered orders'), 400
        
        # Update status to CANCELLED
        cur.execute("""
            UPDATE numerojyutishdb.orders
            SET status = 'CANCELLED'
            WHERE order_id = %s
            RETURNING order_id
        """, (order_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Order {order_id} cancelled")
        return jsonify(success=True, message='Order cancelled successfully'), 200
    
    except Exception as e:
        logging.error(f"Error cancelling order {order_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error cancelling order: {str(e)}'), 500


@order_bp.route('/api/orders/<int:order_id>/items', methods=['GET'])
def get_order_items(order_id):
    """
    Retrieve all items in an order.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify order exists
        cur.execute("SELECT order_id FROM numerojyutishdb.orders WHERE order_id = %s", (order_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify(success=False, message='Order not found'), 404
        
        # Get order items
        cur.execute("""
            SELECT oi.order_item_id, oi.order_id, oi.product_id, p.product_name,
                   oi.quantity, oi.unit_price, oi.discount, oi.tax_percent, 
                   oi.tax_amount, oi.total_amount, oi.created_at
            FROM numerojyutishdb.order_items oi
            JOIN numerojyutishdb.products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
            ORDER BY oi.created_at
        """, (order_id,))
        
        items = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(success=True, data=items), 200
    
    except Exception as e:
        logging.error(f"Error retrieving order items for order {order_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving order items: {str(e)}'), 500


@order_bp.route('/api/orders/<int:order_id>/items/<int:order_item_id>', methods=['GET'])
def get_order_item(order_id, order_item_id):
    """
    Retrieve a specific order item.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT oi.order_item_id, oi.order_id, oi.product_id, p.product_name,
                   oi.quantity, oi.unit_price, oi.discount, oi.tax_percent,
                   oi.tax_amount, oi.total_amount, oi.created_at, oi.updated_at
            FROM numerojyutishdb.order_items oi
            JOIN numerojyutishdb.products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s AND oi.order_item_id = %s
        """, (order_id, order_item_id))
        
        item = cur.fetchone()
        cur.close()
        conn.close()
        
        if not item:
            return jsonify(success=False, message='Order item not found'), 404
        
        return jsonify(success=True, data=dict(item)), 200
    
    except Exception as e:
        logging.error(f"Error retrieving order item {order_item_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving order item: {str(e)}'), 500


@order_bp.route('/api/orders/stats/summary', methods=['GET'])
def get_order_stats():
    """
    Get summary statistics for all orders.
    Query params: user_id (optional), date_from, date_to
    """
    try:
        user_id = request.args.get('user_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        query = """
            SELECT 
                COUNT(DISTINCT o.order_id) as total_orders,
                COUNT(DISTINCT o.user_id) as unique_customers,
                SUM(o.total_amount) as total_revenue,
                SUM(o.total_tax) as total_tax,
                AVG(o.total_amount) as average_order_value,
                MIN(o.created_at) as first_order_date,
                MAX(o.created_at) as last_order_date
            FROM numerojyutishdb.orders o
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND o.user_id = %s"
            params.append(user_id)
        
        if date_from:
            query += " AND o.created_at >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND o.created_at <= %s"
            params.append(date_to)
        
        cur.execute(query, params)
        stats = cur.fetchone()
        cur.close()
        conn.close()
        
        return jsonify(
            success=True,
            data=dict(stats) if stats else {
                'total_orders': 0,
                'unique_customers': 0,
                'total_revenue': 0,
                'total_tax': 0,
                'average_order_value': 0
            }
        ), 200
    
    except Exception as e:
        logging.error(f"Error retrieving order stats: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving order stats: {str(e)}'), 500


# ============================================================================
# INVOICE ENDPOINTS
# ============================================================================

@order_bp.route('/api/invoices/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """
    Retrieve invoice details including associated order items.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get invoice details
        cur.execute("""
            SELECT invoice_id, order_id, invoice_number, subtotal, discount,
                   tax_amount, total_amount, status, invoice_date, due_date, paid_date, notes
            FROM numerojyutishdb.invoices
            WHERE invoice_id = %s
        """, (invoice_id,))
        
        invoice = cur.fetchone()
        if not invoice:
            conn.close()
            return jsonify(success=False, message='Invoice not found'), 404
        
        # Get associated order items
        order_id = invoice['order_id']
        cur.execute("""
            SELECT oi.order_item_id, oi.product_id, p.product_name, oi.quantity,
                   oi.unit_price, oi.discount, oi.tax_percent, oi.tax_amount, oi.total_amount
            FROM numerojyutishdb.order_items oi
            JOIN numerojyutishdb.products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
            ORDER BY oi.created_at
        """, (order_id,))
        
        items = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(
            success=True,
            data={
                'invoice': dict(invoice),
                'items': items
            }
        ), 200
    
    except Exception as e:
        logging.error(f"Error retrieving invoice {invoice_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving invoice: {str(e)}'), 500


@order_bp.route('/api/invoices/order/<int:order_id>', methods=['GET'])
def get_invoice_by_order(order_id):
    """
    Retrieve invoice associated with an order.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT invoice_id, order_id, invoice_number, subtotal, discount,
                   tax_amount, total_amount, status, invoice_date, due_date, paid_date, notes
            FROM numerojyutishdb.invoices
            WHERE order_id = %s
        """, (order_id,))
        
        invoice = cur.fetchone()
        cur.close()
        conn.close()
        
        if not invoice:
            return jsonify(success=False, message='Invoice not found for this order'), 404
        
        return jsonify(success=True, data=dict(invoice)), 200
    
    except Exception as e:
        logging.error(f"Error retrieving invoice for order {order_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving invoice: {str(e)}'), 500


@order_bp.route('/api/invoices/<int:invoice_id>/status', methods=['PUT'])
def update_invoice_status(invoice_id):
    """
    Update invoice status (DRAFT, SENT, PAID, OVERDUE, CANCELLED).
    
    Expected JSON:
    {
        "status": "SENT",
        "paid_date": "2024-02-15" (optional, required for PAID status)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify(success=False, message='Status field is required'), 400
        
        valid_statuses = ['DRAFT', 'SENT', 'PAID', 'OVERDUE', 'CANCELLED']
        if data['status'] not in valid_statuses:
            return jsonify(success=False, message=f'Invalid status. Must be one of: {", ".join(valid_statuses)}'), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # If marking as PAID, require paid_date
        paid_date = None
        if data['status'] == 'PAID':
            paid_date = data.get('paid_date', datetime.now().strftime('%Y-%m-%d'))
            cur.execute("""
                UPDATE numerojyutishdb.invoices
                SET status = %s, paid_date = %s
                WHERE invoice_id = %s
                RETURNING invoice_id, status
            """, (data['status'], paid_date, invoice_id))
        else:
            cur.execute("""
                UPDATE numerojyutishdb.invoices
                SET status = %s
                WHERE invoice_id = %s
                RETURNING invoice_id, status
            """, (data['status'], invoice_id))
        
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify(success=False, message='Invoice not found'), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Invoice {invoice_id} status updated to {data['status']}")
        return jsonify(
            success=True,
            message=f'Invoice status updated to {data["status"]}',
            data={'invoice_id': invoice_id, 'status': data['status']}
        ), 200
    
    except Exception as e:
        logging.error(f"Error updating invoice {invoice_id} status: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating invoice status: {str(e)}'), 500


@order_bp.route('/api/invoices/<int:invoice_id>', methods=['PUT'])
def update_invoice(invoice_id):
    """
    Update invoice details (notes, due_date, etc.).
    
    Expected JSON:
    {
        "notes": "Payment terms: Net 30",
        "due_date": "2024-03-15"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(success=False, message='No update fields provided'), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        if 'notes' in data:
            update_fields.append('notes = %s')
            params.append(data['notes'])
        
        if 'due_date' in data:
            update_fields.append('due_date = %s')
            params.append(data['due_date'])
        
        if not update_fields:
            conn.close()
            return jsonify(success=False, message='No valid update fields provided'), 400
        
        params.append(invoice_id)
        query = f"UPDATE numerojyutishdb.invoices SET {', '.join(update_fields)} WHERE invoice_id = %s RETURNING invoice_id"
        
        cur.execute(query, params)
        row = cur.fetchone()
        
        if not row:
            conn.close()
            return jsonify(success=False, message='Invoice not found'), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Invoice {invoice_id} updated")
        return jsonify(success=True, message='Invoice updated successfully', data={'invoice_id': invoice_id}), 200
    
    except Exception as e:
        logging.error(f"Error updating invoice {invoice_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating invoice: {str(e)}'), 500


@order_bp.route('/api/invoices/user/<int:user_id>', methods=['GET'])
def get_user_invoices(user_id):
    """
    Retrieve all invoices for a specific user with pagination.
    Query params: page (default 1), limit (default 10), status (optional)
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status')
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total count
        if status:
            cur.execute("""
                SELECT COUNT(*) FROM numerojyutishdb.invoices i
                JOIN numerojyutishdb.orders o ON i.order_id = o.order_id
                WHERE o.user_id = %s AND i.status = %s
            """, (user_id, status))
        else:
            cur.execute("""
                SELECT COUNT(*) FROM numerojyutishdb.invoices i
                JOIN numerojyutishdb.orders o ON i.order_id = o.order_id
                WHERE o.user_id = %s
            """, (user_id,))
        
        total = cur.fetchone()['count']
        
        # Get invoices
        if status:
            cur.execute("""
                SELECT i.invoice_id, i.order_id, i.invoice_number, i.subtotal, i.discount,
                       i.tax_amount, i.total_amount, i.status, i.invoice_date, i.due_date, i.paid_date
                FROM numerojyutishdb.invoices i
                JOIN numerojyutishdb.orders o ON i.order_id = o.order_id
                WHERE o.user_id = %s AND i.status = %s
                ORDER BY i.invoice_date DESC
                LIMIT %s OFFSET %s
            """, (user_id, status, limit, offset))
        else:
            cur.execute("""
                SELECT i.invoice_id, i.order_id, i.invoice_number, i.subtotal, i.discount,
                       i.tax_amount, i.total_amount, i.status, i.invoice_date, i.due_date, i.paid_date
                FROM numerojyutishdb.invoices i
                JOIN numerojyutishdb.orders o ON i.order_id = o.order_id
                WHERE o.user_id = %s
                ORDER BY i.invoice_date DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
        
        invoices = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(
            success=True,
            data={
                'invoices': invoices,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            }
        ), 200
    
    except Exception as e:
        logging.error(f"Error retrieving invoices for user {user_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving invoices: {str(e)}'), 500


@order_bp.route('/api/invoices/stats/summary', methods=['GET'])
def get_invoice_stats():
    """
    Get invoice statistics (total invoiced, paid, pending, overdue).
    Query params: user_id (optional), date_from, date_to
    """
    try:
        user_id = request.args.get('user_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        query = """
            SELECT 
                COUNT(*) as total_invoices,
                SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_invoices,
                SUM(CASE WHEN status IN ('DRAFT', 'SENT') THEN 1 ELSE 0 END) as pending_invoices,
                SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) as overdue_invoices,
                SUM(total_amount) as total_invoiced,
                SUM(CASE WHEN status = 'PAID' THEN total_amount ELSE 0 END) as total_paid,
                SUM(CASE WHEN status IN ('DRAFT', 'SENT') THEN total_amount ELSE 0 END) as pending_amount,
                SUM(CASE WHEN status = 'OVERDUE' THEN total_amount ELSE 0 END) as overdue_amount
            FROM numerojyutishdb.invoices i
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += """
                AND EXISTS (
                    SELECT 1 FROM numerojyutishdb.orders o
                    WHERE o.order_id = i.order_id AND o.user_id = %s
                )
            """
            params.append(user_id)
        
        if date_from:
            query += " AND i.invoice_date >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND i.invoice_date <= %s"
            params.append(date_to)
        
        cur.execute(query, params)
        stats = cur.fetchone()
        cur.close()
        conn.close()
        
        return jsonify(
            success=True,
            data=dict(stats) if stats else {
                'total_invoices': 0,
                'paid_invoices': 0,
                'pending_invoices': 0,
                'overdue_invoices': 0,
                'total_invoiced': 0,
                'total_paid': 0,
                'pending_amount': 0,
                'overdue_amount': 0
            }
        ), 200
    
    except Exception as e:
        logging.error(f"Error retrieving invoice stats: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving invoice stats: {str(e)}'), 500
