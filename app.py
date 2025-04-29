import os
import uuid
import logging
from flask import Flask, request, jsonify, send_file
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY', 'your-default-api-key')

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Directory paths
UPLOAD_FOLDER = '/app/uploads'
CONVERTED_FOLDER = '/app/converted'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# Validate API key
def validate_api_key(request_api_key):
    return request_api_key == API_KEY

@app.route('/convert', methods=['POST'])
def convert_audio():
    # Check API key
    api_key = request.headers.get('X-API-Key')
    
    if not api_key or not validate_api_key(api_key):
        return jsonify({'error': 'Unauthorized - Invalid API key'}), 401
    
    # Log request information for debugging
    app.logger.info(f"Request form: {request.form}")
    app.logger.info(f"Request files: {request.files}")
    
    # Check if file is in request
    if 'file' not in request.files:
        # Check if the file was sent as binary data directly
        if request.data:
            try:
                # Generate a temporary file from the raw data
                unique_id = str(uuid.uuid4())
                input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.ogg")
                
                with open(input_file_path, 'wb') as f:
                    f.write(request.data)
                
                # Continue with the conversion process
                filename = "audio.ogg"  # Default name
                file_ext = ".ogg"
                return process_file(input_file_path, file_ext, filename)
            except Exception as e:
                return jsonify({'error': f'Error processing raw data: {str(e)}'}), 400
        # If content-type is multipart/form-data but no file field
        return jsonify({'error': 'No file provided. Ensure the file is sent with field name "file"'}), 400
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected or filename is empty'}), 400
    
    # Check file extension
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in ['.ogg', '.oga']:
        return jsonify({'error': 'Invalid file format. Only .ogg and .oga files are supported'}), 400
    
    return process_file(file, file_ext, filename)

def process_file(file, file_ext, filename):
    """Process the audio file conversion"""
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Handle both file object and file path
    if isinstance(file, str):
        # File is already saved at this path
        input_file_path = file
    else:
        # Save the uploaded file
        input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}{file_ext}")
        file.save(input_file_path)
    
    output_file_path = os.path.join(CONVERTED_FOLDER, f"{unique_id}.wav")
    
    try:
        # Convert to WAV
        app.logger.info(f"Converting file: {input_file_path} to {output_file_path}")
        sound = AudioSegment.from_file(input_file_path)
        sound.export(output_file_path, format="wav")
        
        # Clean up the input file
        os.remove(input_file_path)
        
        # Return the converted file
        return send_file(output_file_path, as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.wav")
    
    except Exception as e:
        app.logger.error(f"Conversion error: {str(e)}")
        # Clean up in case of error
        if os.path.exists(input_file_path):
            os.remove(input_file_path)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
        
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
