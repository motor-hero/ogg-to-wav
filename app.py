import os
import uuid
import logging
import mimetypes
from flask import Flask, request, jsonify, send_file
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY', 'your-default-api-key')

# Configure maximum logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

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

def write_debug_file(data, filename):
    """Write data to a debug file for inspection"""
    debug_path = os.path.join(UPLOAD_FOLDER, f"debug_{filename}")
    try:
        with open(debug_path, 'wb') as f:
            if isinstance(data, str):
                f.write(data.encode('utf-8', errors='replace'))
            else:
                f.write(data)
        app.logger.debug(f"Wrote debug file: {debug_path}")
        return debug_path
    except Exception as e:
        app.logger.error(f"Failed to write debug file: {str(e)}")
        return None

@app.route('/convert', methods=['POST'])
def convert_audio():
    # Check API key
    if not validate_api_key(request):
        return jsonify({'error': 'Unauthorized - Invalid API key'}), 401
    
    # Extreme debugging
    app.logger.debug(f"Request method: {request.method}")
    app.logger.debug(f"Request headers: {dict(request.headers)}")
    app.logger.debug(f"Request form keys: {list(request.form.keys())}")
    app.logger.debug(f"Request files keys: {list(request.files.keys())}")
    app.logger.debug(f"Content-Type: {request.headers.get('Content-Type', 'Not provided')}")
    app.logger.debug(f"Content-Length: {request.headers.get('Content-Length', 'Not provided')}")
    
    # Save raw request data for debugging
    if request.data:
        debug_file = write_debug_file(request.data, "raw_request.bin")
        app.logger.debug(f"Raw request data saved to: {debug_file}")
    
    # Universal approach - try all possible ways to get the file data
    try:
        # Method 1: Check if file is in request.files
        if 'file' in request.files:
            app.logger.debug("Found 'file' in request.files")
            file = request.files['file']
            app.logger.debug(f"File info: filename={file.filename}, content_type={file.content_type}")
            
            # Save file content for debugging
            file_content = file.read()
            debug_file = write_debug_file(file_content, f"file_content_{secure_filename(file.filename)}")
            app.logger.debug(f"File content saved to: {debug_file}")
            
            # Reset file pointer for further processing
            file.seek(0)
            
            # Process the file
            unique_id = str(uuid.uuid4())
            filename = secure_filename(file.filename) if file.filename else "audio.ogg"
            file_ext = os.path.splitext(filename)[1].lower() or ".ogg"
            input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}{file_ext}")
            file.save(input_file_path)
            
            return process_and_convert(input_file_path, unique_id, filename)
            
        # Method 2: Check for any file in request.files (different name)
        if request.files:
            app.logger.debug(f"No 'file' key, but found files: {list(request.files.keys())}")
            
            # Try the first file
            first_key = list(request.files.keys())[0]
            file = request.files[first_key]
            app.logger.debug(f"Using file with key '{first_key}': filename={file.filename}, content_type={file.content_type}")
            
            # Save file content for debugging
            file_content = file.read()
            debug_file = write_debug_file(file_content, f"alt_file_content_{secure_filename(file.filename)}")
            app.logger.debug(f"Alternative file content saved to: {debug_file}")
            
            # Reset file pointer for further processing
            file.seek(0)
            
            # Process the file
            unique_id = str(uuid.uuid4())
            filename = secure_filename(file.filename) if file.filename else "audio.ogg"
            file_ext = os.path.splitext(filename)[1].lower() or ".ogg"
            input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}{file_ext}")
            file.save(input_file_path)
            
            return process_and_convert(input_file_path, unique_id, filename)
        
        # Method 3: Check for raw request data
        if request.data and len(request.data) > 100:
            app.logger.debug("Using raw request data")
            unique_id = str(uuid.uuid4())
            input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.ogg")
            
            with open(input_file_path, 'wb') as f:
                f.write(request.data)
                
            app.logger.debug(f"Saved raw data to: {input_file_path}")
            return process_and_convert(input_file_path, unique_id, "audio.ogg")
        
        # Method 4: Check for binary data in form fields
        for key in request.form.keys():
            form_data = request.form[key]
            app.logger.debug(f"Checking form key: {key}, data length: {len(form_data) if form_data else 0}")
            
            if form_data and len(form_data) > 100:
                app.logger.debug(f"Found potential binary data in form key: {key}")
                
                # Save for debugging
                debug_data = form_data.encode('latin1') if isinstance(form_data, str) else form_data
                debug_file = write_debug_file(debug_data, f"form_data_{key}.bin")
                app.logger.debug(f"Form data saved to: {debug_file}")
                
                # Try to process it
                try:
                    unique_id = str(uuid.uuid4())
                    input_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.ogg")
                    
                    with open(input_file_path, 'wb') as f:
                        f.write(debug_data)
                    
                    app.logger.debug(f"Saved form data to: {input_file_path}")
                    return process_and_convert(input_file_path, unique_id, "audio.ogg")
                except Exception as e:
                    app.logger.error(f"Failed to process form data from {key}: {str(e)}")
                    continue
        
        # If we got here, no file was found
        return jsonify({'error': 'No file data found in request. Try using the parameter name "file" or sending raw binary data.'}), 400
        
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def process_and_convert(input_file_path, unique_id, filename):
    """Process a saved file and convert it to WAV"""
    app.logger.debug(f"Converting file: {input_file_path}")
    
    # Try different approaches to convert the file
    output_file_path = os.path.join(CONVERTED_FOLDER, f"{unique_id}.wav")
    
    try:
        # Try to get file info
        if os.path.exists(input_file_path):
            file_size = os.path.getsize(input_file_path)
            app.logger.debug(f"File exists, size: {file_size} bytes")
            
            # Read the first few bytes to help identify the file type
            with open(input_file_path, 'rb') as f:
                header = f.read(12)  # First 12 bytes
            
            header_hex = ' '.join([f'{b:02x}' for b in header])
            app.logger.debug(f"File header (hex): {header_hex}")
            
            # Common OGG header starts with "OggS"
            if header.startswith(b'OggS'):
                app.logger.debug("File appears to be a valid OGG file based on header")
            else:
                app.logger.debug("File does not have an OGG header")
        
        # Attempt conversion with pydub
        try:
            sound = AudioSegment.from_file(input_file_path, format="ogg")
            app.logger.debug("Successfully loaded the file as OGG with pydub")
            sound.export(output_file_path, format="wav")
            app.logger.debug(f"Successfully converted to WAV: {output_file_path}")
            
            # Clean up the input file
            os.remove(input_file_path)
            
            # Return the converted file
            return send_file(output_file_path, as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.wav")
        except Exception as e:
            app.logger.error(f"Failed to convert with explicit OGG format: {str(e)}")
            
            # Fallback: Try to let pydub detect the format
            try:
                sound = AudioSegment.from_file(input_file_path)
                app.logger.debug("Successfully loaded the file with pydub auto-detection")
                sound.export(output_file_path, format="wav")
                app.logger.debug(f"Successfully converted to WAV: {output_file_path}")
                
                # Clean up the input file
                os.remove(input_file_path)
                
                # Return the converted file
                return send_file(output_file_path, as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.wav")
            except Exception as e2:
                app.logger.error(f"Failed to convert with auto-detection: {str(e2)}")
                
                # Keep the failed file for further debugging
                return jsonify({'error': f'Failed to convert file to WAV. File is not a valid OGG/OGA format. Errors: {str(e)} and {str(e2)}'}), 400
    
    except Exception as e:
        app.logger.error(f"Unexpected error during conversion: {str(e)}")
        
        # Cleanup
        if os.path.exists(input_file_path):
            os.remove(input_file_path)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
            
        return jsonify({'error': f'Server error during conversion: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
