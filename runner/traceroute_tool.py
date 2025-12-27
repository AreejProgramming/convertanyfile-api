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
            # Try simplified traceroute that doesn't require raw sockets
            hops = trace_route_simple(clean_target, max_hops)
        else:
            # Use simplified traceroute (more compatible with GitHub Actions)
            hops = trace_route_simple(clean_target, max_hops)
        
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
