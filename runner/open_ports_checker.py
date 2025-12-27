import os
import json
import time
import sys
import re
import socket
import threading
from datetime import datetime
import uuid

def generate_session_id():
    return str(uuid.uuid4())

def validate_host(host):
    """
    Validate if host is a valid IP address or domain name
    """
    # IPv4 regex
    ipv4_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    # IPv6 regex (simplified)
    ipv6_regex = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    
    return (re.match(ipv4_regex, host) or 
            re.match(ipv6_regex, host) or 
            re.match(domain_regex, host))

def parse_ports(input_str):
    """
    Parse port input string into a list of ports
    """
    ports = set()
    parts = input_str.split(',')
    
    for part in parts:
        part = part.strip()
        if part.isdigit():
            port = int(part)
            if 1 <= port <= 65535:
                ports.add(port)
        elif '-' in part:
            try:
                start, end = part.split('-', 1)
                start, end = int(start.strip()), int(end.strip())
                if 1 <= start <= 65535 and 1 <= end <= 65535:
                    for port in range(start, min(end + 1, 65536)):
                        ports.add(port)
            except ValueError:
                continue
    
    return sorted(list(ports))

def check_port(host, port, timeout=3):
    """
    Check if a specific port is open, closed, or filtered
    """
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        response_time = (time.time() - start_time) * 1000  # in milliseconds
        sock.close()
        
        if result == 0:
            return {
                "port": port,
                "status": "Open",
                "latency": round(response_time, 2)
            }
        else:
            return {
                "port": port,
                "status": "Closed",
                "latency": None
            }
    except socket.timeout:
        return {
            "port": port,
            "status": "Filtered",
            "latency": None
        }
    except Exception as e:
        return {
            "port": port,
            "status": "Error",
            "error": str(e),
            "latency": None
        }

def scan_ports(host, ports, max_threads=50):
    """
    Scan multiple ports using threading for speed
    """
    results = []
    threads = []
    
    def worker(port):
        result = check_port(host, port)
        results.append(result)
    
    # Create and start threads
    for i in range(0, len(ports), max_threads):
        batch = ports[i:i+max_threads]
        for port in batch:
            thread = threading.Thread(target=worker, args=(port,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads in the current batch to complete
        for thread in threads:
            thread.join()
        
        threads = []  # Reset for next batch
    
    # Sort results by port number
    results.sort(key=lambda x: x["port"])
    return results

def check_open_ports(host, port_input):
    """
    Main function to check open ports for a host
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting port scan for host: {host}")
    print(f"Ports to check: {port_input}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Scanning ports...",
        "session_id": session_id
    }
    
    try:
        # Validate host
        if not host or not validate_host(host):
            raise ValueError("Invalid hostname or IP address")
        
        # Parse ports
        ports = parse_ports(port_input)
        if not ports:
            raise ValueError("No valid ports specified")
        
        print(f"Parsed {len(ports)} ports to check")
        
        # Limit the number of ports to check to prevent abuse
        if len(ports) > 1000:
            raise ValueError("Too many ports specified. Maximum allowed is 1000.")
        
        # Perform the port scan
        print(f"Scanning {len(ports)} ports on {host}...")
        scan_results = scan_ports(host, ports)
        
        # Count open, closed, and filtered ports
        open_count = sum(1 for r in scan_results if r["status"] == "Open")
        closed_count = sum(1 for r in scan_results if r["status"] == "Closed")
        filtered_count = sum(1 for r in scan_results if r["status"] == "Filtered")
        error_count = sum(1 for r in scan_results if r["status"] == "Error")
        
        # Create final results
        results = {
            "status": "success",
            "host": host,
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
    host = os.environ.get("HOST")
    ports = os.environ.get("PORTS")
    
    if not host:
        print("ERROR: HOST environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "HOST environment variable not set.",
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
    
    if not ports:
        print("ERROR: PORTS environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "PORTS environment variable not set.",
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
        
    port_results = check_open_ports(host, ports)
    
    # The results are already printed in the function
    sys.exit(0)
