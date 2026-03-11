import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

class SensorDataGenerator:
    def __init__(self):
        """Initialize the sensor data generator"""
        self.equipment_configs = {
            'HVAC-001': {
                'name': 'HVAC System - Building A',
                'type': 'HVAC',
                'base_temp': 65,
                'temp_range': 15,
                'temp_threshold': 85,
                'base_vibration': 0.1,
                'vibration_range': 0.3,
                'vibration_threshold': 0.8,
                'base_hours': 1000,
                'hours_per_day': 16,
                'efficiency_base': 95,
                'efficiency_drop_rate': 0.02,
                'failure_probability': 0.001,
                'maintenance_schedule': 180
            },
            'PUMP-002': {
                'name': 'Water Pump - Station 2',
                'type': 'Pump',
                'base_temp': 70,
                'temp_range': 20,
                'temp_threshold': 95,
                'base_vibration': 0.15,
                'vibration_range': 0.4,
                'vibration_threshold': 1.0,
                'base_hours': 500,
                'hours_per_day': 20,
                'efficiency_base': 90,
                'efficiency_drop_rate': 0.03,
                'failure_probability': 0.002,
                'maintenance_schedule': 120
            },
            'MOTOR-003': {
                'name': 'Electric Motor - Line 3',
                'type': 'Motor',
                'base_temp': 75,
                'temp_range': 25,
                'temp_threshold': 100,
                'base_vibration': 0.2,
                'vibration_range': 0.5,
                'vibration_threshold': 1.2,
                'base_hours': 2000,
                'hours_per_day': 24,
                'efficiency_base': 88,
                'efficiency_drop_rate': 0.025,
                'failure_probability': 0.0015,
                'maintenance_schedule': 150
            },
            'GEN-004': {
                'name': 'Generator - Backup',
                'type': 'Generator',
                'base_temp': 80,
                'temp_range': 30,
                'temp_threshold': 105,
                'base_vibration': 0.25,
                'vibration_range': 0.6,
                'vibration_threshold': 1.5,
                'base_hours': 500,
                'hours_per_day': 8,
                'efficiency_base': 92,
                'efficiency_drop_rate': 0.015,
                'failure_probability': 0.0005,
                'maintenance_schedule': 365
            },
            'COMP-005': {
                'name': 'Air Compressor - Shop Floor',
                'type': 'Compressor',
                'base_temp': 85,
                'temp_range': 20,
                'temp_threshold': 110,
                'base_vibration': 0.3,
                'vibration_range': 0.7,
                'vibration_threshold': 1.8,
                'base_hours': 800,
                'hours_per_day': 12,
                'efficiency_base': 85,
                'efficiency_drop_rate': 0.04,
                'failure_probability': 0.0025,
                'maintenance_schedule': 90
            }
        }
        
        self.failure_modes = {
            'bearing_failure': {
                'temp_effect': 1.3,
                'vibration_effect': 2.5,
                'efficiency_effect': 0.7,
                'duration': [12, 48]
            },
            'overheating': {
                'temp_effect': 1.8,
                'vibration_effect': 1.2,
                'efficiency_effect': 0.6,
                'duration': [6, 24]
            },
            'imbalance': {
                'temp_effect': 1.1,
                'vibration_effect': 3.0,
                'efficiency_effect': 0.8,
                'duration': [24, 72]
            },
            'misalignment': {
                'temp_effect': 1.2,
                'vibration_effect': 2.2,
                'efficiency_effect': 0.75,
                'duration': [48, 120]
            },
            'lubrication_issue': {
                'temp_effect': 1.4,
                'vibration_effect': 1.5,
                'efficiency_effect': 0.85,
                'duration': [72, 168]
            }
        }

    def generate_dataset(self, days=90, frequency='1H'):
        """Generate complete dataset for all equipment"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        timestamps = pd.date_range(start=start_date, end=end_date, freq=frequency)
        
        print(f"Generating data for {days} days ({len(timestamps)} points per equipment)")
        
        all_data = []
        
        for equip_id, config in self.equipment_configs.items():
            df = self._generate_equipment_data(equip_id, config, timestamps)
            all_data.append(df)
        
        return pd.concat(all_data, ignore_index=True)

    def _generate_equipment_data(self, equip_id, config, timestamps):
        """Generate data for single equipment"""
        
        n_points = len(timestamps)
        
        # Initialize arrays
        temperatures = []
        vibrations = []
        usage_hours = []
        efficiencies = []
        maintenance_events = []
        failure_indicators = []
        failure_types = []
        
        current_hours = config['base_hours']
        days_since_maintenance = 0
        current_failure = None
        failure_start = None
        failure_duration = 0
        
        for i, ts in enumerate(timestamps):
            # Update usage hours
            if i > 0:
                hours_passed = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
                current_hours += hours_passed * (config['hours_per_day'] / 24)
            
            usage_hours.append(current_hours)
            
            # Update days since maintenance
            days_since_maintenance += 1/24
            
            # Check for maintenance
            if days_since_maintenance >= config['maintenance_schedule']:
                maintenance_events.append(1)
                days_since_maintenance = 0
                current_efficiency = config['efficiency_base']
            else:
                maintenance_events.append(0)
            
            # Calculate base values
            base_temp = config['base_temp']
            temp_variation = np.random.normal(0, config['temp_range']/3)
            base_vibration = config['base_vibration']
            vibration_variation = np.random.normal(0, config['vibration_range']/3)
            
            # Time effects
            hour = ts.hour
            day_of_year = ts.timetuple().tm_yday
            
            time_factor = np.sin((hour - 14) * np.pi / 12) * 0.2
            seasonal_factor = np.sin((day_of_year - 172) * 2 * np.pi / 365) * 0.15
            
            # Degradation
            degradation = (current_hours / config['base_hours']) * config['efficiency_drop_rate']
            
            # Check for failure
            if i > n_points // 2 and current_failure is None:
                if np.random.random() < config['failure_probability']:
                    current_failure = random.choice(list(self.failure_modes.keys()))
                    failure_start = i
                    failure_duration = random.randint(
                        self.failure_modes[current_failure]['duration'][0],
                        self.failure_modes[current_failure]['duration'][1]
                    )
                    failure_types.append(current_failure)
            
            # Apply failure effects
            if current_failure and i - failure_start < failure_duration:
                progress = (i - failure_start) / failure_duration
                effects = self.failure_modes[current_failure]
                
                temp_mult = 1 + (effects['temp_effect'] - 1) * progress
                vib_mult = 1 + (effects['vibration_effect'] - 1) * progress
                eff_mult = max(0.3, 1 - (1 - effects['efficiency_effect']) * progress)
                
                failure_indicators.append(progress * 100)
            else:
                if current_failure:
                    current_failure = None
                failure_indicators.append(0)
            
            # Calculate final values
            temp_mult = 1 + (failure_indicators[-1] / 100 * 0.5)
            vib_mult = 1 + (failure_indicators[-1] / 100 * 1.5)
            
            temp = (base_temp + temp_variation) * temp_mult + time_factor * 10 + seasonal_factor * 15
            vibration = (base_vibration + vibration_variation) * vib_mult
            efficiency = config['efficiency_base'] - degradation * current_hours - failure_indicators[-1] * 0.3
            
            # Add noise
            temp += np.random.normal(0, 1)
            vibration += np.random.normal(0, 0.05)
            efficiency += np.random.normal(0, 0.5)
            
            # Clamp values
            temp = max(40, min(150, temp))
            vibration = max(0, min(3.0, vibration))
            efficiency = max(50, min(100, efficiency))
            
            temperatures.append(round(temp, 1))
            vibrations.append(round(vibration, 3))
            efficiencies.append(round(efficiency, 1))
        
        # Create dataframe
        df = pd.DataFrame({
            'timestamp': timestamps,
            'equipment_id': equip_id,
            'equipment_name': config['name'],
            'equipment_type': config['type'],
            'temperature': temperatures,
            'vibration': vibrations,
            'usage_hours': [round(h, 1) for h in usage_hours],
            'efficiency': efficiencies,
            'maintenance_event': maintenance_events,
            'failure_indicator': [round(f, 1) for f in failure_indicators],
            'failure_type': failure_types + [''] * (n_points - len(failure_types))
        })
        
        return df

    def add_metadata_columns(self, df):
        """Add additional metadata columns"""
        
        # Time features
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        df['month'] = pd.to_datetime(df['timestamp']).dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Health score (0-100, higher is better)
        health_scores = []
        for _, row in df.iterrows():
            equip_id = row['equipment_id']
            config = self.equipment_configs.get(equip_id, {})
            
            if config:
                temp_score = max(0, 100 - (max(0, row['temperature'] - config['base_temp']) / config['temp_threshold'] * 200))
                vib_score = max(0, 100 - (row['vibration'] / config['vibration_threshold'] * 100))
                eff_score = row['efficiency']
                
                health_score = (temp_score + vib_score + eff_score) / 3
                health_scores.append(round(health_score, 1))
            else:
                health_scores.append(50)
        
        df['health_score'] = health_scores
        
        # Risk level
        conditions = [
            (df['health_score'] >= 80),
            (df['health_score'] >= 60),
            (df['health_score'] >= 40),
            (df['health_score'] >= 20),
            (df['health_score'] < 20)
        ]
        choices = ['Low', 'Medium', 'High', 'Critical', 'Extreme']
        df['risk_level'] = np.select(conditions, choices, default='Unknown')
        
        # Maintenance recommendation
        recommendations = []
        for _, row in df.iterrows():
            if row['failure_indicator'] > 50:
                recommendations.append('Immediate maintenance required!')
            elif row['risk_level'] in ['Critical', 'Extreme']:
                recommendations.append('Schedule maintenance within 24 hours')
            elif row['risk_level'] == 'High':
                recommendations.append('Schedule maintenance within 7 days')
            elif row['risk_level'] == 'Medium':
                recommendations.append('Monitor closely')
            else:
                recommendations.append('Normal operation')
        
        df['maintenance_recommendation'] = recommendations
        
        return df