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
def validate_api_key(request):
    # Check for X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key and api_key == API_KEY:
        return True
        
    # Check for Authorization Bearer token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        if token == API_KEY:
            return True
            
    return False

@app.route('/convert', methods=['POST'])
def convert_audio():
    # Check API key
    if not validate_api_key(request):
        return jsonify({'error': 'Unauthorized - Invalid API key'}), 401
    
    # Log request information for debugging
    app.logger.info(f"Request headers: {request.headers}")
    app.logger.info(f"Request form: {request.form}")
    app.logger.info(f"Request files: {request.files}")
    app.logger.info(f"Content-Type: {request.headers.get('Content-Type', 'Not provided')}")
    
    # Check if file is in request
    if 'file' not in request.files:
        # Try to handle raw binary data or different method
        app.logger.info("No 'file' in request.files - trying alternative methods")
        
        if request.data:
            try:
                # Generate a temporary file from the raw data
                unique_id = str(uuid.uuid4())
                input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.ogg")
                
                with open(input_file_path, 'wb') as f:
                    f.write(request.data)
                
                # Continue with the conversion process
                app.logger.info(f"Created temporary file from raw data: {input_file_path}")
                filename = "audio.ogg"  # Default name
                file_ext = ".ogg"
                return process_file(input_file_path, file_ext, filename)
            except Exception as e:
                app.logger.error(f"Error processing raw data: {str(e)}")
                return jsonify({'error': f'Error processing raw data: {str(e)}'}), 400
                
        # Check for data in form fields that might contain binary data
        app.logger.info(f"All form keys: {list(request.form.keys())}")
        for key in request.form.keys():
            app.logger.info(f"Found key in form: {key}")
            if request.form[key] and len(request.form[key]) > 100:  # Likely binary data
                try:
                    app.logger.info(f"Attempting to process form data from key: {key}")
                    # Try to save and process this data
                    unique_id = str(uuid.uuid4())
                    input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.ogg")
                    
                    with open(input_file_path, 'wb') as f:
                        f.write(request.form[key].encode('latin1') if isinstance(request.form[key], str) else request.form[key])
                    
                    app.logger.info(f"Created file from form data: {input_file_path}")
                    filename = "audio.ogg"
                    file_ext = ".ogg"
                    return process_file(input_file_path, file_ext, filename)
                except Exception as e:
                    app.logger.error(f"Error processing form data from {key}: {str(e)}")
                    continue
        
        # If content-type is multipart/form-data but no file field
        return jsonify({'error': 'No file provided. Ensure the file is sent with field name "file"'}), 400
    
    file = request.files['file']
    app.logger.info(f"Received file: {file.filename}, content_type: {file.content_type}")
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected or filename is empty'}), 400
    
    # Check file extension - more permissive check
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Save the file for inspection regardless of extension
    unique_id = str(uuid.uuid4())
    input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}{file_ext}")
    file.save(input_file_path)
    
    app.logger.info(f"Saved file to {input_file_path}")
    
    # Try to identify file type regardless of extension
    try:
        # Use ffmpeg/pydub to check if it's a valid audio file
        sound = AudioSegment.from_file(input_file_path)
        app.logger.info(f"Successfully loaded audio file with pydub: {input_file_path}")
        
        # If we get here, it's a valid audio file, proceed with conversion
        output_file_path = os.path.join(CONVERTED_FOLDER, f"{unique_id}.wav")
        sound.export(output_file_path, format="wav")
        
        app.logger.info(f"Successfully converted to WAV: {output_file_path}")
        
        # Clean up the input file
        os.remove(input_file_path)
        
        # Return the converted file
        return send_file(output_file_path, as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.wav")
    except Exception as e:
        # Clean up the input file
        if os.path.exists(input_file_path):
            os.remove(input_file_path)
            
        app.logger.error(f"Failed to process audio file: {str(e)}")
        return jsonify({'error': f'File must be OGG format. Error: {str(e)}'}), 400
    
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
