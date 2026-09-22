import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle

# Generate 400 realistic monitoring points along the Sikkim NH-10 corridor
np.random.seed(42)
n_samples = 400

latitudes = np.random.uniform(27.15, 27.40, n_samples)
longitudes = np.random.uniform(88.45, 88.65, n_samples)
slope = np.random.uniform(15, 60, n_samples)
elevation = np.random.uniform(300, 2200, n_samples)
soil_moisture = np.random.uniform(20, 85, n_samples)
historical_rainfall = np.random.uniform(10, 220, n_samples)

# Heuristic failure calculation based on slope and moisture
risk_score = (
    0.35 * (slope / 60) +
    0.40 * (historical_rainfall / 220) +
    0.15 * (soil_moisture / 85) +
    0.10 * (elevation / 2200)
)
labels = (risk_score > 0.55).astype(int)

df = pd.DataFrame({
    'latitude': latitudes,
    'longitude': longitudes,
    'slope': slope,
    'elevation': elevation,
    'soil_moisture': soil_moisture,
    'rainfall': historical_rainfall,
    'landslide': labels
})

# Train Random Forest
X = df[['slope', 'elevation', 'soil_moisture', 'rainfall']]
y = df['landslide']
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# Export trained model and baseline coordinates
with open('landslide_model.pkl', 'wb') as f:
    pickle.dump(model, f)

df[['latitude', 'longitude', 'slope', 'elevation', 'soil_moisture']].to_csv('sikkim_points.csv', index=False)
print("SUCCESS: Model saved as 'landslide_model.pkl' and points saved as 'sikkim_points.csv'")