from flask import Flask, render_template, jsonify
from models import db, SensorData

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensors.db'
db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(20).all()
    result = [{
        'timestamp': entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'temperature': entry.temperature,
        'humidity': entry.humidity,
        'air_quality': entry.air_quality,
        'light_percent': entry.light_percent,
        'lux': entry.lux
    } for entry in reversed(data)]  # reversed to show oldest first
    return jsonify(result)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
