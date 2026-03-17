from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client
import os
import requests
from dotenv import load_dotenv
import bcrypt
import json

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, 
            template_folder='../frontend', 
            static_folder='../frontend')

# Determine environments
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000","https://bangbro-s.vercel.app")    
    
# Enable CORS for frontend
CORS(app, 
     resources={r"/*": {"origins": ["http://localhost:8000", "http://127.0.0.1:8000", "https://bangbro-s.vercel.app"]}},
     supports_credentials=True)

# Supabase Credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Google Apps Script URL for Google Sheets
GOOGLE_SCRIPT_ID = os.getenv("GOOGLE_SCRIPT_URL")
if GOOGLE_SCRIPT_ID and not GOOGLE_SCRIPT_ID.startswith("http"):
    GOOGLE_SCRIPT_URL = f"https://script.google.com/macros/s/{GOOGLE_SCRIPT_ID}/exec"
else:
    GOOGLE_SCRIPT_URL = GOOGLE_SCRIPT_ID or "YOUR_GOOGLE_WEB_APP_URL_HERE"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def home():
    # List of applicants
    applicants_name= [
        "C.V Jagadeeshwar", 
        "J.Santhosh", 
        "Vanam Gangadhar Reddy", 
        "KONDAMANENI DHANUSH KUMAR NAIDU"
    ]
    return render_template('submitbooking.html', applicants=applicants_name)

@app.route('/submitbooking', methods=['POST'])
def submit_booking():
    try:
        # Get form data
        company = request.form.get('company')
        applicant_name = request.form.get('applicant_name')
        gmail = request.form.get('gmail')
        meeting_type = request.form.get('meeting_type')
        meeting_time = request.form.get('meeting_time')
        link = request.form.get('link')
        notes = request.form.get('notes')
        
        # Prepare data for Supabase - using the correct column names
        form_data = {
            "company_name": company,
            "applicant_name": applicant_name,
            "gmail": gmail,
            "meeting_type": meeting_type,
            "start_time": meeting_time,
            "meeting_link": link,
            "notes": notes
        }
        
        # Debug: Print what we're sending
        print(f"Inserting data: {form_data}")
        
        # Insert into Supabase
        result = supabase.table("recruiter_bookings").insert(form_data).execute()
        print("✓ Data saved to Supabase successfully")
        
        # Send to Google Sheets via Apps Script (if URL is configured)
        if GOOGLE_SCRIPT_URL and GOOGLE_SCRIPT_URL != "YOUR_GOOGLE_WEB_APP_URL_HERE":
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
                
                # The Apps script uses JSON.parse(e.postData.contents), so we must send JSON
                response = requests.post(GOOGLE_SCRIPT_URL, json=google_sheet_data, timeout=10)
                
                print(f"Data sent to Google Sheets. Status Code: {response.status_code}")
            except Exception as google_error:
                print(f"⚠ Google Sheets sync failed: {str(google_error)}")
        
        return f"<h1>Success!</h1><p>Meeting for {applicant_name}  saved.</p><a href='{FRONTEND_URL}/'>Go Back</a>"
        
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Error: {error_msg}")
        return f"<h1>Error</h1><p>{error_msg}</p><a href='{FRONTEND_URL}/'>Go Back</a>", 400


@app.route('/signup', methods=['POST'])
def signup():
    """User signup endpoint - stores user credentials in database"""
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate input
        if not email or not password or not name:
            return f"<h1>Error</h1><p>Name, email and password are required.</p><a href='{FRONTEND_URL}/signup.html'>Go Back</a>", 400
        
        # Check if user already exists
        try:
            existing_user = supabase.table("users").select("*").eq("email", email).execute()
            if existing_user.data:
                return f"<h1>Error</h1><p>User with this email already exists.</p><a href='{FRONTEND_URL}/signup.html'>Go Back</a>", 400
        except Exception as check_error:
            print(f"⚠ Error checking existing user: {str(check_error)}")
        
        # Hash the password using bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Prepare user data - only email and password_hash (as per database schema)
        user_data = {
            "email": email,
            "password_hash": password_hash
        }
        
        # Insert into Supabase users table
        result = supabase.table("users").insert(user_data).execute()
        print(f"✓ User {email} registered successfully")
        
        # Store name in session for later use (avatar generation)
        session['signup_name'] = name
        
        return f"<h1>Success!</h1><p>Account created successfully! You can now <a href='{FRONTEND_URL}/login.html'>login</a>.</p>", 200
        
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Signup Error: {error_msg}")
        return f"<h1>Error</h1><p>Signup failed: {error_msg}</p><a href='{FRONTEND_URL}/signup.html'>Go Back</a>", 400


@app.route('/login', methods=['POST'])
def login():
    """User login endpoint - authenticates user credentials and stores in session"""
    try:
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate input
        if not email or not password:
            return f"<h1>Error</h1><p>Email and password are required.</p><a href='{FRONTEND_URL}/login.html'>Go Back</a>", 400
        
        # Query user from database
        result = supabase.table("users").select("*").eq("email", email).execute()
        
        if not result.data:
            return f"<h1>Error</h1><p>Invalid email or password.</p><a href='{FRONTEND_URL}/login.html'>Go Back</a>", 401
        
        user = result.data[0]
        stored_hash = user['password_hash']
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            # Generate name from email or use stored name if available
            email_name = email.split('@')[0].replace('.', ' ').title()
            user_name = email_name
            
            # Generate avatar URL based on user name
            name_parts = user_name.strip().split()
            initials = ''.join([part[0].upper() for part in name_parts[:2]]) if name_parts else 'U'
            avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={initials}"
            
            # Store user info in session
            session['user_id'] = user.get('id')
            session['user_email'] = user.get('email')
            session['user_name'] = user_name
            session['user_avatar'] = avatar_url
            
            print(f"✓ User {email} logged in successfully")
            return redirect(f'{FRONTEND_URL}/')
        else:
            print(f"✗ Failed login attempt for {email}")
            return f"<h1>Error</h1><p>Invalid email or password.</p><a href='{FRONTEND_URL}/login.html'>Go Back</a>", 401
            
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Login Error: {error_msg}")
        return f"<h1>Error</h1><p>Login failed: {error_msg}</p><a href='{FRONTEND_URL}/login.html'>Go Back</a>", 400


@app.route('/api/user', methods=['GET'])
def get_user():
    """Get current logged in user info from session"""
    if 'user_id' in session:
        user_name = session.get('user_name', 'User')
        
        # Generate avatar URL based on stored name
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
    """User logout endpoint - clears session"""
    session.clear()
    print("✓ User logged out")
    return redirect(f'{FRONTEND_URL}/')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
