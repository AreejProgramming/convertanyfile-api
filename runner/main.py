# runner/main.py
import os
import json
import time
from playwright.sync_api import sync_playwright

def run_accessibility_check(url):
    results = {"status": "error", "message": "Analysis failed to start."}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Go to the page and wait for it to be reasonably loaded
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Inject the axe-core library into the page
            page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
            
            # Run the axe analysis
            axe_results = page.evaluate("axe.run()")
            
            browser.close()
            
            results = {
                "status": "success",
                "url": url,
                "timestamp": time.time(),
                "data": axe_results
            }

    except Exception as e:
        print(f"An error occurred: {e}")
        results = {"status": "error", "message": str(e)}

    return results

if __name__ == "__main__":
    target_url = os.environ.get("TARGET_URL")
    if not target_url:
        print("Error: TARGET_URL environment variable not set.")
        exit(1)

    analysis_results = run_accessibility_check(target_url)
    
    # Save the results to a file
    output_path = os.environ.get("GITHUB_OUTPUT")
    with open(output_path, "a") as f:
        f.write(f"results={json.dumps(analysis_results)}\n")

