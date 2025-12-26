import os
import json
import time
import sys
from urllib.parse import urlparse
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def setup_webdriver():
    """
    Set up Chrome webdriver for standard environment
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=375,812")  # Mobile viewport
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1")
        
        # Use webdriver-manager to handle ChromeDriver automatically
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        return driver
    except Exception as e:
        print(f"Error setting up webdriver: {str(e)}")
        return None

# ... rest of your existing functions remain the same ...

def write_results_safely(results, session_id):
    """
    Safely write results to file with proper error handling
    """
    try:
        # Try multiple locations
        locations = [
            f'results_{session_id}.json',
            'results.json',
            f'/tmp/results_{session_id}.json'
        ]
        
        for location in locations:
            try:
                directory = os.path.dirname(location)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                
                with open(location, 'w') as f:
                    json.dump(results, f)
                print(f"Results successfully written to {location}")
                return
            except Exception as e:
                print(f"Failed to write to {location}: {str(e)}")
                continue
                
        # Final fallback - output to stdout
        print(f"results={json.dumps(results)}")
        
    except Exception as e:
        print(f"ERROR in write_results_safely: {str(e)}")
        print(f"results={json.dumps(results)}")

# ... rest of your code remains the same ...
