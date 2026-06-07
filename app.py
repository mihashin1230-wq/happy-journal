import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'uploads'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm'}

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id SERIAL PRIMARY KEY,
                    date TEXT NOT NULL,
                    author TEXT,
                    text TEXT NOT NULL,
                    media_filename TEXT,
                    media_type TEXT,
                    created_at TEXT NOT NULL,
                    likes INTEGER DEFAULT 0
                )
            ''')
        conn.commit()
    finally:
        conn.close()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/entries', methods=['GET'])
def get_entries():
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM entries ORDER BY date DESC, created_at DESC')
            rows = cur.fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route('/api/entries', methods=['POST'])
def create_entry():
    date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    text = request.form.get('text', '').strip()
    author = request.form.get('author', '').strip() or '익명'

    if not text:
        return jsonify({'error': '내용을 입력해주세요.'}), 400

    media_filename = None
    media_type = None

    if 'media' in request.files:
        file = request.files['media']
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            media_filename = f"{timestamp}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], media_filename))
            media_type = 'video' if ext in {'mp4', 'mov', 'avi', 'webm'} else 'image'

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''INSERT INTO entries (date, author, text, media_filename, media_type, created_at, likes)
                   VALUES (%s, %s, %s, %s, %s, %s, 0) RETURNING *''',
                (date, author, text, media_filename, media_type, datetime.now().isoformat())
            )
            entry = cur.fetchone()
        conn.commit()
        return jsonify(dict(entry)), 201
    finally:
        conn.close()


@app.route('/api/entries/<int:entry_id>/like', methods=['POST'])
def like_entry(entry_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM entries WHERE id = %s', (entry_id,))
            if not cur.fetchone():
                return jsonify({'error': '없는 항목'}), 404
            cur.execute('UPDATE entries SET likes = likes + 1 WHERE id = %s', (entry_id,))
            cur.execute('SELECT likes FROM entries WHERE id = %s', (entry_id,))
            new_count = cur.fetchone()[0]
        conn.commit()
        return jsonify({'likes': new_count})
    finally:
        conn.close()


@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM entries WHERE id = %s', (entry_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': '항목을 찾을 수 없습니다.'}), 404
            if row['media_filename']:
                path = os.path.join(app.config['UPLOAD_FOLDER'], row['media_filename'])
                if os.path.exists(path):
                    os.remove(path)
            cur.execute('DELETE FROM entries WHERE id = %s', (entry_id,))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()


@app.route('/api/admin/verify', methods=['POST'])
def verify_admin():
    if not ADMIN_PASSWORD:
        return jsonify({'ok': False}), 403
    data = request.get_json()
    if data and data.get('password') == ADMIN_PASSWORD:
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401


@app.route('/backup')
def backup():
    key = request.args.get('key', '')
    if not ADMIN_PASSWORD or key != ADMIN_PASSWORD:
        return jsonify({'error': '권한 없음'}), 403
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM entries ORDER BY date DESC, created_at DESC')
            rows = cur.fetchall()
        data = [dict(r) for r in rows]
        filename = f"journal_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return Response(
            json.dumps(data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    finally:
        conn.close()


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    print(f"일기장 실행 중 → http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
