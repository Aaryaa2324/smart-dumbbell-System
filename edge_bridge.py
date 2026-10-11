import json, math, time
import requests, serial

COM_PORT = 'COM3'
BAUD_RATE = 115200
BASE_URL = 'https://smart-dumbbell-system.onrender.com'
TELEMETRY_URL = BASE_URL + '/api/telemetry'

session = requests.Session()  # reuses the TLS connection = much faster

def wait_for_server():
    print("Waiting for Render to wake up (cold start can take 30-60s)...")
    while True:
        try:
            r = session.get(BASE_URL + '/api/live_stream', timeout=30)
            if r.status_code == 200:
                print("Server is awake.")
                return
        except requests.exceptions.RequestException as e:
            print(f"  still waiting... ({e})")
        time.sleep(3)

def process_and_send():
    print(f"Connecting to Arduino on {COM_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return

    wait_for_server()
    print("Bridge active. Reading sensor data...")

    rep_count = 0
    in_rep = False
    last_rep_time = 0
    alpha = 0.3
    filtered_magnitude = 0.0

    THRESHOLD_HIGH = 0.8
    THRESHOLD_LOW = 0.2
    DEBOUNCE_DELAY = 0.3

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    ax = float(data.get("ax", 0.0))
                    ay = float(data.get("ay", 0.0))
                    az = float(data.get("az", 9.81))
                    magnitude = math.sqrt(ax**2 + ay**2 + az**2)
                    movement_delta = abs(magnitude - 9.81)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

                filtered_magnitude = (alpha * movement_delta) + ((1 - alpha) * filtered_magnitude)

                current_time = time.time()
                if not in_rep and filtered_magnitude > THRESHOLD_HIGH:
                    if (current_time - last_rep_time) > DEBOUNCE_DELAY:
                        in_rep = True
                elif in_rep and filtered_magnitude < THRESHOLD_LOW:
                    rep_count += 1
                    last_rep_time = current_time
                    in_rep = False

                if filtered_magnitude < 0.2:
                    status = "Stationary - Not Started"
                elif filtered_magnitude < 0.7:
                    status = "Resting"
                else:
                    status = "Good Form"

                payload = {
                    "accel": round(filtered_magnitude, 2),
                    "filtered_accel": round(filtered_magnitude, 2),
                    "raw_accel": round(movement_delta, 2),
                    "rep_count": rep_count,
                    "reps": rep_count,
                    "form_status": status,
                    "form_rating": status
                }

                try:
                    response = session.post(TELEMETRY_URL, json=payload, timeout=30)
                    if response.status_code == 200:
                        print(f"Reps: {rep_count} | Mag: {filtered_magnitude:.2f} | sent OK")
                    else:
                        print(f"HTTP {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    print(f"Send failed (will retry): {e}")
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping bridge...")
            ser.close()
            break

if __name__ == '__main__':
    process_and_send()