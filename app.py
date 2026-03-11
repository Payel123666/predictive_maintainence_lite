from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from models.predictor import MaintenancePredictor
from models.data_generator import SensorDataGenerator

app = Flask(__name__)

# Initialize predictor
predictor = MaintenancePredictor()

# Global variables to store data
sensor_data = None
equipment_list = []
last_update = None

def load_or_generate_data():
    """Load existing data or generate new one"""
    global sensor_data, equipment_list, last_update
    
    data_path = 'data/sensor_data.csv'
    
    # Check if data exists and is less than 1 hour old
    if os.path.exists(data_path):
        file_modified = datetime.fromtimestamp(os.path.getmtime(data_path))
        if datetime.now() - file_modified < timedelta(hours=1):
            try:
                sensor_data = pd.read_csv(data_path)
                sensor_data['timestamp'] = pd.to_datetime(sensor_data['timestamp'])
                print(f"✅ Loaded existing data from {data_path}")
            except Exception as e:
                print(f"⚠️ Error loading data: {e}")
                sensor_data = None
    
    # Generate new data if needed
    if sensor_data is None:
        print("🔄 Generating new sensor data...")
        generator = SensorDataGenerator()
        sensor_data = generator.generate_dataset(days=90, frequency='1H')
        sensor_data = generator.add_metadata_columns(sensor_data)
        
        # Save to CSV
        os.makedirs('data', exist_ok=True)
        sensor_data.to_csv(data_path, index=False)
        print(f"✅ Generated new data and saved to {data_path}")
    
    # Get unique equipment
    equipment_list = sensor_data['equipment_id'].unique().tolist()
    last_update = datetime.now()
    
    return sensor_data

# Load data on startup
sensor_data = load_or_generate_data()

@app.route('/')
def index():
    """Render the main dashboard"""
    return render_template('dashboard.html', 
                         equipment=equipment_list,
                         last_update=last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else 'N/A')

@app.route('/api/equipment/<equipment_id>')
def get_equipment_data(equipment_id):
    """Get data for specific equipment"""
    global sensor_data
    
    if sensor_data is None:
        sensor_data = load_or_generate_data()
    
    # Filter data for equipment
    equip_data = sensor_data[sensor_data['equipment_id'] == equipment_id].copy()
    
    if len(equip_data) == 0:
        return jsonify({'error': 'Equipment not found'}), 404
    
    # Get latest reading
    latest = equip_data.iloc[-1].to_dict()
    
    # Calculate trends
    temp_trend = calculate_trend(equip_data['temperature'].values[-168:])  # Last 7 days
    vib_trend = calculate_trend(equip_data['vibration'].values[-168:])
    eff_trend = calculate_trend(equip_data['efficiency'].values[-168:])
    
    # Make prediction
    prediction = predictor.predict_maintenance(equip_data)
    
    # Prepare historical data for charts
    historical = {
        'timestamps': equip_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M').tolist()[-336:],  # Last 14 days
        'temperature': equip_data['temperature'].tolist()[-336:],
        'vibration': equip_data['vibration'].tolist()[-336:],
        'efficiency': equip_data['efficiency'].tolist()[-336:],
        'health_score': equip_data['health_score'].tolist()[-336:],
        'failure_indicator': equip_data['failure_indicator'].tolist()[-336:]
    }
    
    # Get failure history
    failures = equip_data[equip_data['failure_indicator'] > 0]
    failure_history = []
    for _, row in failures.iterrows():
        if row['failure_type'] and pd.notna(row['failure_type']) and row['failure_type'] != '':
            failure_history.append({
                'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M'),
                'type': row['failure_type'],
                'severity': row['failure_indicator']
            })
    
    response = {
        'equipment_id': equipment_id,
        'equipment_name': latest.get('equipment_name', equipment_id),
        'equipment_type': latest.get('equipment_type', 'Unknown'),
        'current_temp': round(latest['temperature'], 1),
        'current_vibration': round(latest['vibration'], 3),
        'current_efficiency': round(latest['efficiency'], 1),
        'current_hours': round(latest['usage_hours'], 0),
        'health_score': round(latest['health_score'], 1),
        'risk_level': latest['risk_level'],
        'maintenance_recommendation': latest['maintenance_recommendation'],
        'temp_trend': temp_trend,
        'vib_trend': vib_trend,
        'eff_trend': eff_trend,
        'prediction': prediction,
        'historical': historical,
        'failure_history': failure_history,
        'last_maintenance': find_last_maintenance(equip_data),
        'days_until_maintenance': calculate_days_until_maintenance(equip_data)
    }
    
    return jsonify(response)

@app.route('/api/dashboard/summary')
def get_dashboard_summary():
    """Get summary of all equipment"""
    global sensor_data
    
    if sensor_data is None:
        sensor_data = load_or_generate_data()
    
    summary = []
    
    for equip_id in equipment_list:
        equip_data = sensor_data[sensor_data['equipment_id'] == equip_id]
        latest = equip_data.iloc[-1]
        
        # Calculate risk score
        risk_score = 100 - latest['health_score']
        
        # Count active failures
        active_failures = len(equip_data[
            (equip_data['failure_indicator'] > 50) & 
            (equip_data['timestamp'] > datetime.now() - timedelta(days=1))
        ])
        
        summary.append({
            'id': equip_id,
            'name': latest['equipment_name'],
            'type': latest['equipment_type'],
            'health_score': round(latest['health_score'], 1),
            'risk_level': latest['risk_level'],
            'temperature': round(latest['temperature'], 1),
            'vibration': round(latest['vibration'], 3),
            'efficiency': round(latest['efficiency'], 1),
            'active_failures': active_failures,
            'needs_attention': latest['risk_level'] in ['High', 'Critical', 'Extreme']
        })
    
    # Sort by health score (lowest first - most critical)
    summary.sort(key=lambda x: x['health_score'])
    
    # Calculate overall statistics
    stats = {
        'total_equipment': len(summary),
        'critical_count': sum(1 for e in summary if e['risk_level'] in ['Critical', 'Extreme']),
        'warning_count': sum(1 for e in summary if e['risk_level'] == 'High'),
        'healthy_count': sum(1 for e in summary if e['risk_level'] in ['Low', 'Medium']),
        'avg_health_score': round(np.mean([e['health_score'] for e in summary]), 1),
        'active_failures': sum(e['active_failures'] for e in summary)
    }
    
    return jsonify({
        'equipment': summary,
        'stats': stats,
        'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else 'N/A'
    })

@app.route('/api/equipment/<equipment_id>/predict', methods=['POST'])
def predict_equipment(equipment_id):
    """Get specific prediction for equipment"""
    global sensor_data
    
    if sensor_data is None:
        sensor_data = load_or_generate_data()
    
    equip_data = sensor_data[sensor_data['equipment_id'] == equipment_id]
    
    if len(equip_data) == 0:
        return jsonify({'error': 'Equipment not found'}), 404
    
    # Get prediction
    prediction = predictor.predict_maintenance(equip_data)
    
    return jsonify(prediction)

@app.route('/api/refresh-data')
def refresh_data():
    """Force refresh of sensor data"""
    global sensor_data, equipment_list, last_update
    
    # Delete old file to force regeneration
    data_path = 'data/sensor_data.csv'
    if os.path.exists(data_path):
        os.remove(data_path)
    
    sensor_data = load_or_generate_data()
    
    return jsonify({
        'success': True,
        'message': 'Data refreshed successfully',
        'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S')
    })

def calculate_trend(data, window=24):
    """Calculate trend direction"""
    if len(data) < window:
        return 'stable'
    
    recent = data[-window:]
    if len(recent) < 2:
        return 'stable'
    
    # Simple linear regression for trend
    x = np.arange(len(recent))
    z = np.polyfit(x, recent, 1)
    slope = z[0]
    
    if slope > 0.05:
        return 'increasing'
    elif slope < -0.05:
        return 'decreasing'
    else:
        return 'stable'

def find_last_maintenance(equip_data):
    """Find the last maintenance event"""
    maintenance = equip_data[equip_data['maintenance_event'] == 1]
    if len(maintenance) > 0:
        last = maintenance.iloc[-1]['timestamp']
        return last.strftime('%Y-%m-%d')
    return 'Never'

def calculate_days_until_maintenance(equip_data):
    """Calculate days until next maintenance"""
    latest = equip_data.iloc[-1]
    last_maintenance = find_last_maintenance(equip_data)
    
    if last_maintenance != 'Never':
        last_date = datetime.strptime(last_maintenance, '%Y-%m-%d')
        days_since = (datetime.now() - last_date).days
        # Assuming maintenance every 180 days
        days_until = max(0, 180 - days_since)
        return days_until
    return 180  # Default if no maintenance history

# if __name__ == '__main__':
#     app.run(debug=True, port=5001)

import os
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT
    app.run(host='0.0.0.0', port=port)