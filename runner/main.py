import os
import json
import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def run_accessibility_check(url):
    """
    Launches a browser, runs axe-core, and returns the results.
    Includes robust error handling and logging.
    """
    print(f"Starting accessibility check for URL: {url}", file=sys.stderr) # Log to stderr
    
    results = {"status": "error", "message": "Analysis failed to start."}
    browser = None
    try:
        print("Launching browser...", file=sys.stderr)
        browser = sync_playwright().launch() # Use default launch options for now
        
        print("Navigating to page...", file=sys.stderr)
        page = browser.new_page()
        
        # Go to the page and wait for it to be reasonably loaded
        # Use a longer timeout for slow websites
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        print("Injecting axe-core...", file=sys.stderr)
        # Inject the axe-core library into the page
        page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
        
        print("Running axe analysis...", file=sys.stderr)
        # Run the axe analysis
        axe_results = page.evaluate("axe.run()")
        
        print("Analysis complete. Closing browser.", file=sys.stderr)
        browser.close()
        
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "data": axe_results
        }

    except PlaywrightTimeoutError as e:
        print(f"ERROR: A timeout occurred. The page took too long to load. Details: {e}", file=sys.stderr)
        results = {"status": "error", "message": f"Timeout: The page took too long to load."}
    except Exception as e:
        # Catch any other exception
        print(f"ERROR: An unexpected error occurred. Details: {e}", file=sys.stderr)
        results = {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    finally:
        # Ensure browser is closed even if an error occurred
        if browser:
            browser.close()
            print("Browser closed in finally block.", file=sys.stderr)
            
    return results

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print(json.dumps({"status": "error", "message": "TARGET_URL environment variable not set."}))
        sys.exit(1)
        
    analysis_results = run_accessibility_check(target_url)
    
    # Print the results directly to stdout (not to GITHUB_OUTPUT)
    print(json.dumps(analysis_results))
    sys.exit(0)
