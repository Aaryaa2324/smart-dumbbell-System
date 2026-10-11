import json
import requests
import math
import time
import serial

COM_PORT = 'COM3'
BAUD_RATE = 115200
FLASK_URL = 'https://smart-dumbbell-system.onrender.com/api/telemetry'

def process_and_send():
    # Sensitive thresholds for reliable rep detection
    REP_THRESHOLD_HIGH = 0.5   # Lowered from 1.0 to catch even lighter lifts
    REP_THRESHOLD_LOW = 0.15   # Lowered from 0.3 to close reps earlier
    DEBOUNCE_DELAY = 0.2       # Shortened cooldown so rapid reps register      # Minimum seconds between valid reps
    last_rep_time = 0
    alpha = 0.4                # Low-pass filter smoothing coefficient

    rep_count = 0
    in_rep = False
    filtered_accel = 0.0

    print(f"Connecting to Arduino on {COM_PORT} at {BAUD_RATE} baud...")
    
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Allow connection to settle
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return

    print("Bridge active. Listening for sensor data...")

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                raw_accel = 0.0
                try:
                    # Try parsing as JSON first
                    data = json.loads(line)
                    ax = float(data.get("ax", 0.0))
                    ay = float(data.get("ay", 0.0))
                    az = float(data.get("az", 9.81))
                    total_accel = math.sqrt(ax**2 + ay**2 + az**2)
                    raw_accel = abs(total_accel - 9.81)
                except json.JSONDecodeError:
                    # Fallback: handle plain strings or comma-separated values
                    try:
                        parts = [float(p.strip()) for p in line.replace('{','').replace('}','').replace('"','').split(',')]
                        if len(parts) >= 3:
                            total_accel = math.sqrt(parts[0]**2 + parts[1]**2 + parts[2]**2)
                            raw_accel = abs(total_accel - 9.81)
                        elif len(parts) == 1:
                            raw_accel = abs(parts[0] - 9.81)
                        else:
                            clean_line = ''.join(c for c in line if c.isdigit() or c in '.-')
                            raw_accel = abs(float(clean_line) - 9.81)
                    except Exception:
                        continue

                # Apply low-pass filter
                filtered_accel = (alpha * raw_accel) + ((1 - alpha) * filtered_accel)
                print(f"DEBUG Magnitude: {filtered_accel:.2f}") # Add this line

                # Responsive rep counting state machine
                current_time = time.time()
                if not in_rep and filtered_accel > REP_THRESHOLD_HIGH:
                    if (current_time - last_rep_time) > DEBOUNCE_DELAY:
                        in_rep = True
                elif in_rep and filtered_accel < REP_THRESHOLD_LOW:
                    rep_count += 1
                    last_rep_time = current_time
                    in_rep = False

                # Form status evaluation
                if filtered_accel < 0.2:
                    form_status = "Stationary - Not Started"
                elif filtered_accel < 0.8:
                    form_status = "Resting"
                else:
                    form_status = "Good Form"

                # Construct comprehensive payload
                payload = {
                    "accel": round(filtered_accel, 2),
                    "filtered_accel": round(filtered_accel, 2),
                    "raw_accel": round(raw_accel, 2),
                    "rep_count": rep_count,
                    "reps": rep_count,
                    "form_status": form_status,
                    "form_rating": form_status
                }

                # POST to Render cloud endpoint
                response = requests.post(FLASK_URL, json=payload, timeout=3.0)
                print(f"Pushed: Reps={rep_count} | Mag={round(filtered_accel, 2)} | Status={response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"Network error pushing telemetry: {e}")
        except KeyboardInterrupt:
            print("\nStopping Edge Bridge...")
            ser.close()
            break

if __name__ == "__main__":
    process_and_send()