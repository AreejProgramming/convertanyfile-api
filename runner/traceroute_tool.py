import os
import json
import time
import sys
import re
import subprocess
import uuid
from datetime import datetime

def generate_session_id():
    return str(uuid.uuid4())

def validate_input(input_str):
    """
    Validate if input is a valid IP address or domain name
    """
    # IPv4 regex
    ipv4_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    # IPv6 regex (simplified)
    ipv6_regex = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    
    return (re.match(ipv4_regex, input_str) or 
            re.match(ipv6_regex, input_str) or 
            re.match(domain_regex, input_str))

def run_traceroute(target):
    """
    Run traceroute command and parse the output
    """
    try:
        # Use traceroute command (Linux/Mac) or tracert (Windows)
        if sys.platform.startswith('win'):
            cmd = ['tracert', target]
        else:
            cmd = ['traceroute', target]
        
        # Run the command with timeout
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        if result.returncode != 0:
            return {"error": f"Traceroute failed: {result.stderr}"}
        
        # Parse the output
        hops = []
        lines = result.stdout.split('\n')
        
        for line in lines:
            # Skip empty lines and header
            if not line.strip() or line.startswith('traceroute to'):
                continue
                
            # Parse hop information
            hop_match = re.match(r'^\s*(\d+)\s+(.*)$', line)
            if hop_match:
                hop_num = int(hop_match.group(1))
                hop_info = hop_match.group(2)
                
                # Extract IP addresses and hostnames
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', hop_info)
                ip = ip_match.group(1) if ip_match else "Unknown"
                
                # Extract hostname (if available)
                hostname_match = re.search(r'([a-zA-Z0-9.-]+)\s+\(', hop_info)
                hostname = hostname_match.group(1) if hostname_match else "Unknown"
                
                # Extract times (ms)
                times = []
                time_matches = re.findall(r'(\d+\.\d+)\s*ms', hop_info)
                for time_match in time_matches:
                    times.append(float(time_match))
                
                # If no times found, check for asterisks
                if not times:
                    asterisk_count = hop_info.count('*')
                    if asterisk_count >= 3:
                        times = ["*", "*", "*"]
                    else:
                        times = ["Timeout"]
                
                # Calculate average time (if numeric)
                avg_time = 0
                if times and times[0] != "*":
                    numeric_times = [t for t in times if isinstance(t, float)]
                    if numeric_times:
                        avg_time = sum(numeric_times) / len(numeric_times)
                
                hops.append({
                    "hop": hop_num,
                    "ip": ip,
                    "hostname": hostname,
                    "times": times,
                    "avgTime": round(avg_time, 2) if avg_time else 0,
                    "status": "success" if times and times[0] != "*" else "timeout"
                })
        
        return {"hops": hops}
        
    except subprocess.TimeoutExpired:
        return {"error": "Traceroute timed out. Please try again."}
    except Exception as e:
        return {"error": f"Error running traceroute: {str(e)}"}

def check_traceroute(target):
    """
    Main function to check traceroute
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting traceroute for: {target}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Running traceroute...",
        "session_id": session_id
    }
    
    try:
        # Validate input
        if not target or not validate_input(target):
            raise ValueError("Invalid IP address or domain format")
        
        # Run traceroute
        print(f"Running traceroute to {target}...")
        traceroute_data = run_traceroute(target)
        
        if "error" in traceroute_data:
            raise ValueError(traceroute_data["error"])
        
        # Calculate total time
        total_time = sum(hop.get("avgTime", 0) for hop in traceroute_data["hops"])
        
        # Create final results
        results = {
            "status": "success",
            "target": target,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "hops": traceroute_data["hops"],
                "totalTime": round(total_time, 2),
                "hopCount": len(traceroute_data["hops"])
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
    target = os.environ.get("TARGET")
    if not target:
        print("ERROR: TARGET environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "TARGET environment variable not set.",
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
        
    traceroute_results = check_traceroute(target)
    
    # The results are already printed in the function
    sys.exit(0)
