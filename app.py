from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from googleapiclient.discovery import build
import pickle
import os.path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pandas as pd
import io
import re
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 안전하게 유지하기 위한 비밀키

# 세션과 쿠키 타임아웃 설정
app.permanent_session_lifetime = timedelta(minutes=30)  # 세션 타임아웃
app.config['SESSION_COOKIE_AGE'] = 30 * 60  # 쿠키 타임아웃

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# 개발 환경 변수 (0: 자동 로그인, 1: 로그인 필요)
LOGIN_OX = int(os.environ.get('LOGIN_OX', 1))  # 기본값은 1

def get_drive_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
    return service

def check_credentials(username, password):
    try:
        with open('users.txt', 'r') as f:
            users = f.readlines()
        for user in users:
            user_info = user.strip().split(':')
            if len(user_info) == 2:
                if username == user_info[0] and password == user_info[1]:
                    return True
    except FileNotFoundError:
        return False
    return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session or LOGIN_OX == 0:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_credentials(username, password):
            session.permanent = True  # 세션을 영구적으로 설정
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password', 403

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/files', methods=['GET'])
def list_files():
    if 'username' not in session and LOGIN_OX == 1:
        return redirect(url_for('login'))

    service = get_drive_service()
    results = service.files().list(pageSize=200, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    filtered_files = []
    for item in items:
        if item['name'].startswith('(e)df_npp'):
            print(f"Processing file: {item['name']}")  # Debugging line

            # 정규 표현식: _MM-DD-HH-MM 형식에 해당
            match = re.search(r'_(\d{2}-\d{2})-\d{2}-\d{2}', item['name'])
            if match:
                date_str = match.group(1)
            else:
                date_str = 'Unknown'

            print(f"Extracted date_str: {date_str}")  # Debugging line

            try:
                # 날짜 문자열을 파싱하여 원하는 형식으로 변환
                date_obj = datetime.strptime(date_str, '%m-%d')

                # Check if 'npp_m' is in the file name
                if '_m' in item['name']:
                    formatted_date = 'B ' + date_obj.strftime('%m-%d')
                else:
                    formatted_date = 'K ' + date_obj.strftime('%m-%d')
            except ValueError:
                formatted_date = 'Unknown'

            filtered_files.append({'id': item['id'], 'name': item['name'], 'date': formatted_date})

    return jsonify(filtered_files)

@app.route('/data', methods=['POST'])
def data():
    if 'username' not in session and LOGIN_OX == 1:
        return redirect(url_for('login'))

    file_id = request.form['file_id']
    service = get_drive_service()
    file = service.files().get_media(fileId=file_id).execute()

    try:
        # CSV 파일 읽기
        df = pd.read_csv(io.BytesIO(file))

        # 'time' 컬럼의 형식 확인 및 변환
        def convert_to_time_format(time_str):
            # 'HHMMSS' 형식으로 되어 있는 문자열을 'HH:MM:SS' 형식으로 변환
            time_str = str(time_str).zfill(6)  # 6자리로 맞추기
            return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"

        df['time'] = df['time'].apply(convert_to_time_format)
        df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')

        # 변환이 실패한 데이터는 NaT (Not a Time)로 변환됨
        df = df.dropna(subset=['time'])

        # 원하는 형식으로 변환
        df['time'] = df['time'].dt.strftime('%H:%M:%S')
        df = df[['time', 'now_prc', 'np1', 'np2', 'prf']]  # prf 열 추가

        # 데이터를 JSON 형식으로 변환
        data = df.rename(columns={'now_prc': 'price'}).to_dict(orient='records')
        return jsonify(data)

    except Exception as e:
        app.logger.error(f"Error processing data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    if 'username' not in session and LOGIN_OX == 1:
        return redirect(url_for('login'))
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
