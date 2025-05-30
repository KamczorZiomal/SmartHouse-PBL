from flask import Flask, render_template, jsonify, request
from models import db, SensorData
import socket

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensors.db'
db.init_app(app)

# Socket client configuration for communicating with serial_reader.py
HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

# Function to send commands to serial_reader.py via socket
def send_command_to_serial(command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(command)
            response = s.recv(1024)
            return True, response.decode('utf-8')
    except Exception as e:
        print(f"Error sending command to serial_reader.py: {e}")
        return False, str(e)

# Check if serial_reader.py is available
try:
    success, response = send_command_to_serial(b'CHECK_CONNECTION\n')
    if success and "Connection OK" in response:
        serial_available = True
        print("Successfully connected to serial_reader.py")
    else:
        serial_available = False
        print(f"Failed to connect to serial_reader.py: {response}")
except Exception as e:
    print(f"Error connecting to serial_reader.py: {e}")
    print("Make sure serial_reader.py is running before starting app.py")
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
    Endpoint to handle motion detection events.
    When motion is detected, this endpoint will trigger the buzzer for 1 second.
    """
    if not serial_available:
        return jsonify({'success': False, 'message': 'Serial connection not available'}), 500

    try:
        # Turn buzzer on
        success_on, response_on = send_command_to_serial(b'BUZZER_ON\n')
        if not success_on:
            return jsonify({'success': False, 'message': f'Failed to turn buzzer on: {response_on}'}), 500

        # Wait for 1 second
        import time
        time.sleep(1)

        # Turn buzzer off
        success_off, response_off = send_command_to_serial(b'BUZZER_OFF\n')
        if not success_off:
            return jsonify({'success': False, 'message': f'Failed to turn buzzer off: {response_off}'}), 500

        return jsonify({
            'success': True, 
            'message': 'Motion detected, buzzer triggered for 1 second'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/buzzer', methods=['POST'])
def control_buzzer():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Serial connection not available'}), 500

    try:
        data = request.json
        state = data.get('state', False)

        if state:
            command = b'BUZZER_ON\n'
            message = 'Buzzer turned ON'
        else:
            command = b'BUZZER_OFF\n'
            message = 'Buzzer turned OFF'

        success, response = send_command_to_serial(command)
        if not success:
            return jsonify({'success': False, 'message': f'Failed to send command: {response}'}), 500

        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/servo', methods=['POST'])
def control_servo():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Serial connection not available'}), 500

    try:
        data = request.json
        angle = data.get('angle', 90)

        # Ensure angle is within valid range
        angle = max(0, min(180, angle))

        # Send command to Arduino via socket
        command = f'SG90_{angle}\n'.encode()
        success, response = send_command_to_serial(command)

        if not success:
            return jsonify({'success': False, 'message': f'Failed to send command: {response}'}), 500

        return jsonify({'success': True, 'message': f'Servo set to {angle} degrees'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/control/stepper', methods=['POST'])
def control_stepper():
    if not serial_available:
        return jsonify({'success': False, 'message': 'Serial connection not available'}), 500

    try:
        data = request.json
        speed = data.get('speed', 0)

        # Ensure speed is within valid range (0-15 RPM for 28BYJ-48)
        speed = max(0, min(15, speed))

        # Send command to Arduino via socket
        command = f'STEPPER_{speed}\n'.encode()
        success, response = send_command_to_serial(command)

        if not success:
            return jsonify({'success': False, 'message': f'Failed to send command: {response}'}), 500

        return jsonify({'success': True, 'message': f'Stepper speed set to {speed} RPM'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
