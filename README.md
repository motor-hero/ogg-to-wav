# OGG to WAV Converter API

A simple Docker-based service that converts OGG/OGA audio files to WAV format. This service is designed to be lightweight and can easily integrate with n8n workflows.

## Features

- API key authentication for secure access
- Converts OGG/OGA files to WAV format
- Simple REST API
- Dockerized for easy deployment
- Health check endpoint

## Setup Instructions

### Build the Docker Image

```bash
docker build -t ogg-to-wav-converter .
```

### Run the Container

```bash
docker run -d -p 5000:5000 --env-file .env --name ogg-converter ogg-to-wav-converter
```

Make sure to create a `.env` file based on the provided `.env.example` with your secure API key.

## API Usage

### Convert an OGG file to WAV

```bash
curl -X POST -H "X-API-Key: your-api-key-here" -F "file=@your-file.ogg" http://localhost:5000/convert -o converted-file.wav
```

### Health Check

```bash
curl http://localhost:5000/health
```

## Using with n8n

1. Set up an HTTP Request node in n8n.
2. Configure it as a POST request to `http://your-docker-host:5000/convert`.
3. Add the header `X-API-Key` with your API key.
4. Set up binary data handling for the OGG file input.
5. Connect to your workflow to process the resulting WAV file.

## Environment Variables

- `API_KEY`: Your secure API key for authentication
- `PORT`: Port to run the service on (default: 5000)
