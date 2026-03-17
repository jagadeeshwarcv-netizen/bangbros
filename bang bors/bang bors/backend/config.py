import os
from flask import Flask,jsonify,request
from dotenv import load_dotenv
from supabase import create_client,client

load_dotenv()

app = Flask(__name__)
supabase = create_client(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_key=os.getenv("SUPABASE_KEY")
)
@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    print("Received data:", data)
    # Store the data in Supabase
    response = supabase.table('data').insert(data).execute()
    if response.status_code == 201:
        return jsonify({"message": "Data stored successfully!"}), 201
    else:
        return jsonify({"error": "Failed to store data."}), 500
if __name__ == '__main__':
    app.run(debug=True)