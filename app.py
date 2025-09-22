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
DATABASE_URL = os.getenv('DATABASE_URL','postgresql://postgres.duybmkpkytephxnhpdbk:mq4nNpX8TtSdzgzz@aws-1-ap-south-1.pooler.supabase.com:6543/postgres')
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
    cci_id = data['cci']
    child_name = data['child-name']
    dob = data['dob']
    gender = data['gender']
    category = data['category']
    cwc_name = data['authority-name']
    release_date = data['release-dt'] if data['release-dt'] else None
    is_sir_done = data['is-sir-done']
    is_aftercare_trained = data['is-aftercare-trained']
    aftercare_training = data['aftercare-details']
    phone_no = data['phone-number']
    address = data['address']

    # Save to database
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO careleavers
                (cci_id, child_name, dob, gender, category, 
                cwc_name, release_dt, is_sir_done, is_aftercare_trained, aftercare_training, 
                phone_no, address)
                VALUES (%s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, 
                %s, %s);''', 
                (cci_id, child_name, dob, gender, category,
                cwc_name, release_date, is_sir_done, is_aftercare_trained, aftercare_training,
                phone_no, address))
        conn.commit()
        return jsonify({
            'status': True,
            'message': 'Data saved successfully!'
        })
    except Exception as e:
        conn.rollback()
        print(e)
        return jsonify({
            'status': False,
            'message': 'Error saving data: ' + str(e)
        })
    finally:
        conn.close()

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
            ROW_NUMBER() OVER(ORDER BY careleavers.cci_id), 
            cci.district, 
            cci.cci_name || ' (' || cci.category || ' : ' || cci.gender || ')', 
            careleavers.cci_id,
            careleavers.child_name, 
            careleavers.gender, 
            careleavers.dob, 
            careleavers.category, 
            careleavers.cwc_name, 
            careleavers.release_dt, 
            careleavers.is_sir_done, 
            careleavers.is_aftercare_trained, 
            careleavers.aftercare_training, 
            careleavers.phone_no, 
            careleavers.address 
        FROM careleavers 
        JOIN cci ON careleavers.cci_id = cci.cci_id 
        WHERE 1=1
        """
        params = []
        if district:
            sql += " AND cci.district = %s"
            params.append(district)
        if cci:
            sql += " AND careleavers.cci_id = %s"
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
                'gender': row[5],
                'dob': row[6].strftime('%d-%m-%Y'),
                'category': row[7],
                'cwc_name': row[8],
                'release_dt': row[9].strftime('%d-%m-%Y') if row[9] else '',
                'is_sir_done': "Yes" if row[10] else "No",
                'is_aftercare_trained': "Yes" if row[11] else "No",
                'aftercare_training': row[12] if row[12] else '',
                'phone_no': row[13],
                'address': row[14]
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