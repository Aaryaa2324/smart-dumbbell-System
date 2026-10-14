import os
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'smart_dumbbell_secure_secret_key'

# Configure Database: Render PostgreSQL or local fallback
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///local_dumbbell.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class DumbbellSession(db.Model):
    __tablename__ = 'dumbbell_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    rep_count = db.Column(db.Integer, nullable=False, default=0)
    ax = db.Column(db.Float, nullable=True)
    ay = db.Column(db.Float, nullable=True)
    az = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

with app.app_context():
    try:
        db.create_all()
        print("Database tables verified/created successfully.")
    except Exception as e:
        print(f"Database setup error: {e}")

# --- HTML TEMPLATES ---
BASE_LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <title>Smart Dumbbell Hub</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 0; }
        nav { background: #1e293b; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
        nav a { color: #38bdf8; text-decoration: none; margin-left: 20px; font-weight: 600; }
        nav a:hover { color: #7dd3fc; }
        .container { max-width: 1000px; margin: 40px auto; padding: 20px; text-align: center; }
        .card { background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; }
        .btn { background: #38bdf8; color: #0f172a; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; }
        .btn:hover { background: #7dd3fc; }
        input { padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin: 10px; width: 250px; }
    </style>
</head>
<body>
    <nav>
        <div><strong>🏋️‍♂️ Smart Dumbbell System</strong></div>
        <div>
            <a href="/">Home</a>
            {% if session.get('user') %}
                <a href="/dashboard">Dashboard</a>
                <a href="/logout">Logout</a>
            {% else %}
                <a href="/login">Login</a>
            {% endif %}
        </div>
    </nav>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <div class="card">
        <h1>Next-Gen AI Fitness Tracking</h1>
        <p>Monitor your reps, accelerations, and workout duration in real-time with precise edge computing.</p>
        <br>
        <a href="/dashboard" class="btn">Launch Live Dashboard</a>
    </div>
    {% endblock %}
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['user'] = username
            return redirect(url_for('dashboard'))
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <div class="card">
        <h2>Athlete Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Enter your name" required><br>
            <button type="submit" class="btn">Login</button>
        </form>
    </div>
    {% endblock %}
    ''')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <div class="card">
        <h2>Live Workout Dashboard (Welcome, {{ session.get('user') }})</h2>
        <div style="display: flex; justify-content: space-around; margin: 20px 0;">
            <div><h3>Rep Count</h3><p id="rep-metric" style="font-size: 36px; color: #4ade80; font-weight: bold;">0</p></div>
            <div><h3>Workout Timer</h3><p id="timer" style="font-size: 36px; color: #38bdf8; font-weight: bold;">00:00</p></div>
        </div>
        <button onclick="resetTimer()" class="btn" style="background: #ef4444; color: white; margin-bottom: 20px;">Reset Timer</button>
        
        <div style="background: #0f172a; padding: 15px; border-radius: 8px;">
            <canvas id="accelChart"></canvas>
        </div>
    </div>

    <script>
        let seconds = 0;
        let timerInterval = setInterval(() => {
            seconds++;
            let mins = Math.floor(seconds / 60).toString().padStart(2, '0');
            let secs = (seconds % 60).toString().padStart(2, '0');
            document.getElementById('timer').innerText = mins + ":" + secs;
        }, 1000);

        function resetTimer() { seconds = 0; }

        const ctx = document.getElementById('accelChart').getContext('2d');
        const accelChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'Accel X', borderColor: '#38bdf8', data: [], tension: 0.2 },
                    { label: 'Accel Y', borderColor: '#4ade80', data: [], tension: 0.2 },
                    { label: 'Accel Z', borderColor: '#f43f5e', data: [], tension: 0.2 }
                ]
            },
            options: { responsive: true, scales: { y: { beginAndZero: false } } }
        });

        async function fetchData() {
            try {
                let response = await fetch('/api/live-data');
                let data = await response.json();
                if(data) {
                    document.getElementById('rep-metric').innerText = data.rep_count;
                    
                    let timeLabel = new Date().toLocaleTimeString();
                    if(accelChart.data.labels.length > 20) {
                        accelChart.data.labels.shift();
                        accelChart.data.datasets[0].data.shift();
                        accelChart.data.datasets[1].data.shift();
                        accelChart.data.datasets[2].data.shift();
                    }
                    accelChart.data.labels.push(timeLabel);
                    accelChart.data.datasets[0].data.push(data.ax);
                    accelChart.data.datasets[1].data.push(data.ay);
                    accelChart.data.datasets[2].data.push(data.az);
                    accelChart.update();
                }
            } catch(e) { console.error(e); }
        }

        setInterval(fetchData, 1000);
    </script>
    {% endblock %}
    ''')

@app.route('/api/live-data')
def live_data():
    try:
        latest = DumbbellSession.query.order_by(DumbbellSession.id.desc()).first()
        if not latest:
            return jsonify({"rep_count": 0, "ax": 0, "ay": 0, "az": 0})
        return jsonify({
            "rep_count": latest.rep_count,
            "ax": latest.ax,
            "ay": latest.ay,
            "az": latest.az
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    try:
        content = request.json
        if not content:
            return jsonify({"error": "No payload"}), 400
        
        new_entry = DumbbellSession(
            rep_count=content.get('rep_count', 0),
            ax=content.get('ax'),
            ay=content.get('ay'),
            az=content.get('az')
        )
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)