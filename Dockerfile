FROM python:3.11-slim

# Install ffmpeg for audio conversion
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application code
COPY app.py .

# Install Python dependencies
RUN pip install --no-cache-dir flask

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
