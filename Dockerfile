FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY .env.example .env

# Create directory for file processing with proper permissions
RUN mkdir -p /app/uploads /app/converted && \
    chmod 777 /app/uploads /app/converted

# Expose API port
EXPOSE 5000

# Set environment variables for better Python logging
ENV PYTHONUNBUFFERED=1

# Run service with logging
CMD ["python", "-u", "app.py"]
