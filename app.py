from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import bcrypt
import os
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pandas as pd
import io
import re
from datetime import datetime, timedelta
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')  # 환경 변수에서 비밀키 가져오기

# 세션과 쿠키 타임아웃 설정
app.permanent_session_lifetime = timedelta(minutes=30)  # 세션 타임아웃
app.config['SESSION_COOKIE_AGE'] = 30 * 60  # 쿠키 타임아웃

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# 개발 환경 변수 (0: 자동 로그인, 1: 로그인 필요)
LOGIN_OX = int(os.environ.get('LOGIN_OX', 0))  # 기본값은 1

# 캐시 변수
cache = {
    'files': None,
    'timestamp': None
}

CACHE_EXPIRY = 300  # 캐시 만료 시간 (초), 예: 5분


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


def get_files_from_drive():
    """Google Drive에서 파일 목록을 가져오는 함수"""
    service = get_drive_service()
    items = []
    page_token = None

    while True:
        response = service.files().list(
            pageSize=200,
            fields="nextPageToken, files(id, name)",
            pageToken=page_token
        ).execute()

        items.extend(response.get('files', []))
        page_token = response.get('nextPageToken', None)

        if page_token is None:
            break

    return items


@app.route('/files', methods=['GET'])
def list_files():
    strategy = request.args.get('strategy', '')
    current_time = time.time()
    if cache['files'] is None or (current_time - cache['timestamp']) > CACHE_EXPIRY:
        # 캐시가 없거나 캐시 만료 시 Google Drive에서 파일 목록을 가져옵니다.
        items = get_files_from_drive()

        filtered_files = []
        for item in items:
            if item['name'].startswith('(e)df_npp'):
                # 정규 표현식: _MM-DD-HH-MM 형식에 해당
                match = re.search(r'_(\d{2}-\d{2})-\d{2}-\d{2}', item['name'])
                date_str = match.group(1) if match else 'Unknown'

                try:
                    date_obj = datetime.strptime(date_str, '%m-%d')
                    formatted_date = 'B ' + date_obj.strftime('%m-%d') if '_m' in item[
                        'name'] else 'K ' + date_obj.strftime('%m-%d')
                except ValueError:
                    formatted_date = 'Unknown'

                filtered_files.append({'id': item['id'], 'name': item['name'], 'date': formatted_date})

        cache['files'] = filtered_files
        cache['timestamp'] = current_time

    if strategy == 'bit':
        filtered_files = [file for file in cache['files'] if file['date'].startswith('B')]
    elif strategy == 'kospi':
        filtered_files = [file for file in cache['files'] if file['date'].startswith('K')]
    else:
        filtered_files = cache['files']

    return jsonify(filtered_files)


def check_credentials(username, password):
    try:
        with open('users.txt', 'r') as f:
            users = f.readlines()
        for user in users:
            user_info = user.strip().split(':')
            if len(user_info) == 2:
                stored_username, stored_hashed_password = user_info
                if username == stored_username and bcrypt.checkpw(password.encode('utf-8'),
                                                                  stored_hashed_password.encode('utf-8')):
                    return True
    except FileNotFoundError:
        return False
    return False


def add_user(username, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    with open('users.txt', 'a') as f:
        f.write(f"{username}:{hashed_password.decode('utf-8')}\n")


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


@app.route('/data', methods=['POST'])
def data():
    if 'username' not in session and LOGIN_OX == 1:
        return redirect(url_for('login'))

    file_id = request.form['file_id']
    service = get_drive_service()
    file = service.files().get_media(fileId=file_id).execute()

    try:
        df = pd.read_csv(io.BytesIO(file))

        def convert_to_time_format(time_str):
            time_str = str(time_str).zfill(6)  # 6자리로 맞추기
            return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"

        df['time'] = df['time'].apply(convert_to_time_format)
        df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')

        df = df.dropna(subset=['time'])
        df['time'] = df['time'].dt.strftime('%H:%M:%S')
        df = df[['time', 'now_prc', 'np1', 'np2', 'prf']]

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
