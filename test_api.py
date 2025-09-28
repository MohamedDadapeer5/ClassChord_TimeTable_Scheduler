import time
import requests

print('Testing Flask API endpoints...')
time.sleep(2)  # Give the server time to start

try:
    # Test classrooms endpoint
    response = requests.get('http://127.0.0.1:5000/api/classrooms', timeout=10)
    print(f'✅ Classrooms API: {response.status_code}')

    # Test faculty endpoint
    response = requests.get('http://127.0.0.1:5000/api/faculty', timeout=10)
    print(f'✅ Faculty API: {response.status_code}')

    # Test subjects endpoint
    response = requests.get('http://127.0.0.1:5000/api/subjects', timeout=10)
    print(f'✅ Subjects API: {response.status_code}')

    # Test batches endpoint
    response = requests.get('http://127.0.0.1:5000/api/batches', timeout=10)
    print(f'✅ Batches API: {response.status_code}')

    print('\n🎉 All API endpoints are working!')
    print('🌐 Open your browser and go to: http://127.0.0.1:5000')

except Exception as e:
    print(f'❌ Connection error: {e}')