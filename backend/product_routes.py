import logging
import logging
import os
from flask import Blueprint, request, jsonify
import psycopg2
from datetime import datetime
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader

product_bp = Blueprint('product_bp', __name__)

# File upload configuration (duplicate of app config where needed)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Minimal local get_db_connection to avoid circular imports
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )


@product_bp.route('/api/product-categories', methods=['GET'])
def get_product_categories():
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


@product_bp.route('/api/products', methods=['GET'])
def get_products():
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


@product_bp.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
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


@product_bp.route('/api/products-with-pricing', methods=['GET'])
def get_products_with_pricing():
    try:
        country_code = request.args.get('country_code', 'IN')
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
        # Note: this endpoint originally combined plans with pricing; kept here for parity
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
            if row[6] is not None:
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


@product_bp.route('/api/product-images/<int:product_id>', methods=['GET'])
def get_product_images(product_id):
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
                'productID': r[1],
                'imageUrl': r[2],
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


@product_bp.route('/api/product-images', methods=['GET'])
def get_all_product_images():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT image_id, product_id, image_url, is_primary, created_at
            FROM numerojyutishdb.product_images
            ORDER BY product_id, is_primary DESC, image_id
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        images = [
            {
                'productID': r[1],
                'imageUrl': r[2],
                'image_id': r[0],
                'is_primary': r[3],
                'created_at': r[4].isoformat() if r[4] else None
            }
            for r in rows
        ]
        return jsonify(success=True, data=images), 200
    except Exception as e:
        logging.error(f"Error fetching all product images: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching product images: {str(e)}'), 500


@product_bp.route('/api/upload-product-image', methods=['POST'])
def upload_product_image():
    try:
        logging.info("📥 [UPLOAD_IMAGE] Request received for image upload (blueprint)")
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        if not token:
            return jsonify(success=False, message='Authorization token required'), 401
        product_id = request.form.get('product_id')
        if not product_id:
            return jsonify(success=False, message='product_id is required'), 400
        if 'file' not in request.files:
            return jsonify(success=False, message='No file provided'), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify(success=False, message='No file selected'), 400
        if not allowed_file(file.filename):
            return jsonify(success=False, message='File type not allowed'), 400
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE:
            return jsonify(success=False, message='File size exceeds maximum (5MB)'), 400
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"numerojyutish/products/{product_id}",
            resource_type="auto",
            overwrite=False
        )
        image_url = upload_result.get('secure_url')
        public_id = upload_result.get('public_id')
        logging.info(f"✅ [UPLOAD_IMAGE] Image uploaded successfully (bp) {public_id}")
        return jsonify(success=True, data={'image_url': image_url, 'public_id': public_id, 'filename': file.filename}, message='Image uploaded successfully'), 201
    except Exception as e:
        logging.error(f"❌ [UPLOAD_IMAGE] Error (bp): {e}")
        return jsonify(success=False, message=f'Error uploading image: {str(e)}'), 500


# ---------- Create / Update endpoints for products and pricing ----------
@product_bp.route('/api/product-categories', methods=['POST'])
def create_product_category():
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


@product_bp.route('/api/product-categories/<int:category_id>', methods=['PUT'])
def update_product_category(category_id):
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


@product_bp.route('/api/products', methods=['POST'])
def create_product():
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


@product_bp.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
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


@product_bp.route('/api/product-pricing', methods=['GET'])
def get_product_pricing():
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


@product_bp.route('/api/product-pricing', methods=['POST'])
def create_product_pricing():
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


@product_bp.route('/api/product-pricing/<int:pricing_id>', methods=['PUT'])
def update_product_pricing(pricing_id):
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


@product_bp.route('/api/product-pricing/<int:pricing_id>', methods=['GET'])
def get_single_product_pricing(pricing_id):
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


@product_bp.route('/api/product-pricing/<int:pricing_id>', methods=['DELETE'])
def delete_product_pricing(pricing_id):
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


@product_bp.route('/api/product-details', methods=['GET'])
def get_product_details():
    try:
        logging.info("📦 [GET_PRODUCT_DETAILS] Fetching product details with images")
        
        country_code = request.args.get('country_code')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Fetch product details
        if country_code:
            cur.execute(
                """
                SELECT product_id, product_name, product_description, category_name, category_description, 
                       pricing_id, country_code, state_code, currency_code, base_price, discount_percent, 
                       is_tax_inclusive, tax_id, tax_name, tax_percent, product_active, pricing_active,quantity_available
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
                       is_tax_inclusive, tax_id, tax_name, tax_percent, product_active, pricing_active,quantity_available
                FROM numerojyutishdb.product_details
                """
            )
        
        rows = cur.fetchall()
        
        # Fetch all product images with new format
        logging.info("📷 [GET_PRODUCT_DETAILS] Fetching product images")
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
        
        # Group images by product_id with new format: {productID, imageUrl}
        logging.info(f"📊 [GET_PRODUCT_DETAILS] Processing {len(image_rows)} images")
        images_by_product = {}
        for img_row in image_rows:
            product_id = img_row[0]
            if product_id not in images_by_product:
                images_by_product[product_id] = []
            
            images_by_product[product_id].append({
                'productID': product_id,
                'imageUrl': img_row[2],
                'image_id': img_row[1],
                'is_primary': img_row[3],
                'created_at': img_row[4].isoformat() if img_row[4] else None
            })
        
        # Build products with images
        products = []
        for r in rows:
            product_id = r[0]
            product = {
                'product_id': product_id,
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
                'pricing_active': r[16],
                'quantity_available': r[17] if len(r) > 17 else None,
                'images': images_by_product.get(product_id, []),
                
            }
            products.append(product)
        
        logging.info(f"✅ [GET_PRODUCT_DETAILS] Retrieved {len(products)} products with {len(image_rows)} total images")
        
        for pid, imgs in images_by_product.items():
            logging.info(f"   Product {pid}: {len(imgs)} image(s)")
        
        return jsonify(success=True, data=products), 200
        
    except Exception as e:
        logging.error(f"❌ [GET_PRODUCT_DETAILS] Error fetching product details: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching product details: {str(e)}'), 500


@product_bp.route('/api/product-details/<int:product_id>', methods=['GET'])
def get_product_details_by_id(product_id):
    try:
        logging.info(f"📦 [GET_PRODUCT_DETAILS_BY_ID] Fetching product details for product_id={product_id}")

        country_code = request.args.get('country_code')

        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch single product detail
        if country_code:
            cur.execute(
                """
                SELECT product_id, product_name, product_description, category_name, category_description,
                       pricing_id, country_code, state_code, currency_code, base_price, discount_percent,
                       is_tax_inclusive, tax_id, tax_name, tax_percent, product_active, pricing_active, quantity_available
                FROM numerojyutishdb.product_details
                WHERE product_id = %s AND country_code = %s
                """,
                (product_id, country_code)
            )
        else:
            cur.execute(
                """
                SELECT product_id, product_name, product_description, category_name, category_description,
                       pricing_id, country_code, state_code, currency_code, base_price, discount_percent,
                       is_tax_inclusive, tax_id, tax_name, tax_percent, product_active, pricing_active, quantity_available
                FROM numerojyutishdb.product_details
                WHERE product_id = %s
                """,
                (product_id,)
            )

        rows = cur.fetchall()
        if not rows:
            cur.close()
            conn.close()
            return jsonify(success=False, message='Product details not found'), 404

        # Fetch product images
        cur.execute(
            """
            SELECT product_id, image_id, image_url, is_primary, created_at
            FROM numerojyutishdb.product_images
            WHERE product_id = %s
            ORDER BY is_primary DESC, image_id
            """,
            (product_id,)
        )

        image_rows = cur.fetchall()
        cur.close()
        conn.close()

        images = [
            {
                'productID': img_row[0],
                'imageUrl': img_row[2],
                'image_id': img_row[1],
                'is_primary': img_row[3],
                'created_at': img_row[4].isoformat() if img_row[4] else None
            }
            for img_row in image_rows
        ]

        # If multiple country rows exist, return as list preserving current data model
        product_details = []
        for r in rows:
            product_details.append({
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
                'pricing_active': r[16],
                'quantity_available': r[17] if len(r) > 17 else None,
                'images': images
            })

        logging.info(f"✅ [GET_PRODUCT_DETAILS_BY_ID] Retrieved {len(product_details)} row(s) for product_id={product_id}")

        return jsonify(success=True, data=product_details), 200

    except Exception as e:
        logging.error(f"❌ [GET_PRODUCT_DETAILS_BY_ID] Error fetching product details for product_id={product_id}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(success=False, message=f'Error fetching product details: {str(e)}'), 500


# --- Additional product routes moved from app.py: delete product/category and image DB CRUD ---


@product_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
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


@product_bp.route('/api/product-categories/<int:category_id>', methods=['DELETE'])
def delete_product_category(category_id):
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


@product_bp.route('/api/product-images', methods=['POST'])
def create_product_image():
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


@product_bp.route('/api/product-images/<int:image_id>', methods=['GET'])
def get_single_product_image(image_id):
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


@product_bp.route('/api/product-images/<int:image_id>', methods=['PUT'])
def update_product_image(image_id):
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


@product_bp.route('/api/product-images/<int:image_id>', methods=['DELETE'])
def delete_product_image(image_id):
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

