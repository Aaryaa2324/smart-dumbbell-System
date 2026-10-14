import os
from flask import Flask, render_template_string, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure Database: Render provides DATABASE_URL. 
# SQLAlchemy requires 'postgresql://' instead of legacy 'postgres://'
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///local_dumbbell.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model for Smart Dumbbell telemetry/reps
class DumbbellSession(db.Model):
    __tablename__ = 'dumbbell_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    rep_count = db.Column(db.Integer, nullable=False, default=0)
    ax = db.Column(db.Float, nullable=True)
    ay = db.Column(db.Float, nullable=True)
    az = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

# Create tables automatically on startup if they don't exist
with app.app_context():
    db.create_all()

# Simple dashboard view
@app.route('/')
def index():
    latest_data = DumbbellSession.query.order_by(DumbbellSession.id.desc()).first()
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Smart Dumbbell Dashboard</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 50px; }
            .card { background: #1e293b; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            h1 { color: #38bdf8; }
            .metric { font-size: 48px; font-weight: bold; margin: 20px 0; color: #4ade80; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Smart Dumbbell Live Stats</h1>
            <p>Latest Rep Count</p>
            <div class="metric">{{ data.rep_count if data else 0 }}</div>
            <p>Accelerometer (X, Y, Z): {{ data.ax }}, {{ data.ay }}, {{ data.az }}</p>
            <p><small>Auto-refreshes every 5 seconds</small></p>
        </div>
    </body>
    </html>
    ''', data=latest_data)

# API endpoint for the local edge bridge to push sensor/rep data
@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    content = request.json
    if not content:
        return jsonify({"error": "No JSON payload provided"}), 400
    
    new_entry = DumbbellSession(
        rep_count=content.get('rep_count', 0),
        ax=content.get('ax'),
        ay=content.get('ay'),
        az=content.get('az')
    )
    db.session.add(new_entry)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Telemetry saved to PostgreSQL!"}), 201

if __name__ == '__main__':
    # Dynamic port configuration for Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)