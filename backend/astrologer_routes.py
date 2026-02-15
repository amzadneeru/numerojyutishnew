"""
Astrologer Consultation Routes
Handles listing astrologers, viewing profiles, managing consultations, and ratings.
"""

import logging
from datetime import datetime
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

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )


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
