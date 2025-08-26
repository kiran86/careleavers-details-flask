from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from datetime import datetime
import sqlite3
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Set data directory, for production
# DATA_DIR = '/data'
# DATABASE = os.path.join(DATA_DIR, 'data.db')

# Set database path for flask, for local development
# DATABASE = os.path.join('data', 'data.db')

# Supabase connection
DATABASE_URL = os.getenv('DATABASE_URL','postgresql://postgres.duybmkpkytephxnhpdbk:b113hsDbVCgBAXYK@aws-1-ap-south-1.pooler.supabase.com:6543/postgres')
# Connect to the database
def db_connect():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Get a list of districts
def get_districts():
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT DISTINCT district FROM cci ORDER BY district;")
    rows = c.fetchall()
    districts = [row[0] for row in rows]
    conn.close()
    # print(districts)
    return districts

# AJAX route to fetch a list of ccis based on district
@app.route('/get_ccis', methods=['POST'])
def get_ccis():
    district = request.json['district']
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT cci_id, cci_name, category, gender FROM cci WHERE district = %s ORDER BY cci_name;", (district,))
    rows = c.fetchall()
    ccis = [(row[0], row[1] + " (" + row[2] + ": " + row[3] + ")") for row in rows]
    conn.close()
    # print(ccis)
    return jsonify(ccis)

# Home route
@app.route('/')
def home():
    districts = get_districts()
    return render_template('index.html', districts=districts)

# Form submission route
@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    # Get form data
    cci = data['cci']
    child_name = data['child-name']
    age = data['age']
    gender = data['gender']
    category = data['category']
    admission_date = data['admission-dt'] if data['admission-dt'] else None
    order_by = data['placed-by']
    cwc_jjb_name = data['authority-name']
    placement_order_no = data['placement-order-no']
    placement_order_dt = data['placement-order-dt'] if data['placement-order-dt'] else None
    sir_order_no = data['sir-order-no']
    sir_order_date = data['sir-order-dt'] if data['sir-order-dt'] else None
    sir_due_date = data['sir-due-dt'] if data['sir-due-dt'] else None
    sir_status = data['sir-status']

    # Save to database
    conn = db_connect()
    c = conn.cursor()
    c.execute('''INSERT INTO sir_pending
              (cci_id, child_name, age, gender, category, 
              admission_dt, order_by, cwc_jjb_name, placement_odr, placement_dt, 
              sir_odr, sir_ord_dt, sir_due_dt, sir_status)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);''', 
              (cci, child_name, age, gender, category,
               admission_date, order_by, cwc_jjb_name, placement_order_no, placement_order_dt,
               sir_order_no, sir_order_date, sir_due_date, sir_status))
    conn.commit()
    conn.close()

    return jsonify({
        'status': True,
        'message': 'Data saved successfully!'
    })

# Route to fetch all data from database
@app.route('/view', methods=['POST'])
def view():
    try:
        # Manually parse the request data
        data = request.get_json(force=True)

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        district = data.get('district')
        cci = data.get('cci')

        # Build the SQL query dynamically
        sql = """
        SELECT 
            ROW_NUMBER() OVER(ORDER BY sir_pending.cci_id), 
            cci.district, 
            cci.cci_name || ' (' || cci.category || ' : ' || cci.gender || ')', 
            sir_pending.* 
        FROM sir_pending 
        JOIN cci ON sir_pending.cci_id = cci.cci_id 
        WHERE 1=1
        """
        params = []
        if district:
            sql += " AND cci.district = %s"
            params.append(district)
        if cci:
            sql += " AND sir_pending.cci_id = %s"
            params.append(cci)

        conn = db_connect()
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()
        # print(rows)
        data = []
        for row in rows:
            data.append({
                'sl_no': row[0],
                'district': row[1],
                'cci': row[2],
                'child_name': row[4],
                'age': row[5],
                'gender': row[6],
                'category': row[7],
                'admission_dt': row[8].strftime('%d-%m-%Y'),
                'order_by': row[9] + ' ' + row[10],
                'order_no': row[11],
                'order_dt': row[12].strftime('%d-%m-%Y'),
                'sir_order_no': row[13] if row[13] else '',
                'sir_order_dt': row[14].strftime('%d-%m-%Y') if row[14] else '',
                'sir_due_dt': row[15].strftime('%d-%m-%Y') if row[15] else '',
                'sir_status': row[16]
            })
        return jsonify(data)
    except Exception as e:
        print(e)
        return jsonify({'error': 'Invalid JSON data'}), 400

# Route to download the database file
# @app.route('/download-db')
# def download_db():
#     return send_file(DATABASE, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)