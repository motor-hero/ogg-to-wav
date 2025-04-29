from flask import Flask, request, send_file, jsonify
import os
import subprocess
import uuid
import shutil
import logging
import mimetypes

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
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
    
    # If no API key is required, return True
    if API_KEY == 'default_key_please_change':
        return True
        
    return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # For POST requests, process the conversion
        return process_conversion()
    else:
        # For GET requests, show API info
        return jsonify({
            'service': 'Audio to WAV Converter',
            'endpoints': ['/', '/convert', '/health'],
            'version': '1.0.0'
        })

@app.route('/convert', methods=['POST'])
def convert():
    return process_conversion()

def process_conversion():
    logger.debug("Request headers: %s", request.headers)
    logger.debug("Request form: %s", request.form)
    logger.debug("Request files: %s", list(request.files.keys()))
    
    # Validate API key
    if not validate_api_key(request):
        logger.warning("Unauthorized access attempt")
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if file is in the request
    if not request.files:
        logger.warning("No files in the request")
        return jsonify({'error': 'No file part'}), 400
    
    # Try to find the file parameter
    file = None
    for file_key in request.files:
        file = request.files[file_key]
        logger.debug(f"Found file with key: {file_key}, filename: {file.filename}")
        break
    
    if not file:
        logger.warning("No file found in request.files")
        return jsonify({'error': 'No file part'}), 400
    
    # If user does not select file, browser may submit an empty part without filename
    if file.filename == '':
        logger.warning("Empty filename submitted")
        return jsonify({'error': 'No selected file'}), 400
    
    # Create unique filenames for input and output
    unique_id = str(uuid.uuid4())
    input_ext = os.path.splitext(file.filename)[1]  # Get original extension
    if not input_ext:
        input_ext = '.audio'  # Default extension if none provided
    
    input_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_input{input_ext}")
    output_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_output.wav")
    
    try:
        # Save the uploaded file
        file.save(input_path)
        logger.info(f"Saved input file: {input_path}")
        
        # Log file info
        logger.debug(f"File size: {os.path.getsize(input_path)} bytes")
        mime_type = mimetypes.guess_type(input_path)[0]
        logger.debug(f"Guessed MIME type: {mime_type}")
        
        # Try to identify file type using ffprobe
        try:
            probe_cmd = [
                'ffprobe', 
                '-v', 'error',
                '-show_entries', 'format=format_name',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            format_result = subprocess.run(probe_cmd, check=True, 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE)
            format_name = format_result.stdout.decode().strip()
            logger.debug(f"FFprobe identified format: {format_name}")
        except Exception as e:
            logger.warning(f"FFprobe couldn't identify format: {str(e)}")
        
        # Convert audio to WAV using FFmpeg
        command = [
            'ffmpeg', 
            '-y',  # Overwrite output files without asking
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
        
        # Check if output file was created and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Output file created successfully: {output_path}, size: {os.path.getsize(output_path)} bytes")
            # Send the converted file
            return send_file(output_path, as_attachment=True, 
                            download_name=f"{os.path.splitext(file.filename)[0]}.wav")
        else:
            logger.error(f"Output file not created or empty: {output_path}")
            return jsonify({'error': 'Conversion failed to create output file'}), 500
    
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"FFmpeg error: {error_msg}")
        return jsonify({'error': f"Conversion error: {error_msg}"}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Clean up temporary files
        try:
            logger.info("Cleaning up temporary files")
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path) and os.path.isfile(output_path):
                os.remove(output_path)
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")

@app.route('/health', methods=['GET'])
def health_check():
    # Check if FFmpeg is installed
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return jsonify({
            'status': 'healthy',
            'message': 'Service is running and FFmpeg is available'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'message': f'FFmpeg not available: {str(e)}'
        }), 500

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Starting Audio to WAV converter service on {host}:{port}")
    logger.info(f"API authentication is {'enabled' if API_KEY != 'default_key_please_change' else 'using default key (not recommended for production)'}")
    
    # Start the Flask application
    app.run(host=host, port=port, debug=True)
