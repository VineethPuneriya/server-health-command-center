import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import classification_report, confusion_matrix

telemetryData = pd.read_csv("Data/ai4i2020.csv")

renameMap = {
    'Air temperature [K]': 'airTemperature',
    'Process temperature [K]': 'processTemperature',
    'Rotational speed [rpm]': 'rotationalSpeed',
    'Torque [Nm]': 'torque',
    'Tool wear [min]': 'toolWear'
}
telemetryData = telemetryData.rename(columns=renameMap)

telemetryData['temperatureDiff'] = telemetryData['processTemperature'] - telemetryData['airTemperature']
telemetryData['powerFactor'] = telemetryData['rotationalSpeed'] * telemetryData['torque']

featureCols = ['airTemperature', 'processTemperature', 'rotationalSpeed', 'torque', 'toolWear', 'temperatureDiff', 'powerFactor']
xFeatures = telemetryData[featureCols]
yTarget = telemetryData['Machine failure']

xTrain, xTest, yTrain, yTest = train_test_split(xFeatures, yTarget, test_size=0.2, random_state=42, stratify=yTarget)

healthyCount = len(yTrain[yTrain == 0])
failureCount = len(yTrain[yTrain == 1])
scaleWeight = healthyCount / failureCount

xgbModel = XGBClassifier(
    scale_pos_weight=scaleWeight,
    n_estimators=150,
    max_depth=4,
    learning_rate=0.1,
    random_state=42,
    eval_metric='logloss'
)

xgbModel.fit(xTrain, yTrain)

# --- PRECISION TUNING START ---
# Getting probabilities instead of classes
testProbs = xgbModel.predict_proba(xTest)[:, 1]

# Raising threshold to 0.85 to prioritize Precision
precisionThreshold = 0.85
testPredictions = (testProbs >= precisionThreshold).astype(int)

print(f"\n=== XGBOOST PRECISION-TUNED REPORT (Threshold: {precisionThreshold}) ===")
print(classification_report(yTest, testPredictions))
print("=== CONFUSION MATRIX ===")
print(confusion_matrix(yTest, testPredictions))
# --- PRECISION TUNING END ---

xgbModel.fit(xFeatures, yTarget)
finalProbs = xgbModel.predict_proba(xFeatures)[:, 1]
telemetryData['predictedFailure'] = (finalProbs >= precisionThreshold).astype(int)
telemetryData['systemStatus'] = telemetryData['predictedFailure'].map({0: 'Normal', 1: 'Critical Warning'})

def generateLog(row):
    if row['systemStatus'] == 'Normal':
        return "INFO: System operating within normal thermal and rotational parameters."
    if row['temperatureDiff'] > 10.5:
        return "CRITICAL ERROR: Thermal threshold exceeded. Cooling unit failure."
    if row['rotationalSpeed'] < 1300:
        return "WARNING: Fan rotational speed dropped below minimum RPM constraints."
    if row['powerFactor'] > 60000:
        return "CRITICAL WARNING: Mechanical stress detected. Torque/RPM mismatch."
    return "ERROR: Unidentified hardware failure detected in telemetry stream."

telemetryData['rawSystemLog'] = telemetryData.apply(generateLog, axis=1)

tfidfVector = TfidfVectorizer(stop_words='english', max_features=10)
textMatrix = tfidfVector.fit_transform(telemetryData['rawSystemLog'])
kmeansModel = KMeans(n_clusters=3, random_state=42)
telemetryData['nlpLogCategory'] = kmeansModel.fit_predict(textMatrix)

telemetryData.to_csv("Data/processed_server_health.csv", index=False)

import joblib
# Save the model to a file so the API can use it
joblib.dump(xgbModel, 'xgboost_model.joblib')
print("Model saved for production!")