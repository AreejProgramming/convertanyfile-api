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

def validate_target(target):
    """
    Validate if input is a valid domain name or IP address
    """
    # Remove protocol if present
    if target.startswith(('http://', 'https://')):
        target = target.split('://', 1)[1]
    
    # Remove path if present
    if '/' in target:
        target = target.split('/', 1)[0]
    
    # Domain name regex
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    # IPv4 regex
    ip_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    
    return re.match(domain_regex, target) or re.match(ip_regex, target)

def run_traceroute(target, max_hops=30, timeout=2):
    """
    Run traceroute command and parse the output
    """
    try:
        # Run traceroute command with specific parameters
        # Using -n for numeric output, -w for timeout, -m for max hops
        cmd = ['traceroute', '-n', '-w', str(timeout), '-m', str(max_hops), target]
        
        # Measure execution time
        start_time = time.time()
        
        # Execute traceroute
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60  # Overall timeout for the command
        )
        
        execution_time = (time.time() - start_time) * 1000  # milliseconds
        
        if result.returncode != 0:
            return {
                'target': target,
                'success': False,
                'error': result.stderr.strip() or "Traceroute command failed",
                'executionTime': execution_time
            }
        
        # Parse traceroute output
        hops = parse_traceroute_output(result.stdout)
        
        return {
            'target': target,
            'success': True,
            'hops': hops,
            'executionTime': execution_time,
            'totalHops': len(hops)
        }
        
    except subprocess.TimeoutExpired:
        return {
            'target': target,
            'success': False,
            'error': "Traceroute command timed out",
            'errorType': 'TIMEOUT_ERROR'
        }
    except Exception as e:
        return {
            'target': target,
            'success': False,
            'error': f"Unexpected error: {str(e)}",
            'errorType': 'UNKNOWN_ERROR'
        }

def parse_traceroute_output(output):
    """
    Parse the output of traceroute command
    """
    hops = []
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Parse hop information
        hop = parse_hop_line(line)
        if hop:
            hops.append(hop)
    
    return hops

def parse_hop_line(line):
    """
    Parse a single line from traceroute output
    """
    # Skip empty lines or header lines
    if not line or line.startswith('traceroute to'):
        return None
    
    # Try to extract hop number, IP, and time values
    # This regex handles various traceroute output formats
    hop_pattern = r'^\s*(\d+)\s+([^\s]+)\s+([^\s]+)'
    match = re.search(hop_pattern, line)
    
    if not match:
        # Try alternative pattern for lines with time measurements
        alt_pattern = r'^\s*(\d+)\s+([^\s]+)\s+([0-9.]+)'
        alt_match = re.search(alt_pattern, line)
        
        if alt_match:
            hop_num = int(alt_match.group(1))
            ip_or_host = alt_match.group(2)
            time_str = alt_match.group(3)
            
            # Parse time values (can be multiple measurements)
            times = []
            if 'ms' in time_str:
                time_parts = time_str.replace('ms', '').split()
                times = [float(t) for t in time_parts if t.replace('.', '', 1).isdigit()]
            
            # Determine if this is the destination
            is_destination = 'Destination' in line or '*' not in line
            
            return {
                'hop': hop_num,
                'ip': ip_or_host,
                'hostname': ip_or_host if is_destination else f"hop-{hop_num}.example.com",
                'times': times,
                'avgTime': sum(times) / len(times) if times else 0,
                'status': 'success' if is_destination else 'intermediate'
            }
    
    return None

def trace_route(target):
    """
    Main function to trace route to target
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting traceroute to: {target}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Tracing route to target...",
        "session_id": session_id
    }
    
    try:
        # Validate and clean target
        if not target or not validate_target(target):
            raise ValueError("Invalid target format")
        
        # Clean target (remove protocol and path)
        clean_target = target.strip()
        if clean_target.startswith(('http://', 'https://')):
            clean_target = clean_target.split('://', 1)[1]
        if '/' in clean_target:
            clean_target = clean_target.split('/', 1)[0]
        
        print(f"Cleaned target: {clean_target}")
        
        # Run traceroute
        print(f"Running traceroute to {clean_target}...")
        trace_data = run_traceroute(clean_target)
        
        if not trace_data.get('success'):
            raise ValueError(trace_data.get('error', 'Traceroute failed'))
        
        # Calculate total time
        total_time = sum(hop['avgTime'] for hop in trace_data['hops'])
        
        # Create final results
        results = {
            "status": "success",
            "target": clean_target,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "hops": trace_data['hops'],
                "totalHops": trace_data['totalHops'],
                "totalTime": total_time,
                "executionTime": trace_data['executionTime']
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
        
    trace_results = trace_route(target)
    
    # The results are already printed in the function
    sys.exit(0)
