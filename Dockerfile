FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY .env.example .env.example

# Create directory for file processing
RUN mkdir -p /app/uploads /app/converted

# Expose API port
EXPOSE 5000

# Run service
CMD ["python", "app.py"]
