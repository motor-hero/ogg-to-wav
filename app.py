from flask import Flask, request, send_file, jsonify
import os
import subprocess
import uuid
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
API_KEY = os.environ.get('API_KEY', 'default_key_please_change')
UPLOAD_FOLDER = '/tmp/audio_files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def validate_api_key(request):
    # Method 1: Check Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header:
        # Expected format: "Bearer YOUR_API_KEY"
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            token = parts[1]
            return token == API_KEY
    
    # Method 2: Check for API key in query parameters
    token = request.args.get('api_key')
    if token and token == API_KEY:
        return True
    
    # Method 3: Check for API key in form data
    token = request.form.get('api_key')
    if token and token == API_KEY:
        return True
    
    return False

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'service': 'OGG to WAV Converter',
        'endpoints': ['/convert', '/health'],
        'version': '1.0.0'
    })

@app.route('/convert', methods=['POST'])
def convert_ogg_to_wav():
    logger.info("Received conversion request")
    
    # Validate API key
    if not validate_api_key(request):
        logger.warning("Unauthorized access attempt")
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if file is in the request
    if 'file' not in request.files:
        logger.warning("No file part in the request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # If user does not select file, browser may submit an empty part without filename
    if file.filename == '':
        logger.warning("Empty filename submitted")
        return jsonify({'error': 'No selected file'}), 400
    
    # Check file type
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.ogg') or filename_lower.endswith('.oga')):
        logger.warning(f"Invalid file format: {file.filename}")
        return jsonify({'error': 'File must be OGG or OGA format'}), 400
    
    # Create unique filenames for input and output
    unique_id = str(uuid.uuid4())
    input_ext = os.path.splitext(file.filename)[1]  # Get original extension (.ogg or .oga)
    input_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_input{input_ext}")
    output_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_output.wav")
    
    try:
        # Save the uploaded file
        file.save(input_path)
        logger.info(f"Saved input file: {input_path}")
        
        # Convert OGG/OGA to WAV using FFmpeg
        command = [
            'ffmpeg', 
            '-i', input_path, 
            '-acodec', 'pcm_s16le',  # Standard WAV format
            '-ar', '44100',          # Sample rate: 44.1 kHz
            '-ac', '2',              # 2 channels (stereo)
            output_path
        ]
        
        # Execute the conversion
        logger.info(f"Running FFmpeg command: {' '.join(command)}")
        process = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Conversion completed successfully")
        
        # Send the converted file
        return send_file(output_path, as_attachment=True, 
                         download_name=f"{os.path.splitext(file.filename)[0]}.wav")
    
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        return jsonify({'error': f"Conversion error: {e.stderr.decode() if e.stderr else str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Clean up temporary files
        logger.info("Cleaning up temporary files")
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
