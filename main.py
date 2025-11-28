import requests
from flask import Flask, request, Response, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os

# --- Flask 및 SQLAlchemy 설정 ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///url_proxy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# flash 메시지를 사용하기 위한 시크릿 키 설정 (실제 배포 시에는 복잡한 문자열 사용)
app.secret_key = 'super_secret_key' 
db = SQLAlchemy(app)

# --- 데이터베이스 모델 정의 ---
class URLMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    target_url = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f'<URLMapping {self.id}: {self.target_url}>'

# --- 데이터베이스 초기화 함수 ---
def initialize_database():
    with app.app_context():
        db.create_all()
        # 테스트용 데이터 추가
        if not URLMapping.query.get(1234):
            db.session.add(URLMapping(id=1234, target_url='http://example.com'))
        if not URLMapping.query.get(5678):
            db.session.add(URLMapping(id=5678, target_url='https://www.google.com'))
        db.session.commit()
        print("데이터베이스 초기화 완료.")

# --- HTML 폼 템플릿 (수정 없음) ---
ADD_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Add New URL with Custom ID</title>
</head>
<body>
    <h2>새로운 리다이렉트 URL 추가</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul class=flashes>
        {% for message in messages %}
          <li style="color: red;">{{ message }}</li>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST" action="/">
        <label for="url_id">원하는 URL ID (숫자):</label>
        <input type="number" id="url_id" name="url_id" required>
        <br>
        <label for="target_url">대상 URL (http:// 포함):</label>
        <input type="text" id="target_url" name="target_url" required>
        <button type="submit">URL 추가</button>
    </form>
    <hr>
    <h3>기존 URL 테스트 (GET 요청 시 즉시 리다이렉트):</h3>
    <ul>
        <li><a href="/?id=1234">/?id=1234 (example.com으로 리다이렉트)</a></li>
        <li><a href="/?id=5678">/?id=5678 (google.com으로 리다이렉트)</a></li>
        <li><a href="/?id=9999">/?id=9999 (유효하지 않은 ID, 폼으로 이동)</a></li>
    </ul>
</body>
</html>
"""

# --- 메인 라우트: GET/POST 처리 ---
@app.route('/', methods=['GET', 'POST'])
def handle_requests():
    if request.method == 'POST':
        # POST 요청 처리: 새 URL과 사용자 지정 ID 추가
        url_id = request.form.get('url_id')
        target_url = request.form.get('target_url')

        if not url_id or not target_url:
            flash("오류: ID와 URL을 모두 입력해야 합니다.")
            return redirect(url_for('handle_requests'))
        
        try:
            url_id = int(url_id)
            new_mapping = URLMapping(id=url_id, target_url=target_url)
            db.session.add(new_mapping)
            db.session.commit()
            flash(f"성공: ID {url_id}에 대한 URL 매핑이 추가되었습니다.")
            return redirect(url_for('handle_requests'))
        
        except ValueError:
            flash("오류: URL ID는 유효한 숫자여야 합니다.")
            db.session.rollback()
            return redirect(url_for('handle_requests'))
        except IntegrityError:
            # 기본 키(ID) 중복 오류 처리
            flash(f"오류: ID {url_id}는 이미 사용 중입니다. 다른 ID를 선택해 주세요.")
            db.session.rollback()
            return redirect(url_for('handle_requests'))

    else:
        # GET 요청 처리 (즉시 리다이렉트 또는 폼 표시)
        url_id = request.args.get('id')

        if not url_id:
            # 'id' 파라미터가 없으면 URL 추가 폼 반환
            return render_template_string(ADD_FORM_HTML)

        # 'id' 파라미터가 있으면 리다이렉션 기능 수행
        try:
            mapping = URLMapping.query.get(int(url_id))
            
            if mapping:
                # 유효한 URL이 있으면 즉시 해당 URL로 HTTP 302 리다이렉트
                print(f"ID {url_id}을(를) {mapping.target_url}(으)로 즉시 리다이렉트합니다.")
                return redirect(mapping.target_url, code=302)
            else:
                # 데이터베이스에 ID가 없으면 에러 메시지를 flash하고 폼 페이지로 리다이렉트
                flash(f"오류: ID {url_id}에 해당하는 URL을 찾을 수 없습니다. 새로운 URL을 추가해 주세요.")
                return redirect(url_for('handle_requests'))

        except ValueError:
            # ID가 숫자가 아닌 경우 에러 메시지를 flash하고 폼 페이지로 리다이렉트
            flash("오류: 유효하지 않은 URL ID 형식입니다. 숫자만 입력 가능합니다.")
            return redirect(url_for('handle_requests'))

# --- 애플리케이션 실행 ---
if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
