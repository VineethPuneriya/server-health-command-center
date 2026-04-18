# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for the Flask API
EXPOSE 5000

# Run the API using Gunicorn (production-grade server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]