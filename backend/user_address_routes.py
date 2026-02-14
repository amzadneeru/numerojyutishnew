"""
User Address Management Routes
Handles saving, retrieving, and managing user delivery addresses for faster checkout.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

user_address_bp = Blueprint('user_address', __name__)

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )


@user_address_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    """
    Retrieve complete user details including profile, contact, and default address.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get user profile information from users and security tables
        cur.execute("""
            SELECT u.user_id, u.full_name, u.email,
                   u.created_at, u.updated_at
            FROM numerojyutishdb.users u
            WHERE u.user_id = %s
        """, (user_id,))
        
        user = cur.fetchone()
        
        if not user:
            conn.close()
            return jsonify(success=False, message='User not found'), 404
        
        # Get default address (most recently used or marked as default)
        cur.execute("""
            SELECT address_id, user_id, address_type, address_line1, address_line2,
                   city, state, postal_code, country_code, is_default,
                   created_at, updated_at
            FROM numerojyutishdb.user_addresses
            WHERE user_id = %s AND is_default = true
            LIMIT 1
        """, (user_id,))
        
        default_address = cur.fetchone()
        
        # Get all addresses
        cur.execute("""
            SELECT address_id, user_id, address_type, address_line1, address_line2,
                   city, state, postal_code, country_code, is_default, created_at, updated_at
            FROM numerojyutishdb.user_addresses
            WHERE user_id = %s
            ORDER BY is_default DESC, updated_at DESC
        """, (user_id,))
        
        addresses = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(
            success=True,
            data={
                'user': dict(user),
                'default_address': dict(default_address) if default_address else None,
                'all_addresses': addresses
            }
        ), 200
    
    except Exception as e:
        logging.error(f"Error retrieving user details for user {user_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving user details: {str(e)}'), 500


@user_address_bp.route('/api/users/<int:user_id>/addresses', methods=['GET'])
def get_user_addresses(user_id):
    """
    Retrieve all addresses for a user.
    Query params: limit (default 20)
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify user exists
        cur.execute("SELECT user_id FROM numerojyutishdb.users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify(success=False, message='User not found'), 404
        
        # Get all addresses
        cur.execute("""
            SELECT address_id, user_id, address_type, address_line1, address_line2,
                   city, state, postal_code, country_code, is_default, created_at, updated_at
            FROM numerojyutishdb.user_addresses
            WHERE user_id = %s
            ORDER BY is_default DESC, updated_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        addresses = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(success=True, data=addresses), 200
    
    except Exception as e:
        logging.error(f"Error retrieving addresses for user {user_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving addresses: {str(e)}'), 500


@user_address_bp.route('/api/users/<int:user_id>/addresses', methods=['POST'])
def create_user_address(user_id):
    """
    Save a new delivery address for a user.
    
    Expected JSON:
    {
        "address_type": "home",
        "address_line1": "123 Main Street",
        "address_line2": "Apt 4B",
        "city": "Mumbai",
        "state": "Maharashtra",
        "postal_code": "400001",
        "country_code": "IN",
        "is_default": false
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['address_line1', 'city', 'postal_code', 'country_code']
        if not data or not all(k in data for k in required_fields):
            return jsonify(success=False, message='Missing required fields'), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify user exists
        cur.execute("SELECT user_id FROM numerojyutishdb.users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify(success=False, message='User not found'), 404
        
        # If marking as default, unset other defaults
        if data.get('is_default', False):
            cur.execute("""
                UPDATE numerojyutishdb.user_addresses
                SET is_default = false
                WHERE user_id = %s
            """, (user_id,))
        
        # Insert address
        cur.execute("""
            INSERT INTO numerojyutishdb.user_addresses
            (user_id, address_type, address_line1, address_line2, city, state, 
             postal_code, country_code, is_default)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING address_id, created_at
        """, (
            user_id,
            data.get('address_type', 'home'),
            data['address_line1'],
            data.get('address_line2', ''),
            data['city'],
            data.get('state', ''),
            data['postal_code'],
            data['country_code'],
            data.get('is_default', False)
        ))
        
        address = cur.fetchone()
        address_id, created_at = address[0], address[1]
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Address {address_id} created for user {user_id}")
        return jsonify(
            success=True,
            message='Address saved successfully',
            data={
                'address_id': address_id,
                'user_id': user_id,
                'address_type': data.get('address_type', 'home'),
                'address_line1': data['address_line1'],
                'address_line2': data.get('address_line2', ''),
                'city': data['city'],
                'state': data.get('state', ''),
                'postal_code': data['postal_code'],
                'country_code': data['country_code'],
                'is_default': data.get('is_default', False),
                'created_at': created_at.isoformat() if created_at else None
            }
        ), 201
    
    except Exception as e:
        logging.error(f"Error creating address for user {user_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error saving address: {str(e)}'), 500


@user_address_bp.route('/api/users/addresses/<int:address_id>', methods=['GET'])
def get_address(address_id):
    """
    Retrieve a specific address by ID.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT address_id, user_id, address_type, address_line1, address_line2,
                   city, state, postal_code, country_code, is_default, created_at, updated_at
            FROM numerojyutishdb.user_addresses
            WHERE address_id = %s
        """, (address_id,))
        
        address = cur.fetchone()
        cur.close()
        conn.close()
        
        if not address:
            return jsonify(success=False, message='Address not found'), 404
        
        return jsonify(success=True, data=dict(address)), 200
    
    except Exception as e:
        logging.error(f"Error retrieving address {address_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error retrieving address: {str(e)}'), 500


@user_address_bp.route('/api/users/addresses/<int:address_id>', methods=['PUT'])
def update_address(address_id):
    """
    Update an existing address.
    
    Expected JSON:
    {
        "full_name": "Jane Doe",
        "city": "Bangalore",
        "is_default": true
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(success=False, message='No update fields provided'), 400
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get the address to find user_id
        cur.execute("SELECT user_id FROM numerojyutishdb.user_addresses WHERE address_id = %s", 
                   (address_id,))
        result = cur.fetchone()
        
        if not result:
            conn.close()
            return jsonify(success=False, message='Address not found'), 404
        
        user_id = result[0]
        
        # If marking as default, unset other defaults for this user
        if data.get('is_default', False):
            cur.execute("""
                UPDATE numerojyutishdb.user_addresses
                SET is_default = false
                WHERE user_id = %s AND address_id != %s
            """, (user_id, address_id))
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        field_map = {
            'address_type': 'address_type',
            'address_line1': 'address_line1',
            'address_line2': 'address_line2',
            'city': 'city',
            'state': 'state',
            'postal_code': 'postal_code',
            'country_code': 'country_code',
            'is_default': 'is_default'
        }
        
        for key, col in field_map.items():
            if key in data:
                update_fields.append(f'{col} = %s')
                params.append(data[key])
        
        if not update_fields:
            conn.close()
            return jsonify(success=False, message='No valid update fields provided'), 400
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(address_id)
        
        query = f"UPDATE numerojyutishdb.user_addresses SET {', '.join(update_fields)} WHERE address_id = %s RETURNING *"
        
        cur.execute(query, params)
        updated_address = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Address {address_id} updated")
        return jsonify(
            success=True,
            message='Address updated successfully',
            data=dict(updated_address)
        ), 200
    
    except Exception as e:
        logging.error(f"Error updating address {address_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating address: {str(e)}'), 500


@user_address_bp.route('/api/users/addresses/<int:address_id>', methods=['DELETE'])
def delete_address(address_id):
    """
    Delete a user address.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if address exists
        cur.execute("""
            SELECT address_id, is_default FROM numerojyutishdb.user_addresses 
            WHERE address_id = %s
        """, (address_id,))
        
        address = cur.fetchone()
        
        if not address:
            conn.close()
            return jsonify(success=False, message='Address not found'), 404
        
        # Delete the address
        cur.execute("DELETE FROM numerojyutishdb.user_addresses WHERE address_id = %s", 
                   (address_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Address {address_id} deleted")
        return jsonify(success=True, message='Address deleted successfully'), 200
    
    except Exception as e:
        logging.error(f"Error deleting address {address_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting address: {str(e)}'), 500


@user_address_bp.route('/api/users/<int:user_id>/default-address', methods=['PUT'])
def set_default_address(user_id):
    """
    Set a specific address as the default for a user.
    
    Expected JSON:
    {
        "address_id": 5
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'address_id' not in data:
            return jsonify(success=False, message='address_id is required'), 400
        
        address_id = data['address_id']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verify address belongs to user
        cur.execute("""
            SELECT address_id FROM numerojyutishdb.user_addresses 
            WHERE address_id = %s AND user_id = %s
        """, (address_id, user_id))
        
        if not cur.fetchone():
            conn.close()
            return jsonify(success=False, message='Address not found for this user'), 404
        
        # Unset all default addresses for this user
        cur.execute("""
            UPDATE numerojyutishdb.user_addresses
            SET is_default = false
            WHERE user_id = %s
        """, (user_id,))
        
        # Set the specified address as default
        cur.execute("""
            UPDATE numerojyutishdb.user_addresses
            SET is_default = true
            WHERE address_id = %s
            RETURNING *
        """, (address_id,))
        
        updated_address = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"Address {address_id} set as default for user {user_id}")
        return jsonify(
            success=True,
            message='Default address updated successfully',
            data=dict(updated_address)
        ), 200
    
    except Exception as e:
        logging.error(f"Error setting default address for user {user_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error setting default address: {str(e)}'), 500
