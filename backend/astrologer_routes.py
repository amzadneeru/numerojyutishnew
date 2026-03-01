"""
Astrologer Consultation Routes
Handles listing astrologers, viewing profiles, managing consultations, and ratings.
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import cloudinary
import cloudinary.uploader

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

astrologer_bp = Blueprint('astrologer', __name__)


def ensure_booking_tables():
    """Create booking-related tables if they don't exist."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS numerojyutishdb.astrologer_availability (
                availability_id SERIAL PRIMARY KEY,
                astrologer_id INTEGER REFERENCES numerojyutishdb.consult_astrologers(astrologer_id) ON DELETE CASCADE,
                day_of_week VARCHAR(15) NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                is_available BOOLEAN DEFAULT TRUE,
                CHECK (end_time > start_time)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS numerojyutishdb.consult_bookings (
                booking_id SERIAL PRIMARY KEY,
                astrologer_id INTEGER REFERENCES numerojyutishdb.consult_astrologers(astrologer_id),
                user_id INTEGER,
                booking_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                consultation_type VARCHAR(50),
                booking_status VARCHAR(30) DEFAULT 'Pending',
                amount_paid NUMERIC(10,2),
                payment_status VARCHAR(30) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (end_time > start_time)
            )
        """)
        conn.commit()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def ensure_astrologer_pricing_table():
    """Create astrologer pricing table if it doesn't exist."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS numerojyutishdb.astrologer_pricing (
                pricing_id SERIAL PRIMARY KEY,
                astrologer_id INTEGER NOT NULL REFERENCES numerojyutishdb.consult_astrologers(astrologer_id) ON DELETE CASCADE,
                consultation_type VARCHAR(50) NOT NULL,
                price_per_minute NUMERIC(10,2) NOT NULL,
                currency VARCHAR(10) NOT NULL DEFAULT 'INR',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_astrologer_pricing UNIQUE (astrologer_id, consultation_type),
                CHECK (price_per_minute > 0)
            )
        """)
        conn.commit()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def _time_to_str(value):
    return value.strftime('%H:%M') if value else None


def _slot_overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/pricing', methods=['GET'])
@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/charges', methods=['GET'])
def list_astrologer_charges(astrologer_id):
    """List all charges configured for an astrologer."""
    conn = None
    cur = None
    try:
        ensure_astrologer_pricing_table()

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
                 SELECT pricing_id, astrologer_id, consultation_type,
                     price_per_minute, currency, is_active, created_at, updated_at
                 FROM numerojyutishdb.astrologer_pricing
            WHERE astrologer_id = %s
                 ORDER BY consultation_type
        """, (astrologer_id,))
        rows = cur.fetchall()

        return jsonify(
            success=True,
            data=[
                {
                    'pricing_id': row['pricing_id'],
                    'astrologer_id': row['astrologer_id'],
                    'consultation_type': row['consultation_type'],
                    'price_per_minute': float(row['price_per_minute']) if row['price_per_minute'] is not None else 0,
                    'currency': row['currency'],
                    'is_active': row['is_active'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                }
                for row in rows
            ]
        ), 200
    except Exception as e:
        logging.error(f"Error listing astrologer charges for {astrologer_id}: {e}")
        return jsonify(success=False, message=f'Error fetching astrologer charges: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/pricing', methods=['POST'])
@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/charges', methods=['POST'])
def create_astrologer_charge(astrologer_id):
    """
    Create new charge configuration for astrologer.
    Expected JSON:
    {
        "consultation_type": "Call",
        "price_per_minute": 20,
        "currency": "INR",
        "is_active": true
    }
    """
    conn = None
    cur = None
    try:
        ensure_astrologer_pricing_table()
        data = request.get_json() or {}

        consultation_type = (data.get('consultation_type') or '').strip()
        price_per_minute = data.get('price_per_minute')
        currency = (data.get('currency') or 'INR').strip().upper()
        is_active = data.get('is_active', True)

        if not consultation_type:
            return jsonify(success=False, message='consultation_type is required'), 400
        if price_per_minute in (None, ''):
            return jsonify(success=False, message='price_per_minute is required'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT astrologer_id FROM numerojyutishdb.consult_astrologers WHERE astrologer_id = %s", (astrologer_id,))
        if not cur.fetchone():
            return jsonify(success=False, message='Astrologer not found'), 404

        cur.execute("""
            INSERT INTO numerojyutishdb.astrologer_pricing
            (astrologer_id, consultation_type, price_per_minute, currency, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING pricing_id, astrologer_id, consultation_type, price_per_minute, currency, is_active
        """, (astrologer_id, consultation_type, price_per_minute, currency, is_active))
        row = cur.fetchone()
        conn.commit()

        return jsonify(
            success=True,
            message='Astrologer pricing created successfully',
            data={
                'pricing_id': row['pricing_id'],
                'astrologer_id': row['astrologer_id'],
                'consultation_type': row['consultation_type'],
                'price_per_minute': float(row['price_per_minute']) if row['price_per_minute'] is not None else 0,
                'currency': row['currency'],
                'is_active': row['is_active']
            }
        ), 201
    except psycopg2.IntegrityError:
        if conn:
            conn.rollback()
        return jsonify(success=False, message='Pricing already exists for this consultation type'), 409
    except Exception as e:
        logging.error(f"Error creating astrologer pricing for {astrologer_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error creating astrologer pricing: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologer-pricing/<int:pricing_id>', methods=['PUT'])
@astrologer_bp.route('/api/astrologer-charges/<int:pricing_id>', methods=['PUT'])
def update_astrologer_charge(pricing_id):
    """Update an existing astrologer pricing configuration."""
    conn = None
    cur = None
    try:
        ensure_astrologer_pricing_table()
        data = request.get_json() or {}

        update_fields = []
        params = []

        field_map = {
            'consultation_type': 'consultation_type',
            'price_per_minute': 'price_per_minute',
            'currency': 'currency',
            'is_active': 'is_active'
        }

        for key, col in field_map.items():
            if key in data:
                value = data[key]
                if key == 'currency' and isinstance(value, str):
                    value = value.upper()
                update_fields.append(f"{col} = %s")
                params.append(value)

        if not update_fields:
            return jsonify(success=False, message='No update fields provided'), 400

        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(pricing_id)

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = f"""
            UPDATE numerojyutishdb.astrologer_pricing
            SET {', '.join(update_fields)}
            WHERE pricing_id = %s
            RETURNING pricing_id, astrologer_id, consultation_type,
                      price_per_minute, currency, is_active, updated_at
        """
        cur.execute(query, params)
        row = cur.fetchone()

        if not row:
            return jsonify(success=False, message='Charge not found'), 404

        conn.commit()

        return jsonify(
            success=True,
            message='Astrologer pricing updated successfully',
            data={
                'pricing_id': row['pricing_id'],
                'astrologer_id': row['astrologer_id'],
                'consultation_type': row['consultation_type'],
                'price_per_minute': float(row['price_per_minute']) if row['price_per_minute'] is not None else 0,
                'currency': row['currency'],
                'is_active': row['is_active'],
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            }
        ), 200
    except psycopg2.IntegrityError:
        if conn:
            conn.rollback()
        return jsonify(success=False, message='Pricing already exists for this consultation type'), 409
    except Exception as e:
        logging.error(f"Error updating astrologer pricing {pricing_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error updating astrologer pricing: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologer-pricing/<int:pricing_id>', methods=['DELETE'])
@astrologer_bp.route('/api/astrologer-charges/<int:pricing_id>', methods=['DELETE'])
def delete_astrologer_charge(pricing_id):
    """Delete astrologer pricing configuration."""
    conn = None
    cur = None
    try:
        ensure_astrologer_pricing_table()
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            DELETE FROM numerojyutishdb.astrologer_pricing
            WHERE pricing_id = %s
            RETURNING pricing_id
        """, (pricing_id,))
        row = cur.fetchone()

        if not row:
            return jsonify(success=False, message='Charge not found'), 404

        conn.commit()
        return jsonify(success=True, message='Astrologer pricing deleted successfully'), 200
    except Exception as e:
        logging.error(f"Error deleting astrologer pricing {pricing_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error deleting astrologer pricing: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/availability', methods=['POST'])
def create_astrologer_availability(astrologer_id):
    """
    Save astrologer weekly availability.
    Expected JSON:
    {
        "day_of_week": "Monday",
        "start_time": "10:00",
        "end_time": "13:00",
        "is_available": true
    }
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        data = request.get_json() or {}
        day_of_week = (data.get('day_of_week') or '').strip()
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        is_available = data.get('is_available', True)

        if not day_of_week or not start_time or not end_time:
            return jsonify(success=False, message='day_of_week, start_time and end_time are required'), 400

        valid_days = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
        if day_of_week not in valid_days:
            return jsonify(success=False, message='day_of_week must be a valid weekday name'), 400

        start_dt = datetime.strptime(start_time, '%H:%M').time()
        end_dt = datetime.strptime(end_time, '%H:%M').time()
        if end_dt <= start_dt:
            return jsonify(success=False, message='end_time must be greater than start_time'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT astrologer_id FROM numerojyutishdb.consult_astrologers WHERE astrologer_id = %s",
            (astrologer_id,)
        )
        if not cur.fetchone():
            return jsonify(success=False, message='Astrologer not found'), 404

        cur.execute("""
            INSERT INTO numerojyutishdb.astrologer_availability
            (astrologer_id, day_of_week, start_time, end_time, is_available)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING availability_id, astrologer_id, day_of_week, start_time, end_time, is_available
        """, (astrologer_id, day_of_week, start_dt, end_dt, is_available))

        row = cur.fetchone()
        conn.commit()

        return jsonify(
            success=True,
            message='Availability saved successfully',
            data={
                'availability_id': row['availability_id'],
                'astrologer_id': row['astrologer_id'],
                'day_of_week': row['day_of_week'],
                'start_time': _time_to_str(row['start_time']),
                'end_time': _time_to_str(row['end_time']),
                'is_available': row['is_available']
            }
        ), 201
    except ValueError:
        return jsonify(success=False, message='Time format must be HH:MM'), 400
    except Exception as e:
        logging.error(f"Error creating astrologer availability: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error creating availability: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/availability', methods=['GET'])
def get_astrologer_availability(astrologer_id):
    """
    Get availability by astrologer.
    Query params:
    - booking_date (optional): YYYY-MM-DD (filters by weekday)
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        booking_date = request.args.get('booking_date')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        day_filter = None
        if booking_date:
            day_filter = datetime.strptime(booking_date, '%Y-%m-%d').strftime('%A')

        query = """
            SELECT availability_id, astrologer_id, day_of_week, start_time, end_time, is_available
            FROM numerojyutishdb.astrologer_availability
            WHERE astrologer_id = %s AND is_available = true
        """
        params = [astrologer_id]
        if day_filter:
            query += " AND LOWER(day_of_week) = LOWER(%s)"
            params.append(day_filter)

        query += """
            ORDER BY CASE LOWER(day_of_week)
                WHEN 'monday' THEN 1
                WHEN 'tuesday' THEN 2
                WHEN 'wednesday' THEN 3
                WHEN 'thursday' THEN 4
                WHEN 'friday' THEN 5
                WHEN 'saturday' THEN 6
                WHEN 'sunday' THEN 7
                ELSE 99
            END,
            start_time
        """
        cur.execute(query, params)
        rows = cur.fetchall()

        return jsonify(
            success=True,
            data=[
                {
                    'availability_id': row['availability_id'],
                    'astrologer_id': row['astrologer_id'],
                    'day_of_week': row['day_of_week'],
                    'start_time': _time_to_str(row['start_time']),
                    'end_time': _time_to_str(row['end_time']),
                    'is_available': row['is_available']
                }
                for row in rows
            ]
        ), 200
    except ValueError:
        return jsonify(success=False, message='booking_date format must be YYYY-MM-DD'), 400
    except Exception as e:
        logging.error(f"Error fetching availability for astrologer {astrologer_id}: {e}")
        return jsonify(success=False, message=f'Error fetching availability: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/available-slots', methods=['GET'])
def get_available_slots(astrologer_id):
    """
    Get available 30-minute slots for a given date.
    Query params:
    - booking_date: YYYY-MM-DD
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        booking_date = request.args.get('booking_date')
        if not booking_date:
            return jsonify(success=False, message='booking_date is required'), 400

        date_obj = datetime.strptime(booking_date, '%Y-%m-%d').date()
        day_of_week = date_obj.strftime('%A')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT start_time, end_time
            FROM numerojyutishdb.astrologer_availability
            WHERE astrologer_id = %s
                            AND LOWER(day_of_week) = LOWER(%s)
              AND is_available = true
            ORDER BY start_time
        """, (astrologer_id, day_of_week))
        availability_rows = cur.fetchall()

        if not availability_rows:
            return jsonify(success=True, data=[], message='Astrologer has no availability configured for selected day'), 200

        cur.execute("""
            SELECT start_time, end_time
            FROM numerojyutishdb.consult_bookings
            WHERE astrologer_id = %s
              AND booking_date = %s
              AND booking_status IN ('Pending', 'Confirmed')
            ORDER BY start_time
        """, (astrologer_id, date_obj))
        booking_rows = cur.fetchall()

        slots = []
        for row in availability_rows:
            current = datetime.combine(date_obj, row['start_time'])
            end_boundary = datetime.combine(date_obj, row['end_time'])

            while current + timedelta(minutes=30) <= end_boundary:
                slot_start = current.time()
                slot_end = (current + timedelta(minutes=30)).time()

                conflict = any(
                    _slot_overlaps(slot_start, slot_end, booking['start_time'], booking['end_time'])
                    for booking in booking_rows
                )

                if not conflict:
                    slots.append({
                        'start_time': _time_to_str(slot_start),
                        'end_time': _time_to_str(slot_end)
                    })

                current += timedelta(minutes=30)

        return jsonify(success=True, data=slots), 200
    except ValueError:
        return jsonify(success=False, message='booking_date format must be YYYY-MM-DD'), 400
    except Exception as e:
        logging.error(f"Error fetching slots for astrologer {astrologer_id}: {e}")
        return jsonify(success=False, message=f'Error fetching slots: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologer-availability/<int:availability_id>', methods=['PUT'])
def update_astrologer_availability(availability_id):
    """Update a specific astrologer availability entry."""
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        data = request.get_json() or {}

        day_of_week = (data.get('day_of_week') or '').strip()
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        is_available = data.get('is_available', True)

        if not day_of_week or not start_time or not end_time:
            return jsonify(success=False, message='day_of_week, start_time and end_time are required'), 400

        valid_days = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
        if day_of_week not in valid_days:
            return jsonify(success=False, message='day_of_week must be a valid weekday name'), 400

        start_dt = datetime.strptime(start_time, '%H:%M').time()
        end_dt = datetime.strptime(end_time, '%H:%M').time()
        if end_dt <= start_dt:
            return jsonify(success=False, message='end_time must be greater than start_time'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            UPDATE numerojyutishdb.astrologer_availability
            SET day_of_week = %s,
                start_time = %s,
                end_time = %s,
                is_available = %s
            WHERE availability_id = %s
            RETURNING availability_id, astrologer_id, day_of_week, start_time, end_time, is_available
        """, (day_of_week, start_dt, end_dt, is_available, availability_id))

        row = cur.fetchone()
        if not row:
            return jsonify(success=False, message='Availability not found'), 404

        conn.commit()
        return jsonify(
            success=True,
            message='Availability updated successfully',
            data={
                'availability_id': row['availability_id'],
                'astrologer_id': row['astrologer_id'],
                'day_of_week': row['day_of_week'],
                'start_time': _time_to_str(row['start_time']),
                'end_time': _time_to_str(row['end_time']),
                'is_available': row['is_available']
            }
        ), 200
    except ValueError:
        return jsonify(success=False, message='Time format must be HH:MM'), 400
    except Exception as e:
        logging.error(f"Error updating astrologer availability {availability_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error updating availability: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologer-availability/<int:availability_id>', methods=['DELETE'])
def delete_astrologer_availability(availability_id):
    """Delete a specific astrologer availability entry."""
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            DELETE FROM numerojyutishdb.astrologer_availability
            WHERE availability_id = %s
            RETURNING availability_id
        """, (availability_id,))
        row = cur.fetchone()

        if not row:
            return jsonify(success=False, message='Availability not found'), 404

        conn.commit()
        return jsonify(success=True, message='Availability deleted successfully'), 200
    except Exception as e:
        logging.error(f"Error deleting astrologer availability {availability_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error deleting availability: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/consult-bookings', methods=['POST'])
def create_consult_booking():
    """
    Create consultation booking.
    Expected JSON:
    {
        "astrologer_id": 10,
        "user_id": 1001,
        "booking_date": "2026-02-24",
        "start_time": "10:00",
        "end_time": "10:30",
        "consultation_type": "Call",
        "amount_paid": 500
    }
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        ensure_astrologer_pricing_table()
        data = request.get_json() or {}

        required_fields = ['astrologer_id', 'user_id', 'booking_date', 'start_time', 'end_time']
        missing = [field for field in required_fields if data.get(field) in (None, '')]
        if missing:
            return jsonify(success=False, message=f"Missing required fields: {', '.join(missing)}"), 400

        astrologer_id = int(data['astrologer_id'])
        user_id = int(data['user_id'])
        booking_date = datetime.strptime(data['booking_date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        consultation_type = (data.get('consultation_type') or 'Call').strip()
        amount_paid_input = data.get('amount_paid')

        if end_time <= start_time:
            return jsonify(success=False, message='end_time must be greater than start_time'), 400

        day_of_week = booking_date.strftime('%A')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT astrologer_id FROM numerojyutishdb.consult_astrologers WHERE astrologer_id = %s AND is_active = true",
            (astrologer_id,)
        )
        if not cur.fetchone():
            return jsonify(success=False, message='Astrologer not found'), 404

        cur.execute("""
            SELECT start_time, end_time
            FROM numerojyutishdb.astrologer_availability
            WHERE astrologer_id = %s
              AND LOWER(day_of_week) = LOWER(%s)
              AND is_available = true
        """, (astrologer_id, day_of_week))
        availability_rows = cur.fetchall()

        if not availability_rows:
            return jsonify(success=False, message='Astrologer is not available on selected day'), 400

        fits_availability = any(
            start_time >= row['start_time'] and end_time <= row['end_time']
            for row in availability_rows
        )
        if not fits_availability:
            return jsonify(success=False, message='Selected slot is outside astrologer availability'), 400

        cur.execute("""
            SELECT booking_id, start_time, end_time
            FROM numerojyutishdb.consult_bookings
            WHERE astrologer_id = %s
              AND booking_date = %s
              AND booking_status IN ('Pending', 'Confirmed')
        """, (astrologer_id, booking_date))
        conflict_rows = cur.fetchall()

        has_conflict = any(
            _slot_overlaps(start_time, end_time, row['start_time'], row['end_time'])
            for row in conflict_rows
        )
        if has_conflict:
            return jsonify(success=False, message='Selected slot is already booked'), 409

        slot_minutes = int(
            (datetime.combine(booking_date, end_time) - datetime.combine(booking_date, start_time)).total_seconds() / 60
        )

        cur.execute("""
            SELECT pricing_id, price_per_minute
            FROM numerojyutishdb.astrologer_pricing
            WHERE astrologer_id = %s
              AND LOWER(consultation_type) = LOWER(%s)
              AND is_active = true
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
        """, (astrologer_id, consultation_type))
        pricing_row = cur.fetchone()

        if amount_paid_input in (None, ''):
            if not pricing_row:
                return jsonify(
                    success=False,
                    message='No active pricing configured for selected consultation type'
                ), 400

            amount_paid = round(float(pricing_row['price_per_minute']) * slot_minutes, 2)
        else:
            amount_paid = float(amount_paid_input)

        cur.execute("""
            INSERT INTO numerojyutishdb.consult_bookings
            (astrologer_id, user_id, booking_date, start_time, end_time,
             consultation_type, booking_status, amount_paid, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING booking_id, astrologer_id, user_id, booking_date, start_time, end_time,
                      consultation_type, booking_status, amount_paid, payment_status, created_at
        """, (
            astrologer_id,
            user_id,
            booking_date,
            start_time,
            end_time,
            consultation_type,
            'Pending',
            amount_paid,
            'Pending'
        ))
        booking_row = cur.fetchone()

        conn.commit()

        return jsonify(
            success=True,
            message='Booking created successfully',
            data={
                'booking_id': booking_row['booking_id'],
                'astrologer_id': booking_row['astrologer_id'],
                'user_id': booking_row['user_id'],
                'booking_date': booking_row['booking_date'].isoformat(),
                'start_time': _time_to_str(booking_row['start_time']),
                'end_time': _time_to_str(booking_row['end_time']),
                'consultation_type': booking_row['consultation_type'],
                'booking_status': booking_row['booking_status'],
                'amount_paid': float(booking_row['amount_paid']) if booking_row['amount_paid'] is not None else None,
                'payment_status': booking_row['payment_status'],
                'created_at': booking_row['created_at'].isoformat() if booking_row['created_at'] else None
            }
        ), 201
    except ValueError:
        return jsonify(success=False, message='Invalid input. booking_date must be YYYY-MM-DD and time must be HH:MM'), 400
    except Exception as e:
        logging.error(f"Error creating booking: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error creating booking: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/consult-bookings', methods=['GET'])
def list_consult_bookings():
    """
    List consultation bookings.
    Query params:
    - user_id (required)
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify(success=False, message='user_id is required'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT b.booking_id, b.astrologer_id, b.user_id, b.booking_date, b.start_time, b.end_time,
                   b.consultation_type, b.booking_status, b.amount_paid, b.payment_status, b.created_at,
                   a.full_name, a.display_name, a.currency
            FROM numerojyutishdb.consult_bookings b
            LEFT JOIN numerojyutishdb.consult_astrologers a ON a.astrologer_id = b.astrologer_id
            WHERE b.user_id = %s
            ORDER BY b.booking_date DESC, b.start_time DESC, b.created_at DESC
        """, (user_id,))
        rows = cur.fetchall()

        data = [
            {
                'booking_id': row['booking_id'],
                'astrologer_id': row['astrologer_id'],
                'user_id': row['user_id'],
                'booking_date': row['booking_date'].isoformat() if row['booking_date'] else None,
                'start_time': _time_to_str(row['start_time']),
                'end_time': _time_to_str(row['end_time']),
                'consultation_type': row['consultation_type'],
                'booking_status': row['booking_status'],
                'amount_paid': float(row['amount_paid']) if row['amount_paid'] is not None else None,
                'payment_status': row['payment_status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'astrologer_name': row['display_name'] or row['full_name'],
                'currency': row['currency'] or 'INR'
            }
            for row in rows
        ]

        return jsonify(success=True, data=data), 200
    except Exception as e:
        logging.error(f"Error listing consult bookings: {e}")
        return jsonify(success=False, message=f'Error listing bookings: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/admin/consult-bookings', methods=['GET'])
def admin_list_consult_bookings():
    """List all consultation bookings for admin charge management."""
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        status = request.args.get('payment_status')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT b.booking_id, b.astrologer_id, b.user_id, b.booking_date, b.start_time, b.end_time,
                   b.consultation_type, b.booking_status, b.amount_paid, b.payment_status, b.created_at,
                   a.full_name, a.display_name, a.currency
            FROM numerojyutishdb.consult_bookings b
            LEFT JOIN numerojyutishdb.consult_astrologers a ON a.astrologer_id = b.astrologer_id
        """
        params = []

        if status:
            query += " WHERE b.payment_status = %s"
            params.append(status)

        query += " ORDER BY b.created_at DESC"
        cur.execute(query, params)
        rows = cur.fetchall()

        data = [
            {
                'booking_id': row['booking_id'],
                'astrologer_id': row['astrologer_id'],
                'user_id': row['user_id'],
                'booking_date': row['booking_date'].isoformat() if row['booking_date'] else None,
                'start_time': _time_to_str(row['start_time']),
                'end_time': _time_to_str(row['end_time']),
                'consultation_type': row['consultation_type'],
                'booking_status': row['booking_status'],
                'amount_paid': float(row['amount_paid']) if row['amount_paid'] is not None else 0,
                'payment_status': row['payment_status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'astrologer_name': row['display_name'] or row['full_name'],
                'currency': row['currency'] or 'INR'
            }
            for row in rows
        ]

        return jsonify(success=True, data=data), 200
    except Exception as e:
        logging.error(f"Error listing admin consult bookings: {e}")
        return jsonify(success=False, message=f'Error listing admin bookings: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/admin/consult-bookings/<int:booking_id>/charge', methods=['PUT'])
def admin_update_booking_charge(booking_id):
    """
    Admin update booking charge/payment details.
    Expected JSON:
    {
        "amount_paid": 500,
        "payment_status": "Paid",
        "booking_status": "Confirmed"
    }
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        data = request.get_json() or {}

        payment_status = data.get('payment_status')
        booking_status = data.get('booking_status')
        amount_paid = data.get('amount_paid')

        if payment_status and payment_status not in {'Pending', 'Paid', 'Failed'}:
            return jsonify(success=False, message='Invalid payment_status'), 400
        if booking_status and booking_status not in {'Pending', 'Confirmed', 'Cancelled'}:
            return jsonify(success=False, message='Invalid booking_status'), 400

        update_fields = []
        params = []

        if amount_paid is not None:
            update_fields.append('amount_paid = %s')
            params.append(amount_paid)
        if payment_status is not None:
            update_fields.append('payment_status = %s')
            params.append(payment_status)
        if booking_status is not None:
            update_fields.append('booking_status = %s')
            params.append(booking_status)

        if not update_fields:
            return jsonify(success=False, message='No update fields provided'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        params.append(booking_id)
        query = f"""
            UPDATE numerojyutishdb.consult_bookings
            SET {', '.join(update_fields)}
            WHERE booking_id = %s
            RETURNING booking_id, amount_paid, payment_status, booking_status
        """
        cur.execute(query, params)
        row = cur.fetchone()

        if not row:
            return jsonify(success=False, message='Booking not found'), 404

        conn.commit()

        return jsonify(
            success=True,
            message='Booking charge details updated successfully',
            data={
                'booking_id': row['booking_id'],
                'amount_paid': float(row['amount_paid']) if row['amount_paid'] is not None else 0,
                'payment_status': row['payment_status'],
                'booking_status': row['booking_status']
            }
        ), 200
    except Exception as e:
        logging.error(f"Error updating admin booking charge {booking_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error updating booking charge: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/consult-bookings/<int:booking_id>', methods=['GET'])
def get_consult_booking(booking_id):
    """Get consult booking details by booking_id."""
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT b.booking_id, b.astrologer_id, b.user_id, b.booking_date, b.start_time, b.end_time,
                   b.consultation_type, b.booking_status, b.amount_paid, b.payment_status, b.created_at,
                   a.full_name, a.display_name, a.currency, a.consultation_fee
            FROM numerojyutishdb.consult_bookings b
            LEFT JOIN numerojyutishdb.consult_astrologers a ON a.astrologer_id = b.astrologer_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        row = cur.fetchone()

        if not row:
            return jsonify(success=False, message='Booking not found'), 404

        return jsonify(
            success=True,
            data={
                'booking_id': row['booking_id'],
                'astrologer_id': row['astrologer_id'],
                'user_id': row['user_id'],
                'booking_date': row['booking_date'].isoformat() if row['booking_date'] else None,
                'start_time': _time_to_str(row['start_time']),
                'end_time': _time_to_str(row['end_time']),
                'consultation_type': row['consultation_type'],
                'booking_status': row['booking_status'],
                'amount_paid': float(row['amount_paid']) if row['amount_paid'] is not None else None,
                'payment_status': row['payment_status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'astrologer_name': row['display_name'] or row['full_name'],
                'currency': row['currency'] or 'INR',
                'consultation_fee': float(row['consultation_fee']) if row['consultation_fee'] is not None else None
            }
        ), 200
    except Exception as e:
        logging.error(f"Error fetching booking {booking_id}: {e}")
        return jsonify(success=False, message=f'Error fetching booking: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/consult-bookings/<int:booking_id>/charge', methods=['POST'])
def charge_consult_booking(booking_id):
    """
    Mark booking payment as paid and confirm booking.
    Expected JSON:
    {
        "payment_method": "card",
        "transaction_ref": "TXN12345",
        "amount_paid": 500
    }
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        data = request.get_json() or {}
        payment_method = (data.get('payment_method') or 'card').strip().lower()
        transaction_ref = (data.get('transaction_ref') or '').strip()
        amount_paid = data.get('amount_paid')

        valid_methods = {'card', 'upi', 'bank'}
        if payment_method not in valid_methods:
            return jsonify(success=False, message='payment_method must be one of card, upi, bank'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT booking_id, booking_status, payment_status, amount_paid
            FROM numerojyutishdb.consult_bookings
            WHERE booking_id = %s
        """, (booking_id,))
        existing = cur.fetchone()
        if not existing:
            return jsonify(success=False, message='Booking not found'), 404

        if existing['payment_status'] == 'Paid':
            return jsonify(success=False, message='Booking already paid'), 409

        final_amount = amount_paid if amount_paid is not None else existing['amount_paid']
        if final_amount is None:
            final_amount = 0

        cur.execute("""
            UPDATE numerojyutishdb.consult_bookings
            SET amount_paid = %s,
                payment_status = 'Paid',
                booking_status = 'Confirmed'
            WHERE booking_id = %s
            RETURNING booking_id, booking_status, amount_paid, payment_status
        """, (final_amount, booking_id))
        updated = cur.fetchone()
        conn.commit()

        return jsonify(
            success=True,
            message='Payment successful and booking confirmed',
            data={
                'booking_id': updated['booking_id'],
                'booking_status': updated['booking_status'],
                'amount_paid': float(updated['amount_paid']) if updated['amount_paid'] is not None else 0,
                'payment_status': updated['payment_status'],
                'payment_method': payment_method,
                'transaction_ref': transaction_ref
            }
        ), 200
    except Exception as e:
        logging.error(f"Error charging booking {booking_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error charging booking: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/consult-bookings/<int:booking_id>/cancel', methods=['PUT'])
def cancel_consult_booking(booking_id):
    """
    Cancel consultation booking.
    Expected JSON:
    {
        "user_id": 1001
    }
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        data = request.get_json() or {}
        user_id = data.get('user_id')
        if not user_id:
            return jsonify(success=False, message='user_id is required'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT booking_id, user_id, booking_status
            FROM numerojyutishdb.consult_bookings
            WHERE booking_id = %s
        """, (booking_id,))
        booking = cur.fetchone()

        if not booking:
            return jsonify(success=False, message='Booking not found'), 404
        if int(booking['user_id']) != int(user_id):
            return jsonify(success=False, message='You are not allowed to cancel this booking'), 403
        if booking['booking_status'] == 'Cancelled':
            return jsonify(success=False, message='Booking is already cancelled'), 409

        cur.execute("""
            UPDATE numerojyutishdb.consult_bookings
            SET booking_status = 'Cancelled'
            WHERE booking_id = %s
            RETURNING booking_id, booking_status, payment_status
        """, (booking_id,))
        updated = cur.fetchone()
        conn.commit()

        return jsonify(
            success=True,
            message='Booking cancelled successfully',
            data={
                'booking_id': updated['booking_id'],
                'booking_status': updated['booking_status'],
                'payment_status': updated['payment_status']
            }
        ), 200
    except Exception as e:
        logging.error(f"Error cancelling booking {booking_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error cancelling booking: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/consult-bookings/<int:booking_id>/reschedule', methods=['PUT'])
def reschedule_consult_booking(booking_id):
    """
    Reschedule consultation booking.
    Expected JSON:
    {
        "user_id": 1001,
        "booking_date": "2026-02-24",
        "start_time": "10:00",
        "end_time": "10:30"
    }
    """
    conn = None
    cur = None
    try:
        ensure_booking_tables()
        data = request.get_json() or {}
        required_fields = ['user_id', 'booking_date', 'start_time', 'end_time']
        missing = [field for field in required_fields if data.get(field) in (None, '')]
        if missing:
            return jsonify(success=False, message=f"Missing required fields: {', '.join(missing)}"), 400

        user_id = int(data['user_id'])
        booking_date = datetime.strptime(data['booking_date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()

        if end_time <= start_time:
            return jsonify(success=False, message='end_time must be greater than start_time'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT booking_id, astrologer_id, user_id, booking_status
            FROM numerojyutishdb.consult_bookings
            WHERE booking_id = %s
        """, (booking_id,))
        booking = cur.fetchone()

        if not booking:
            return jsonify(success=False, message='Booking not found'), 404
        if int(booking['user_id']) != user_id:
            return jsonify(success=False, message='You are not allowed to reschedule this booking'), 403
        if booking['booking_status'] == 'Cancelled':
            return jsonify(success=False, message='Cancelled booking cannot be rescheduled'), 409

        astrologer_id = booking['astrologer_id']
        day_of_week = booking_date.strftime('%A')

        cur.execute("""
            SELECT start_time, end_time
            FROM numerojyutishdb.astrologer_availability
            WHERE astrologer_id = %s
              AND LOWER(day_of_week) = LOWER(%s)
              AND is_available = true
        """, (astrologer_id, day_of_week))
        availability_rows = cur.fetchall()
        if not availability_rows:
            return jsonify(success=False, message='Astrologer is not available on selected day'), 400

        fits_availability = any(
            start_time >= row['start_time'] and end_time <= row['end_time']
            for row in availability_rows
        )
        if not fits_availability:
            return jsonify(success=False, message='Selected slot is outside astrologer availability'), 400

        cur.execute("""
            SELECT booking_id, start_time, end_time
            FROM numerojyutishdb.consult_bookings
            WHERE astrologer_id = %s
              AND booking_date = %s
              AND booking_status IN ('Pending', 'Confirmed')
              AND booking_id <> %s
        """, (astrologer_id, booking_date, booking_id))
        conflict_rows = cur.fetchall()

        has_conflict = any(
            _slot_overlaps(start_time, end_time, row['start_time'], row['end_time'])
            for row in conflict_rows
        )
        if has_conflict:
            return jsonify(success=False, message='Selected slot is already booked'), 409

        cur.execute("""
            UPDATE numerojyutishdb.consult_bookings
            SET booking_date = %s,
                start_time = %s,
                end_time = %s,
                booking_status = CASE WHEN booking_status = 'Cancelled' THEN booking_status ELSE 'Pending' END
            WHERE booking_id = %s
            RETURNING booking_id, booking_date, start_time, end_time, booking_status
        """, (booking_date, start_time, end_time, booking_id))
        updated = cur.fetchone()
        conn.commit()

        return jsonify(
            success=True,
            message='Booking rescheduled successfully',
            data={
                'booking_id': updated['booking_id'],
                'booking_date': updated['booking_date'].isoformat() if updated['booking_date'] else None,
                'start_time': _time_to_str(updated['start_time']),
                'end_time': _time_to_str(updated['end_time']),
                'booking_status': updated['booking_status']
            }
        ), 200
    except ValueError:
        return jsonify(success=False, message='Invalid input. booking_date must be YYYY-MM-DD and time must be HH:MM'), 400
    except Exception as e:
        logging.error(f"Error rescheduling booking {booking_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error rescheduling booking: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@astrologer_bp.route('/api/astrologers', methods=['GET'])
def list_astrologers():
    """
    Retrieve all active astrologers with optional filtering and pagination.
    Query params:
    - expertise: Filter by expertise (e.g., "Vedic", "Tarot")
    - language: Filter by language
    - min_rating: Minimum rating filter (0.0-5.0)
    - verified_only: Boolean to show only verified astrologers
    - limit: Number of results (default 20)
    - offset: Pagination offset (default 0)
    """
    try:
        expertise = request.args.get('expertise', None)
        language = request.args.get('language', None)
        min_rating = request.args.get('min_rating', 0.0, type=float)
        verified_only = request.args.get('verified_only', False, type=lambda x: x.lower() == 'true')
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Build dynamic query with filters
        query = """
            SELECT astrologer_id, full_name, display_name, email, phone_number, gender,
                   experience_years, expertise, languages, consultation_fee, currency,
                   profile_image_url, bio, rating, total_reviews, is_active, is_verified,
                   created_at, updated_at
            FROM numerojyutishdb.consult_astrologers
            WHERE is_active = true
        """
        params = []

        if verified_only:
            query += " AND is_verified = true"

        if expertise:
            query += " AND expertise ILIKE %s"
            params.append(f"%{expertise}%")

        if language:
            query += " AND languages ILIKE %s"
            params.append(f"%{language}%")

        if min_rating:
            query += " AND rating >= %s"
            params.append(min_rating)

        # Add sorting and pagination
        query += " ORDER BY rating DESC, total_reviews DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM numerojyutishdb.consult_astrologers WHERE is_active = true"
        count_params = []

        if verified_only:
            count_query += " AND is_verified = true"
            
        if expertise:
            count_query += " AND expertise ILIKE %s"
            count_params.append(f"%{expertise}%")
            
        if language:
            count_query += " AND languages ILIKE %s"
            count_params.append(f"%{language}%")
            
        if min_rating:
            count_query += " AND rating >= %s"
            count_params.append(min_rating)

        cur.execute(count_query, count_params)
        count_row = cur.fetchone()
        total_count = count_row.get('count', 0) if count_row else 0

        cur.close()
        conn.close()

        astrologers = [
            {
                'astrologer_id': row['astrologer_id'],
                'full_name': row['full_name'],
                'display_name': row['display_name'],
                'email': row['email'],
                'phone_number': row['phone_number'],
                'gender': row['gender'],
                'experience_years': row['experience_years'],
                'expertise': row['expertise'],
                'languages': row['languages'],
                'consultation_fee': float(row['consultation_fee']),
                'currency': row['currency'],
                'profile_image_url': row['profile_image_url'],
                'bio': row['bio'],
                'rating': float(row['rating']),
                'total_reviews': row['total_reviews'],
                'is_active': row['is_active'],
                'is_verified': row['is_verified'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in rows
        ]

        return jsonify(
            success=True,
            data=astrologers,
            pagination={
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'count': len(astrologers)
            }
        ), 200

    except Exception as e:
        logging.error(f"Error listing astrologers: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error listing astrologers: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>', methods=['GET'])
def get_astrologer_profile(astrologer_id):
    """
    Retrieve detailed profile of a specific astrologer.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT astrologer_id, full_name, display_name, email, phone_number, gender,
                   experience_years, expertise, languages, consultation_fee, currency,
                   profile_image_url, bio, rating, total_reviews, is_active, is_verified,
                   created_at, updated_at
            FROM numerojyutishdb.consult_astrologers
            WHERE astrologer_id = %s
        """, (astrologer_id,))

        astrologer = cur.fetchone()
        cur.close()
        conn.close()

        if not astrologer:
            return jsonify(success=False, message='Astrologer not found'), 404

        return jsonify(
            success=True,
            data={
                'astrologer_id': astrologer['astrologer_id'],
                'full_name': astrologer['full_name'],
                'display_name': astrologer['display_name'],
                'email': astrologer['email'],
                'phone_number': astrologer['phone_number'],
                'gender': astrologer['gender'],
                'experience_years': astrologer['experience_years'],
                'expertise': astrologer['expertise'],
                'languages': astrologer['languages'],
                'consultation_fee': float(astrologer['consultation_fee']),
                'currency': astrologer['currency'],
                'profile_image_url': astrologer['profile_image_url'],
                'bio': astrologer['bio'],
                'rating': float(astrologer['rating']),
                'total_reviews': astrologer['total_reviews'],
                'is_verified': astrologer['is_verified'],
                'created_at': astrologer['created_at'].isoformat() if astrologer['created_at'] else None
            }
        ), 200

    except Exception as e:
        logging.error(f"Error fetching astrologer {astrologer_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching astrologer: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers', methods=['POST'])
def create_astrologer():
    """
    Create a new astrologer profile (Admin only).
    Expected JSON:
    {
        "full_name": "Dr. Rajesh Kumar",
        "display_name": "Rajesh",
        "email": "rajesh@example.com",
        "phone_number": "+919876543210",
        "gender": "male",
        "experience_years": 15,
        "expertise": "Vedic, Numerology",
        "languages": "English, Hindi, Sanskrit",
        "consultation_fee": 500.00,
        "currency": "INR",
        "profile_image_url": "https://...",
        "bio": "Expert in vedic astrology..."
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['full_name', 'email', 'consultation_fee']
        if not data or not all(k in data for k in required_fields):
            return jsonify(success=False, message='Missing required fields: full_name, email, consultation_fee'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if email already exists
        cur.execute("SELECT astrologer_id FROM numerojyutishdb.consult_astrologers WHERE email = %s", 
                   (data['email'],))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Email already exists'), 409

        # Insert astrologer
        cur.execute("""
            INSERT INTO numerojyutishdb.consult_astrologers
            (full_name, display_name, email, phone_number, gender, experience_years,
             expertise, languages, consultation_fee, currency, profile_image_url, bio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING astrologer_id, created_at
        """, (
            data['full_name'],
            data.get('display_name', data['full_name']),
            data['email'],
            data.get('phone_number'),
            data.get('gender'),
            data.get('experience_years', 0),
            data.get('expertise'),
            data.get('languages'),
            data['consultation_fee'],
            data.get('currency', 'INR'),
            data.get('profile_image_url'),
            data.get('bio')
        ))

        result = cur.fetchone()
        astrologer_id, created_at = result[0], result[1]

        conn.commit()
        cur.close()
        conn.close()

        logging.info(f"Astrologer {astrologer_id} created successfully")
        return jsonify(
            success=True,
            message='Astrologer created successfully',
            data={
                'astrologer_id': astrologer_id,
                'full_name': data['full_name'],
                'display_name': data.get('display_name', data['full_name']),
                'email': data['email'],
                'consultation_fee': float(data['consultation_fee']),
                'created_at': created_at.isoformat() if created_at else None
            }
        ), 201

    except Exception as e:
        logging.error(f"Error creating astrologer: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating astrologer: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>', methods=['PUT'])
def update_astrologer(astrologer_id):
    """
    Update astrologer profile (Admin only).
    Expected JSON: Any subset of fields from creation
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(success=False, message='No update fields provided'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify astrologer exists
        cur.execute("SELECT astrologer_id FROM numerojyutishdb.consult_astrologers WHERE astrologer_id = %s",
                   (astrologer_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Astrologer not found'), 404

        # Build dynamic update query
        update_fields = []
        params = []

        field_map = {
            'full_name': 'full_name',
            'display_name': 'display_name',
            'email': 'email',
            'phone_number': 'phone_number',
            'gender': 'gender',
            'experience_years': 'experience_years',
            'expertise': 'expertise',
            'languages': 'languages',
            'consultation_fee': 'consultation_fee',
            'currency': 'currency',
            'profile_image_url': 'profile_image_url',
            'bio': 'bio',
            'is_active': 'is_active',
            'is_verified': 'is_verified'
        }

        for key, col in field_map.items():
            if key in data:
                update_fields.append(f'{col} = %s')
                params.append(data[key])

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No valid fields to update'), 400

        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(astrologer_id)

        query = f"""
            UPDATE numerojyutishdb.consult_astrologers
            SET {', '.join(update_fields)}
            WHERE astrologer_id = %s
            RETURNING astrologer_id, full_name, display_name, email, consultation_fee
        """

        cur.execute(query, params)
        result = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logging.info(f"Astrologer {astrologer_id} updated successfully")
        return jsonify(
            success=True,
            message='Astrologer updated successfully',
            data={
                'astrologer_id': result['astrologer_id'],
                'full_name': result['full_name'],
                'display_name': result['display_name'],
                'email': result['email'],
                'consultation_fee': float(result['consultation_fee'])
            }
        ), 200

    except Exception as e:
        logging.error(f"Error updating astrologer {astrologer_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating astrologer: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>', methods=['DELETE'])
def delete_astrologer(astrologer_id):
    """
    Deactivate an astrologer (soft delete by setting is_active to false).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if astrologer exists
        cur.execute("SELECT astrologer_id FROM numerojyutishdb.consult_astrologers WHERE astrologer_id = %s",
                   (astrologer_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Astrologer not found'), 404

        # Soft delete: set is_active to false
        cur.execute("""
            UPDATE numerojyutishdb.consult_astrologers
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE astrologer_id = %s
        """, (astrologer_id,))

        conn.commit()
        cur.close()
        conn.close()

        logging.info(f"Astrologer {astrologer_id} deleted successfully")
        return jsonify(success=True, message='Astrologer deleted successfully'), 200

    except Exception as e:
        logging.error(f"Error deleting astrologer {astrologer_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting astrologer: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/verify', methods=['PUT'])
def verify_astrologer(astrologer_id):
    """
    Mark an astrologer as verified (Admin only).
    Expected JSON:
    {
        "is_verified": true
    }
    """
    try:
        data = request.get_json() or {}
        is_verified = data.get('is_verified', True)

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE numerojyutishdb.consult_astrologers
            SET is_verified = %s, updated_at = CURRENT_TIMESTAMP
            WHERE astrologer_id = %s
            RETURNING astrologer_id, full_name, is_verified
        """, (is_verified, astrologer_id))

        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            return jsonify(success=False, message='Astrologer not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        logging.info(f"Astrologer {astrologer_id} verification status updated to {is_verified}")
        return jsonify(
            success=True,
            message=f'Astrologer {"verified" if is_verified else "unverified"} successfully',
            data={
                'astrologer_id': result[0],
                'full_name': result[1],
                'is_verified': result[2]
            }
        ), 200

    except Exception as e:
        logging.error(f"Error verifying astrologer {astrologer_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error verifying astrologer: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers/<int:astrologer_id>/rating', methods=['POST'])
def submit_astrologer_rating(astrologer_id):
    """
    Submit a rating and review for an astrologer.
    Expected JSON:
    {
        "user_id": 123,
        "rating": 4.5,  # 0.0 to 5.0
        "review_text": "Excellent consultation...",
        "consultation_date": "2025-02-14"
    }
    """
    try:
        data = request.get_json()

        if not data or 'rating' not in data or 'user_id' not in data:
            return jsonify(success=False, message='rating and user_id are required'), 400

        rating = float(data['rating'])
        if rating < 0 or rating > 5:
            return jsonify(success=False, message='Rating must be between 0 and 5'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Verify astrologer exists
        cur.execute("SELECT astrologer_id FROM numerojyutishdb.consult_astrologers WHERE astrologer_id = %s",
                   (astrologer_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Astrologer not found'), 404

        # Update astrologer rating (calculate average)
        cur.execute("""
            UPDATE numerojyutishdb.consult_astrologers
            SET rating = (rating * total_reviews + %s) / (total_reviews + 1),
                total_reviews = total_reviews + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE astrologer_id = %s
            RETURNING astrologer_id, rating, total_reviews
        """, (rating, astrologer_id))

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        logging.info(f"Rating {rating} submitted for astrologer {astrologer_id}")
        return jsonify(
            success=True,
            message='Rating submitted successfully',
            data={
                'astrologer_id': result[0],
                'rating': float(result[1]),
                'total_reviews': result[2]
            }
        ), 201

    except ValueError:
        return jsonify(success=False, message='Invalid rating value'), 400
    except Exception as e:
        logging.error(f"Error submitting rating for astrologer {astrologer_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error submitting rating: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers/search', methods=['GET'])
def search_astrologers():
    """
    Search astrologers by name or expertise.
    Query params:
    - q: Search query (searches in full_name, display_name, expertise)
    - limit: Number of results (default 10)
    """
    try:
        search_query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)

        if not search_query:
            return jsonify(success=False, message='Search query required'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT astrologer_id, full_name, display_name, expertise, consultation_fee,
                   currency, bio, rating, total_reviews, is_verified
            FROM numerojyutishdb.consult_astrologers
            WHERE is_active = true AND (
                full_name ILIKE %s OR
                display_name ILIKE %s OR
                expertise ILIKE %s
            )
            ORDER BY is_verified DESC, rating DESC
            LIMIT %s
        """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", limit))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        astrologers = [
            {
                'astrologer_id': row['astrologer_id'],
                'full_name': row['full_name'],
                'display_name': row['display_name'],
                'expertise': row['expertise'],
                'consultation_fee': float(row['consultation_fee']),
                'currency': row['currency'],
                'bio': row['bio'],
                'rating': float(row['rating']),
                'total_reviews': row['total_reviews'],
                'is_verified': row['is_verified']
            }
            for row in rows
        ]

        return jsonify(success=True, data=astrologers), 200

    except Exception as e:
        logging.error(f"Error searching astrologers: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error searching astrologers: {str(e)}'), 500


@astrologer_bp.route('/api/astrologers/top-rated', methods=['GET'])
def get_top_rated_astrologers():
    """
    Get top-rated astrologers.
    Query params:
    - limit: Number of results (default 10)
    - min_reviews: Minimum number of reviews (default 0)
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        min_reviews = request.args.get('min_reviews', 0, type=int)

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT astrologer_id, full_name, display_name, expertise, languages,
                   consultation_fee, currency, profile_image_url, bio, rating,
                   total_reviews, is_verified
            FROM numerojyutishdb.consult_astrologers
            WHERE is_active = true AND total_reviews >= %s
            ORDER BY rating DESC, total_reviews DESC
            LIMIT %s
        """, (min_reviews, limit))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        astrologers = [
            {
                'astrologer_id': row['astrologer_id'],
                'full_name': row['full_name'],
                'display_name': row['display_name'],
                'expertise': row['expertise'],
                'languages': row['languages'],
                'consultation_fee': float(row['consultation_fee']),
                'currency': row['currency'],
                'profile_image_url': row['profile_image_url'],
                'bio': row['bio'],
                'rating': float(row['rating']),
                'total_reviews': row['total_reviews'],
                'is_verified': row['is_verified']
            }
            for row in rows
        ]

        return jsonify(success=True, data=astrologers), 200

    except Exception as e:
        logging.error(f"Error fetching top-rated astrologers: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching astrologers: {str(e)}'), 500


@astrologer_bp.route('/api/upload-astrologer-image', methods=['POST'])
def upload_astrologer_image():
    """
    Upload astrologer profile image to Cloudinary.
    Expects: multipart/form-data with 'file' and optional 'astrologer_id'
    Returns: image_url, public_id
    """
    try:
        logging.info("📥 [UPLOAD_ASTROLOGER_IMAGE] Request received")
        
        # Check authorization
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        if not token:
            return jsonify(success=False, message='Authorization token required'), 401
        
        # Get astrologer_id (optional, for organizing uploads)
        astrologer_id = request.form.get('astrologer_id', 'temp')
        
        # Check if file exists
        if 'file' not in request.files:
            return jsonify(success=False, message='No file provided'), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify(success=False, message='No file selected'), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify(success=False, message='File type not allowed. Use png, jpg, jpeg, gif, or webp'), 400
        
        # Validate file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify(success=False, message='File size exceeds maximum (5MB)'), 400
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"numerojyutish/astrologers/{astrologer_id}",
            resource_type="auto",
            overwrite=False
        )
        
        image_url = upload_result.get('secure_url')
        public_id = upload_result.get('public_id')
        
        logging.info(f"✅ [UPLOAD_ASTROLOGER_IMAGE] Image uploaded successfully: {public_id}")
        
        return jsonify(
            success=True,
            data={
                'image_url': image_url,
                'public_id': public_id,
                'filename': file.filename
            },
            message='Astrologer image uploaded successfully'
        ), 201
    
    except Exception as e:
        logging.error(f"❌ [UPLOAD_ASTROLOGER_IMAGE] Error: {e}")
        return jsonify(success=False, message=f'Error uploading image: {str(e)}'), 500
