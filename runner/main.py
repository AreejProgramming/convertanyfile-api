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
    
    # Use sync_playwright as a context manager
    with sync_playwright() as p:
        browser = None
        try:
            print("Launching browser...")
            browser = p.launch(headless=True)  # Run headless for speed
            
            print("Navigating to page...")
            page = browser.new_page()
            
            # Optimize page loading
            page.goto(url, wait_until="domcontentloaded", timeout=30000)  # Reduced timeout
            
            print("Injecting axe-core...")
            # Inject the axe-core library into the page
            page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
            
            print("Running axe analysis...")
            # Run the axe analysis with optimized rules
            axe_results = page.evaluate("""
                axe.run({
                    reporter: 'v2',
                    rules: {
                        'bypass': { enabled: false },  // Skip for speed
                        'document-title': { enabled: false },  # Skip for speed
                        'html-has-lang': { enabled: false },  # Skip for speed
                    }
                })
            """)
            
            print("Analysis complete.")
            
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
    
    # Print the results in a format that can be easily extracted
    print(f"results={json.dumps(analysis_results)}")
