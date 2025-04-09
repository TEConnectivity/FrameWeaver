FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# # Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    npm mosquitto \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code 
COPY . /app

# Copy mosquitto conf to allow for 0.0.0.0 listening
COPY ./app/lib/mosquitto.conf /etc/mosquitto.conf

# Expose necessary ports (for MQTT, HTTP)
EXPOSE 1883 8080

# Set environment variable for Flask to run in production mode
ENV FLASK_ENV=production

# Set the working directory
WORKDIR /app/app

LABEL org.opencontainers.image.source=https://github.com/TEConnectivity/FrameWeaver
LABEL org.opencontainers.image.description="FrameWeaver"
LABEL org.opencontainers.image.licenses=MIT

# Command to run the app
CMD ["python", "main.py"]
