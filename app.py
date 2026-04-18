from flask import Flask, request, jsonify
import pandas as pd
import joblib

# Initialize the Flask App
app = Flask(__name__)

# Load the trained XGBoost model
try:
    model = joblib.load('xgboost_model.joblib')
except FileNotFoundError:
    model = None

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running", "model_loaded": model is not None})

@app.route('/predict', methods=['POST'])
def predict_failure():
    if not model:
        return jsonify({"error": "Model not found on server."}), 500

    try:
        # Get live data from the incoming request
        live_data = request.get_json()
        
        # Convert JSON to a DataFrame
        df = pd.DataFrame([live_data])
        
        # Perform Live Feature Engineering
        df['temperatureDiff'] = df['processTemperature'] - df['airTemperature']
        df['powerFactor'] = df['rotationalSpeed'] * df['torque']
        
        # Reorder columns to match training exactly
        features = ['airTemperature', 'processTemperature', 'rotationalSpeed', 'torque', 'toolWear', 'temperatureDiff', 'powerFactor']
        X_live = df[features]
        
        # Make Prediction using the 0.85 High-Precision Threshold
        probability = model.predict_proba(X_live)[0][1]
        is_critical = int(probability >= 0.85)
        
        # Generate the response
        response = {
            "server_id": live_data.get("server_id", "UNKNOWN"),
            "probability_of_failure": round(float(probability), 4),
            "system_status": "Critical Warning" if is_critical else "Normal",
            "recommended_action": "Dispatch technician immediately." if is_critical else "Continue standard monitoring."
        }
        
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    # Run the server on port 5000
    app.run(host='0.0.0.0', port=5000)