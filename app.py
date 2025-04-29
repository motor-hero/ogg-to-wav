import os
import uuid
import subprocess
import tempfile
import requests
from flask import Flask, request, send_file, jsonify

# Configuration
env_api_key = os.getenv('API_KEY', 'default_key')

app = Flask(__name__)


def validate_api_key(req):
    auth = req.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1]
        return token == env_api_key
    return False

@app.route('/convert', methods=['POST'])
def convert_audio_url():
    # API key validation
    if not validate_api_key(request):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No url provided'}), 400

    url = data['url']
    # Create temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Determine filename from URL
        filename = os.path.basename(url.split('?')[0]) or str(uuid.uuid4())
        name, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext not in ['.ogg', '.oga']:
            return jsonify({'error': 'URL must point to an OGG or OGA file'}), 400

        input_path = os.path.join(tmpdir, filename)
        output_path = os.path.join(tmpdir, name + '.wav')

        # Download file
        try:
            resp = requests.get(url, stream=True, timeout=15)
            resp.raise_for_status()
            with open(input_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            return jsonify({'error': 'Failed to download file', 'details': str(e)}), 400

        # Convert using ffmpeg
        try:
            subprocess.run([
                'ffmpeg', '-y', '-i', input_path,
                '-acodec', 'pcm_s16le', '-ar', '16000', output_path
            ], check=True)
        except subprocess.CalledProcessError:
            return jsonify({'error': 'Conversion failed'}), 500

        # Send back wav
        return send_file(
            output_path,
            mimetype='audio/wav',
            as_attachment=True,
            download_name=name + '.wav'
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
