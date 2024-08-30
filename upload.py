
from __future__ import print_function
import pickle
import os.path
import time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# SCOPES를 수정했습니다. 더 넓은 범위의 권한을 요청합니다.
# SCOPES = ['https://www.googleapis.com/auth/drive']
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.appdata', 'https://www.googleapis.com/auth/drive']

which_market = 3

def get_file_size(file_path):
    return os.path.getsize(file_path)


def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

def find_latest_file(directory, prefix):
    files = [f for f in os.listdir(directory) if f.startswith(prefix)]
    files_path = [os.path.join(directory, f) for f in files]
    latest_file = max(files_path, key=os.path.getctime)
    return latest_file

def delete_older_files_from_drive(service, folder_id, prefix, date):
    # 구글 드라이브에서 해당 접두사와 날짜를 포함한 파일 검색
    query = f"'{folder_id}' in parents and name contains '{prefix}{date}' and mimeType != 'application/vnd.google-apps.folder'"
    results = service.files().list(q=query, fields="files(id, name, createdTime)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
        return None

    # 파일 생성 시간 기준으로 정렬하여 최신 파일을 마지막에 위치
    items.sort(key=lambda x: x['createdTime'])

    # 최신 파일을 제외한 나머지 파일 삭제
    for item in items[:-1]:
        try:
            service.files().delete(fileId=item['id']).execute()
            print(f"Deleted: {item['name']}")
        except Exception as e:
            print(f"Error deleting file {item['name']}: {e}")

    return items[-1]  # 최신 파일 반환

def main():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'upload.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    folder_path = 'C:/Users/jkyook/PycharmProjects/MG_Hanto/'

    total_files = len(os.listdir(folder_path))
    for index, filename in enumerate(os.listdir(folder_path), 1):
        filepath = os.path.join(folder_path, filename)
        file_size = get_file_size(filepath)

        # print(f"\n[{index}/{total_files}] Uploading: {filename}")
        print(f"File size: {format_size(file_size)}")

        directory = 'C:/Users/jkyook/PycharmProjects/MG_Hanto/'  # 파일이 저장된 디렉토리 경로
        prefix = '(e)df_npp_m_'
        latest_file = find_latest_file(directory, prefix)
        # print(latest_file, directory+filename)

        if latest_file == directory + filename:
            file_metadata = {'name': filename}
            media = MediaFileUpload(filepath, resumable=True)
            request = service.files().create(body=file_metadata, media_body=media, fields='id')

            response = None
            start_time = time.time()
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    elapsed_time = time.time() - start_time
                    speed = (status.progress() * file_size) / elapsed_time if elapsed_time > 0 else 0
                    remaining_time = (file_size - (status.progress() * file_size)) / speed if speed > 0 else 0

                    print(f"\rProgress: {progress}% | Speed: {format_size(speed)}/s | ETA: {remaining_time:.2f}s", end='',
                          flush=True)

            print(f"\nUpload completed: {filename}")
            print(f"File ID: {response.get('id')}")

    # 폴더 ID 설정
    if which_market == 1:
        folder_id = '1VeT1XHKnV_Te681rMTvzf5LsMQ6NV77I'
    elif which_market == 3:
        folder_id = '0ANBkpyLyg1WAUk9PVA'
    
    # 구글 드라이브에서 불필요한 파일 삭제 및 최신 파일 가져오기
    delete_older_files_from_drive(service, folder_id, prefix, date)

if __name__ == '__main__':
    main()
