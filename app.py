import os
import uuid
import subprocess
from flask import Flask, request, send_file, jsonify

# Configuration
env_api_key = os.getenv('API_KEY', 'default_key')
UPLOAD_FOLDER = '/tmp/audio_files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)


def validate_api_key(req):
    # Check Bearer token
    auth = req.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1]
        return token == env_api_key
    return False


@app.route('/convert', methods=['POST'])
def convert_audio():
    # API key validation
    if not validate_api_key(request):
        return jsonify({'error': 'Unauthorized'}), 401

    # Check file presence
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    original_filename = file.filename
    name, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    # Accept .ogg and .oga
    if ext not in ['.ogg', '.oga']:
        return jsonify({'error': 'Invalid file type'}), 400

    # Generate unique names
    unique_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_FOLDER, unique_id + ext)
    output_path = os.path.join(UPLOAD_FOLDER, unique_id + '.wav')

    # Save and convert
    file.save(input_path)
    try:
        subprocess.run([
            'ffmpeg', '-i', input_path,
            '-acodec', 'pcm_s16le', '-ar', '16000', output_path
        ], check=True)
    except subprocess.CalledProcessError:
        return jsonify({'error': 'Conversion failed'}), 500

    # Return converted file
    return send_file(
        output_path,
        mimetype='audio/wav',
        as_attachment=True,
        download_name=name + '.wav'
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
