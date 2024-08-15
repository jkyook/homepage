from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import bcrypt
import os
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials  # 이 줄을 추가
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
    # 기존 자격 증명 파일(token.json)이 있는지 확인
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # 자격 증명이 없거나 유효하지 않은 경우
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError:
                # 토큰 갱신 실패 시, 토큰 파일 삭제하여 재인증 유도
                os.remove('token.json')
                creds = None

        if not creds:
            # 새로운 인증 절차 진행
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # 새로운 자격 증명을 저장
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    return service


def get_files_from_drive():
    """Google Drive의 홈 디렉토리에서 파일 목록을 가져오는 함수"""
    service = get_drive_service()
    items = []
    page_token = None

    while True:
        response = service.files().list(
            q="'root' in parents and trashed = false",
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
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    current_time = time.time()

    # 캐시 확인 및 갱신
    if cache['files'] is None or (current_time - cache['timestamp']) > CACHE_EXPIRY:
        # Google Drive에서 파일 목록을 가져옵니다.
        items = get_files_from_drive()

        filtered_files = []
        for item in items:
            if item['name'].startswith('(e)df_npp'):
                # 정규 표현식: _MM-DD-HH-MM 형식에 해당
                match = re.search(r'_(\d{2}-\d{2})-\d{2}-\d{2}', item['name'])
                date_str = match.group(1) if match else 'Unknown'

                # 날짜 포맷팅: '08-09' 형식을 '08-09'로 저장
                formatted_date = 'B ' + date_str if '_m' in item['name'] else 'K ' + date_str

                filtered_files.append({'id': item['id'], 'name': item['name'], 'date': formatted_date})

        # 캐시에 필터링된 파일 목록 저장
        cache['files'] = filtered_files
        cache['timestamp'] = current_time

    # 날짜 범위 필터링
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            def extract_date_from_filename(filename):
                # '08-09-15-29'에서 '08-09' 부분 추출
                match = re.search(r'_(\d{2}-\d{2})-\d{2}-\d{2}', filename)
                if match:
                    return datetime.strptime(match.group(1), '%m-%d').date().replace(year=datetime.now().year)
                return None

            # 날짜 범위에 포함되는 파일만 필터링
            filtered_files = [file for file in cache['files']
                              if extract_date_from_filename(file['name']) and start_date <= extract_date_from_filename(file['name']) <= end_date]

        except ValueError:
            filtered_files = []
    else:
        filtered_files = cache['files']

    # 전략 필터링
    if strategy == 'bit':
        filtered_files = [file for file in filtered_files if file['date'].startswith('B')]
    elif strategy == 'kospi':
        filtered_files = [file for file in filtered_files if file['date'].startswith('K')]

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


@app.route('/live_data', methods=['GET'])
def live_data():
    service = get_drive_service()

    # 구글 드라이브에서 "(e)df_npp_m" 파일 찾기
    files = service.files().list(q="name contains '(e)df_npp_m'", spaces='drive', fields='files(id, name)').execute()

    if not files['files']:
        return jsonify({'error': 'File not found'})

    file_id = files['files'][0]['id']

    # 파일 내용 읽기
    file_content = service.files().get_media(fileId=file_id).execute()

    # CSV 파일 파싱
    df = pd.read_csv(io.BytesIO(file_content))

    # 필요한 열만 선택
    data = df[['time', 'now_prc', 'np1', 'np2', 'prf']].to_dict(orient='records')

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)