import serial
import json
import requests
import math
import time

COM_PORT = 'COM3'
BAUD_RATE = 115200
FLASK_URL = 'https://smart-dumbbell-system.onrender.com/api/telemetry'

def process_and_send():
    # Thresholds and state variables
    REP_THRESHOLD_HIGH = 12.0  # Upper movement peak
    REP_THRESHOLD_LOW = 8.0    # Lower movement valley
    DEBOUNCE_DELAY = 0.4       # Minimum seconds required between valid reps
    last_rep_time = 0
    alpha = 0.2                # Low-pass filter smoothing coefficient

    rep_count = 0
    in_rep = False
    filtered_accel = 9.81
    
    print(f"Connecting to Arduino on {COM_PORT} at {BAUD_RATE} baud...")
    
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Allow Arduino to reset after connection
        print("Connected! Reading telemetry...")
    except Exception as e:
        print(f"Failed to open serial port {COM_PORT}: {e}")
        return

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line or not line.startswith('{'):
                continue
            
            # Parse raw JSON coming from Arduino Wire sketch
            data = json.loads(line)
            ax = data.get('ax', 0.0)
            ay = data.get('ay', 0.0)
            az = data.get('az', 0.0)

            # Calculate total raw acceleration magnitude
            raw_accel = math.sqrt(ax**2 + ay**2 + az**2)

            # Apply Exponential Moving Average (Low-Pass Filter)
            filtered_accel = (alpha * raw_accel) + ((1 - alpha) * filtered_accel)

            # Rep counting state machine with debounce
            if filtered_accel > REP_THRESHOLD_HIGH and not in_rep:
                in_rep = True
            elif filtered_accel < REP_THRESHOLD_LOW and in_rep:
                current_time = time.time()
                if current_time - last_rep_time > DEBOUNCE_DELAY:
                    rep_count += 1
                    last_rep_time = current_time
                in_rep = False

            # Form evaluation with balanced thresholds
            if filtered_accel > 19.0:
                form_status = "Too Jerky!"
            elif in_rep:
                form_status = "Lifting"
            elif abs(filtered_accel - 9.81) < 0.4 and rep_count == 0:
                form_status = "Stationary - Not Started"
            elif abs(filtered_accel - 9.81) < 0.4:
                form_status = "Resting"
            else:
                form_status = "Good Form"

            # Construct payload
            payload = {
                "raw_accel": round(raw_accel, 2),
                "filtered_accel": round(filtered_accel, 2),
                "form_status": form_status,
                "rep_count": rep_count
            }

            # POST to Flask in-memory endpoint
            response = requests.post(FLASK_URL, json=payload, timeout=3.0)
            print(f"Pushed: Reps={rep_count} | Form={form_status} | Status={response.status_code}")

        except json.JSONDecodeError:
            pass
        except requests.exceptions.RequestException as e:
            print(f"Failed to post to Flask: {e}")
        except KeyboardInterrupt:
            print("\nStopping Edge Bridge...")
            ser.close()
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    process_and_send()