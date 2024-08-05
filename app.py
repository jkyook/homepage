
from flask import Flask, request, jsonify, render_template
import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def download_file(file_id, filename):
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    request = service.files().get_media(fileId=file_id)
    with open(filename, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data', methods=['POST'])
def data():
    file_id = request.form['file_id']
    filename = 'data.csv'

    try:
        # 파일 다운로드 함수 호출
        download_file(file_id, filename)

        # CSV 파일 읽기
        df = pd.read_csv(filename)

        # 'time' 컬럼의 형식 확인 및 변환
        # 데이터의 실제 형식에 맞게 수정하세요. 예: '%H%M%S', '%H:%M:%S', '%H:%M' 등
        df['time'] = pd.to_datetime(df['time'], format='%H%M', errors='coerce')

        # 변환이 실패한 데이터는 NaT (Not a Time)로 변환됨
        # NaT 값을 제거할 수 있습니다.
        df = df.dropna(subset=['time'])

        df['time'] = df['time'].dt.strftime('%H:%M:%S')  # 원하는 형식으로 변환
        df = df[['time', 'now_prc']]

        # 데이터를 JSON 형식으로 변환
        data = df.rename(columns={'now_prc': 'price'}).to_dict(orient='records')
        return jsonify(data)

    except Exception as e:
        # 오류 메시지 로그에 기록
        app.logger.error(f"Error processing data: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
