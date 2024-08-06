from flask import Flask, render_template, jsonify, request
from googleapiclient.discovery import build
import pickle
import os.path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pandas as pd
import io

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
    results = service.files().list(pageSize=50, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    filtered_files = []
    for item in items:
        if item['name'].startswith('(e)df_npp_m'):
            date_part = item['name'].split('_')[3]
            filtered_files.append({'id': item['id'], 'name': item['name'], 'date': date_part})

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
        df['time'] = pd.to_datetime(df['time'], format='%H%M', errors='coerce')

        # 변환이 실패한 데이터는 NaT (Not a Time)로 변환됨
        df = df.dropna(subset=['time'])

        df['time'] = df['time'].dt.strftime('%H:%M:%S')  # 원하는 형식으로 변환
        df = df[['time', 'now_prc']]

        # 데이터를 JSON 형식으로 변환
        data = df.rename(columns={'now_prc': 'price'}).to_dict(orient='records')
        print(f"Data sent to frontend: {data}")  # Debugging line
        return jsonify(data)

    except Exception as e:
        app.logger.error(f"Error processing data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
