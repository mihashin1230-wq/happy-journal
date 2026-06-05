import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'uploads'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm'}

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'journal.db'))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                author TEXT,
                text TEXT NOT NULL,
                media_filename TEXT,
                media_type TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        cols = [r[1] for r in conn.execute('PRAGMA table_info(entries)').fetchall()]
        if 'author' not in cols:
            conn.execute('ALTER TABLE entries ADD COLUMN author TEXT')
        if 'likes' not in cols:
            conn.execute('ALTER TABLE entries ADD COLUMN likes INTEGER DEFAULT 0')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/entries', methods=['GET'])
def get_entries():
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM entries ORDER BY date DESC, created_at DESC'
        ).fetchall()
    return jsonify([dict(r) for r in rows])


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

    with get_db() as conn:
        cursor = conn.execute(
            'INSERT INTO entries (date, author, text, media_filename, media_type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (date, author, text, media_filename, media_type, datetime.now().isoformat())
        )
        entry_id = cursor.lastrowid
        entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()

    return jsonify(dict(entry)), 201


@app.route('/api/entries/<int:entry_id>/like', methods=['POST'])
def like_entry(entry_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
        if not row:
            return jsonify({'error': '없는 항목'}), 404
        conn.execute('UPDATE entries SET likes = likes + 1 WHERE id = ?', (entry_id,))
        new_count = conn.execute('SELECT likes FROM entries WHERE id = ?', (entry_id,)).fetchone()[0]
    return jsonify({'likes': new_count})


@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
        if not row:
            return jsonify({'error': '항목을 찾을 수 없습니다.'}), 404
        if row['media_filename']:
            path = os.path.join(app.config['UPLOAD_FOLDER'], row['media_filename'])
            if os.path.exists(path):
                os.remove(path)
        conn.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
    return jsonify({'ok': True})


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    print(f"일기장 실행 중 → http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
