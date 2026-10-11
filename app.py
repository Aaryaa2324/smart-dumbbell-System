import hashlib
import sqlite3
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = 'smart_dumbbell_secure_key'  # Needed for session management

DB_FILE = 'dumbbell.db'


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Workouts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            duration TEXT,
            reps INTEGER,
            form_rating TEXT
        )
    """)
    # Users table for secure SHA-256 login
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username_hash TEXT UNIQUE,
            password_hash TEXT
        )
    """)
    # Persistent telemetry table for cloud synchronization across workers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_telemetry (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            raw_accel REAL,
            filtered_accel REAL,
            form_status TEXT,
            rep_count INTEGER
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO live_telemetry (id, raw_accel, filtered_accel, form_status, rep_count)
        VALUES (1, 0.0, 0.0, 'Stationary - Not Started', 0)
    """)
    conn.commit()

    # Create a default test user if none exists (Password: "workout123")
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        default_user_hash = hashlib.sha256('athlete'.encode()).hexdigest()
        default_pass_hash = hashlib.sha256('workout123'.encode()).hexdigest()
        cursor.execute(
            'INSERT INTO users (username_hash, password_hash) VALUES (?, ?)',
            (default_user_hash, default_pass_hash),
        )
        conn.commit()
    conn.close()


init_db()


# Routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        password = data.get('password', '')

        # Hash the entered password using SHA-256
        pass_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Verify against stored password hash
        cursor.execute(
            'SELECT * FROM users WHERE password_hash = ?', (pass_hash,)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['logged_in'] = True
            return (
                jsonify({
                    'status': 'success',
                    'message': 'Login successful!',
                    'redirect': '/dashboard',
                }),
                200,
            )
        else:
            return (
                jsonify({'status': 'error', 'message': 'Invalid password!'}),
                401,
            )

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/history')
def history():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('history.html')


# Telemetry APIs using SQLite persistence
@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    data = request.get_json()
    if data:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE live_telemetry 
            SET raw_accel = ?, filtered_accel = ?, form_status = ?, rep_count = ?
            WHERE id = 1
        """, (
            data.get('raw_accel', 0.0),
            data.get('filtered_accel', 0.0),
            data.get('form_status', 'Stationary - Not Started'),
            data.get('rep_count', 0)
        ))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'No data received'}), 400


@app.route('/api/live_stream', methods=['GET'])
def send_live_stream():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT raw_accel, filtered_accel, form_status, rep_count FROM live_telemetry WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        telemetry_data = {
            'raw_accel': row[0],
            'filtered_accel': row[1],
            'form_status': row[2],
            'rep_count': row[3]
        }
        return jsonify(telemetry_data)
    return jsonify({
        'raw_accel': 0.0,
        'filtered_accel': 0.0,
        'form_status': 'Stationary - Not Started',
        'rep_count': 0
    })


@app.route('/api/save_workout', methods=['POST'])
def save_workout():
    data = request.get_json()
    duration = data.get('duration', '00:00:00')
    reps = data.get('reps', 0)
    form_rating = data.get('form_rating', 'Good Form')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''
            INSERT INTO workouts (duration, reps, form_rating) 
            VALUES (?, ?, ?)
        ''',
        (duration, reps, form_rating),
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Workout saved!'}), 200


@app.route('/api/get_history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, timestamp, duration, reps, form_rating FROM workouts ORDER BY id DESC'
    )
    rows = cursor.fetchall()
    conn.close()

    history_data = [
        {
            'id': r[0],
            'timestamp': r[1],
            'duration': r[2],
            'reps': r[3],
            'form_rating': r[4],
        }
        for r in rows
    ]
    return jsonify(history_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)