# runner/main.py
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
    browser = None
    try:
        print("Launching browser...")
        browser = sync_playwright().launch() # Use default launch options for now
        
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
        browser.close()
        
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
    finally:
        # Ensure browser is closed even if an error occurred
        if browser:
            browser.close()
            print("Browser closed in finally block.")
            
    return results

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("ERROR: TARGET_URL environment variable not set.")
        sys.exit(1)
        
    analysis_results = run_accessibility_check(target_url)
    
    # Save the results to the GITHUB_OUTPUT file
    output_path = os.environ.get("GITHUB_OUTPUT")
    
    # The format for GITHUB_OUTPUT is 'name=value'
    with open(output_path, "a") as f:
        f.write(f"results={json.dumps(analysis_results)}\n")

    print("Successfully wrote results to GITHUB_OUTPUT.")
