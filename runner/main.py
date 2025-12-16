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
    print(f"Starting accessibility check for URL: {url}") # Log for debugging
    
    results = {"status": "error", "message": "Analysis failed to start."}
    
    try:
        # Use sync_playwright as a context manager
        with sync_playwright() as p:
            print("Launching browser...")
            # Launch the browser using the playwright instance 'p'
            browser = p.chromium.launch(headless=True) # Explicitly launch chromium
            
            print("Navigating to page...")
            page = browser.new_page()
            
            # Go to the page and wait for it to be reasonably loaded
            # Use a longer timeout for slow websites
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            print("Injecting axe-core...")
            # Inject the axe-core library into the page
            page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
            
            print("Running axe analysis...")
            # Run the axe analysis
            axe_results = page.evaluate("axe.run()")
            
            print("Analysis complete. Closing browser.")
            # The 'with' statement will handle closing the browser automatically
            
            results = {
                "status": "success",
                "url": url,
                "timestamp": time.time(),
                "data": axe_results
            }

    except PlaywrightTimeoutError as e:
        print(f"ERROR: A timeout occurred. The page took too long to load. Details: {e}")
        results = {"status": "error", "message": f"Timeout: The page took too long to load."}
    except Exception as e:
        # Catch any other exception
        print(f"ERROR: An unexpected error occurred. Details: {e}")
        results = {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
            
    return results

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        sys.exit(1)
        
    analysis_results = run_accessibility_check(target_url)
    
    # Print the results in a format that can be easily extracted
    print(f"results={json.dumps(analysis_results)}")
