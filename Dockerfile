FROM python:3.9-slim

# Install FFmpeg and other dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000

# Create app directory with proper permissions
WORKDIR /app
RUN mkdir -p /tmp/audio_files && chmod 777 /tmp/audio_files

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create a non-root user to run the application
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app /tmp/audio_files

# Switch to non-root user
USER appuser

# Expose port for the API
EXPOSE 5000

# Add healthcheck to verify the service is running
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Command to run the application
CMD ["python", "app.py"]
