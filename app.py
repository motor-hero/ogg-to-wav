import os
import uuid
from flask import Flask, request, jsonify, send_file
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY', 'your-default-api-key')

app = Flask(__name__)

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
    
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file extension
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in ['.ogg', '.oga']:
        return jsonify({'error': 'Invalid file format. Only .ogg and .oga files are supported'}), 400
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}{file_ext}")
    output_file_path = os.path.join(CONVERTED_FOLDER, f"{unique_id}.wav")
    
    # Save the uploaded file
    file.save(input_file_path)
    
    try:
        # Convert to WAV
        sound = AudioSegment.from_file(input_file_path)
        sound.export(output_file_path, format="wav")
        
        # Clean up the input file
        os.remove(input_file_path)
        
        # Return the converted file
        return send_file(output_file_path, as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.wav")
    
    except Exception as e:
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
