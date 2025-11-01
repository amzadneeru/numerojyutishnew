import logging
import os
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import secrets
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Minimal app: only user registration (create-user) functionality
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

load_dotenv(dotenv_path=Path(__file__).resolve().parent / 'data.env')

app = Flask(__name__)
# Allow CORS for the frontend dev server during development
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}})


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
        cur.execute("SELECT user_id, email, username, password_hash FROM numerojyutishdb.users WHERE username = %s OR email = %s", (username, username))
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

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    full_name = data.get('full_name')
    email = data.get('email')
    phone = data.get('phoneNo')
    username = data.get('username')
    password = data.get('password')
    mpin = data.get('mpin')
    #authtoken = data.get('authtoken')
    user_role = data.get('user_role')

    # Basic validations
    if not full_name or not email or not phone or not username or not password or not mpin:
        return jsonify(success=False, message='full_name, email, phoneNo, username, password  are required'), 400

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
                (full_name, email, phoneNo, username, password_hash, mpin, authtoken)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING user_id
            """,
            (full_name, email, phone, username, password_hash, mpin, None)
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


if __name__ == '__main__':
    app.run(debug=True)
