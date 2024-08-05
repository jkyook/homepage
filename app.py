from flask import Flask, jsonify, render_template
import pandas as pd
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    # app.py와 동일한 디렉토리에 있는 CSV 파일 경로
    file_path = os.path.join(os.path.dirname(__file__), '(e)df_npp_m_08-05-14-35.csv')
    try:
        # CSV 파일 읽기
        df = pd.read_csv(file_path)

        # 'time' 컬럼을 시간 형식으로 변환하고, 'price'로 사용할 'now_prc' 컬럼 선택
        df['time'] = pd.to_datetime(df['time'], format='%H%M%S').dt.strftime('%H:%M:%S')
        df = df[['time', 'now_prc']]  # 'now_prc'가 'price'를 대체합니다.

        # 데이터를 JSON 형식으로 변환
        data = df.rename(columns={'now_prc': 'price'}).to_dict(orient='records')
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
