from flask import Flask, render_template, jsonify, request
from googleapiclient.discovery import build
import pickle
import os.path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pandas as pd
import io
import re
from datetime import datetime

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


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


@app.route('/files', methods=['GET'])
def list_files():
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
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
