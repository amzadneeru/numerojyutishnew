"""
Inventory Stock Management Routes
Handles CRUD operations for inventory_stock table
"""

import logging
import os
from flask import Blueprint, request, jsonify
import psycopg2
from datetime import datetime

inventory_bp = Blueprint('inventory_bp', __name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def get_db_connection():
    """Get database connection using environment variables."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )


@inventory_bp.route('/api/inventory-stock', methods=['GET'])
def get_inventory_stock():
    """
    Retrieve all inventory stock records.
    Optional query parameters: product_id, warehouse_id
    Returns: inventory_id, product_id, warehouse_id, quantity_available, quantity_reserved, reorder_level, last_updated
    """
    try:
        product_id = request.args.get('product_id', type=int)
        warehouse_id = request.args.get('warehouse_id', type=int)

        conn = get_db_connection()
        cur = conn.cursor()

        query = "SELECT inventory_id, product_id, warehouse_id, quantity_available, quantity_reserved, reorder_level, last_updated FROM numerojyutishdb.inventory_stock WHERE 1=1"
        params = []

        if product_id:
            query += " AND product_id = %s"
            params.append(product_id)
        if warehouse_id:
            query += " AND warehouse_id = %s"
            params.append(warehouse_id)

        query += " ORDER BY product_id, warehouse_id"

        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        stocks = [
            {
                'inventory_id': r[0],
                'product_id': r[1],
                'warehouse_id': r[2],
                'quantity_available': float(r[3]) if r[3] else 0,
                'quantity_reserved': float(r[4]) if r[4] else 0,
                'reorder_level': float(r[5]) if r[5] else 0,
                'last_updated': r[6].isoformat() if r[6] else None
            }
            for r in rows
        ]

        logging.info(f"Retrieved {len(stocks)} inventory stock records")
        return jsonify(success=True, data=stocks), 200

    except Exception as e:
        logging.error(f"Error fetching inventory stock: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching inventory stock: {str(e)}'), 500


@inventory_bp.route('/api/inventory-stock/<int:inventory_id>', methods=['GET'])
def get_single_inventory_stock(inventory_id):
    """
    Retrieve a specific inventory stock record by inventory_id.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT inventory_id, product_id, warehouse_id, quantity_available, quantity_reserved, reorder_level, last_updated
            FROM numerojyutishdb.inventory_stock
            WHERE inventory_id = %s
            """,
            (inventory_id,)
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify(success=False, message='Inventory stock not found'), 404

        stock = {
            'inventory_id': row[0],
            'product_id': row[1],
            'warehouse_id': row[2],
            'quantity_available': float(row[3]) if row[3] else 0,
            'quantity_reserved': float(row[4]) if row[4] else 0,
            'reorder_level': float(row[5]) if row[5] else 0,
            'last_updated': row[6].isoformat() if row[6] else None
        }

        return jsonify(success=True, data=stock), 200

    except Exception as e:
        logging.error(f"Error fetching inventory stock {inventory_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching inventory stock: {str(e)}'), 500


@inventory_bp.route('/api/inventory-stock', methods=['POST'])
def create_inventory_stock():
    """
    Create a new inventory stock record.
    Required fields: product_id, warehouse_id, quantity_available
    Optional fields: quantity_reserved (default 0), reorder_level (default 0)
    
    Example request:
    {
        "product_id": 1,
        "warehouse_id": 1,
        "quantity_available": 100,
        "quantity_reserved": 10,
        "reorder_level": 20
    }
    """
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        warehouse_id = data.get('warehouse_id')
        quantity_available = data.get('quantity_available')
        quantity_reserved = data.get('quantity_reserved', 0)
        reorder_level = data.get('reorder_level', 0)

        if not all([product_id, warehouse_id, quantity_available is not None]):
            return jsonify(success=False, message='product_id, warehouse_id, and quantity_available are required'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO numerojyutishdb.inventory_stock (product_id, warehouse_id, quantity_available, quantity_reserved, reorder_level)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING inventory_id, product_id, warehouse_id, quantity_available, quantity_reserved, reorder_level, last_updated
            """,
            (product_id, warehouse_id, quantity_available, quantity_reserved, reorder_level)
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        stock = {
            'inventory_id': row[0],
            'product_id': row[1],
            'warehouse_id': row[2],
            'quantity_available': float(row[3]) if row[3] else 0,
            'quantity_reserved': float(row[4]) if row[4] else 0,
            'reorder_level': float(row[5]) if row[5] else 0,
            'last_updated': row[6].isoformat() if row[6] else None
        }

        logging.info(f"Created inventory stock: product_id={product_id}, warehouse_id={warehouse_id}")
        return jsonify(success=True, data=stock, message='Inventory stock created successfully'), 201

    except Exception as e:
        logging.error(f"Error creating inventory stock: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating inventory stock: {str(e)}'), 500


@inventory_bp.route('/api/inventory-stock/<int:inventory_id>', methods=['PUT'])
def update_inventory_stock(inventory_id):
    """
    Update an existing inventory stock record.
    Updatable fields: quantity_available, quantity_reserved, reorder_level
    
    Example request:
    {
        "quantity_available": 150,
        "quantity_reserved": 30,
        "reorder_level": 25
    }
    """
    try:
        data = request.get_json() or {}

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        update_values = []

        if 'quantity_available' in data:
            update_fields.append("quantity_available = %s")
            update_values.append(data['quantity_available'])
        if 'quantity_reserved' in data:
            update_fields.append("quantity_reserved = %s")
            update_values.append(data['quantity_reserved'])
        if 'reorder_level' in data:
            update_fields.append("reorder_level = %s")
            update_values.append(data['reorder_level'])

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400

        update_fields.append("last_updated = CURRENT_TIMESTAMP")
        update_values.append(inventory_id)

        query = f"""
            UPDATE numerojyutishdb.inventory_stock
            SET {', '.join(update_fields)}
            WHERE inventory_id = %s
            RETURNING inventory_id, product_id, warehouse_id, quantity_available, quantity_reserved, reorder_level, last_updated
        """

        cur.execute(query, update_values)
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Inventory stock not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        stock = {
            'inventory_id': row[0],
            'product_id': row[1],
            'warehouse_id': row[2],
            'quantity_available': float(row[3]) if row[3] else 0,
            'quantity_reserved': float(row[4]) if row[4] else 0,
            'reorder_level': float(row[5]) if row[5] else 0,
            'last_updated': row[6].isoformat() if row[6] else None
        }

        logging.info(f"Updated inventory stock {inventory_id}")
        return jsonify(success=True, data=stock, message='Inventory stock updated successfully'), 200

    except Exception as e:
        logging.error(f"Error updating inventory stock {inventory_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating inventory stock: {str(e)}'), 500


@inventory_bp.route('/api/inventory-stock/<int:inventory_id>', methods=['DELETE'])
def delete_inventory_stock(inventory_id):
    """
    Delete an inventory stock record by inventory_id.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            DELETE FROM numerojyutishdb.inventory_stock
            WHERE inventory_id = %s
            RETURNING inventory_id
            """,
            (inventory_id,)
        )

        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Inventory stock not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        logging.info(f"Deleted inventory stock {inventory_id}")
        return jsonify(success=True, message='Inventory stock deleted successfully'), 200

    except Exception as e:
        logging.error(f"Error deleting inventory stock {inventory_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting inventory stock: {str(e)}'), 500
