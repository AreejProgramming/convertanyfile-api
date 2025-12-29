# File: runner/website_technology_detector.py

import os
import json
import time
import sys
import uuid
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import ssl

def generate_session_id():
    return str(uuid.uuid4())

def normalize_url(url):
    """
    Normalize the URL to ensure it has a protocol
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def extract_domain(url):
    """
    Extract domain from URL
    """
    parsed_url = urlparse(url)
    return parsed_url.netloc

def detect_technologies(url):
    """
    Detect technologies used by a website
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Normalize the URL
    url = normalize_url(url)
    domain = extract_domain(url)
    
    print(f"Starting technology detection for: {url}")
    print(f"Domain: {domain}")
    print(f"Session ID: {session_id}")
    
    results = {
        "status": "error", 
        "message": "Technology detection failed to start.",
        "session_id": session_id
    }
    
    try:
        # Create a session with custom headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Disable SSL verification for sites with certificate issues
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        print(f"Fetching {url}")
        
        # Make the request with timeout
        response = session.get(url, timeout=10, verify=False)
        response.raise_for_status()
        
        # Get response headers
        headers = response.headers
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize technology categories
        cms = []
        javascript_frameworks = []
        web_server = []
        hosting_provider = []
        analytics = []
        other = []
        
        # Detect CMS
        cms_indicators = {
            'WordPress': ['wp-content', 'wp-includes', 'wp-json', 'wordpress'],
            'Drupal': ['drupal', 'sites/default/files'],
            'Joomla': ['joomla', '/media/jui'],
            'Shopify': ['Shopify.shop', 'cdn.shopify.com'],
            'Magento': ['magento', 'skin/frontend'],
            'Squarespace': ['squarespace'],
            'Wix': ['wix'],
            'Ghost': ['ghost'],
            'HubSpot': ['hubspot']
        }
        
        for cms_name, indicators in cms_indicators.items():
            for indicator in indicators:
                if indicator in response.text.lower():
                    cms.append(cms_name)
                    break
        
        # Detect JavaScript frameworks
        js_indicators = {
            'React': ['react', 'react-dom', 'React.createElement'],
            'Vue.js': ['vue.js', 'vue.min.js', 'new Vue'],
            'Angular': ['angular', 'ng-app', 'ng-controller'],
            'jQuery': ['jquery', 'jQuery'],
            'Next.js': ['next.js', '_next'],
            'Gatsby': ['gatsby', 'gatsby-'],
            'Nuxt.js': ['nuxt.js', '_nuxt'],
            'Svelte': ['svelte'],
            'Ember': ['ember'],
            'Backbone.js': ['backbone'],
            'Bootstrap': ['bootstrap'],
            'Tailwind CSS': ['tailwindcss']
        }
        
        for js_name, indicators in js_indicators.items():
            for indicator in indicators:
                if indicator in response.text:
                    javascript_frameworks.append(js_name)
                    break
        
        # Detect web server from headers
        server_header = headers.get('Server', '').lower()
        if 'apache' in server_header:
            web_server.append('Apache')
        elif 'nginx' in server_header:
            web_server.append('Nginx')
        elif 'iis' in server_header or 'microsoft' in server_header:
            web_server.append('Microsoft IIS')
        elif 'cloudflare' in server_header:
            web_server.append('Cloudflare')
        elif 'litespeed' in server_header:
            web_server.append('LiteSpeed')
        elif 'caddy' in server_header:
            web_server.append('Caddy')
        
        # Detect hosting provider
        hosting_indicators = {
            'Amazon Web Services': ['amazonaws.com', 'aws', 's3.amazonaws.com'],
            'Google Cloud': ['googleusercontent.com', 'appspot.com'],
            'Microsoft Azure': ['azurewebsites.net', 'azureedge.net'],
            'DigitalOcean': ['digitalocean'],
            'Heroku': ['herokuapp.com'],
            'Netlify': ['netlify.com'],
            'Vercel': ['vercel.app'],
            'GitHub Pages': ['github.io'],
            'Bluehost': ['bluehost'],
            'GoDaddy': ['godaddy'],
            'HostGator': ['hostgator']
        }
        
        for hosting_name, indicators in hosting_indicators.items():
            for indicator in indicators:
                if indicator in response.text.lower() or indicator in domain.lower():
                    hosting_provider.append(hosting_name)
                    break
        
        # Detect analytics
        analytics_indicators = {
            'Google Analytics': ['google-analytics.com', 'ga.js', 'analytics.js', 'gtag'],
            'Google Tag Manager': ['googletagmanager.com'],
            'Hotjar': ['hotjar'],
            'Mixpanel': ['mixpanel'],
            'Segment': ['segment.com'],
            'Adobe Analytics': ['omniture', 'sc.omtrdc.net'],
            'Matomo': ['matomo', 'piwik'],
            'Facebook Pixel': ['facebook.com/tr'],
            'LinkedIn Insight Tag': ['linkedin.com/insight-tag']
        }
        
        for analytics_name, indicators in analytics_indicators.items():
            for indicator in indicators:
                if indicator in response.text:
                    analytics.append(analytics_name)
                    break
        
        # Detect other technologies
        other_indicators = {
            'SSL': ['https', 'ssl', 'tls'],
            'CDN': ['cdn', 'cloudflare', 'fastly', 'akamai'],
            'Font Awesome': ['font-awesome'],
            'Google Fonts': ['fonts.googleapis.com'],
            'Adobe Fonts': ['use.typekit.net', 'fonts.adobe.com']
        }
        
        for other_name, indicators in other_indicators.items():
            for indicator in indicators:
                if indicator in response.text.lower():
                    other.append(other_name)
                    break
        
        # Extract SSL information
        if url.startswith('https://'):
            other.append('SSL Enabled')
        
        # Remove duplicates
        cms = list(set(cms))
        javascript_frameworks = list(set(javascript_frameworks))
        web_server = list(set(web_server))
        hosting_provider = list(set(hosting_provider))
        analytics = list(set(analytics))
        other = list(set(other))
        
        results = {
            "status": "success",
            "url": url,
            "domain": domain,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "cms": cms,
                "javascript_frameworks": javascript_frameworks,
                "web_server": web_server,
                "hosting_provider": hosting_provider,
                "analytics": analytics,
                "other": other
            }
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        results = {
            "status": "error", 
            "message": f"Failed to access the website: {str(e)}",
            "session_id": session_id
        }
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        print(f"results={json.dumps({'status': 'error', 'message': 'TARGET_URL environment variable not set.'})}")
        sys.exit(1)
        
    tech_results = detect_technologies(target_url)
    
    # The results are already printed in the function
