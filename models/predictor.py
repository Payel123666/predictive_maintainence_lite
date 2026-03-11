import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime, timedelta
import os

class MaintenancePredictor:
    def __init__(self):
        """Initialize the predictor"""
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = 'models/trained_model.pkl'
        
        # Try to load existing model
        if os.path.exists(self.model_path):
            try:
                self.load_model()
                print("✅ Loaded existing model")
            except:
                print("⚠️ Could not load model, will train on the fly")
    
    def extract_features(self, df):
        """Extract features from time series data"""
        if len(df) < 24:
            return None
        
        # Use last 24 hours for features
        recent = df.iloc[-24:]
        
        features = {
            # Temperature features
            'temp_mean': recent['temperature'].mean(),
            'temp_std': recent['temperature'].std(),
            'temp_max': recent['temperature'].max(),
            'temp_min': recent['temperature'].min(),
            'temp_trend': self._calculate_trend(recent['temperature'].values),
            
            # Vibration features
            'vib_mean': recent['vibration'].mean(),
            'vib_std': recent['vibration'].std(),
            'vib_max': recent['vibration'].max(),
            'vib_trend': self._calculate_trend(recent['vibration'].values),
            
            # Efficiency features
            'eff_mean': recent['efficiency'].mean(),
            'eff_std': recent['efficiency'].std(),
            'eff_min': recent['efficiency'].min(),
            'eff_trend': self._calculate_trend(recent['efficiency'].values),
            
            # Usage features
            'hours_total': recent['usage_hours'].iloc[-1],
            'hours_increase': recent['usage_hours'].iloc[-1] - recent['usage_hours'].iloc[0],
            
            # Rate of change
            'temp_rate': (recent['temperature'].iloc[-1] - recent['temperature'].iloc[0]) / 24,
            'vib_rate': (recent['vibration'].iloc[-1] - recent['vibration'].iloc[0]) / 24,
            
            # Health indicators
            'health_score': recent['health_score'].iloc[-1] if 'health_score' in recent.columns else 50,
            'failure_indicator': recent['failure_indicator'].max() if 'failure_indicator' in recent.columns else 0
        }
        
        return features
    
    def _calculate_trend(self, data):
        """Calculate trend slope"""
        if len(data) < 2:
            return 0
        x = np.arange(len(data))
        z = np.polyfit(x, data, 1)
        return z[0]
    
    def predict_maintenance(self, df):
        """Predict maintenance needs"""
        if len(df) < 24:
            return self._rule_based_prediction(df)
        
        # Extract features
        features = self.extract_features(df)
        
        if features is None:
            return self._rule_based_prediction(df)
        
        # Calculate risk score based on multiple factors
        risk_score = 0
        reasons = []
        
        # Temperature risk
        temp = features['temp_mean']
        temp_max = features['temp_max']
        if temp_max > 90:
            risk_score += 30
            reasons.append(f"High temperature ({temp_max:.1f}°F)")
        elif temp_max > 80:
            risk_score += 15
            reasons.append(f"Elevated temperature ({temp_max:.1f}°F)")
        
        # Vibration risk
        vib = features['vib_mean']
        vib_max = features['vib_max']
        if vib_max > 1.0:
            risk_score += 25
            reasons.append(f"High vibration ({vib_max:.3f}g)")
        elif vib_max > 0.7:
            risk_score += 10
            reasons.append(f"Elevated vibration ({vib_max:.3f}g)")
        
        # Efficiency risk
        eff = features['eff_mean']
        if eff < 70:
            risk_score += 25
            reasons.append(f"Low efficiency ({eff:.1f}%)")
        elif eff < 80:
            risk_score += 10
            reasons.append(f"Decreasing efficiency ({eff:.1f}%)")
        
        # Trends
        if features['temp_trend'] > 0.5:
            risk_score += 10
            reasons.append("Temperature rising rapidly")
        
        if features['vib_trend'] > 0.05:
            risk_score += 15
            reasons.append("Vibration increasing")
        
        if features['eff_trend'] < -0.5:
            risk_score += 15
            reasons.append("Efficiency dropping")
        
        # Usage hours
        if features['hours_total'] > 8000:
            risk_score += 10
            reasons.append("High usage hours")
        
        # Failure history
        if features['failure_indicator'] > 0:
            risk_score += features['failure_indicator'] / 2
            reasons.append("Previous failure detected")
        
        # Cap risk score
        risk_score = min(100, risk_score)
        
        # Determine priority and days to maintenance
        if risk_score >= 80:
            priority = 'Critical'
            days = 0
            recommendation = 'IMMEDIATE MAINTENANCE REQUIRED'
        elif risk_score >= 60:
            priority = 'High'
            days = 7
            recommendation = 'Schedule maintenance within 7 days'
        elif risk_score >= 40:
            priority = 'Medium'
            days = 30
            recommendation = 'Schedule maintenance within 30 days'
        elif risk_score >= 20:
            priority = 'Low'
            days = 90
            recommendation = 'Monitor regularly'
        else:
            priority = 'Normal'
            days = 180
            recommendation = 'No action needed'
        
        return {
            'risk_score': round(risk_score, 1),
            'priority': priority,
            'days_to_maintenance': days,
            'recommendation': recommendation,
            'reasons': reasons[:3],  # Top 3 reasons
            'confidence': self._calculate_confidence(features)
        }
    
    def _rule_based_prediction(self, df):
        """Fallback rule-based prediction"""
        latest = df.iloc[-1]
        
        risk_score = 100 - latest['health_score']
        
        if risk_score >= 80:
            priority = 'Critical'
            days = 0
            rec = 'IMMEDIATE MAINTENANCE REQUIRED'
        elif risk_score >= 60:
            priority = 'High'
            days = 7
            rec = 'Schedule maintenance within 7 days'
        elif risk_score >= 40:
            priority = 'Medium'
            days = 30
            rec = 'Schedule maintenance within 30 days'
        elif risk_score >= 20:
            priority = 'Low'
            days = 90
            rec = 'Monitor regularly'
        else:
            priority = 'Normal'
            days = 180
            rec = 'No action needed'
        
        return {
            'risk_score': round(risk_score, 1),
            'priority': priority,
            'days_to_maintenance': days,
            'recommendation': rec,
            'reasons': ['Based on current health score'],
            'confidence': 'Medium'
        }
    
    def _calculate_confidence(self, features):
        """Calculate confidence in prediction"""
        # More data and clearer signals = higher confidence
        confidence = 'Medium'
        
        if features['failure_indicator'] > 50:
            confidence = 'High'
        elif features['temp_trend'] > 1 or features['vib_trend'] > 0.1:
            confidence = 'High'
        elif features['health_score'] < 30:
            confidence = 'High'
        elif features['health_score'] > 80:
            confidence = 'High'  # Confident it's healthy
        
        return confidence
    
    def train_model(self, training_data):
        """Train ML model (for future enhancement)"""
        # This would be implemented with actual training data
        pass
    
    def save_model(self):
        """Save trained model"""
        if self.model:
            joblib.dump({
                'model': self.model,
                'scaler': self.scaler
            }, self.model_path)
    
    def load_model(self):
        """Load trained model"""
        data = joblib.load(self.model_path)
        self.model = data['model']
        self.scaler = data['scaler']