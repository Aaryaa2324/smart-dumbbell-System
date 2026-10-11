import requests
response = requests.post('https://smart-dumbbell-system.onrender.com/api/telemetry', json={'rep_count': 1, 'form_status': 'Test'})
print(response.status_code, response.text)
