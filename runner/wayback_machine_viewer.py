import os
import json
import time
import sys
import re
import requests
import uuid
from datetime import datetime
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

def normalize_url(url):
    """
    Normalize URL format
    """
    if not url:
        return None
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    if url.endswith('/'):
        url = url[:-1]
    
    return url

def fetch_wayback_data(url):
    """
    Fetch data from Wayback Machine API
    """
    try:
        # Wayback Machine CDX API endpoint
        cdx_url = f"http://web.archive.org/cdx/search/cdx?url={url}&output=json&collapse=timestamp:8&filter=statuscode:200&limit=100"
        
        print(f"Fetching data from: {cdx_url}")
        
        # Make request to Wayback Machine API
        response = requests.get(cdx_url, timeout=30)
        
        if response.status_code != 200:
            return {"error": f"API request failed with status code {response.status_code}"}
        
        data = response.json()
        
        # Check if data is valid
        if not data or len(data) < 2:
            return {"error": "No data found for this URL"}
        
        # Parse the data (first row is headers)
        headers = data[0]
        snapshots = []
        
        for row in data[1:]:
            if len(row) < len(headers):
                continue
                
            # Create a dictionary for the row
            snapshot_data = dict(zip(headers, row))
            
            # Parse timestamp
            timestamp = snapshot_data.get('timestamp', '')
            if timestamp:
                try:
                    # Convert timestamp to datetime
                    year = int(timestamp[:4])
                    month = int(timestamp[4:6])
                    day = int(timestamp[6:8])
                    hour = int(timestamp[8:10])
                    minute = int(timestamp[10:12])
                    date = datetime(year, month, day, hour, minute)
                except:
                    date = datetime.now()
            else:
                date = datetime.now()
            
            # Get status code
            status_code = snapshot_data.get('statuscode', '200')
            
            # Get MIME type
            mime_type = snapshot_data.get('mimetype', 'text/html')
            
            # Get digest (for uniqueness)
            digest = snapshot_data.get('digest', '')
            
            # Get original URL
            original = snapshot_data.get('original', url)
            
            # Create snapshot URL
            snapshot_url = f"https://web.archive.org/web/{timestamp}/{original}"
            
            # Determine status
            status = 'success' if status_code == '200' else 'redirect'
            
            # Calculate size (rough estimate based on digest)
            size = len(digest) * 10  # Rough estimate
            
            snapshots.append({
                "date": date,
                "status": status,
                "size": f"{size} KB",
                "url": snapshot_url,
                "timestamp": timestamp,
                "status_code": status_code,
                "mime_type": mime_type
            })
        
        # Sort snapshots by date (newest first)
        snapshots.sort(key=lambda x: x['date'], reverse=True)
        
        # Get domain info
        domain = urlparse(url).netloc
        
        # Get first and last crawled dates
        first_crawled = snapshots[-1]['date'] if snapshots else None
        last_crawled = snapshots[0]['date'] if snapshots else None
        
        return {
            "snapshots": snapshots,
            "domain": domain,
            "first_crawled": first_crawled,
            "last_crawled": last_crawled,
            "total_snapshots": len(snapshots)
        }
        
    except Exception as e:
        print(f"Error fetching Wayback data: {str(e)}")
        return {"error": str(e)}

def check_wayback(url):
    """
    Main function to check Wayback Machine for a URL
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting Wayback Machine check for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Fetching Wayback Machine data...",
        "session_id": session_id
    }
    
    try:
        # Validate and normalize URL
        normalized_url = normalize_url(url)
        
        if not normalized_url or not validate_url(normalized_url):
            raise ValueError("Invalid URL format")
        
        # Fetch Wayback Machine data
        print(f"Fetching Wayback Machine data for {normalized_url}")
        wayback_data = fetch_wayback_data(normalized_url)
        
        if "error" in wayback_data:
            raise ValueError(wayback_data["error"])
        
        # Create final results
        results = {
            "status": "success",
            "url": normalized_url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": wayback_data
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
    url = os.environ.get("URL")
    if not url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "URL environment variable not set.",
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
        
    wayback_results = check_wayback(url)
    
    # The results are already printed in the function
    sys.exit(0)
