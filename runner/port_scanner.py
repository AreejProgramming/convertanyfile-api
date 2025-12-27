import os
import json
import time
import sys
import re
import socket
import threading
import concurrent.futures
from datetime import datetime
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_target(target):
    """
    Validate if target is a valid IP address or domain name
    """
    # IPv4 regex
    ipv4_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    # IPv6 regex (simplified)
    ipv6_regex = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    
    return (re.match(ipv4_regex, target) or 
            re.match(ipv6_regex, target) or 
            re.match(domain_regex, target))

def get_common_ports():
    """
    Returns a list of common ports to scan with their service names and descriptions
    """
    return [
        { "port": 21, "service": "FTP", "description": "File Transfer Protocol" },
        { "port": 22, "service": "SSH", "description": "Secure Shell" },
        { "port": 23, "service": "Telnet", "description": "Telnet Protocol" },
        { "port": 25, "service": "SMTP", "description": "Simple Mail Transfer" },
        { "port": 53, "service": "DNS", "description": "Domain Name System" },
        { "port": 80, "service": "HTTP", "description": "HyperText Transfer" },
        { "port": 110, "service": "POP3", "description": "Post Office Protocol v3" },
        { "port": 143, "service": "IMAP", "description": "Internet Message Access" },
        { "port": 443, "service": "HTTPS", "description": "HTTP Secure" },
        { "port": 993, "service": "IMAPS", "description": "IMAP Secure" },
        { "port": 995, "service": "POP3S", "description": "POP3 Secure" },
    ]

def scan_port(target, port_info, timeout=3):
    """
    Scan a single port and return its status
    """
    port = port_info["port"]
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((target, port))
        response_time = (time.time() - start_time) * 1000  # in milliseconds
        sock.close()
        
        if result == 0:
            return {
                **port_info,
                "status": "Open",
                "responseTime": round(response_time, 2)
            }
        else:
            return {
                **port_info,
                "status": "Closed",
                "responseTime": None
            }
    except socket.timeout:
        return {
            **port_info,
            "status": "Filtered",
            "responseTime": None
        }
    except Exception as e:
        return {
            **port_info,
            "status": "Error",
            "error": str(e),
            "responseTime": None
        }

def scan_ports(target, max_workers=10):
    """
    Scan multiple ports using ThreadPoolExecutor for better performance
    """
    ports_to_scan = get_common_ports()
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scan tasks to the executor
        future_to_port = {
            executor.submit(scan_port, target, port_info): port_info 
            for port_info in ports_to_scan
        }
        
        # Process completed tasks as they finish
        for future in concurrent.futures.as_completed(future_to_port):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                port_info = future_to_port[future]
                results.append({
                    **port_info,
                    "status": "Error",
                    "error": str(e),
                    "responseTime": None
                })
    
    # Sort results by port number
    results.sort(key=lambda x: x["port"])
    return results

def check_ports(target):
    """
    Main function to check ports for a target
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting port scan for target: {target}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Scanning ports...",
        "session_id": session_id
    }
    
    try:
        # Validate target
        if not target or not validate_target(target):
            raise ValueError("Invalid hostname or IP address")
        
        print(f"Scanning common ports on {target}...")
        
        # Perform the port scan
        scan_results = scan_ports(target)
        
        # Count open, closed, and filtered ports
        open_count = sum(1 for r in scan_results if r["status"] == "Open")
        closed_count = sum(1 for r in scan_results if r["status"] == "Closed")
        filtered_count = sum(1 for r in scan_results if r["status"] == "Filtered")
        error_count = sum(1 for r in scan_results if r["status"] == "Error")
        
        # Create final results
        results = {
            "status": "success",
            "target": target,
            "timestamp": time.time(),
            "session_id": session_id,
            "summary": {
                "total": len(scan_results),
                "open": open_count,
                "closed": closed_count,
                "filtered": filtered_count,
                "errors": error_count
            },
            "results": scan_results
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
        
    port_results = check_ports(target)
    
    # The results are already printed in the function
    sys.exit(0)
