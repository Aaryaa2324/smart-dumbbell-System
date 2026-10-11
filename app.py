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

latest_telemetry = {
    'raw_accel': 0.0,
    'filtered_accel': 0.0,
    'form_status': 'Stationary - Not Started',
    'rep_count': 0,
}


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
    # Verify against stored password hash (keeping username hidden/hashed)
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
  return redirect(url_for('home'))  # Redirects to home page instead of login


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


# Telemetry APIs
@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
  global latest_telemetry
  data = request.get_json()
  if data:
    latest_telemetry = data
    return jsonify({'status': 'success'}), 200
  return jsonify({'status': 'error', 'message': 'No data received'}), 400


@app.route('/api/live_stream', methods=['GET'])
def send_live_stream():
  return jsonify(latest_telemetry)


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
      'SELECT id, timestamp, duration, reps, form_rating FROM workouts ORDER BY'
      ' id DESC'
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