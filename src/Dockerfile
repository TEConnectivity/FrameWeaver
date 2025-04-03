FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl-dev mosquitto \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code 
COPY . /app

# Expose necessary ports (for MQTT, HTTP)
EXPOSE 1883 8080

# Set environment variable for Flask to run in production mode
ENV FLASK_ENV=production

# Command to run the app (ensure it's using your app's entry point)
CMD ["python", "app.py"]
