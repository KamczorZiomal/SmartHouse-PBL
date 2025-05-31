from flask import Flask, render_template, jsonify, request
from models import db, SensorData
import socket

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensors.db'
db.init_app(app)

# Konfiguracja klienta gniazda do komunikacji z serial_reader.py
HOST = '127.0.0.1'  # Adres hosta serwera
PORT = 65432        # Port używany przez serwer

# Funkcja do wysyłania komend do serial_reader.py przez gniazdo
def send_command_to_serial(command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(command)
            response = s.recv(1024)
            return True, response.decode('utf-8')
    except Exception as e:
        print(f"Błąd wysyłania komendy do serial_reader.py: {e}")
        return False, str(e)

# Sprawdź czy serial_reader.py jest dostępny
try:
    success, response = send_command_to_serial(b'CHECK_CONNECTION\n')
    if success and "Connection OK" in response:
        serial_available = True
        print("Pomyślnie połączono z serial_reader.py")
    else:
        serial_available = False
        print(f"Nie udało się połączyć z serial_reader.py: {response}")
except Exception as e:
    print(f"Błąd połączenia z serial_reader.py: {e}")
    print("Upewnij się, że serial_reader.py jest uruchomiony przed startem app.py")
    serial_available = False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(20).all()
    result = []
    latest = None
    oldest = None
    if data:
        latest = {
            'temperature': data[0].temperature,
            'humidity': data[0].humidity,
            'air_quality': data[0].air_quality,
            'light_percent': data[0].light_percent,
            'motion_detected': data[0].motion_detected,
            'timestamp': data[0].timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        oldest = {
            'temperature': data[-1].temperature,
            'humidity': data[-1].humidity,
            'air_quality': data[-1].air_quality,
            'light_percent': data[-1].light_percent,
            'motion_detected': data[-1].motion_detected,
            'timestamp': data[-1].timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        history = [{
            'timestamp': entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'temperature': entry.temperature,
            'humidity': entry.humidity,
            'air_quality': entry.air_quality,
            'light_percent': entry.light_percent,
            'motion_detected': entry.motion_detected
        } for entry in reversed(data)]
        result = {'latest': latest, 'oldest': oldest, 'history': history}
    return jsonify(result)


@app.route('/api/sensors/motion')
def get_motion():
    data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(24).all()
    result = {
        'motion_detected': False,
        'timestamp': None,
        'motion_history': []
    }

    if data:
        # Get latest motion status
        result['motion_detected'] = data[0].motion_detected
        result['timestamp'] = data[0].timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Create motion history
        motion_history = []
        for entry in reversed(data):
            motion_history.append({
                'time': entry.timestamp.strftime("%H:%M"),
                'value': 1 if entry.motion_detected else 0
            })
        result['motion_history'] = motion_history

    return jsonify(result)

@app.route('/api/motion/detected', methods=['POST'])
def motion_detected():
    """
    Endpoint do obsługi zdarzeń wykrycia ruchu.
    Gdy wykryto ruch, ten endpoint uruchomi buzzer na 1 sekundę.
    """
    if not serial_available:
        return jsonify({'success': False, 'message': 'Brak połączenia szeregowego'}), 500

    try:
        # Włącz buzzer
        success_on, response_on = send_command_to_serial(b'BUZZER_ON\n')
        if not success_on:
            return jsonify({'success': False, 'message': f'Nie udało się włączyć buzzera: {response_on}'}), 500

        # Poczekaj 1 sekundę
        import time
        time.sleep(1)

        # Wyłącz buzzer
        success_off, response_off = send_command_to_serial(b'BUZZER_OFF\n')
        if not success_off:
            return jsonify({'success': False, 'message': f'Nie udało się wyłączyć buzzera: {response_off}'}), 500

        return jsonify({
            'success': True, 
            'message': 'Wykryto ruch, buzzer uruchomiony na 1 sekundę'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/buzzer', methods=['POST'])
def control_buzzer():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Brak połączenia szeregowego'}), 500

    try:
        data = request.json
        state = data.get('state', False)

        if state:
            command = b'BUZZER_ON\n'
            message = 'Buzzer WŁĄCZONY'
        else:
            command = b'BUZZER_OFF\n'
            message = 'Buzzer WYŁĄCZONY'

        success, response = send_command_to_serial(command)
        if not success:
            return jsonify({'success': False, 'message': f'Nie udało się wysłać komendy: {response}'}), 500

        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/servo', methods=['POST'])
def control_servo():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Brak połączenia szeregowego'}), 500

    try:
        data = request.json
        angle = data.get('angle', 90)

        # Upewnij się, że kąt jest w prawidłowym zakresie
        angle = max(0, min(180, angle))

        # Wyślij komendę do Arduino przez gniazdo
        command = f'SG90_{angle}\n'.encode()
        success, response = send_command_to_serial(command)

        if not success:
            return jsonify({'success': False, 'message': f'Nie udało się wysłać komendy: {response}'}), 500

        return jsonify({'success': True, 'message': f'Serwo ustawione na {angle} stopni'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/stepper', methods=['POST'])
def control_stepper():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Brak połączenia szeregowego'}), 500

    try:
        data = request.json
        direction = data.get('direction')  # 'clockwise' lub 'counterclockwise'

        if direction not in ['clockwise', 'counterclockwise']:
            return jsonify({'success': False, 'message': 'Nieprawidłowy kierunek obrotu'}), 400

        # Wyślij komendę do Arduino przez gniazdo
        command = b'Silnik_ruch\n' if direction == 'clockwise' else b'Silnik_lewo\n'
        success, response = send_command_to_serial(command)

        if not success:
            return jsonify({'success': False, 'message': f'Nie udało się wysłać komendy: {response}'}), 500

        return jsonify({
            'success': True, 
            'message': f'Silnik obrócony o 500 kroków {"zgodnie z ruchem wskazówek zegara" if direction == "clockwise" else "przeciwnie do ruchu wskazówek zegara"}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/led', methods=['POST'])
def control_led():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Brak połączenia szeregowego'}), 500

    try:
        data = request.json
        state = data.get('state', 'off')  # Domyślnie 'off' jeśli nie określono

        # Konwersja stanu tekstowego na wartość logiczną
        is_on = state.lower() == 'on'

        # Wyślij komendę do Arduino przez gniazdo
        command = b'LED_ON\n' if is_on else b'LED_OFF\n'
        success, response = send_command_to_serial(command)

        if not success:
            return jsonify({'success': False, 'message': f'Nie udało się wysłać komendy: {response}'}), 500

        return jsonify({'success': True, 'message': f'LED {"WŁĄCZONY" if is_on else "WYŁĄCZONY"}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/motion', methods=['POST'])
def control_motion():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Brak połączenia szeregowego'}), 500

    try:
        data = request.json
        state = data.get('state', 'off')  # Domyślnie 'off' jeśli nie określono

        # Konwersja stanu tekstowego na wartość logiczną
        is_on = state.lower() == 'on'

        # Wyślij komendę do Arduino przez gniazdo
        command = b'MOTION_ON\n' if is_on else b'MOTION_OFF\n'
        success, response = send_command_to_serial(command)

        if not success:
            return jsonify({'success': False, 'message': f'Nie udało się wysłać komendy: {response}'}), 500

        return jsonify({'success': True, 'message': f'Monitoring ruchu {"WŁĄCZONY" if is_on else "WYŁĄCZONY"}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
