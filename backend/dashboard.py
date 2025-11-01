class Dashboard:
    def __init__(self, email, conn):
        self.email = email
        self.conn = conn

    def member_type(self):
        member_data = {
            'customer_id': None,
            'total_sum': 0,
            'first_name': '',
            'last_name': ''
        }
        if not self.conn:
            raise Exception("Database connection failed.")

        stmt = '''
            SELECT customer_id, SUM(total_price::numeric) AS total_sum, cust.first_name, cust.last_name
            FROM shopify.orders ord
            INNER JOIN shopify.customers cust ON ord.customer_id = cust.id
            WHERE ord.email = %s
            GROUP BY ord.customer_id, cust.first_name, cust.last_name
        '''
        with self.conn.cursor() as cur:
            cur.execute(stmt, (self.email,))
            row = cur.fetchone()
            if row:
                member_data.update({
                    'customer_id': row[0],
                    'total_sum': float(row[1]) if row[1] else 0,
                    'first_name': row[2],
                    'last_name': row[3]
                })
        return member_data

    def dashboard_data(self):
        data = []
        stmt = '''
            SELECT 
  customer_first_name, 
  customer_last_name, 
  total_price, 
  total_discounts,
  order_status, 
  fulfillment_status,
  financial_status, 
  cancel_reason
            FROM shopify.orders
            WHERE email = %s
        '''
        with self.conn.cursor() as cur:
            cur.execute(stmt, (self.email,))
            data = [list(row) for row in cur.fetchall()]
        return data

    def generate_pie_chart(self):
        months = {i: 0 for i in range(1, 13)}
        stmt = '''
            SELECT EXTRACT(MONTH FROM created_at::timestamp) AS month_number,
                   SUM(total_price::numeric) AS total_price
            FROM shopify.orders
            WHERE email = %s
            GROUP BY month_number
            ORDER BY month_number
        '''
        with self.conn.cursor() as cur:
            cur.execute(stmt, (self.email,))
            for row in cur.fetchall():
                month_index = int(row[0])
                months[month_index] = float(row[1]) if row[1] else 0

        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        values = [months[i + 1] for i in range(12)]
        return labels, values
