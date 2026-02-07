import logging
import os
from pathlib import Path
from flask import Flask, request, jsonify, redirect, send_from_directory
from flask_cors import CORS
import psycopg2
import secrets
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from authlib.integrations.flask_client import OAuth
import requests
from twilio.rest import Client as TwilioClient
from datetime import datetime, timedelta

# Minimal app: only user registration (create-user) functionality
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

load_dotenv(dotenv_path=Path(__file__).resolve().parent / 'data.env')

app = Flask(__name__)
# Allow CORS from any origin (useful for development/testing).
# Note: allowing all origins with credentials can be unsafe in production.
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads', 'product-images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# OAuth configuration (Google / Facebook)
oauth = OAuth(app)

# Simple in-memory OTP store for signup OTPs (development use only).
# Structure: { contact_string: { 'otp': '123456', 'expires': datetime } }
otp_store = {}

# Register Google (OpenID Connect)
try:
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
except Exception:
    # registration may fail if env vars are not set; we'll handle missing config at runtime
    pass

# Register Facebook
try:
    oauth.register(
        name='facebook',
        client_id=os.getenv('FACEBOOK_CLIENT_ID'),
        client_secret=os.getenv('FACEBOOK_CLIENT_SECRET'),
        access_token_url='https://graph.facebook.com/v11.0/oauth/access_token',
        authorize_url='https://www.facebook.com/v11.0/dialog/oauth',
        api_base_url='https://graph.facebook.com/v11.0/',
        client_kwargs={'scope': 'email'}
    )
except Exception:
    pass


def get_db_connection():
    # Support either a full DATABASE_URL/DSN (e.g. rendered/Heroku style)
    # or separate DB_HOST/DB_NAME/DB_USER/DB_PASSWORD/DB_PORT variables.
   

    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )


ALLOWED_ROLES = (
    'End user who will buy subscription',
    'Internal user how will manage app',
    'Student',
    'Numerology consultant',
    'Super user',
    'Admin',
)





# Serve uploaded product images
@app.route('/uploads/product-images/<filename>')
def uploaded_file(filename):
    """Serve uploaded product images."""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logging.error(f"Error serving file: {e}")
        return jsonify(success=False, message='File not found'), 404

@app.route('/', methods=['GET'])
def health():
    return jsonify(status='ok')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify(success=False, message='username and password required'), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Look up by username or email
        cur.execute("SELECT user_id, email, phone, password_hash FROM numerojyutishdb.security WHERE phone = %s OR email = %s", (username, username))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify(success=False, message='Invalid credentials'), 401

        user_id, email, db_username, password_hash = row
        if not check_password_hash(password_hash, password):
            cur.close()
            conn.close()
            return jsonify(success=False, message='Invalid credentials'), 401

        # generate token, store in DB
        token = secrets.token_urlsafe(32)
        cur.execute("UPDATE numerojyutishdb.users SET authtoken = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", (token, user_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(success=True, message='Login successful', token=token, user_id=user_id, email=email)
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error during login: {str(e)}'), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    # Check if either email or phone is provided
    if not email and not phone:
        return jsonify(success=False, message='Either email or phone is required'), 400
        
    # Validate password
    if not password:
        return jsonify(success=False, message='Password is required'), 400
        
    # Check password confirmation
    if password != confirm_password:
        return jsonify(success=False, message='Passwords do not match'), 400
        
    # Basic email validation
    if email and not '@' in email:
        return jsonify(success=False, message='Invalid email format'), 400
        
    # Basic phone validation (assuming simple length check)
    if phone and not phone.isdigit():
        return jsonify(success=False, message='Phone number should contain only digits'), 400

    password_hash = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if email/phone already exists
        if email:
            cur.execute("SELECT user_id FROM numerojyutishdb.security WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return jsonify(success=False, message='Email already registered'), 409
                
        if phone:
            cur.execute("SELECT user_id FROM numerojyutishdb.security WHERE phone = %s", (phone,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return jsonify(success=False, message='Phone number already registered'), 409
        
        # Insert new user
        cur.execute(
            """
            INSERT INTO numerojyutishdb.security
                (email, phone, password_hash, user_role, authtoken)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
            """,
            (email, phone, password_hash, '1', None)
        )
        
        user_id = cur.fetchone()[0]
        conn.commit()
        
        # Generate auth token for immediate login
        token = secrets.token_urlsafe(32)
        cur.execute("UPDATE numerojyutishdb.security SET authtoken = %s WHERE user_id = %s", (token, user_id))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify(
            success=True, 
            message='Signup successful!',
            user_id=user_id,
            token=token,
            email=email,
            phone=phone
        ), 201
        
    except Exception as e:
        logging.error(f"Error during signup: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error during signup. Please try again.'), 500


# OTP endpoints temporarily disabled. To re-enable, restore the route decorators and function names.
# @app.route('/api/send-signup-otp', methods=['POST'])
def send_signup_otp_disabled():
    data = request.get_json() or {}
    email = data.get('email')
    phone = data.get('phone')
    if not email and not phone:
        return jsonify(success=False, message='Either email or phone is required'), 400

    contact = email if email else phone
    # 6-digit OTP
    otp = f"{secrets.randbelow(1000000):06d}"
    otp_store[contact] = {'otp': otp, 'expires': datetime.utcnow() + timedelta(minutes=5)}
    # If TWILIO credentials are available and a phone number was provided, send SMS.
    tw_sid = os.getenv('MG3db7c4b2e813f1fd2cc25bca713c89a6')
    tw_token = os.getenv('AC498cb0b4be4c95124be8ccef8cbdc280')
    tw_from = os.getenv('15707415917')
    if phone and tw_sid and tw_token and tw_from:
        try:
            tw_client = TwilioClient(tw_sid, tw_token)
            # phone should be in E.164 format (e.g. +9198XXXXXXXX)
            msg = tw_client.messages.create(
                body=f"Your OTP is {otp}",
                from_=tw_from,
                to=phone
            )
            logging.info(f"Sent OTP SMS to {phone}, sid={getattr(msg, 'sid', None)}")
            return jsonify(success=True, message='OTP sent via SMS'), 200
        except Exception as e:
            logging.error(f"Error sending OTP via Twilio to {phone}: {e}")
            # return error so client can surface it
            return jsonify(success=False, message='Failed to send OTP via SMS'), 500

    # Fallback for email or when Twilio not configured: log OTP (development only)
    logging.info(f"Signup OTP for {contact}: {otp}")
    return jsonify(success=True, message='OTP sent (logged on server)'), 200


# @app.route('/api/verify-signup-otp', methods=['POST'])
def verify_signup_otp_disabled():
    data = request.get_json() or {}
    email = data.get('email')
    phone = data.get('phone')
    otp = data.get('otp')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not (email or phone) or not otp or not password:
        return jsonify(success=False, message='email/phone, otp and password required'), 400

    contact = email if email else phone
    record = otp_store.get(contact)
    if not record:
        return jsonify(success=False, message='OTP not requested or expired'), 400
    if datetime.utcnow() > record['expires']:
        otp_store.pop(contact, None)
        return jsonify(success=False, message='OTP expired'), 400
    if record['otp'] != str(otp):
        return jsonify(success=False, message='Invalid OTP'), 400

    # OTP is valid, proceed with registration (similar checks to /api/signup)
    if password != confirm_password:
        return jsonify(success=False, message='Passwords do not match'), 400
    if email and '@' not in email:
        return jsonify(success=False, message='Invalid email format'), 400
    if phone and not phone.isdigit():
        return jsonify(success=False, message='Phone number should contain only digits'), 400

    password_hash = generate_password_hash(password)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Check for existing email/phone
        if email:
            cur.execute("SELECT user_id FROM numerojyutishdb.security WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close(); conn.close()
                return jsonify(success=False, message='Email already registered'), 409
        if phone:
            cur.execute("SELECT user_id FROM numerojyutishdb.security WHERE phone = %s", (phone,))
            if cur.fetchone():
                cur.close(); conn.close()
                return jsonify(success=False, message='Phone number already registered'), 409

        cur.execute(
            """
            INSERT INTO numerojyutishdb.security
                (email, phone, password_hash, user_role, authtoken)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
            """,
            (email, phone, password_hash, '1', None)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        # Generate auth token for immediate login
        token = secrets.token_urlsafe(32)
        cur.execute("UPDATE numerojyutishdb.security SET authtoken = %s WHERE user_id = %s", (token, user_id))
        conn.commit()
        cur.close()
        conn.close()
        # remove OTP record
        otp_store.pop(contact, None)
        return jsonify(success=True, message='Signup successful', user_id=user_id, token=token, email=email, phone=phone), 201
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error creating user (OTP flow): {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        msg = str(e).lower()
        if 'email' in msg:
            return jsonify(success=False, message='Email already registered'), 409
        if 'phoneno' in msg or 'phone' in msg:
            return jsonify(success=False, message='Phone number already registered'), 409
        if 'username' in msg:
            return jsonify(success=False, message='Username already taken'), 409
        return jsonify(success=False, message='Duplicate value'), 409
    except Exception as e:
        logging.error(f"Error creating user (OTP flow): {e}")
        return jsonify(success=False, message=f'Error creating user: {str(e)}'), 500

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    full_name = data.get('full_name')
    email = data.get('email')
    phone = data.get('phoneNo')
    authtoken = data.get('authtoken')
    dob = data.get('dob')
    gender = data.get('gender')
    # relationship / professional lookup values
    relationship_code = data.get('relationship_status_key')
    relationship_status_key = data.get('relationship_status_key')
    professional_code = data.get('profession_key')
    profession_key = data.get('profession_key')
    professional_status_code = data.get('professional_status_key')
    professional_status_key = data.get('professional_status_key')

    # Basic validations
    if not full_name or not email or not phone or not dob or not gender:
        return jsonify(success=False, message='full_name, email, phoneNo, dob, and gender are required'), 400

    if (relationship_code is None or not relationship_status_key or
        professional_code is None or not profession_key or
        professional_status_code is None or not professional_status_key):
        return jsonify(success=False, message='relationship_code, relationship_status_key, professional_code, profession_key, professional_status_code and professional_status_key are required'), 400

    if gender not in ['male', 'female', 'other']:
        return jsonify(success=False, message='Invalid gender value'), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        logging.info(f"database connection established")

        # Try to locate an existing user by authtoken first
        existing_user_id = None
        if authtoken:
            cur.execute("SELECT user_id, email FROM numerojyutishdb.security WHERE authtoken = %s", (authtoken,))
            row = cur.fetchone()
            if row:
                logging.info(f"Found security row for authtoken: user_id={row[0]}")
                # prefer to find profile by user_id
                security_user_id = row[0]
                cur.execute("SELECT user_id FROM numerojyutishdb.users WHERE user_id = %s", (security_user_id,))
                r2 = cur.fetchone()
                if r2:
                    existing_user_id = r2[0]
                else:
                    # fallback to finding by email returned from security row
                    sec_email = row[1]
                    if sec_email:
                        cur.execute("SELECT user_id FROM numerojyutishdb.users WHERE email = %s", (sec_email,))
                        r3 = cur.fetchone()
                        if r3:
                            existing_user_id = r3[0]

        # If not found yet, try by provided email
        if existing_user_id is None and email:
            cur.execute("SELECT user_id FROM numerojyutishdb.users WHERE email = %s", (email,))
            r = cur.fetchone()
            if r:
                existing_user_id = r[0]

        # If user exists -> update
        if existing_user_id:
            cur.execute(
                """
                UPDATE numerojyutishdb.users
                SET full_name = %s,
                    email = %s,                   
                    dob = %s,
                    gender = %s,                  
                    relationship_status_key = %s,                    
                    profession_key = %s,                   
                    professional_status_key = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                RETURNING user_id
                """,
                (
                    full_name, email,  dob, gender,
                     relationship_status_key,
                     profession_key,  professional_status_key,
                    existing_user_id
                )
            )
            updated_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            logging.info(f"Updated user {email} id={updated_id}")
            return jsonify(success=True, message='User updated', user_id=updated_id), 200

        # else create new profile
        cur.execute(
            """
            INSERT INTO numerojyutishdb.users
                (full_name, email, dob, gender,
                  relationship_status_key,
                  profession_key,  professional_status_key)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING user_id
            """,
            (
                full_name, email,  dob, gender,
                relationship_status_key,
                profession_key,  professional_status_key
            )
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Created user {email} with id {user_id}")
        return jsonify(success=True, message='User created', user_id=user_id), 201

    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error creating/updating user: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify(success=False, message='Duplicate value or constraint violation'), 409
    except Exception as e:
        logging.error(f"Error creating/updating user: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating/updating user: {str(e)}'), 500


@app.route('/api/user-profile/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    """
    Retrieve user profile data by user_id.
    Expects Authorization header with Bearer token for authentication.
    """
    # Check if user has provided authorization token
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    
    if not token:
        return jsonify(success=False, message='Authorization token required'), 401
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify token belongs to the requested user
        cur.execute(
            "SELECT user_id FROM numerojyutishdb.security WHERE authtoken = %s AND user_id = %s",
            (token, user_id)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Unauthorized'), 403
        
        # Fetch user profile data
        cur.execute(
            """
            SELECT 
                u.user_id,
                u.full_name,
                u.dob,
                u.gender,
                u.email,
                u.phone_no,
                u.username,
                u.relationship_status,
                u.professional_status,
                u.profession,
                s.password_hash
            FROM numerojyutishdb.users u
            LEFT JOIN numerojyutishdb.security s ON u.user_id = s.user_id
            WHERE u.user_id = %s
            """,
            (user_id,)
        )
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify(success=False, message='User not found'), 404
        
        user_data = {
            'user_id': row[0],
            'full_name': row[1],
            'dob': row[2],
            'gender': row[3],
            'email': row[4],
            'phoneNo': row[5],
            'username': row[6],
            'relationship_status': row[7],
            'professional_status': row[8],
            'profession': row[9],
            'password': row[10] or ''  # Return hashed password (not ideal, but frontend may need it)
        }
        
        return jsonify(success=True, user=user_data), 200
        
    except Exception as e:
        logging.error(f"Error fetching user profile {user_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching user profile: {str(e)}'), 500


@app.route('/api/user-profile/<int:user_id>', methods=['PUT'])
def update_user_profile(user_id):
    """
    Update user profile data by user_id.
    Expects Authorization header with Bearer token for authentication.
    """
    # Check if user has provided authorization token
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    
    if not token:
        return jsonify(success=False, message='Authorization token required'), 401
    
    data = request.get_json() or {}
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify token belongs to the requested user
        cur.execute(
            "SELECT user_id FROM numerojyutishdb.security WHERE authtoken = %s AND user_id = %s",
            (token, user_id)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Unauthorized'), 403
        
        # Extract update fields from request
        full_name = data.get('full_name')
        dob = data.get('dob')
        gender = data.get('gender')
        email = data.get('email')
        phoneNo = data.get('phoneNo')
        username = data.get('username')
        relationship_status = data.get('relationship_status_key')
        professional_status = data.get('professional_status_key')
        profession = data.get('profession_key')
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if full_name is not None:
            update_fields.append("full_name = %s")
            params.append(full_name)
        if dob is not None:
            update_fields.append("dob = %s")
            params.append(dob)
        if gender is not None:
            update_fields.append("gender = %s")
            params.append(gender)
        if email is not None:
            update_fields.append("email = %s")
            params.append(email)
        if phoneNo is not None:
            update_fields.append("phone_no = %s")
            params.append(phoneNo)
        if username is not None:
            update_fields.append("username = %s")
            params.append(username)
        if relationship_status is not None:
            update_fields.append("relationship_status = %s")
            params.append(relationship_status)
        if professional_status is not None:
            update_fields.append("professional_status = %s")
            params.append(professional_status)
        if profession is not None:
            update_fields.append("profession = %s")
            params.append(profession)
        
        # Add user_id to params for WHERE clause
        params.append(user_id)
        
        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400
        
        # Execute update
        query = f"""
            UPDATE numerojyutishdb.users
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        
        cur.execute(query, params)
        conn.commit()
        
        # Also update password in security table if provided
        password = data.get('password')
        if password:
            password_hash = generate_password_hash(password)
            cur.execute(
                "UPDATE numerojyutishdb.security SET password_hash = %s WHERE user_id = %s",
                (password_hash, user_id)
            )
            conn.commit()
        
        cur.close()
        conn.close()
        
        logging.info(f"Updated user profile for user_id {user_id}")
        return jsonify(success=True, message='Profile updated successfully'), 200
        
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error updating user profile: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify(success=False, message='Duplicate value or constraint violation'), 409
    except Exception as e:
        logging.error(f"Error updating user profile {user_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating user profile: {str(e)}'), 500


# Subscription Plans endpoints
@app.route('/api/subscription-plans', methods=['GET'])
def get_subscription_plans():
    """
    Retrieve all subscription plans.
    Returns plan_id, plan_code, plan_name, description, is_active, subscribefor
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT plan_id, plan_code, plan_name, description, is_active, subscribefor
            FROM numerojyutishdb.subscription_plans
            WHERE is_active = true
            ORDER BY plan_id
            """
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        plans = [
            {
                'plan_id': r[0],
                'plan_code': r[1],
                'plan_name': r[2],
                'description': r[3],
                'is_active': r[4],
                'subscribefor': r[5]
            }
            for r in rows
        ]
        
        return jsonify(success=True, data=plans), 200
        
    except Exception as e:
        logging.error(f"Error fetching subscription plans: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching subscription plans: {str(e)}'), 500


@app.route('/api/subscription-plans/<int:plan_id>', methods=['GET'])
def get_subscription_plan(plan_id):
    """
    Retrieve a specific subscription plan by plan_id.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT plan_id, plan_code, plan_name, description, is_active, subscribefor
            FROM numerojyutishdb.subscription_plans
            WHERE plan_id = %s
            """,
            (plan_id,)
        )
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify(success=False, message='Subscription plan not found'), 404
        
        plan = {
            'plan_id': row[0],
            'plan_code': row[1],
            'plan_name': row[2],
            'description': row[3],
            'is_active': row[4],
            'subscribefor': row[5]
        }
        
        return jsonify(success=True, data=plan), 200
        
    except Exception as e:
        logging.error(f"Error fetching subscription plan {plan_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching subscription plan: {str(e)}'), 500


# Subscription Pricing endpoints
@app.route('/api/subscription-pricing', methods=['GET'])
def get_subscription_pricing():
    """
    Retrieve all subscription pricing.
    Returns plan_id, billing_cycle_id, country_code, base_price, tax_percent, final_price, is_active
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT plan_id, billing_cycle_id, country_code, base_price, tax_percent, final_price, is_active
            FROM numerojyutishdb.subscription_pricing
            WHERE is_active = true
            ORDER BY plan_id, billing_cycle_id, country_code
            """
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        pricing = [
            {
                'plan_id': r[0],
                'billing_cycle_id': r[1],
                'country_code': r[2],
                'base_price': float(r[3]) if r[3] else 0,
                'tax_percent': float(r[4]) if r[4] else 0,
                'final_price': float(r[5]) if r[5] else 0,
                'is_active': r[6]
            }
            for r in rows
        ]
        
        return jsonify(success=True, data=pricing), 200
        
    except Exception as e:
        logging.error(f"Error fetching subscription pricing: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching subscription pricing: {str(e)}'), 500


@app.route('/api/subscription-pricing/<int:plan_id>', methods=['GET'])
def get_plan_pricing(plan_id):
    """
    Retrieve pricing for a specific subscription plan.
    Optionally filter by country_code and billing_cycle_id via query parameters.
    """
    try:
        country_code = request.args.get('country_code', 'IN')  # Default to India
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT plan_id, billing_cycle_id, country_code, base_price, tax_percent, final_price, is_active
            FROM numerojyutishdb.subscription_pricing
            WHERE plan_id = %s AND country_code = %s AND is_active = true
            ORDER BY billing_cycle_id
            """,
            (plan_id, country_code)
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        if not rows:
            return jsonify(success=False, message=f'No pricing found for plan {plan_id} in country {country_code}'), 404
        
        pricing = [
            {
                'plan_id': r[0],
                'billing_cycle_id': r[1],
                'country_code': r[2],
                'base_price': float(r[3]) if r[3] else 0,
                'tax_percent': float(r[4]) if r[4] else 0,
                'final_price': float(r[5]) if r[5] else 0,
                'is_active': r[6]
            }
            for r in rows
        ]
        
        return jsonify(success=True, data=pricing), 200
        
    except Exception as e:
        logging.error(f"Error fetching pricing for plan {plan_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching plan pricing: {str(e)}'), 500


@app.route('/api/subscription-plans-with-pricing', methods=['GET'])
def get_plans_with_pricing():
    """
    Retrieve all subscription plans with their pricing information.
    Returns combined data from both tables.
    """
    try:
        country_code = request.args.get('country_code', 'IN')  # Default to India
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT 
                sp.plan_id,
                sp.plan_code,
                sp.plan_name,
                sp.description,
                sp.is_active as plan_active,
                sp.subscribefor,
                spr.billing_cycle_id,
                spr.country_code,
                spr.base_price,
                spr.tax_percent,
                spr.final_price,
                spr.is_active as pricing_active
            FROM numerojyutishdb.subscription_plans sp
            LEFT JOIN numerojyutishdb.subscription_pricing spr 
                ON sp.plan_id = spr.plan_id AND spr.country_code = %s AND spr.is_active = true
            WHERE sp.is_active = true
            ORDER BY sp.plan_id, spr.billing_cycle_id
            """,
            (country_code,)
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Group pricing by plan
        plans_dict = {}
        for row in rows:
            plan_id = row[0]
            
            if plan_id not in plans_dict:
                plans_dict[plan_id] = {
                    'plan_id': row[0],
                    'plan_code': row[1],
                    'plan_name': row[2],
                    'description': row[3],
                    'is_active': row[4],
                    'subscribefor': row[5],
                    'pricing': []
                }
            
            # Add pricing if available
            if row[6] is not None:  # billing_cycle_id exists
                plans_dict[plan_id]['pricing'].append({
                    'billing_cycle_id': row[6],
                    'country_code': row[7],
                    'base_price': float(row[8]) if row[8] else 0,
                    'tax_percent': float(row[9]) if row[9] else 0,
                    'final_price': float(row[10]) if row[10] else 0,
                    'is_active': row[11]
                })
        
        plans = list(plans_dict.values())
        
        return jsonify(success=True, country_code=country_code, data=plans), 200
        
    except Exception as e:
        logging.error(f"Error fetching plans with pricing: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching plans with pricing: {str(e)}'), 500


# Relationship status lookup endpoints
@app.route('/api/relationship-statuses', methods=['GET'])
def list_relationship_statuses():
    """Return all rows from relationship_status_lut."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT code, status_key, display_value FROM numerojyutishdb.relationship_status_lut ORDER BY code")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        data = [
            { 'code': r[0], 'status_key': r[1], 'display_value': r[2] }
            for r in rows
        ]
        return jsonify(success=True, data=data)
    except Exception as e:
        logging.error(f"Error listing relationship statuses: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error fetching relationship statuses'), 500


@app.route('/api/relationship-statuses/<int:code>', methods=['GET'])
def get_relationship_status(code):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT code, status_key, display_value FROM numerojyutishdb.relationship_status_lut WHERE code = %s", (code,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify(success=False, message='Not found'), 404
        return jsonify(success=True, data={ 'code': row[0], 'status_key': row[1], 'display_value': row[2] })
    except Exception as e:
        logging.error(f"Error fetching relationship status {code}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error fetching relationship status'), 500


@app.route('/api/relationship-statuses', methods=['POST'])
def create_relationship_status():
    data = request.get_json() or {}
    code = data.get('code')
    status_key = data.get('status_key')
    display_value = data.get('display_value')
    if code is None or not status_key or not display_value:
        return jsonify(success=False, message='code, status_key and display_value are required'), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO numerojyutishdb.relationship_status_lut (code, status_key, display_value) VALUES (%s, %s, %s)", (code, status_key, display_value))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(success=True, message='Created'), 201
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error inserting relationship status: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Duplicate code or constraint violation'), 409
    except Exception as e:
        logging.error(f"Error creating relationship status: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error creating relationship status'), 500


# Professional status lookup endpoints
@app.route('/api/professional-statuses', methods=['GET'])
def list_professional_statuses():
    """Return all rows from professional_status_lut."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT code, status_key, display_value, description, active_flag FROM numerojyutishdb.professional_status_lut ORDER BY code")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        data = [
            { 'code': r[0], 'status_key': r[1], 'display_value': r[2], 'description': r[3], 'active_flag': r[4] }
            for r in rows
        ]
        return jsonify(success=True, data=data)
    except Exception as e:
        logging.error(f"Error listing professional statuses: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error fetching professional statuses'), 500


@app.route('/api/professional-statuses/<int:code>', methods=['GET'])
def get_professional_status(code):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT code, status_key, display_value, description, active_flag FROM numerojyutishdb.professional_status_lut WHERE code = %s", (code,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify(success=False, message='Not found'), 404
        return jsonify(success=True, data={ 'code': row[0], 'status_key': row[1], 'display_value': row[2], 'description': row[3], 'active_flag': row[4] })
    except Exception as e:
        logging.error(f"Error fetching professional status {code}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error fetching professional status'), 500


@app.route('/api/professional-statuses', methods=['POST'])
def create_professional_status():
    data = request.get_json() or {}
    code = data.get('code')
    status_key = data.get('status_key')
    display_value = data.get('display_value')
    description = data.get('description')
    active_flag = data.get('active_flag', 'Y')
    if code is None or not status_key or not display_value:
        return jsonify(success=False, message='code, status_key and display_value are required'), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO numerojyutishdb.professional_status_lut (code, status_key, display_value, description, active_flag) VALUES (%s, %s, %s, %s, %s)",
            (code, status_key, display_value, description, active_flag)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(success=True, message='Created'), 201
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error inserting professional status: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Duplicate code or constraint violation'), 409
    except Exception as e:
        logging.error(f"Error creating professional status: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error creating professional status'), 500


# Profession lookup endpoints
@app.route('/api/professions', methods=['GET'])
def list_professions():
    """Return all rows from profession_lut."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT code, profession_key, display_value, category, active_flag FROM numerojyutishdb.profession_lut ORDER BY code")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        data = [
            { 'code': r[0], 'profession_key': r[1], 'display_value': r[2], 'category': r[3], 'active_flag': r[4] }
            for r in rows
        ]
        return jsonify(success=True, data=data)
    except Exception as e:
        logging.error(f"Error listing professions: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error fetching professions'), 500


@app.route('/api/professions/<int:code>', methods=['GET'])
def get_profession(code):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT code, profession_key, display_value, category, active_flag FROM numerojyutishdb.profession_lut WHERE code = %s", (code,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify(success=False, message='Not found'), 404
        return jsonify(success=True, data={ 'code': row[0], 'profession_key': row[1], 'display_value': row[2], 'category': row[3], 'active_flag': row[4] })
    except Exception as e:
        logging.error(f"Error fetching profession {code}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error fetching profession'), 500


@app.route('/api/professions', methods=['POST'])
def create_profession():
    data = request.get_json() or {}
    code = data.get('code')
    profession_key = data.get('profession_key')
    display_value = data.get('display_value')
    category = data.get('category')
    active_flag = data.get('active_flag', 'Y')
    if code is None or not profession_key or not display_value:
        return jsonify(success=False, message='code, profession_key and display_value are required'), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO numerojyutishdb.profession_lut (code, profession_key, display_value, category, active_flag) VALUES (%s, %s, %s, %s, %s)",
            (code, profession_key, display_value, category, active_flag)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(success=True, message='Created'), 201
    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error inserting profession: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Duplicate code or constraint violation'), 409
    except Exception as e:
        logging.error(f"Error creating profession: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message='Error creating profession'), 500


# OAuth endpoints to start and complete social login
@app.route('/api/auth/<provider>')
def oauth_login(provider):
    if provider not in ('google', 'facebook'):
        return jsonify(success=False, message='Unsupported provider'), 400
    # Redirect URI must be registered in the OAuth provider console
    # Prefer explicit BACKEND_REDIRECT_URL, otherwise build it from this request (backend callback)
    redirect_uri = os.getenv('BACKEND_REDIRECT_URL') or (request.url_root.rstrip('/') + f'/api/auth/{provider}/callback')
    try:
        client = oauth.create_client(provider)
        return client.authorize_redirect(redirect_uri)
    except Exception as e:
        logging.error(f"OAuth authorize error for {provider}: {e}")
        return jsonify(success=False, message='OAuth configuration error'), 500

@app.route('/api/auth/<provider>/callback')
def oauth_callback(provider):
    if provider not in ('google', 'facebook'):
        return jsonify(success=False, message='Unsupported provider'), 400
    try:
        client = oauth.create_client(provider)
        token = client.authorize_access_token()
        if provider == 'google':
            # OpenID Connect response contains id_token
            userinfo = client.parse_id_token(token)
            email = userinfo.get('email')
            full_name = userinfo.get('name')
        else:
            # Facebook: fetch profile
            resp = client.get('me?fields=id,name,email')
            info = resp.json()
            email = info.get('email')
            full_name = info.get('name')
        if not email:
            return jsonify(success=False, message='Email not provided by provider'), 400

        # Create or find user
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM numerojyutishdb.security WHERE email = %s", (email,))
        row = cur.fetchone()
        if row:
            user_id = row[0]
        else:
            # Insert a new user with no password (social login)
            cur.execute(
                "INSERT INTO numerojyutishdb.security (email, phone, password_hash, user_role, authtoken, full_name) VALUES (%s,%s,%s,%s,%s,%s) RETURNING user_id",
                (email, None, None, '1', None, full_name)
            )
            user_id = cur.fetchone()[0]
            conn.commit()

        # generate application auth token and persist
        app_token = secrets.token_urlsafe(32)
        cur.execute("UPDATE numerojyutishdb.security SET authtoken = %s WHERE user_id = %s", (app_token, user_id))
        conn.commit()
        cur.close()
        conn.close()

        frontend = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        # Redirect back to frontend with token (frontend should handle storing token)
        return redirect(f"{frontend}/social-callback?token={app_token}&user_id={user_id}&email={email}")

    except Exception as e:
        logging.error(f"OAuth callback error for {provider}: {e}")
        return jsonify(success=False, message='OAuth callback error'), 500


# ==================== PRODUCT MANAGEMENT ENDPOINTS ====================

@app.route('/api/product-categories', methods=['GET'])
def get_product_categories():
    """
    Retrieve all active product categories.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT category_id, category_name, category_description, is_active, created_at, updated_at
            FROM numerojyutishdb.product_categories
            WHERE is_active = true
            ORDER BY category_name
            """
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        categories = [
            {
                'category_id': r[0],
                'category_name': r[1],
                'category_description': r[2],
                'is_active': r[3],
                'created_at': r[4].isoformat() if r[4] else None,
                'updated_at': r[5].isoformat() if r[5] else None
            }
            for r in rows
        ]
        
        return jsonify(success=True, data=categories), 200
        
    except Exception as e:
        logging.error(f"Error fetching product categories: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching categories: {str(e)}'), 500


@app.route('/api/products', methods=['GET'])
def get_products():
    """
    Retrieve all active products.
    """
    try:
        category_id = request.args.get('category_id', type=int)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if category_id:
            cur.execute(
                """
                SELECT product_id, category_id, product_name, product_description, is_active, created_at, updated_at
                FROM numerojyutishdb.products
                WHERE is_active = true AND category_id = %s
                ORDER BY product_name
                """,
                (category_id,)
            )
        else:
            cur.execute(
                """
                SELECT product_id, category_id, product_name, product_description, is_active, created_at, updated_at
                FROM numerojyutishdb.products
                WHERE is_active = true
                ORDER BY product_name
                """
            )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        products = [
            {
                'product_id': r[0],
                'category_id': r[1],
                'product_name': r[2],
                'product_description': r[3],
                'is_active': r[4],
                'created_at': r[5].isoformat() if r[5] else None,
                'updated_at': r[6].isoformat() if r[6] else None
            }
            for r in rows
        ]
        
        return jsonify(success=True, data=products), 200
        
    except Exception as e:
        logging.error(f"Error fetching products: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching products: {str(e)}'), 500


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Retrieve a specific product by ID.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT product_id, category_id, product_name, product_description, is_active, created_at, updated_at
            FROM numerojyutishdb.products
            WHERE product_id = %s
            """,
            (product_id,)
        )
        
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            return jsonify(success=False, message='Product not found'), 404
        
        product = {
            'product_id': row[0],
            'category_id': row[1],
            'product_name': row[2],
            'product_description': row[3],
            'is_active': row[4],
            'created_at': row[5].isoformat() if row[5] else None,
            'updated_at': row[6].isoformat() if row[6] else None
        }
        
        cur.close()
        conn.close()
        
        return jsonify(success=True, data=product), 200
        
    except Exception as e:
        logging.error(f"Error fetching product {product_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching product: {str(e)}'), 500


@app.route('/api/products-with-pricing', methods=['GET'])
def get_products_with_pricing():
    """
    Retrieve all products with their pricing and tax information for a specific country.
    """
    try:
        country_code = request.args.get('country_code', 'IN')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all products with pricing and tax information
        cur.execute(
            """
            SELECT 
                p.product_id,
                p.category_id,
                p.product_name,
                p.product_description,
                p.is_active,
                p.created_at,
                p.updated_at,
                pp.pricing_id,
                pp.base_price,
                pp.discount_percent,
                pp.is_tax_inclusive,
                tm.tax_percent,
                pp.currency_code
            FROM numerojyutishdb.products p
            LEFT JOIN numerojyutishdb.product_pricing pp 
                ON p.product_id = pp.product_id 
                AND pp.country_code = %s 
                AND pp.is_active = true
            LEFT JOIN numerojyutishdb.product_pricing_tax ppt
                ON pp.pricing_id = ppt.pricing_id
            LEFT JOIN numerojyutishdb.tax_master tm
                ON ppt.tax_id = tm.tax_id
                AND tm.country_code = %s
                AND tm.is_active = true
            WHERE p.is_active = true
            ORDER BY p.product_id, pp.pricing_id
            """,
            (country_code, country_code)
        )
        
        rows = cur.fetchall()
        
        # Get product images
        cur.execute(
            """
            SELECT product_id, image_id, image_url, is_primary, created_at
            FROM numerojyutishdb.product_images
            ORDER BY product_id, is_primary DESC, image_id
            """
        )
        
        image_rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Group images by product
        images_dict = {}
        for img_row in image_rows:
            product_id = img_row[0]
            if product_id not in images_dict:
                images_dict[product_id] = []
            images_dict[product_id].append({
                'image_id': img_row[1],
                'image_url': img_row[2],
                'is_primary': img_row[3],
                'created_at': img_row[4].isoformat() if img_row[4] else None
            })
        
        # Group pricing and tax by product
        products_dict = {}
        for row in rows:
            product_id = row[0]
            
            if product_id not in products_dict:
                products_dict[product_id] = {
                    'product_id': row[0],
                    'category_id': row[1],
                    'product_name': row[2],
                    'product_description': row[3],
                    'is_active': row[4],
                    'created_at': row[5].isoformat() if row[5] else None,
                    'updated_at': row[6].isoformat() if row[6] else None,
                    'pricing': [],
                    'images': images_dict.get(product_id, [])
                }
            
            # Add pricing if available
            if row[7] is not None:  # pricing_id exists
                final_price = row[8]  # base_price
                discount = row[9] or 0
                tax_percent = row[11] or 0
                
                # Apply discount
                if discount > 0:
                    final_price = final_price * (1 - discount / 100)
                
                # Add tax if not tax inclusive
                if not row[10]:  # not is_tax_inclusive
                    tax_amount = final_price * (tax_percent / 100)
                    final_price = final_price + tax_amount
                
                pricing_entry = {
                    'pricing_id': row[7],
                    'base_price': float(row[8]),
                    'discount_percent': float(row[9]) if row[9] else 0,
                    'tax_percent': float(row[11]) if row[11] else 0,
                    'final_price': float(round(final_price, 2)),
                    'currency_code': row[12],
                    'is_tax_inclusive': row[10]
                }
                
                # Avoid duplicates
                if not any(p['pricing_id'] == row[7] for p in products_dict[product_id]['pricing']):
                    products_dict[product_id]['pricing'].append(pricing_entry)
        
        products = list(products_dict.values())
        
        return jsonify(success=True, country_code=country_code, data=products), 200
        
    except Exception as e:
        logging.error(f"Error fetching products with pricing: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching products: {str(e)}'), 500


@app.route('/api/product-images/<int:product_id>', methods=['GET'])
def get_product_images(product_id):
    """
    Retrieve all images for a specific product.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT image_id, product_id, image_url, is_primary, created_at
            FROM numerojyutishdb.product_images
            WHERE product_id = %s
            ORDER BY is_primary DESC, image_id
            """,
            (product_id,)
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        images = [
            {
                'image_id': r[0],
                'product_id': r[1],
                'image_url': r[2],
                'is_primary': r[3],
                'created_at': r[4].isoformat() if r[4] else None
            }
            for r in rows
        ]
        
        return jsonify(success=True, data=images), 200
        
    except Exception as e:
        logging.error(f"Error fetching product images: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching images: {str(e)}'), 500


@app.route('/api/upload-product-image', methods=['POST'])
def upload_product_image():
    """
    Upload a product image file.
    Expects multipart/form-data with 'file' and 'product_id' fields.
    Returns the uploaded image URL.
    """
    try:
        # Check authorization
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        if not token:
            return jsonify(success=False, message='Authorization token required'), 401
        
        # Validate product_id
        product_id = request.form.get('product_id')
        if not product_id:
            return jsonify(success=False, message='product_id is required'), 400
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify(success=False, message='No file provided'), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify(success=False, message='No file selected'), 400
        
        if not allowed_file(file.filename):
            return jsonify(success=False, message='File type not allowed. Allowed types: png, jpg, jpeg, gif, webp'), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify(success=False, message='File size exceeds maximum (5MB)'), 400
        
        # Generate secure filename
        filename = secure_filename(f"{product_id}_{int(datetime.now().timestamp())}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        # Generate image URL (adjust based on your deployment setup)
        # For local development: /uploads/product-images/filename
        image_url = f"/uploads/product-images/{filename}"
        
        logging.info(f"Product image uploaded: {filename}")
        
        return jsonify(
            success=True,
            data={'image_url': image_url, 'filename': filename},
            message='Image uploaded successfully'
        ), 201
        
    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        return jsonify(success=False, message=f'Error uploading image: {str(e)}'), 500


# ==================== PRODUCT MASTER - CREATE/UPDATE ENDPOINTS ====================

@app.route('/api/product-categories', methods=['POST'])
def create_product_category():
    """
    Create a new product category.
    """
    try:
        data = request.get_json() or {}
        category_name = data.get('category_name')
        category_description = data.get('category_description')
        is_active = data.get('is_active', True)

        if not category_name:
            return jsonify(success=False, message='category_name is required'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO numerojyutishdb.product_categories (category_name, category_description, is_active)
            VALUES (%s, %s, %s)
            RETURNING category_id, category_name, category_description, is_active, created_at, updated_at
            """,
            (category_name, category_description, is_active)
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        category = {
            'category_id': row[0],
            'category_name': row[1],
            'category_description': row[2],
            'is_active': row[3],
            'created_at': row[4].isoformat() if row[4] else None,
            'updated_at': row[5].isoformat() if row[5] else None
        }

        return jsonify(success=True, data=category, message='Category created successfully'), 201

    except Exception as e:
        logging.error(f"Error creating category: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating category: {str(e)}'), 500


@app.route('/api/product-categories/<int:category_id>', methods=['PUT'])
def update_product_category(category_id):
    """
    Update an existing product category.
    """
    try:
        data = request.get_json() or {}
        category_name = data.get('category_name')
        category_description = data.get('category_description')
        is_active = data.get('is_active')

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        update_values = []

        if category_name is not None:
            update_fields.append("category_name = %s")
            update_values.append(category_name)
        if category_description is not None:
            update_fields.append("category_description = %s")
            update_values.append(category_description)
        if is_active is not None:
            update_fields.append("is_active = %s")
            update_values.append(is_active)

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(category_id)

        query = f"""
            UPDATE numerojyutishdb.product_categories
            SET {', '.join(update_fields)}
            WHERE category_id = %s
            RETURNING category_id, category_name, category_description, is_active, created_at, updated_at
        """

        cur.execute(query, update_values)
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Category not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        category = {
            'category_id': row[0],
            'category_name': row[1],
            'category_description': row[2],
            'is_active': row[3],
            'created_at': row[4].isoformat() if row[4] else None,
            'updated_at': row[5].isoformat() if row[5] else None
        }

        return jsonify(success=True, data=category, message='Category updated successfully'), 200

    except Exception as e:
        logging.error(f"Error updating category: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating category: {str(e)}'), 500


@app.route('/api/products', methods=['POST'])
def create_product():
    """
    Create a new product.
    """
    try:
        data = request.get_json() or {}
        category_id = data.get('category_id')
        product_name = data.get('product_name')
        product_description = data.get('product_description')
        is_active = data.get('is_active', True)

        if not category_id or not product_name:
            return jsonify(success=False, message='category_id and product_name are required'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO numerojyutishdb.products (category_id, product_name, product_description, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING product_id, category_id, product_name, product_description, is_active, created_at, updated_at
            """,
            (category_id, product_name, product_description, is_active)
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        product = {
            'product_id': row[0],
            'category_id': row[1],
            'product_name': row[2],
            'product_description': row[3],
            'is_active': row[4],
            'created_at': row[5].isoformat() if row[5] else None,
            'updated_at': row[6].isoformat() if row[6] else None
        }

        return jsonify(success=True, data=product, message='Product created successfully'), 201

    except Exception as e:
        logging.error(f"Error creating product: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating product: {str(e)}'), 500


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Update an existing product.
    """
    try:
        data = request.get_json() or {}
        category_id = data.get('category_id')
        product_name = data.get('product_name')
        product_description = data.get('product_description')
        is_active = data.get('is_active')

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        update_values = []

        if category_id is not None:
            update_fields.append("category_id = %s")
            update_values.append(category_id)
        if product_name is not None:
            update_fields.append("product_name = %s")
            update_values.append(product_name)
        if product_description is not None:
            update_fields.append("product_description = %s")
            update_values.append(product_description)
        if is_active is not None:
            update_fields.append("is_active = %s")
            update_values.append(is_active)

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_values.append(product_id)

        query = f"""
            UPDATE numerojyutishdb.products
            SET {', '.join(update_fields)}
            WHERE product_id = %s
            RETURNING product_id, category_id, product_name, product_description, is_active, created_at, updated_at
        """

        cur.execute(query, update_values)
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Product not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        product = {
            'product_id': row[0],
            'category_id': row[1],
            'product_name': row[2],
            'product_description': row[3],
            'is_active': row[4],
            'created_at': row[5].isoformat() if row[5] else None,
            'updated_at': row[6].isoformat() if row[6] else None
        }

        return jsonify(success=True, data=product, message='Product updated successfully'), 200

    except Exception as e:
        logging.error(f"Error updating product: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating product: {str(e)}'), 500


@app.route('/api/product-pricing', methods=['GET'])
def get_product_pricing():
    """
    Retrieve all product pricing records.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT pricing_id, product_id, country_code, state_code, currency_code, base_price, discount_percent, is_tax_inclusive, is_active, created_at
            FROM numerojyutishdb.product_pricing
            ORDER BY product_id, country_code
            """
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        pricings = [
            {
                'pricing_id': r[0],
                'product_id': r[1],
                'country_code': r[2],
                'state_code': r[3],
                'currency_code': r[4],
                'base_price': float(r[5]),
                'discount_percent': float(r[6]),
                'is_tax_inclusive': r[7],
                'is_active': r[8],
                'created_at': r[9].isoformat() if r[9] else None
            }
            for r in rows
        ]

        return jsonify(success=True, data=pricings), 200

    except Exception as e:
        logging.error(f"Error fetching product pricing: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching pricing: {str(e)}'), 500


@app.route('/api/product-pricing', methods=['POST'])
def create_product_pricing():
    """
    Create a new product pricing record.
    """
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        country_code = data.get('country_code')
        state_code = data.get('state_code')
        currency_code = data.get('currency_code')
        base_price = data.get('base_price')
        discount_percent = data.get('discount_percent', 0)
        is_tax_inclusive = data.get('is_tax_inclusive', False)
        is_active = data.get('is_active', True)

        if not all([product_id, country_code, currency_code, base_price]):
            return jsonify(success=False, message='product_id, country_code, currency_code, and base_price are required'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO numerojyutishdb.product_pricing (product_id, country_code, state_code, currency_code, base_price, discount_percent, is_tax_inclusive, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING pricing_id, product_id, country_code, state_code, currency_code, base_price, discount_percent, is_tax_inclusive, is_active, created_at
            """,
            (product_id, country_code, state_code, currency_code, base_price, discount_percent, is_tax_inclusive, is_active)
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        pricing = {
            'pricing_id': row[0],
            'product_id': row[1],
            'country_code': row[2],
            'state_code': row[3],
            'currency_code': row[4],
            'base_price': float(row[5]),
            'discount_percent': float(row[6]),
            'is_tax_inclusive': row[7],
            'is_active': row[8],
            'created_at': row[9].isoformat() if row[9] else None
        }

        return jsonify(success=True, data=pricing, message='Pricing created successfully'), 201

    except Exception as e:
        logging.error(f"Error creating pricing: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating pricing: {str(e)}'), 500


@app.route('/api/product-pricing/<int:pricing_id>', methods=['PUT'])
def update_product_pricing(pricing_id):
    """
    Update an existing product pricing record.
    """
    try:
        data = request.get_json() or {}

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        update_values = []

        if 'product_id' in data:
            update_fields.append("product_id = %s")
            update_values.append(data['product_id'])
        if 'country_code' in data:
            update_fields.append("country_code = %s")
            update_values.append(data['country_code'])
        if 'state_code' in data:
            update_fields.append("state_code = %s")
            update_values.append(data['state_code'])
        if 'currency_code' in data:
            update_fields.append("currency_code = %s")
            update_values.append(data['currency_code'])
        if 'base_price' in data:
            update_fields.append("base_price = %s")
            update_values.append(data['base_price'])
        if 'discount_percent' in data:
            update_fields.append("discount_percent = %s")
            update_values.append(data['discount_percent'])
        if 'is_tax_inclusive' in data:
            update_fields.append("is_tax_inclusive = %s")
            update_values.append(data['is_tax_inclusive'])
        if 'is_active' in data:
            update_fields.append("is_active = %s")
            update_values.append(data['is_active'])

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400

        update_values.append(pricing_id)

        query = f"""
            UPDATE numerojyutishdb.product_pricing
            SET {', '.join(update_fields)}
            WHERE pricing_id = %s
            RETURNING pricing_id, product_id, country_code, state_code, currency_code, base_price, discount_percent, is_tax_inclusive, is_active, created_at
        """

        cur.execute(query, update_values)
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Pricing not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        pricing = {
            'pricing_id': row[0],
            'product_id': row[1],
            'country_code': row[2],
            'state_code': row[3],
            'currency_code': row[4],
            'base_price': float(row[5]),
            'discount_percent': float(row[6]),
            'is_tax_inclusive': row[7],
            'is_active': row[8],
            'created_at': row[9].isoformat() if row[9] else None
        }

        return jsonify(success=True, data=pricing, message='Pricing updated successfully'), 200

    except Exception as e:
        logging.error(f"Error updating pricing: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating pricing: {str(e)}'), 500


@app.route('/api/tax-master', methods=['GET'])
def get_tax_master():
    """
    Retrieve all tax master records.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT tax_id, country_code, state_code, tax_name, tax_percent, is_active, effective_from, effective_to
            FROM numerojyutishdb.tax_master
            ORDER BY country_code, state_code, tax_name
            """
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        taxes = [
            {
                'tax_id': r[0],
                'country_code': r[1],
                'state_code': r[2],
                'tax_name': r[3],
                'tax_percent': float(r[4]),
                'is_active': r[5],
                'effective_from': r[6].isoformat() if r[6] else None,
                'effective_to': r[7].isoformat() if r[7] else None
            }
            for r in rows
        ]

        return jsonify(success=True, data=taxes), 200

    except Exception as e:
        logging.error(f"Error fetching tax master: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching taxes: {str(e)}'), 500


@app.route('/api/tax-master', methods=['POST'])
def create_tax_master():
    """
    Create a new tax master record.
    """
    try:
        data = request.get_json() or {}
        country_code = data.get('country_code')
        state_code = data.get('state_code')
        tax_name = data.get('tax_name')
        tax_percent = data.get('tax_percent')
        is_active = data.get('is_active', True)
        effective_from = data.get('effective_from')
        effective_to = data.get('effective_to')

        if not all([country_code, tax_name, tax_percent]):
            return jsonify(success=False, message='country_code, tax_name, and tax_percent are required'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO numerojyutishdb.tax_master (country_code, state_code, tax_name, tax_percent, is_active, effective_from, effective_to)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING tax_id, country_code, state_code, tax_name, tax_percent, is_active, effective_from, effective_to
            """,
            (country_code, state_code, tax_name, tax_percent, is_active, effective_from, effective_to)
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        tax = {
            'tax_id': row[0],
            'country_code': row[1],
            'state_code': row[2],
            'tax_name': row[3],
            'tax_percent': float(row[4]),
            'is_active': row[5],
            'effective_from': row[6].isoformat() if row[6] else None,
            'effective_to': row[7].isoformat() if row[7] else None
        }

        return jsonify(success=True, data=tax, message='Tax created successfully'), 201

    except Exception as e:
        logging.error(f"Error creating tax: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating tax: {str(e)}'), 500


@app.route('/api/tax-master/<int:tax_id>', methods=['PUT'])
def update_tax_master(tax_id):
    """
    Update an existing tax master record.
    """
    try:
        data = request.get_json() or {}

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        update_values = []

        if 'country_code' in data:
            update_fields.append("country_code = %s")
            update_values.append(data['country_code'])
        if 'state_code' in data:
            update_fields.append("state_code = %s")
            update_values.append(data['state_code'])
        if 'tax_name' in data:
            update_fields.append("tax_name = %s")
            update_values.append(data['tax_name'])
        if 'tax_percent' in data:
            update_fields.append("tax_percent = %s")
            update_values.append(data['tax_percent'])
        if 'is_active' in data:
            update_fields.append("is_active = %s")
            update_values.append(data['is_active'])
        if 'effective_from' in data:
            update_fields.append("effective_from = %s")
            update_values.append(data['effective_from'])
        if 'effective_to' in data:
            update_fields.append("effective_to = %s")
            update_values.append(data['effective_to'])

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400

        update_values.append(tax_id)

        query = f"""
            UPDATE numerojyutishdb.tax_master
            SET {', '.join(update_fields)}
            WHERE tax_id = %s
            RETURNING tax_id, country_code, state_code, tax_name, tax_percent, is_active, effective_from, effective_to
        """

        cur.execute(query, update_values)
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Tax not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        tax = {
            'tax_id': row[0],
            'country_code': row[1],
            'state_code': row[2],
            'tax_name': row[3],
            'tax_percent': float(row[4]),
            'is_active': row[5],
            'effective_from': row[6].isoformat() if row[6] else None,
            'effective_to': row[7].isoformat() if row[7] else None
        }

        return jsonify(success=True, data=tax, message='Tax updated successfully'), 200

    except Exception as e:
        logging.error(f"Error updating tax: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating tax: {str(e)}'), 500


@app.route('/api/product-details', methods=['GET'])
def get_product_details():
    """
    Retrieve all product details with pricing and tax information.
    Optional query parameter: country_code
    Returns product_id, product_name, product_description, category_name, category_description,
    pricing_id, country_code, state_code, currency_code, base_price, discount_percent,
    is_tax_inclusive, tax_id, tax_name, tax_percent, product_active, pricing_active
    """
    try:
        country_code = request.args.get('country_code')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if country_code:
            cur.execute(
                """
                SELECT product_id, product_name, product_description, category_name, category_description, 
                       pricing_id, country_code, state_code, currency_code, base_price, discount_percent, 
                       is_tax_inclusive, tax_id, tax_name, tax_percent, product_active, pricing_active
                FROM numerojyutishdb.product_details
                WHERE country_code = %s
                """
                , (country_code,)
            )
        else:
            cur.execute(
                """
                SELECT product_id, product_name, product_description, category_name, category_description, 
                       pricing_id, country_code, state_code, currency_code, base_price, discount_percent, 
                       is_tax_inclusive, tax_id, tax_name, tax_percent, product_active, pricing_active
                FROM numerojyutishdb.product_details
                """
            )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        products = [
            {
                'product_id': r[0],
                'product_name': r[1],
                'product_description': r[2],
                'category_name': r[3],
                'category_description': r[4],
                'pricing_id': r[5],
                'country_code': r[6],
                'state_code': r[7],
                'currency_code': r[8],
                'base_price': float(r[9]) if r[9] else None,
                'discount_percent': float(r[10]) if r[10] else None,
                'is_tax_inclusive': r[11],
                'tax_id': r[12],
                'tax_name': r[13],
                'tax_percent': float(r[14]) if r[14] else None,
                'product_active': r[15],
                'pricing_active': r[16]
            }
            for r in rows
        ]
        
        return jsonify(success=True, data=products), 200
        
    except Exception as e:
        logging.error(f"Error fetching product details: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching product details: {str(e)}'), 500


@app.route('/api/product-pricing/<int:pricing_id>', methods=['GET'])
def get_single_product_pricing(pricing_id):
    """
    Retrieve a specific product pricing record by pricing_id.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT pricing_id, product_id, country_code, state_code, currency_code, base_price, discount_percent, is_tax_inclusive, is_active, created_at
            FROM numerojyutishdb.product_pricing
            WHERE pricing_id = %s
            """,
            (pricing_id,)
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify(success=False, message='Pricing not found'), 404

        pricing = {
            'pricing_id': row[0],
            'product_id': row[1],
            'country_code': row[2],
            'state_code': row[3],
            'currency_code': row[4],
            'base_price': float(row[5]),
            'discount_percent': float(row[6]),
            'is_tax_inclusive': row[7],
            'is_active': row[8],
            'created_at': row[9].isoformat() if row[9] else None
        }

        return jsonify(success=True, data=pricing), 200

    except Exception as e:
        logging.error(f"Error fetching pricing {pricing_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching pricing: {str(e)}'), 500


@app.route('/api/product-pricing/<int:pricing_id>', methods=['DELETE'])
def delete_product_pricing(pricing_id):
    """
    Delete (soft delete) a product pricing record by setting is_active to false.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE numerojyutishdb.product_pricing
            SET is_active = false
            WHERE pricing_id = %s
            RETURNING pricing_id
            """,
            (pricing_id,)
        )

        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Pricing not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(success=True, message='Pricing deleted successfully'), 200

    except Exception as e:
        logging.error(f"Error deleting pricing {pricing_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting pricing: {str(e)}'), 500


@app.route('/api/tax-master/<int:tax_id>', methods=['GET'])
def get_single_tax_master(tax_id):
    """
    Retrieve a specific tax master record by tax_id.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT tax_id, country_code, state_code, tax_name, tax_percent, is_active, effective_from, effective_to
            FROM numerojyutishdb.tax_master
            WHERE tax_id = %s
            """,
            (tax_id,)
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify(success=False, message='Tax not found'), 404

        tax = {
            'tax_id': row[0],
            'country_code': row[1],
            'state_code': row[2],
            'tax_name': row[3],
            'tax_percent': float(row[4]),
            'is_active': row[5],
            'effective_from': row[6].isoformat() if row[6] else None,
            'effective_to': row[7].isoformat() if row[7] else None
        }

        return jsonify(success=True, data=tax), 200

    except Exception as e:
        logging.error(f"Error fetching tax {tax_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching tax: {str(e)}'), 500


@app.route('/api/tax-master/<int:tax_id>', methods=['DELETE'])
def delete_tax_master(tax_id):
    """
    Delete (soft delete) a tax master record by setting is_active to false.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE numerojyutishdb.tax_master
            SET is_active = false
            WHERE tax_id = %s
            RETURNING tax_id
            """,
            (tax_id,)
        )

        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Tax not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(success=True, message='Tax deleted successfully'), 200

    except Exception as e:
        logging.error(f"Error deleting tax {tax_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting tax: {str(e)}'), 500


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    Delete (soft delete) a product by setting is_active to false.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE numerojyutishdb.products
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = %s
            RETURNING product_id
            """,
            (product_id,)
        )

        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Product not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(success=True, message='Product deleted successfully'), 200

    except Exception as e:
        logging.error(f"Error deleting product {product_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting product: {str(e)}'), 500


@app.route('/api/product-categories/<int:category_id>', methods=['DELETE'])
def delete_product_category(category_id):
    """
    Delete (soft delete) a product category by setting is_active to false.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE numerojyutishdb.product_categories
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE category_id = %s
            RETURNING category_id
            """,
            (category_id,)
        )

        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Category not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(success=True, message='Category deleted successfully'), 200

    except Exception as e:
        logging.error(f"Error deleting category {category_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting category: {str(e)}'), 500


@app.route('/api/product-images', methods=['POST'])
def create_product_image():
    """
    Create a new product image record.
    """
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        image_url = data.get('image_url')
        is_primary = data.get('is_primary', False)

        if not product_id or not image_url:
            return jsonify(success=False, message='product_id and image_url are required'), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # If marking as primary, unset other primary images
        if is_primary:
            cur.execute(
                "UPDATE numerojyutishdb.product_images SET is_primary = false WHERE product_id = %s",
                (product_id,)
            )

        cur.execute(
            """
            INSERT INTO numerojyutishdb.product_images (product_id, image_url, is_primary)
            VALUES (%s, %s, %s)
            RETURNING image_id, product_id, image_url, is_primary, created_at
            """,
            (product_id, image_url, is_primary)
        )

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        image = {
            'image_id': row[0],
            'product_id': row[1],
            'image_url': row[2],
            'is_primary': row[3],
            'created_at': row[4].isoformat() if row[4] else None
        }

        return jsonify(success=True, data=image, message='Image created successfully'), 201

    except Exception as e:
        logging.error(f"Error creating product image: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error creating image: {str(e)}'), 500


@app.route('/api/product-images/<int:image_id>', methods=['GET'])
def get_single_product_image(image_id):
    """
    Retrieve a specific product image by image_id.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT image_id, product_id, image_url, is_primary, created_at
            FROM numerojyutishdb.product_images
            WHERE image_id = %s
            """,
            (image_id,)
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify(success=False, message='Image not found'), 404

        image = {
            'image_id': row[0],
            'product_id': row[1],
            'image_url': row[2],
            'is_primary': row[3],
            'created_at': row[4].isoformat() if row[4] else None
        }

        return jsonify(success=True, data=image), 200

    except Exception as e:
        logging.error(f"Error fetching image {image_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching image: {str(e)}'), 500


@app.route('/api/product-images/<int:image_id>', methods=['PUT'])
def update_product_image(image_id):
    """
    Update a product image record.
    """
    try:
        data = request.get_json() or {}

        conn = get_db_connection()
        cur = conn.cursor()

        update_fields = []
        update_values = []

        if 'image_url' in data:
            update_fields.append("image_url = %s")
            update_values.append(data['image_url'])
        if 'is_primary' in data:
            # If setting as primary, unset other primary images for this product
            if data['is_primary']:
                cur.execute(
                    """
                    SELECT product_id FROM numerojyutishdb.product_images WHERE image_id = %s
                    """,
                    (image_id,)
                )
                product_row = cur.fetchone()
                if product_row:
                    product_id = product_row[0]
                    cur.execute(
                        "UPDATE numerojyutishdb.product_images SET is_primary = false WHERE product_id = %s",
                        (product_id,)
                    )

            update_fields.append("is_primary = %s")
            update_values.append(data['is_primary'])

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400

        update_values.append(image_id)

        query = f"""
            UPDATE numerojyutishdb.product_images
            SET {', '.join(update_fields)}
            WHERE image_id = %s
            RETURNING image_id, product_id, image_url, is_primary, created_at
        """

        cur.execute(query, update_values)
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Image not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        image = {
            'image_id': row[0],
            'product_id': row[1],
            'image_url': row[2],
            'is_primary': row[3],
            'created_at': row[4].isoformat() if row[4] else None
        }

        return jsonify(success=True, data=image, message='Image updated successfully'), 200

    except Exception as e:
        logging.error(f"Error updating image {image_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating image: {str(e)}'), 500


@app.route('/api/product-images/<int:image_id>', methods=['DELETE'])
def delete_product_image(image_id):
    """
    Delete a product image record.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            DELETE FROM numerojyutishdb.product_images
            WHERE image_id = %s
            RETURNING image_id
            """,
            (image_id,)
        )

        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, message='Image not found'), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(success=True, message='Image deleted successfully'), 200

    except Exception as e:
        logging.error(f"Error deleting image {image_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error deleting image: {str(e)}'), 500


if __name__ == '__main__':
    app.run(debug=True)
