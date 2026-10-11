import json
import requests
import math
import time
import serial

COM_PORT = 'COM3'
BAUD_RATE = 115200
FLASK_URL = 'http://127.0.0.1:5000/api/telemetry'

def process_and_send():
    # Fine-tuned thresholds and precision control
    REP_THRESHOLD_HIGH = 3.0   # Trigger when movement force exceeds 3.0
    REP_THRESHOLD_LOW = 1.0    # Reset when motion drops below 1.0
    DEBOUNCE_DELAY = 0.25      # Minimum seconds required between valid reps
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
                print(f"RAW FROM ARDUINO: '{line}'")
                if not line:
                    continue

                # Expecting JSON with ax, ay, az from Arduino
                try:
                    data = json.loads(line)
                    ay = float(data.get("ay", 10.0))
                    # Calculate net motion change by removing gravity baseline
                    raw_accel = abs(ay - 9.81)
                except json.JSONDecodeError:
                    # Fallback if Arduino sends plain float/string numbers instead of JSON
                    try:
                        raw_accel = float(line)
                    except ValueError:
                        continue

                # Apply low-pass filter
                filtered_accel = (alpha * raw_accel) + ((1 - alpha) * filtered_accel)

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
                if filtered_accel < 0.8:
                    form_status = "Stationary - Not Started"
                elif filtered_accel < 2.0:
                    form_status = "Resting"
                else:
                    form_status = "Good Form"

                # Construct payload
                # Construct payload with dual-compatibility keys for Flask app.py
                # Construct comprehensive payload ensuring full frontend compatibility
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
                print(f"Pushed: Reps={rep_count} | Form={form_status} | Status={response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"Network error pushing telemetry: {e}")
        except KeyboardInterrupt:
            print("\nStopping Edge Bridge...")
            ser.close()
            break

if __name__ == "__main__":
    process_and_send()