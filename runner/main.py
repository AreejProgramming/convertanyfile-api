import os
import json
import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def run_accessibility_check(url):
    """
    Launches a browser, runs axe-core, and returns the results.
    Optimized for speed.
    """
    print(f"Starting accessibility check for URL: {url}")
    
    results = {"status": "error", "message": "Analysis failed to start."}
    
    try:
        with sync_playwright() as p:
            print("Launching browser...")
            # Use faster browser launch options
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--disable-translate',
                    '--disable-device-discovery-notifications',
                    '--disable-software-rasterizer',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
            )
            
            print("Creating context with faster settings...")
            # Create a browser context with optimized settings
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                ignore_https_errors=True,
                java_script_enabled=True
            )
            
            print("Navigating to page...")
            page = context.new_page()
            
            # Use a shorter timeout and wait for a more specific event
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait a short time for dynamic content to load
            page.wait_for_timeout(2000)
            
            print("Injecting axe-core...")
            # Inject the axe-core library into the page
            page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
            
            # Wait a moment for axe to initialize
            page.wait_for_timeout(1000)
            
            print("Running axe analysis with optimized rules...")
            # Run only the most important accessibility rules for faster analysis
            axe_results = page.evaluate("""
                axe.run({
                    rules: {
                        // Include only critical and serious impact rules
                        'color-contrast': { enabled: true },
                        'image-alt': { enabled: true },
                        'button-name': { enabled: true },
                        'link-name': { enabled: true },
                        'label': { enabled: true },
                        'html-has-lang': { enabled: true },
                        'page-title': { enabled: true },
                        'frame-title': { enabled: true },
                        'document-title': { enabled: true },
                        // Disable less critical rules for speed
                        'bypass': { enabled: false },
                        'html-lang-valid': { enabled: false },
                        'landmark-one-main': { enabled: false },
                        'meta-viewport': { enabled: false },
                        'region': { enabled: false }
                    }
                })
            """)
            
            print("Analysis complete. Closing browser.")
            context.close()
            browser.close()
            
            results = {
                "status": "success",
                "url": url,
                "timestamp": time.time(),
                "data": axe_results
            }

    except PlaywrightTimeoutError as e:
        print(f"ERROR: A timeout occurred. Details: {e}")
        results = {"status": "error", "message": f"Timeout: The page took too long to load."}
    except Exception as e:
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
