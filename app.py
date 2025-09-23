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
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.duybmkpkytephxnhpdbk:mq4nNpX8TtSdzgzz@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
)


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
@app.route("/get_ccis", methods=["POST"])
def get_ccis():
    district = request.json["district"]
    conn = db_connect()
    c = conn.cursor()
    c.execute(
        "SELECT cci_id, cci_name, category, gender FROM cci WHERE district = %s ORDER BY cci_name;",
        (district,),
    )
    rows = c.fetchall()
    ccis = [(row[0], row[1] + " (" + row[2] + ": " + row[3] + ")") for row in rows]
    conn.close()
    # print(ccis)
    return jsonify(ccis)


# Home route
@app.route("/")
def home():
    districts = get_districts()
    return render_template("index.html", districts=districts)


# Form submission route
@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    # Get form data
    cci_id = data["cci"]
    child_name = data["child-name"]
    dob = data["dob"]
    gender = data["gender"]
    category = data["category"]
    cwc_name = data["authority-name"]
    release_date = data["release-dt"] if data["release-dt"] else None
    is_sir_done = data["is-sir-done"]
    is_aftercare_trained = data["is-aftercare-trained"]
    aftercare_training = data["aftercare-details"]
    phone_no = data["phone-number"]
    email = data["email"]
    present_addr = data["present-addr"]
    family_bg = data["family-bg"]
    support_req = data["support-req"]
    highest_edu = data["highest-education"]
    has_laptop = data["has-laptop"]
    has_birth_cert = data["has-birth-cert"]
    has_caste_cert = data["has-caste-cert"]
    has_release_order = data["has-release-order"]
    has_aadhaar = data["has-aadhaar"]
    has_pan = data["has-pan"]
    has_voter = data["has-voter"]
    has_bank_acc = data["has-bank-acc"]
    has_aayushman = data["has-aayushman"]
    has_disability_cert = data["has-disability-cert"]

    # Save to database
    conn = db_connect()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO public.careleavers (cci_id, child_name, dob, gender, category, cwc_name, release_dt, is_sir_done, is_aftercare_trained, aftercare_training, phone_no, email, present_addr, "family", support_needs, highest_edu, having_computer, having_birth_cert, having_caste_cert, having_release_ord, having_aadhaar, having_pan, having_voter_id, having_bank_acc, having_aayushman, having_disability_cert)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
            (
                cci_id,
                child_name,
                dob,
                gender,
                category,
                cwc_name,
                release_date,
                is_sir_done,
                is_aftercare_trained,
                aftercare_training,
                phone_no,
                email,
                present_addr,
                family_bg,
                support_req,
                highest_edu,
                has_laptop,
                has_birth_cert,
                has_caste_cert,
                has_release_order,
                has_aadhaar,
                has_pan,
                has_voter,
                has_bank_acc,
                has_aayushman,
                has_disability_cert
            ),
        )
        conn.commit()
        return jsonify({"status": True, "message": "Data saved successfully!"})
    except Exception as e:
        conn.rollback()
        print(e)
        return jsonify({"status": False, "message": "Error saving data: " + str(e)})
    finally:
        conn.close()


# Route to fetch all data from database
@app.route("/view", methods=["POST"])
def view():
    try:
        # Manually parse the request data
        data = request.get_json(force=True)

        if not data:
            return jsonify({"error": "No data provided"}), 400

        district = data.get("district")
        cci = data.get("cci")

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
            careleavers.email,
            careleavers.present_addr,
            careleavers."family",
            careleavers.support_needs,
            careleavers.highest_edu,
            careleavers.having_computer,
            careleavers.having_birth_cert,
            careleavers.having_caste_cert,
            careleavers.having_release_ord,
            careleavers.having_aadhaar,
            careleavers.having_pan,
            careleavers.having_voter_id,
            careleavers.having_bank_acc,
            careleavers.having_aayushman,
            careleavers.having_disability_cert
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
            data.append(
                {
                    "sl_no": row[0],
                    "district": row[1],
                    "cci": row[2],
                    "child_name": row[4],
                    "gender": row[5],
                    "age": calculate_age(row[6]) if row[6] else None,
                    "category": row[7],
                    "cwc_name": row[8],
                    "release_dt": row[9].strftime('%d-%m-%Y') if row[9] else None,
                    "is_sir_done": row[10],
                    "is_aftercare_trained": row[11],
                    "aftercare_training": row[12],
                    "phone_no": row[13],
                    "email": row[14],
                    "present_addr": row[15],
                    "family_bg": row[16],
                    "support_needs": row[17],
                    "highest_edu": row[18],
                    "has_laptop": row[19],
                    "has_birth_cert": row[20],
                    "has_caste_cert": row[21],
                    "has_release_order": row[22],
                    "has_aadhaar": row[23],
                    "has_pan": row[24],
                    "has_voter": row[25],
                    "has_bank_acc": row[26],
                    "has_aayushman": row[27],
                    "has_disability_cert": row[28]
                }
            )
        return jsonify(data)
    except Exception as e:
        print(e)
        return jsonify({"error": "Invalid JSON data"}), 400


# Helper function to calculate age in years and months
def calculate_age(born):
    today = datetime.today()
    age_years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    age_months = today.month - born.month - (today.day < born.day)
    if age_months < 0:
        age_months += 12
    return f"{age_years} years, {age_months} months"

# Route to download the database file
# @app.route('/download-db')
# def download_db():
#     return send_file(DATABASE, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
