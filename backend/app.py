import logging
import os
import re
from pathlib import Path
from flask import Flask, request, jsonify, redirect, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import secrets
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from authlib.integrations.flask_client import OAuth
import requests
from twilio.rest import Client as TwilioClient
from datetime import datetime, timedelta, date, time
import cloudinary
import cloudinary.uploader

# Minimal app: only user registration (create-user) functionality
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

load_dotenv(dotenv_path=Path(__file__).resolve().parent / 'data.env')

app = Flask(__name__)
# Allow CORS from any origin (useful for development/testing).
# Note: allowing all origins with credentials can be unsafe in production.
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

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


def ensure_subscription_tables():
    """Ensure subscription and payment tables required for checkout flow exist."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS numerojyutishdb.user_subscriptions
            (
                subscription_id BIGINT NOT NULL DEFAULT nextval('numerojyutishdb.user_subscriptions_subscription_id_seq'::regclass),
                user_id BIGINT NOT NULL,
                plan_id BIGINT NOT NULL,
                billing_cycle_id BIGINT NOT NULL,
                pricing_id BIGINT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status VARCHAR(30) DEFAULT 'ACTIVE',
                auto_renew BOOLEAN DEFAULT TRUE,
                CONSTRAINT user_subscriptions_pkey PRIMARY KEY (subscription_id),
                CONSTRAINT fk_user_cycle FOREIGN KEY (billing_cycle_id)
                    REFERENCES numerojyutishdb.billing_cycles (billing_cycle_id)
                    ON UPDATE NO ACTION
                    ON DELETE NO ACTION,
                CONSTRAINT fk_user_plan FOREIGN KEY (plan_id)
                    REFERENCES numerojyutishdb.subscription_plans (plan_id)
                    ON UPDATE NO ACTION
                    ON DELETE NO ACTION,
                CONSTRAINT fk_user_pricing FOREIGN KEY (pricing_id)
                    REFERENCES numerojyutishdb.subscription_pricing (pricing_id)
                    ON UPDATE NO ACTION
                    ON DELETE NO ACTION
            )
            """
        )

        # Compatibility migrations for older deployments
        cur.execute("ALTER TABLE numerojyutishdb.user_subscriptions ADD COLUMN IF NOT EXISTS pricing_id BIGINT")
        cur.execute("ALTER TABLE numerojyutishdb.user_subscriptions ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN DEFAULT TRUE")
        cur.execute("ALTER TABLE numerojyutishdb.user_subscriptions ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'ACTIVE'")

        # One-time data backfill for legacy rows created before pricing_id existed.
        # Picks active pricing for matching plan + billing cycle, preferring country_code IN.
        cur.execute(
            """
            WITH candidate_pricing AS (
                SELECT
                    us.subscription_id,
                    spr.pricing_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY us.subscription_id
                        ORDER BY CASE WHEN spr.country_code = 'IN' THEN 0 ELSE 1 END,
                                 spr.pricing_id DESC
                    ) AS rn
                FROM numerojyutishdb.user_subscriptions us
                JOIN numerojyutishdb.subscription_pricing spr
                  ON spr.plan_id = us.plan_id
                 AND spr.billing_cycle_id = us.billing_cycle_id
                 AND spr.is_active = true
                WHERE us.pricing_id IS NULL
            )
            UPDATE numerojyutishdb.user_subscriptions us
               SET pricing_id = cp.pricing_id
              FROM candidate_pricing cp
             WHERE us.subscription_id = cp.subscription_id
               AND cp.rn = 1
               AND us.pricing_id IS NULL
            """
        )

        # Normalize legacy mixed-case status values.
        cur.execute(
            """
            UPDATE numerojyutishdb.user_subscriptions
               SET status = UPPER(status)
             WHERE status IS NOT NULL
               AND status <> UPPER(status)
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS numerojyutishdb.subscription_payments
            (
                subscription_payment_id BIGSERIAL PRIMARY KEY,
                subscription_id BIGINT NOT NULL,
                order_id BIGINT,
                payment_id BIGINT,
                amount NUMERIC(12,2),
                status VARCHAR(30),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_sub_payment FOREIGN KEY (subscription_id)
                    REFERENCES numerojyutishdb.user_subscriptions (subscription_id)
                    ON UPDATE NO ACTION
                    ON DELETE NO ACTION
            )
            """
        )

        conn.commit()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def ensure_enquiry_table():
    """Ensure enquiry table exists for enquiry capture flow."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS numerojyutishdb.enquiry
            (
                enquiry_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                gender VARCHAR(10) CHECK (gender IN ('Male','Female','Other')),
                phone_no VARCHAR(15) NOT NULL,
                email VARCHAR(150),
                date_of_birth DATE,
                birth_time TIME,
                birth_place VARCHAR(150),
                enquiry_type VARCHAR(100),
                description TEXT,
                enquiry_status VARCHAR(20)
                    CHECK (enquiry_status IN ('Pending','In Progress','Completed','Cancelled'))
                    DEFAULT 'Pending',
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def serialize_enquiry_row(row):
    """Convert non-JSON-native values in enquiry row to serializable strings."""
    if not row:
        return row

    serialized = dict(row)
    for key, value in serialized.items():
        if isinstance(value, (datetime, date, time)):
            serialized[key] = value.isoformat()
    return serialized





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


@app.route('/api/enquiries', methods=['POST'])
def create_enquiry():
    """Capture a new enquiry."""
    conn = None
    cur = None
    try:
        ensure_enquiry_table()

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        gender = data.get('gender')
        phone_no = (data.get('phone_no') or '').strip()
        email = (data.get('email') or '').strip() or None
        date_of_birth = data.get('date_of_birth')
        birth_time = data.get('birth_time')
        birth_place = data.get('birth_place')
        enquiry_type = data.get('enquiry_type')
        description = data.get('description')
        enquiry_status = data.get('enquiry_status') or 'Pending'
        comment = data.get('comment')

        if not name or not phone_no:
            return jsonify(success=False, message='name and phone_no are required'), 400

        if not re.fullmatch(r'^[0-9]{10,15}$', phone_no):
            return jsonify(success=False, message='phone_no must contain only digits and be 10 to 15 characters long'), 400

        if email and not re.fullmatch(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return jsonify(success=False, message='Invalid email format'), 400

        if gender and gender not in {'Male', 'Female', 'Other'}:
            return jsonify(success=False, message="gender must be one of Male, Female, Other"), 400

        if enquiry_status not in {'Pending', 'In Progress', 'Completed', 'Cancelled'}:
            return jsonify(success=False, message='Invalid enquiry_status'), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            INSERT INTO numerojyutishdb.enquiry
            (name, gender, phone_no, email, date_of_birth, birth_time, birth_place,
             enquiry_type, description, enquiry_status, comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING enquiry_id, name, gender, phone_no, email, date_of_birth,
                      birth_time, birth_place, enquiry_type, description,
                      enquiry_status, comment, created_at
            """,
            (
                name,
                gender,
                phone_no,
                email,
                date_of_birth,
                birth_time,
                birth_place,
                enquiry_type,
                description,
                enquiry_status,
                comment
            )
        )
        row = cur.fetchone()
        conn.commit()
        return jsonify(success=True, message='Enquiry captured successfully', data=serialize_enquiry_row(row)), 201
    except Exception as e:
        logging.error(f"Error creating enquiry: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error creating enquiry: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/enquiries', methods=['GET'])
def list_enquiries():
    """List enquiries with optional status filter."""
    conn = None
    cur = None
    try:
        ensure_enquiry_table()

        status_filter = request.args.get('enquiry_status')
        phone_filter = request.args.get('phone_no')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT enquiry_id, name, gender, phone_no, email, date_of_birth,
                   birth_time, birth_place, enquiry_type, description,
                   enquiry_status, comment, created_at
            FROM numerojyutishdb.enquiry
        """
        params = []
        filters = []

        if status_filter:
            filters.append("enquiry_status = %s")
            params.append(status_filter)
        if phone_filter:
            filters.append("phone_no = %s")
            params.append(phone_filter)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY enquiry_id DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        return jsonify(success=True, data=[serialize_enquiry_row(row) for row in rows]), 200
    except Exception as e:
        logging.error(f"Error listing enquiries: {e}")
        return jsonify(success=False, message=f'Error listing enquiries: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/enquiries/<int:enquiry_id>', methods=['GET'])
def get_enquiry(enquiry_id):
    """Get enquiry details by enquiry_id."""
    conn = None
    cur = None
    try:
        ensure_enquiry_table()

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT enquiry_id, name, gender, phone_no, email, date_of_birth,
                   birth_time, birth_place, enquiry_type, description,
                   enquiry_status, comment, created_at
            FROM numerojyutishdb.enquiry
            WHERE enquiry_id = %s
            """,
            (enquiry_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify(success=False, message='Enquiry not found'), 404
        return jsonify(success=True, data=serialize_enquiry_row(row)), 200
    except Exception as e:
        logging.error(f"Error fetching enquiry {enquiry_id}: {e}")
        return jsonify(success=False, message=f'Error fetching enquiry: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/enquiries/<int:enquiry_id>', methods=['PUT'])
def update_enquiry(enquiry_id):
    """Update enquiry status/comment and basic enquiry fields."""
    conn = None
    cur = None
    try:
        ensure_enquiry_table()

        data = request.get_json() or {}

        allowed_fields = {
            'name': 'name',
            'gender': 'gender',
            'phone_no': 'phone_no',
            'email': 'email',
            'date_of_birth': 'date_of_birth',
            'birth_time': 'birth_time',
            'birth_place': 'birth_place',
            'enquiry_type': 'enquiry_type',
            'description': 'description',
            'enquiry_status': 'enquiry_status',
            'comment': 'comment'
        }

        if 'gender' in data and data.get('gender') not in {'Male', 'Female', 'Other'}:
            return jsonify(success=False, message="gender must be one of Male, Female, Other"), 400

        if 'enquiry_status' in data and data.get('enquiry_status') not in {'Pending', 'In Progress', 'Completed', 'Cancelled'}:
            return jsonify(success=False, message='Invalid enquiry_status'), 400

        if 'phone_no' in data and data.get('phone_no') is not None:
            phone_no = str(data.get('phone_no')).strip()
            if not re.fullmatch(r'^[0-9]{10,15}$', phone_no):
                return jsonify(success=False, message='phone_no must contain only digits and be 10 to 15 characters long'), 400
            data['phone_no'] = phone_no

        if 'email' in data and data.get('email'):
            email = str(data.get('email')).strip()
            if not re.fullmatch(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
                return jsonify(success=False, message='Invalid email format'), 400
            data['email'] = email

        update_fields = []
        params = []
        for payload_key, db_column in allowed_fields.items():
            if payload_key in data:
                update_fields.append(f"{db_column} = %s")
                params.append(data.get(payload_key))

        if not update_fields:
            return jsonify(success=False, message='No fields to update'), 400

        params.append(enquiry_id)

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            f"""
            UPDATE numerojyutishdb.enquiry
            SET {', '.join(update_fields)}
            WHERE enquiry_id = %s
            RETURNING enquiry_id, name, gender, phone_no, email, date_of_birth,
                      birth_time, birth_place, enquiry_type, description,
                      enquiry_status, comment, created_at
            """,
            params
        )
        row = cur.fetchone()
        if not row:
            return jsonify(success=False, message='Enquiry not found'), 404

        conn.commit()
        return jsonify(success=True, message='Enquiry updated successfully', data=serialize_enquiry_row(row)), 200
    except Exception as e:
        logging.error(f"Error updating enquiry {enquiry_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error updating enquiry: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

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

        # generate token, store in auth source table
        token = secrets.token_urlsafe(32)
        cur.execute("UPDATE numerojyutishdb.security SET authtoken = %s WHERE user_id = %s", (token, user_id))
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


@app.route('/api/users', methods=['GET'])
def list_users():
    """
    List users with optional search and pagination.
    Query params:
    - q: search string (matches full_name, email, phone_no, username)
    - limit: number of results (default 50)
    - offset: pagination offset (default 0)
    """
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]

    if not token:
        return jsonify(success=False, message='Authorization token required'), 401

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify token exists
        cur.execute(
            "SELECT user_id FROM numerojyutishdb.users WHERE authtoken = %s",
            (token,)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Unauthorized'), 403

        search_query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        query = """
            Select user_id, full_name, email, dob, gender, status, created_at, phone, user_role, role_name, role_description, relationship_code, relationship_status_key, professional_code, profession_key, professional_status_code, professional_status_key
            FROM numerojyutishdb.v_user_profile
        """
        params = []

        if search_query:
            query += " WHERE (full_name ILIKE %s OR email ILIKE %s OR phone_no ILIKE %s OR username ILIKE %s)"
            search_param = f"%{search_query}%"
            params.extend([search_param, search_param, search_param, search_param])

        query += " ORDER BY user_id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        count_query = "SELECT COUNT(*) FROM numerojyutishdb.v_user_profile"
        count_params = []
        if search_query:
            count_query += " WHERE (full_name ILIKE %s OR email ILIKE %s OR phone_no ILIKE %s OR username ILIKE %s)"
            count_params.extend([search_param, search_param, search_param, search_param])

        cur.execute(count_query, count_params)
        count_row = cur.fetchone()
        total_count = count_row.get('count', 0) if count_row else 0

        cur.close()
        conn.close()

        users = [
            {
                'user_id': row['user_id'],
                'full_name': row['full_name'],
                'email': row['email'],
                'phone_no': row['phone'],
                'username': row['email'],
                'dob': row['dob'].isoformat() if row['dob'] else None,
                'gender': row['gender'],
                'status': row['status'],
                'user_role': row['user_role'],
                'role_name': row['role_name'],
                'role_description': row['role_description'],
                'relationship_code': row['relationship_code'],
                'relationship_status_key': row['relationship_status_key'],
                'professional_code': row['professional_code'],
                'profession_key': row['profession_key'],
                'professional_status_code': row['professional_status_code'],
                'professional_status_key': row['professional_status_key'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None#,
                #'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            }
            for row in rows
        ]

        return jsonify(
            success=True,
            data=users,
            pagination={
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'count': len(users)
            }
        ), 200

    except Exception as e:
        logging.error(f"Error listing users: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error listing users: {str(e)}'), 500


@app.route('/api/users/<int:user_id>/profile', methods=['GET'])
def get_user_by_user_id(user_id):
    """
    Get a single user by user_id.
    """
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]

    if not token:
        return jsonify(success=False, message='Authorization token required'), 401

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify token exists
        cur.execute(
            "SELECT user_id FROM numerojyutishdb.users WHERE authtoken = %s",
            (token,)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Unauthorized'), 403

        cur.execute(
            """
            SELECT user_id, full_name, email, dob, gender, status, created_at,
                   phone, user_role, role_name, role_description,
                   relationship_code, relationship_status_key,
                   professional_code, profession_key,
                   professional_status_code, professional_status_key
            FROM numerojyutishdb.v_user_profile
            WHERE user_id = %s
            """,
            (user_id,)
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify(success=False, message='User not found'), 404

        user = {
            'user_id': row['user_id'],
            'full_name': row['full_name'],
            'email': row['email'],
            'phone_no': row['phone'],
            'username': row['email'],
            'dob': row['dob'].isoformat() if row['dob'] else None,
            'gender': row['gender'],
            'status': row['status'],
            'user_role': row['user_role'],
            'role_name': row['role_name'],
            'role_description': row['role_description'],
            'relationship_code': row['relationship_code'],
            'relationship_status_key': row['relationship_status_key'],
            'professional_code': row['professional_code'],
            'profession_key': row['profession_key'],
            'professional_status_code': row['professional_status_code'],
            'professional_status_key': row['professional_status_key'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        }

        return jsonify(success=True, data=user), 200

    except Exception as e:
        logging.error(f"Error fetching user {user_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching user: {str(e)}'), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user_admin(user_id):
    """
    Admin update for user email/phone.
    Expected JSON (any subset):
    {
        "email": "user@example.com",
        "phone_no": "9876543210",
        "full_name": "User Name"
    }
    """
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

        # Verify token exists
        cur.execute(
            "SELECT user_id FROM numerojyutishdb.users WHERE authtoken = %s",
            (token,)
        )
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify(success=False, message='Unauthorized'), 403

        email = data.get('email')
        phone_no = data.get('phone_no') or data.get('phoneNo')
        full_name = data.get('full_name')

        update_fields = []
        params = []

        if full_name is not None:
            update_fields.append("full_name = %s")
            params.append(full_name)
        if email is not None:
            update_fields.append("email = %s")
            params.append(email)
        if phone_no is not None:
            update_fields.append("phone_no = %s")
            params.append(phone_no)

        if not update_fields:
            cur.close()
            conn.close()
            return jsonify(success=False, message='No fields to update'), 400

        params.append(user_id)

        query = f"""
            UPDATE numerojyutishdb.users
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING user_id, full_name, email, phone_no, username
        """

        cur.execute(query, params)
        result = cur.fetchone()

        if not result:
            cur.close()
            conn.close()
            return jsonify(success=False, message='User not found'), 404

        # Keep security table in sync if email or phone updated
        if email is not None:
            cur.execute(
                "UPDATE numerojyutishdb.security SET email = %s WHERE user_id = %s",
                (email, user_id)
            )
        if phone_no is not None:
            cur.execute(
                "UPDATE numerojyutishdb.security SET phone = %s WHERE user_id = %s",
                (phone_no, user_id)
            )

        conn.commit()
        cur.close()
        conn.close()

        return jsonify(
            success=True,
            message='User updated successfully',
            data={
                'user_id': result[0],
                'full_name': result[1],
                'email': result[2],
                'phone_no': result[3],
                'username': result[4]
            }
        ), 200

    except psycopg2.IntegrityError as e:
        logging.error(f"Integrity error updating user: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify(success=False, message='Duplicate value or constraint violation'), 409
    except Exception as e:
        logging.error(f"Error updating user {user_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error updating user: {str(e)}'), 500


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


@app.route('/api/subscriptions/checkout', methods=['POST'])
def checkout_subscription():
    """
    Complete subscription checkout and save payment record.
    Expected JSON:
    {
      "user_id": 123,
      "plan_id": 1,
      "billing_cycle_id": 1,
      "country_code": "IN",
      "order_id": 10001,
      "payment_id": 20001,
      "status": "Paid"
    }
    """
    conn = None
    cur = None
    try:
        ensure_subscription_tables()

        data = request.get_json() or {}
        user_id = data.get('user_id')
        plan_id = data.get('plan_id')
        billing_cycle_id = data.get('billing_cycle_id')
        country_code = (data.get('country_code') or 'IN').upper()
        order_id = data.get('order_id')
        payment_id = data.get('payment_id')
        payment_status = (data.get('status') or 'Paid').strip().title()
        is_upgrade = bool(data.get('is_upgrade', False))

        if not user_id or not plan_id or not billing_cycle_id:
            return jsonify(success=False, message='user_id, plan_id and billing_cycle_id are required'), 400

        if payment_status not in {'Pending', 'Paid', 'Failed'}:
            return jsonify(success=False, message='status must be one of Pending, Paid, Failed'), 400

        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else None
        if not token:
            return jsonify(success=False, message='Authorization token required'), 401

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT user_id
            FROM numerojyutishdb.security
            WHERE authtoken = %s AND user_id = %s
            UNION
            SELECT user_id
            FROM numerojyutishdb.users
            WHERE authtoken = %s AND user_id = %s
            """,
            (token, user_id, token, user_id)
        )
        if not cur.fetchone():
            return jsonify(success=False, message='Invalid token for user'), 401

        cur.execute(
            """
            SELECT plan_id
            FROM numerojyutishdb.subscription_plans
            WHERE plan_id = %s AND is_active = true
            """,
            (plan_id,)
        )
        if not cur.fetchone():
            return jsonify(success=False, message='Subscription plan not found or inactive'), 404

        cur.execute(
            """
                        SELECT pricing_id, final_price
            FROM numerojyutishdb.subscription_pricing
            WHERE plan_id = %s
              AND billing_cycle_id = %s
              AND country_code = %s
              AND is_active = true
            LIMIT 1
            """,
            (plan_id, billing_cycle_id, country_code)
        )
        pricing_row = cur.fetchone()
        if not pricing_row:
            return jsonify(success=False, message='No active pricing found for selected plan and cycle'), 404

        amount = float(pricing_row['final_price'] or 0)
        start_date = datetime.utcnow().date()
        duration_days = 365 if int(billing_cycle_id) == 2 else 30
        end_date = start_date + timedelta(days=duration_days)
        subscription_status = 'ACTIVE' if payment_status == 'Paid' else 'PENDING'

        cur.execute(
            """
            SELECT subscription_id, plan_id, billing_cycle_id, start_date, end_date, status
            FROM numerojyutishdb.user_subscriptions
            WHERE user_id = %s
              AND status = 'ACTIVE'
              AND end_date >= CURRENT_DATE
            ORDER BY end_date DESC, subscription_id DESC
            LIMIT 1
            """,
            (user_id,)
        )
        active_subscription = cur.fetchone()

        if active_subscription and not is_upgrade:
            cur.execute(
                """
                SELECT
                    sp.plan_id,
                    sp.plan_name,
                    spr.billing_cycle_id,
                    spr.final_price
                FROM numerojyutishdb.subscription_plans sp
                JOIN numerojyutishdb.subscription_pricing spr
                  ON spr.plan_id = sp.plan_id
                 AND spr.country_code = %s
                 AND spr.is_active = true
                WHERE sp.is_active = true
                  AND NOT (sp.plan_id = %s AND spr.billing_cycle_id = %s)
                ORDER BY sp.plan_id, spr.billing_cycle_id
                """,
                (
                    country_code,
                    active_subscription['plan_id'],
                    active_subscription['billing_cycle_id']
                )
            )
            upgrade_rows = cur.fetchall()
            return jsonify(
                success=False,
                upgrade_required=True,
                message='Active subscription already exists. Use upgrade option to change plan.',
                data={
                    'current_subscription': {
                        'subscription_id': active_subscription['subscription_id'],
                        'plan_id': active_subscription['plan_id'],
                        'billing_cycle_id': active_subscription['billing_cycle_id'],
                        'status': active_subscription['status'],
                        'start_date': active_subscription['start_date'].isoformat() if active_subscription['start_date'] else None,
                        'end_date': active_subscription['end_date'].isoformat() if active_subscription['end_date'] else None
                    },
                    'upgrade_options': [
                        {
                            'plan_id': row['plan_id'],
                            'plan_name': row['plan_name'],
                            'billing_cycle_id': row['billing_cycle_id'],
                            'final_price': float(row['final_price'] or 0)
                        }
                        for row in upgrade_rows
                    ]
                }
            ), 409

        if active_subscription and is_upgrade:
            if payment_status != 'Paid':
                return jsonify(success=False, message='Upgrade requires successful payment status Paid'), 400

            if int(active_subscription['plan_id']) == int(plan_id) and int(active_subscription['billing_cycle_id']) == int(billing_cycle_id):
                return jsonify(success=False, message='You already have this active subscription plan'), 400

            cur.execute(
                """
                UPDATE numerojyutishdb.user_subscriptions
                   SET plan_id = %s,
                       billing_cycle_id = %s,
                       pricing_id = %s,
                       start_date = %s,
                       end_date = %s,
                       status = %s,
                       auto_renew = %s
                 WHERE subscription_id = %s
                RETURNING subscription_id, status, start_date, end_date
                """,
                (
                    plan_id,
                    billing_cycle_id,
                    pricing_row['pricing_id'],
                    start_date,
                    end_date,
                    subscription_status,
                    True,
                    active_subscription['subscription_id']
                )
            )
            subscription_row = cur.fetchone()
        else:
            cur.execute(
                """
                INSERT INTO numerojyutishdb.user_subscriptions
                (user_id, plan_id, billing_cycle_id, pricing_id, start_date, end_date, status, auto_renew)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING subscription_id, status, start_date, end_date
                """,
                (
                    user_id,
                    plan_id,
                    billing_cycle_id,
                    pricing_row['pricing_id'],
                    start_date,
                    end_date,
                    subscription_status,
                    True
                )
            )
            subscription_row = cur.fetchone()

        cur.execute(
            """
            INSERT INTO numerojyutishdb.subscription_payments
            (subscription_id, order_id, payment_id, amount, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING subscription_payment_id, subscription_id, amount, status, created_at
            """,
            (
                subscription_row['subscription_id'],
                order_id,
                payment_id,
                amount,
                payment_status
            )
        )
        payment_row = cur.fetchone()

        conn.commit()
        return jsonify(
            success=True,
            message='Subscription process completed successfully',
            data={
                'subscription_id': subscription_row['subscription_id'],
                'subscription_status': subscription_row['status'],
                'is_upgrade': bool(active_subscription and is_upgrade),
                'start_date': subscription_row['start_date'].isoformat() if subscription_row['start_date'] else None,
                'end_date': subscription_row['end_date'].isoformat() if subscription_row['end_date'] else None,
                'payment': {
                    'subscription_payment_id': payment_row['subscription_payment_id'],
                    'amount': float(payment_row['amount'] or 0),
                    'status': payment_row['status'],
                    'created_at': payment_row['created_at'].isoformat() if payment_row['created_at'] else None
                }
            }
        ), 201
    except Exception as e:
        logging.error(f"Error in subscription checkout: {e}")
        if conn:
            conn.rollback()
        return jsonify(success=False, message=f'Error completing subscription process: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/subscriptions/my', methods=['GET'])
def list_my_subscriptions():
    """Return subscriptions for the authenticated user with latest payment details."""
    conn = None
    cur = None
    try:
        ensure_subscription_tables()

        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify(success=False, message='user_id is required'), 400

        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else None
        if not token:
            return jsonify(success=False, message='Authorization token required'), 401

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT user_id
            FROM numerojyutishdb.security
            WHERE authtoken = %s AND user_id = %s
            UNION
            SELECT user_id
            FROM numerojyutishdb.users
            WHERE authtoken = %s AND user_id = %s
            """,
            (token, user_id, token, user_id)
        )
        if not cur.fetchone():
            return jsonify(success=False, message='Invalid token for user'), 401

        cur.execute(
            """
            SELECT
                us.subscription_id,
                us.user_id,
                us.plan_id,
                us.billing_cycle_id,
                us.pricing_id,
                us.status AS subscription_status,
                us.start_date,
                us.end_date,
                sp.plan_name,
                sp.plan_code,
                latest.subscription_payment_id,
                latest.order_id,
                latest.payment_id,
                latest.amount,
                latest.status AS payment_status,
                latest.created_at AS payment_created_at
            FROM numerojyutishdb.user_subscriptions us
            LEFT JOIN numerojyutishdb.subscription_plans sp
                ON sp.plan_id = us.plan_id
            LEFT JOIN LATERAL (
                SELECT
                    p.subscription_payment_id,
                    p.order_id,
                    p.payment_id,
                    p.amount,
                    p.status,
                    p.created_at
                FROM numerojyutishdb.subscription_payments p
                WHERE p.subscription_id = us.subscription_id
                ORDER BY p.created_at DESC, p.subscription_payment_id DESC
                LIMIT 1
            ) latest ON true
            WHERE us.user_id = %s
            ORDER BY us.subscription_id DESC
            """,
            (user_id,)
        )
        rows = cur.fetchall()

        subscriptions = [
            {
                'subscription_id': row['subscription_id'],
                'user_id': row['user_id'],
                'plan_id': row['plan_id'],
                'plan_name': row['plan_name'],
                'plan_code': row['plan_code'],
                'billing_cycle_id': row['billing_cycle_id'],
                'pricing_id': row['pricing_id'],
                'subscription_status': row['subscription_status'],
                'start_date': row['start_date'].isoformat() if row['start_date'] else None,
                'end_date': row['end_date'].isoformat() if row['end_date'] else None,
                'payment': {
                    'subscription_payment_id': row['subscription_payment_id'],
                    'order_id': row['order_id'],
                    'payment_id': row['payment_id'],
                    'amount': float(row['amount']) if row['amount'] is not None else 0,
                    'status': row['payment_status'],
                    'created_at': row['payment_created_at'].isoformat() if row['payment_created_at'] else None
                }
            }
            for row in rows
        ]

        return jsonify(success=True, data=subscriptions), 200
    except Exception as e:
        logging.error(f"Error fetching user subscriptions: {e}")
        return jsonify(success=False, message=f'Error fetching subscriptions: {str(e)}'), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


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

# Product routes moved to product_routes.py (blueprint)
from product_routes import product_bp
app.register_blueprint(product_bp)

# Inventory routes moved to inventory_routes.py (blueprint)
from inventory_routes import inventory_bp
app.register_blueprint(inventory_bp)

# Order routes moved to order_routes.py (blueprint)
from order_routes import order_bp
app.register_blueprint(order_bp)

# User address management routes
from user_address_routes import user_address_bp
app.register_blueprint(user_address_bp)

# Astrologer consultation routes
from astrologer_routes import astrologer_bp
app.register_blueprint(astrologer_bp)


# Product routes moved to `product_routes.py` blueprint (registered earlier).


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


# Product routes moved to `product_routes.py` (blueprint). See backend/product_routes.py


# Product pricing routes moved to `product_routes.py` (blueprint). See backend/product_routes.py


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


# Product delete routes moved to `product_routes.py` (blueprint). See backend/product_routes.py


# Product image CRUD moved to `product_routes.py` (blueprint). See backend/product_routes.py


if __name__ == '__main__':
    app.run(debug=True)
