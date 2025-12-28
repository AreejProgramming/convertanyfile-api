import os
import json
import time
import sys
import re
import uuid
import hashlib
import qrcode
import io
import base64
from datetime import datetime, timedelta
from urllib.parse import urlparse

def generate_session_id():
    return str(uuid.uuid4())

def validate_url(url):
    """
    Validate if input is a valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def generate_short_code(custom_alias=None):
    """
    Generate a short code for the URL
    """
    if custom_alias and re.match(r'^[a-zA-Z0-9_-]+$', custom_alias):
        return custom_alias
    
    # Generate a random 6-character code
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def generate_qr_code(url):
    """
    Generate a QR code for the URL
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert image to base64 string
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

def check_url_shortener(original_url, custom_alias=None, password_protected=False, expiration_date=None, track_analytics=True):
    """
    Main function to shorten URL
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting URL shortener for: {original_url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Shortening URL...",
        "session_id": session_id
    }
    
    try:
        # Validate input
        if not original_url or not validate_url(original_url):
            raise ValueError("Invalid URL format")
        
        # Generate short code
        short_code = generate_short_code(custom_alias)
        
        # Create shortened URL
        short_url = f"https://short.ly/{short_code}"
        
        # Generate QR code
        qr_code = generate_qr_code(short_url)
        
        # Calculate expiration date if provided
        expiration_timestamp = None
        if expiration_date:
            try:
                expiration_timestamp = datetime.strptime(expiration_date, "%Y-%m-%d").timestamp()
            except:
                expiration_timestamp = (datetime.now() + timedelta(days=30)).timestamp()
        
        # Create final results
        results = {
            "status": "success",
            "original_url": original_url,
            "short_url": short_url,
            "short_code": short_code,
            "qr_code": qr_code,
            "password_protected": password_protected,
            "expiration_timestamp": expiration_timestamp,
            "track_analytics": track_analytics,
            "created_at": time.time(),
            "session_id": session_id,
            "clicks": 0,
            "analytics": {
                "clicks": 0,
                "referrers": {},
                "countries": {},
                "devices": {},
                "browsers": {}
            }
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always write results to file, even if there was an error
    try:
        with open('results.json', 'w') as f:
            json.dump(results, f)
        print("Results successfully written to results.json")
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        # Try to write to a different location as fallback
        try:
            with open(f'/tmp/results_{session_id}.json', 'w') as f:
                json.dump(results, f)
            print(f"Results written to fallback location: /tmp/results_{session_id}.json")
        except Exception as fallback_error:
            print(f"ERROR writing to fallback location: {str(fallback_error)}")
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    import random
    import string
    
    original_url = os.environ.get("ORIGINAL_URL")
    custom_alias = os.environ.get("CUSTOM_ALIAS", "")
    password_protected = os.environ.get("PASSWORD_PROTECTED", "false").lower() == "true"
    expiration_date = os.environ.get("EXPIRATION_DATE", "")
    track_analytics = os.environ.get("TRACK_ANALYTICS", "true").lower() == "true"
    
    if not original_url:
        print("ERROR: ORIGINAL_URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "ORIGINAL_URL environment variable not set.",
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        
        # Write error results to file
        try:
            with open('results.json', 'w') as f:
                json.dump(error_result, f)
            print("Error results written to results.json")
        except Exception as file_error:
            print(f"ERROR writing error results file: {str(file_error)}")
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    shortener_results = check_url_shortener(
        original_url, 
        custom_alias, 
        password_protected, 
        expiration_date, 
        track_analytics
    )
    
    # The results are already printed in the function
    sys.exit(0)
