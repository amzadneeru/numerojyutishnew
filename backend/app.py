import logging
import os
from pathlib import Path
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import psycopg2
import secrets
from werkzeug.security import check_password_hash
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
    username = data.get('username')
    password = data.get('password')
    mpin = data.get('mpin')
    dob = data.get('dob')
    gender = data.get('gender')
    #authtoken = data.get('authtoken')
    user_role = data.get('user_role')

    # Basic validations
    if not full_name or not email or not phone or not username or not password or not mpin or not dob or not gender:
        return jsonify(success=False, message='full_name, email, phoneNo, username, password, dob, gender, and mpin are required'), 400
        
    # Validate gender
    if gender not in ['male', 'female', 'other']:
        return jsonify(success=False, message='Invalid gender value'), 400

    if user_role not in ALLOWED_ROLES:
        return jsonify(success=False, message='Invalid user_role'), 400

    # validate mpin is 6 digits
    if not isinstance(mpin, str) or not mpin.isdigit() or len(mpin) != 6:
        return jsonify(success=False, message='mpin must be a 6 digit string'), 400

    password_hash = generate_password_hash(password)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
      
        logging.info(f"database connection established")
        cur.execute(
            """
            INSERT INTO numerojyutishdb.users
                (full_name, email, phoneNo, username, password_hash, mpin, authtoken, dob, gender)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING user_id
            """,
            (full_name, email, phone, username, password_hash, mpin, None, dob, gender)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Created user {email} with id {user_id}")
        return jsonify(success=True, message='User created', user_id=user_id), 201
    except psycopg2.IntegrityError as e:
        # likely duplicate on unique constraint: email, phoneNo or username
        logging.error(f"Integrity error creating user: {e}")
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
        logging.error(f"Error creating user: {e}")
        return jsonify(success=False, message=f'Error creating user: {str(e)}'), 500


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


if __name__ == '__main__':
    app.run(debug=True)
