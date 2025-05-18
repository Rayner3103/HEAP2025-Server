from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

url: str = os.environ.get('SUPABASE_URL')
key: str = os.environ.get('SUPABASE_KEY_SERVICE_ROLE')
supabase: Client = create_client(supabase_url=url, supabase_key=key)

def read_all():
    print('Reading data.')
    data = (
        supabase.table('test')
        .select('*')
        .execute()
    )
    return data.data, data.count

def insert_one(table, data):
    result = (
        supabase.table(table)
        .insert(data)
        .execute()
    )
    return result

def delete_one(table, id):
    result = (
        supabase.table(table)
        .delete()
        .eq('id', id)
        .execute()
    )
    return result

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"], supports_credentials=True, methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/test/')
def test():
    return jsonify(message='test'), 200

@app.route('/read/')
def read():
    data, count = read_all()
    return data, 200

@app.route('/add/', methods=['POST', 'OPTIONS'])
def add():
    if request.method == 'OPTIONS':
        return '', 204
    elif request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        updated_data = dict(
            name = data['recordNumber']
        )
        response = insert_one('test', updated_data)
        return jsonify(message="successfully inserted"), 200

@app.route('/delete/', methods=['POST', 'OPTIONS'])
def delete():
    if request.method == 'OPTIONS':
        return '', 204
    elif request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        response = delete_one('test', data['id'])
        return jsonify(message="successfully deleted"), 200

if __name__ == '__main__':
    app.run(debug=True)