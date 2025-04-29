from flask import Flask, request, send_file, jsonify
import os
import subprocess
import uuid
import shutil

app = Flask(__name__)

# Configuration
API_KEY = os.environ.get('API_KEY', 'default_key_please_change')
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def validate_api_key(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    
    # Expected format: "Bearer YOUR_API_KEY"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return False
    
    token = parts[1]
    return token == API_KEY

@app.route('/convert', methods=['POST'])
def convert_ogg_to_wav():
    # Validate API key
    if not validate_api_key(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if file is in the request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # If user does not select file, browser may submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Check file type
    if not file.filename.lower().endswith('.ogg'):
        return jsonify({'error': 'File must be OGG format'}), 400
    
    # Create unique filenames for input and output
    unique_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_input.ogg")
    output_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_output.wav")
    
    try:
        # Save the uploaded file
        file.save(input_path)
        
        # Convert OGG to WAV using FFmpeg
        command = [
            'ffmpeg', 
            '-i', input_path, 
            '-acodec', 'pcm_s16le',  # Standard WAV format
            '-ar', '44100',          # Sample rate: 44.1 kHz
            '-ac', '2',              # 2 channels (stereo)
            output_path
        ]
        
        # Execute the conversion
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Send the converted file
        return send_file(output_path, as_attachment=True, 
                         download_name=f"{os.path.splitext(file.filename)[0]}.wav")
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Clean up temporary files
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port)
