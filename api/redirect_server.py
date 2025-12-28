# api/redirect_server.py
from flask import Flask, redirect, request, jsonify, render_template_string, send_from_directory
import json
import os
import time
from datetime import datetime
from urllib.parse import urlparse
import qrcode
import io
import base64
import string
import random

app = Flask(__name__, static_folder='static')

# Configuration
BASE_URL = "https://short.ly"  # Change this to your actual domain
DATABASE_FILE = 'url_database.json'

# In-memory database (in production, use PostgreSQL/MySQL)
URL_DATABASE = {}

def load_database():
    """Load URL database from file"""
    global URL_DATABASE
    try:
        if os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, 'r') as f:
                URL_DATABASE = json.load(f)
    except Exception as e:
        print(f"Error loading database: {e}")
        URL_DATABASE = {}

def save_database():
    """Save URL database to file"""
    try:
        with open(DATABASE_FILE, 'w') as f:
            json.dump(URL_DATABASE, f, indent=2)
    except Exception as e:
        print(f"Error saving database: {e}")

def generate_short_code(custom_alias=None):
    """Generate a unique short code"""
    if custom_alias and re.match(r'^[a-zA-Z0-9_-]+$', custom_alias):
        if custom_alias in URL_DATABASE:
            return None, f"Custom alias '{custom_alias}' is already taken"
        return custom_alias, None
    
    # Generate random 6-character code
    while True:
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        if code not in URL_DATABASE:
            return code, None

def generate_qr_code(url):
    """Generate QR code for URL"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

# Load database on startup
load_database()

@app.route('/')
def index():
    """Main page with URL shortener form"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URL Shortener Service</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container { 
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            max-width: 500px;
            width: 90%;
        }
        h1 { 
            color: #333; 
            margin-bottom: 2rem; 
            text-align: center;
            font-size: 2rem;
        }
        .form-group { margin-bottom: 1.5rem; }
        label { 
            display: block; 
            margin-bottom: 0.5rem; 
            color: #555; 
            font-weight: 500;
        }
        input[type="url"], input[type="text"] { 
            width: 100%; 
            padding: 0.75rem; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px; 
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        input[type="url"]:focus, input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 0.75rem 2rem; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            width: 100%;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        .result { 
            margin-top: 2rem; 
            padding: 1rem; 
            background: #f8f9fa; 
            border-radius: 8px; 
            display: none;
        }
        .short-url { 
            background: #e8f5e8; 
            padding: 1rem; 
            border-radius: 8px; 
            margin-top: 1rem;
            word-break: break-all;
        }
        .short-url a { color: #007bff; text-decoration: none; font-weight: 600; }
        .qr-code { 
            text-align: center; 
            margin-top: 1rem;
        }
        .qr-code img { 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            padding: 10px;
            background: white;
        }
        .stats { 
            background: #f8f9fa; 
            padding: 1rem; 
            border-radius: 8px; 
            margin-top: 2rem;
        }
        .error { color: #dc3545; background: #f8d7da; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        
        <div class="form-group">
            <label for="urlInput">Enter URL to shorten:</label>
            <input type="url" id="urlInput" placeholder="https://example.com/very/long/url" />
        </div>
        
        <div class="form-group">
            <label for="aliasInput">Custom alias (optional):</label>
            <input type="text" id="aliasInput" placeholder="my-custom-link" />
        </div>
        
        <button onclick="shortenUrl()">✂️ Shorten URL</button>
        
        <div id="result"></div>
        
        <div class="stats">
            <h3>📊 Statistics</h3>
            <p>Total URLs shortened: <strong>{{ total_urls }}</strong></p>
            <p>Total clicks: <strong>{{ total_clicks }}</strong></p>
        </div>
    </div>
    
    <script>
        async function shortenUrl() {
            const url = document.getElementById('urlInput').value;
            const alias = document.getElementById('aliasInput').value;
            const resultDiv = document.getElementById('result');
            
            if (!url) {
                resultDiv.innerHTML = '<div class="error">Please enter a URL</div>';
                return;
            }
            
            // Show loading
            resultDiv.innerHTML = '<div class="result">⏳ Shortening URL...</div>';
            resultDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/shorten', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, custom_alias: alias })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    resultDiv.innerHTML = `
                        <div class="result">
                            <h3>✅ URL Shortened Successfully!</h3>
                            <div class="short-url">
                                <strong>Short URL:</strong><br>
                                <a href="${data.short_url}" target="_blank">${data.short_url}</a>
                            </div>
                            <div class="qr-code">
                                <strong>QR Code:</strong><br>
                                <img src="data:image/png;base64,${data.qr_code}" alt="QR Code" />
                            </div>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="error">❌ ${data.message}</div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = '<div class="error">❌ Network error. Please try again.</div>';
            }
        }
        
        // Allow Enter key to submit
        document.getElementById('urlInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') shortenUrl();
        });
        document.getElementById('aliasInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') shortenUrl();
        });
    </script>
</body>
</html>
    ''', 
    total_urls=len(URL_DATABASE),
    total_clicks=sum(data.get('clicks', 0) for data in URL_DATABASE.values())
)

@app.route('/<short_code>')
def redirect_url(short_code):
    """Handle URL redirection"""
    global URL_DATABASE
    
    if short_code in URL_DATABASE:
        url_data = URL_DATABASE[short_code]
        
        # Check if URL has expired
        if url_data.get('expiration_timestamp'):
            if time.time() > url_data['expiration_timestamp']:
                return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Link Expired</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            min-height: 100vh; 
            background: #f8f9fa;
            margin: 0;
        }
        .container { 
            text-align: center; 
            background: white; 
            padding: 2rem; 
            border-radius: 10px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #dc3545; margin-bottom: 1rem; }
        p { color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⏰ Link Expired</h1>
        <p>This shortened link has expired and is no longer active.</p>
        <p>Please contact the person who shared this link for a new one.</p>
    </div>
</body>
</html>
                '''), 410  # Gone
        
        # Update analytics
        url_data['clicks'] = url_data.get('clicks', 0) + 1
        url_data['analytics']['clicks'] = url_data['analytics'].get('clicks', 0) + 1
        
        # Track referrer
        referrer = request.referrer
        if referrer:
            if 'referrers' not in url_data['analytics']:
                url_data['analytics']['referrers'] = {}
            url_data['analytics']['referrers'][referrer] = url_data['analytics']['referrers'].get(referrer, 0) + 1
        
        # Track user agent (device/browser)
        user_agent = request.headers.get('User-Agent', '')
        if user_agent:
            if 'Mobile' in user_agent:
                device = 'Mobile'
            else:
                device = 'Desktop'
            
            if 'devices' not in url_data['analytics']:
                url_data['analytics']['devices'] = {}
            url_data['analytics']['devices'][device] = url_data['analytics']['devices'].get(device, 0) + 1
        
        # Track IP for country (simplified)
        ip = request.remote_addr
        if ip:
            # In production, use a proper IP geolocation service
            country = 'Unknown'  # Would be determined from IP
            if 'countries' not in url_data['analytics']:
                url_data['analytics']['countries'] = {}
            url_data['analytics']['countries'][country] = url_data['analytics']['countries'].get(country, 0) + 1
        
        # Update last accessed time
        url_data['last_accessed'] = time.time()
        
        save_database()
        
        # Log the redirect
        print(f"Redirecting {short_code} to {url_data['original_url']} (Click #{url_data['clicks']})")
        
        # Redirect to original URL
        return redirect(url_data['original_url'])
    else:
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Link Not Found</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            min-height: 100vh; 
            background: #f8f9fa;
            margin: 0;
        }
        .container { 
            text-align: center; 
            background: white; 
            padding: 2rem; 
            border-radius: 10px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #dc3545; margin-bottom: 1rem; }
        p { color: #6c757d; }
        a { color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Link Not Found</h1>
        <p>The shortened link you're looking for doesn't exist or has been removed.</p>
        <p><a href="/">Create a new short link</a></p>
    </div>
</body>
</html>
        '''), 404

@app.route('/api/shorten', methods=['POST'])
def api_shorten():
    """API endpoint for URL shortening"""
    data = request.get_json()
    url = data.get('url', '').strip()
    custom_alias = data.get('custom_alias', '').strip()
    
    if not url:
        return jsonify({"status": "error", "message": "URL is required"})
    
    # Validate URL
    parsed = urlparse(url)
    if not all([parsed.scheme, parsed.netloc]):
        return jsonify({"status": "error", "message": "Invalid URL format"})
    
    # Generate short code
    short_code, error = generate_short_code(custom_alias if custom_alias else None)
    if error:
        return jsonify({"status": "error", "message": error})
    
    # Create short URL
    short_url = f"{BASE_URL}/{short_code}"
    
    # Generate QR code
    qr_code = generate_qr_code(short_url)
    
    # Store in database
    URL_DATABASE[short_code] = {
        "original_url": url,
        "short_url": short_url,
        "short_code": short_code,
        "custom_alias": custom_alias if custom_alias else None,
        "created_at": time.time(),
        "clicks": 0,
        "analytics": {
            "clicks": 0,
            "referrers": {},
            "countries": {},
            "devices": {},
            "browsers": {}
        }
    }
    
    save_database()
    
    print(f"Created short URL: {short_url} -> {url}")
    
    return jsonify({
        "status": "success",
        "original_url": url,
        "short_url": short_url,
        "short_code": short_code,
        "qr_code": qr_code,
        "created_at": URL_DATABASE[short_code]["created_at"]
    })

@app.route('/api/stats/<short_code>')
def api_stats(short_code):
    """Get statistics for a short URL"""
    if short_code in URL_DATABASE:
        return jsonify({
            "status": "success",
            "data": URL_DATABASE[short_code]
        })
    return jsonify({"status": "error", "message": "Short URL not found"})

@app.route('/api/all')
def api_all():
    """Get all shortened URLs (admin endpoint)"""
    return jsonify({
        "status": "success",
        "data": URL_DATABASE,
        "total_urls": len(URL_DATABASE),
        "total_clicks": sum(data.get('clicks', 0) for data in URL_DATABASE.values())
    })

if __name__ == '__main__':
    # Create static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Save database on startup
    save_database()
    
    print("🚀 URL Shortener Server Starting...")
    print(f"📍 Base URL: {BASE_URL}")
    print(f"💾 Database file: {DATABASE_FILE}")
    print(f"📊 Total URLs: {len(URL_DATABASE)}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
