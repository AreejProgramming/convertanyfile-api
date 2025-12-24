import os
import json
import time
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_input(input_str):
    """
    Validate if input is an IP address or domain name
    """
    # IP address regex
    ip_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    
    return re.match(ip_regex, input_str) or re.match(domain_regex, input_str)

def lookup_ip_info(query):
    """
    Lookup IP information using ip-api.com (free service)
    """
    try:
        # If it's a domain, first resolve to IP
        if not re.match(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', query):
            import socket
            try:
                ip_address = socket.gethostbyname(query)
                query = ip_address
            except:
                return {"error": "Could not resolve domain to IP address"}
        
        # Use ip-api.com to get IP information
        response = requests.get(f"http://ip-api.com/json/{query}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,reverse,mobile,proxy,hosting", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                # Determine IP type (IPv4 or IPv6)
                ip_type = "IPv6" if ':' in query else "IPv4"
                
                return {
                    "query": query,
                    "ip": data.get("query", query),
                    "type": ip_type,
                    "country": data.get("country", "Unknown"),
                    "countryCode": data.get("countryCode", "Unknown"),
                    "region": data.get("regionName", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "latitude": data.get("lat", 0),
                    "longitude": data.get("lon", 0),
                    "timezone": data.get("timezone", "Unknown"),
                    "isp": data.get("isp", "Unknown"),
                    "org": data.get("org", "Unknown"),
                    "as": data.get("as", "Unknown"),
                    "proxy": data.get("proxy", False),
                    "hosting": data.get("hosting", False)
                }
            else:
                return {"error": data.get("message", "Unknown error")}
        else:
            return {"error": f"API request failed with status code {response.status_code}"}
            
    except Exception as e:
        print(f"Error looking up IP info: {str(e)}")
        return {"error": str(e)}

def check_ip_address(query):
    """
    Check IP address information
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting IP address lookup for: {query}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Looking up IP address...",
        "session_id": session_id
    }
    
    try:
        # Basic input validation
        if not query or not validate_input(query):
            raise ValueError("Invalid IP address or domain name format")
        
        print(f"Looking up IP address for {query}")
        
        # Lookup IP information
        ip_data = lookup_ip_info(query)
        
        if "error" in ip_data:
            raise ValueError(ip_data["error"])
        
        # Create final results
        results = {
            "status": "success",
            "query": query,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": ip_data
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
    target_query = os.environ.get("TARGET_QUERY")
    if not target_query:
        print("ERROR: TARGET_QUERY environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "TARGET_QUERY environment variable not set.",
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
        
    ip_results = check_ip_address(target_query)
    
    # The results are already printed in the function
    sys.exit(0)
