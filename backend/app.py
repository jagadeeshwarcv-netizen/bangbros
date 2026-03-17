from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client
import os
import requests
from dotenv import load_dotenv
import bcrypt
import json

load_dotenv()

app = Flask(__name__, 
            template_folder='../frontend', 
            static_folder='../frontend')

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://bangbro-s.vercel.app")

app.secret_key = os.getenv("SECRET_KEY", "bangbros-secret-key-change-in-prod")

CORS(app, 
     resources={r"/*": {"origins": [
         "http://localhost:8000", 
         "http://127.0.0.1:8000", 
         "https://bangbro-s.vercel.app"
     ]}},
     supports_credentials=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

GOOGLE_SCRIPT_ID = os.getenv("GOOGLE_SCRIPT_URL")
if GOOGLE_SCRIPT_ID and not GOOGLE_SCRIPT_ID.startswith("http"):
    GOOGLE_SCRIPT_URL = f"https://script.google.com/macros/s/{GOOGLE_SCRIPT_ID}/exec"
else:
    GOOGLE_SCRIPT_URL = GOOGLE_SCRIPT_ID or ""

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route('/')
def home():
    applicants_name = [
        "C.V Jagadeeshwar", 
        "J.Santhosh", 
        "Vanam Gangadhar Reddy", 
        "KONDAMANENI DHANUSH KUMAR NAIDU"
    ]
    return render_template('submitbooking.html', applicants=applicants_name)


@app.route('/submitbooking', methods=['POST'])
def submit_booking():
    try:
        company = request.form.get('company')
        applicant_name = request.form.get('applicant_name')
        gmail = request.form.get('gmail')
        meeting_type = request.form.get('meeting_type')
        meeting_time = request.form.get('meeting_time')
        link = request.form.get('link')
        notes = request.form.get('notes')
        
        form_data = {
            "company_name": company,
            "applicant_name": applicant_name,
            "gmail": gmail,
            "meeting_type": meeting_type,
            "start_time": meeting_time,
            "meeting_link": link,
            "notes": notes
        }
        
        print(f"Inserting data: {form_data}")
        result = supabase.table("recruiter_bookings").insert(form_data).execute()
        print("✓ Data saved to Supabase successfully")
        
        if GOOGLE_SCRIPT_URL:
            try:
                google_sheet_data = {
                    "company": company,
                    "applicant_name": applicant_name,
                    "applicants": gmail,
                    "meeting_type": meeting_type,
                    "meeting_time": meeting_time,
                    "link": link,
                    "notes": notes
                }
                response = requests.post(GOOGLE_SCRIPT_URL, json=google_sheet_data, timeout=10)
                print(f"Google Sheets sync status: {response.status_code}")
            except Exception as google_error:
                print(f"⚠ Google Sheets sync failed: {str(google_error)}")
        
        return jsonify({"success": True, "message": f"Meeting for {applicant_name} saved."}), 200
        
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Error: {error_msg}")
        return jsonify({"success": False, "message": error_msg}), 400


@app.route('/signup', methods=['POST'])
def signup():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password or not name:
            return redirect(f'{FRONTEND_URL}/signup.html?error=Name,+email+and+password+are+required')
        
        try:
            existing_user = supabase.table("users").select("*").eq("email", email).execute()
            if existing_user.data:
                return redirect(f'{FRONTEND_URL}/signup.html?error=User+with+this+email+already+exists')
        except Exception as check_error:
            print(f"⚠ Error checking existing user: {str(check_error)}")
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user_data = {
            "email": email,
            "password_hash": password_hash
        }
        
        result = supabase.table("users").insert(user_data).execute()
        print(f"✓ User {email} registered successfully")
        
        return redirect(f'{FRONTEND_URL}/login.html?success=Account+created!+Please+login.')
        
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Signup Error: {error_msg}")
        return redirect(f'{FRONTEND_URL}/signup.html?error={error_msg}')


@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return redirect(f'{FRONTEND_URL}/login.html?error=Email+and+password+are+required')
        
        result = supabase.table("users").select("*").eq("email", email).execute()
        
        if not result.data:
            return redirect(f'{FRONTEND_URL}/login.html?error=Invalid+email+or+password')
        
        user = result.data[0]
        stored_hash = user['password_hash']
        
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            email_name = email.split('@')[0].replace('.', ' ').title()
            user_name = email_name
            
            name_parts = user_name.strip().split()
            initials = ''.join([part[0].upper() for part in name_parts[:2]]) if name_parts else 'U'
            avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={initials}"
            
            session['user_id'] = user.get('id')
            session['user_email'] = user.get('email')
            session['user_name'] = user_name
            session['user_avatar'] = avatar_url
            
            print(f"✓ User {email} logged in successfully")
            return redirect(f'{FRONTEND_URL}/')
        else:
            print(f"✗ Failed login attempt for {email}")
            return redirect(f'{FRONTEND_URL}/login.html?error=Invalid+email+or+password')
            
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Login Error: {error_msg}")
        return redirect(f'{FRONTEND_URL}/login.html?error=Login+failed')


@app.route('/api/user', methods=['GET'])
def get_user():
    if 'user_id' in session:
        user_name = session.get('user_name', 'User')
        name_parts = user_name.strip().split()
        initials = ''.join([part[0].upper() for part in name_parts[:2]]) if name_parts else 'U'
        avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={initials}"
        
        return jsonify({
            "user": {
                "id": session.get('user_id'),
                "name": user_name,
                "email": session.get('user_email'),
                "avatar_url": avatar_url
            }
        }), 200
    return jsonify({"user": None}), 401


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    print("✓ User logged out")
    return redirect(f'{FRONTEND_URL}/')


if __name__ == '__main__':
    app.run(debug=True,port=5000,host='0.0.0.0')
