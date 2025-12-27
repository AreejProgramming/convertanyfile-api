#!/usr/bin/env python3
import os
import sys
import json
import time
import socket
import subprocess
import re
import shutil
from datetime import datetime

def generate_session_id():
    """Generate a unique session ID"""
    return f"{int(time.time())}-{os.getpid()}"

def validate_target(target):
    """Validate if the target is a valid domain or IP address"""
    if not target:
        return False
    
    # Remove protocol and path if present
    clean_target = target.strip()
    if clean_target.startswith(('http://', 'https://')):
        clean_target = clean_target.split('://', 1)[1]
    if '/' in clean_target:
        clean_target = clean_target.split('/', 1)[0]
    
    # Check if it's a valid IP address or domain
    try:
        socket.gethostbyname(clean_target)
        return True
    except socket.gaierror:
        return False

def get_target_ip(target):
    """Get the IP address of the target"""
    try:
        return socket.gethostbyname(target)
    except socket.gaierror:
        return None

def trace_route_simple(target, max_hops=30):
    """
    Perform a simple traceroute using the system's traceroute command
    This is more compatible with GitHub Actions environment
    """
    print(f"Performing traceroute to {target} with max {max_hops} hops")
    
    # Determine the traceroute command based on the OS
    if os.name == 'nt':  # Windows
        cmd = ['tracert', '-h', str(max_hops), target]
    else:  # Unix/Linux
        cmd = ['traceroute', '-m', str(max_hops), target]
    
    try:
        # Run the traceroute command
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60  # Timeout after 60 seconds
        )
        
        if result.returncode != 0:
            print(f"Traceroute command failed with return code {result.returncode}")
            print(f"Error output: {result.stderr}")
            return []
        
        # Parse the traceroute output
        hops = parse_traceroute_output(result.stdout)
        return hops
        
    except subprocess.TimeoutExpired:
        print("Traceroute command timed out")
        return []
    except Exception as e:
        print(f"Error running traceroute: {str(e)}")
        return []

def parse_traceroute_output(output):
    """Parse the output of the traceroute command"""
    hops = []
    lines = output.strip().split('\n')
    
    # Skip the first line (usually just the target)
    for i, line in enumerate(lines[1:], 1):
        # Skip empty lines
        if not line.strip():
            continue
            
        # Parse hop information
        hop_info = parse_hop_line(line, i)
        if hop_info:
            hops.append(hop_info)
    
    return hops

def parse_hop_line(line, hop_num):
    """Parse a single hop line from traceroute output"""
    # Remove leading whitespace
    line = line.strip()
    
    # Skip lines that don't start with a hop number
    if not line or not line[0].isdigit():
        return None
    
    # Extract the hop number
    hop_match = re.match(r'^(\d+)', line)
    if not hop_match:
        return None
    
    hop_number = int(hop_match.group(1))
    
    # Extract IP addresses and hostnames
    # This regex matches IP addresses and hostnames
    ip_pattern = r'(\d+\.\d+\.\d+\.\d+|\S+\.\S+)'
    matches = re.findall(ip_pattern, line)
    
    if not matches:
        return None
    
    # The first match is usually the IP address or hostname
    ip_or_hostname = matches[0]
    
    # Determine if it's an IP address or hostname
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip_or_hostname):
        ip = ip_or_hostname
        hostname = ip  # Use IP as hostname if no hostname is provided
    else:
        hostname = ip_or_hostname
        # Try to resolve the hostname to an IP
        try:
            ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            ip = hostname  # Use hostname as IP if resolution fails
    
    # Extract time measurements (in ms)
    time_pattern = r'(\d+\.?\d*)\s*ms'
    time_matches = re.findall(time_pattern, line)
    
    times = []
    for time_str in time_matches[:3]:  # Take only the first 3 measurements
        try:
            times.append(float(time_str))
        except ValueError:
            pass
    
    # Calculate average time
    avg_time = sum(times) / len(times) if times else 0
    
    return {
        'hop': hop_number,
        'ip': ip,
        'hostname': hostname,
        'times': times,
        'avgTime': avg_time,
        'status': 'success' if times else 'timeout'
    }

def trace_route(target, max_hops=30, timeout=2):
    """
    Main function to trace route to target
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting traceroute to: {target}")
    print(f"Session ID: {session_id}")
    print(f"Max hops: {max_hops}")
    
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
        
        # Check if we can resolve the target
        target_ip = get_target_ip(clean_target)
        if not target_ip:
            print(f"Warning: Could not resolve {clean_target} to an IP address")
        
        # Use simplified traceroute (more compatible with GitHub Actions)
        hops = trace_route_simple(clean_target, max_hops)
        
        if not hops:
            raise ValueError("No hops data collected. The traceroute command may have failed.")
        
        # Calculate total time
        total_time = sum(hop['avgTime'] for hop in hops)
        
        # Create final results
        results = {
            "status": "success",
            "target": clean_target,
            "target_ip": target_ip,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "hops": hops,
                "totalHops": len(hops),
                "totalTime": total_time,
                "maxHops": max_hops
            }
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always write results to the expected location
    results_path = 'results.json'
    try:
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results successfully written to {results_path}")
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        try:
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results successfully written to {results_path} after creating directory")
        except Exception as retry_error:
            print(f"ERROR writing results file on retry: {str(retry_error)}")
            # As a last resort, write to the home directory
            home_path = os.path.expanduser('~/results.json')
            try:
                with open(home_path, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"Results written to home directory: {home_path}")
                # Copy to expected location
                shutil.copy(home_path, results_path)
            except Exception as final_error:
                print(f"ERROR writing results file to home directory: {str(final_error)}")
                raise
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    # Get inputs from environment variables
    target = os.environ.get("TARGET", "example.com")
    max_hops = int(os.environ.get("MAX_HOPS", "30"))
    
    # Run the traceroute
    trace_route(target, max_hops)
