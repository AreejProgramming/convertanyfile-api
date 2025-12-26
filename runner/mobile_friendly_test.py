import os
import json
import time
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def generate_session_id():
    return str(uuid.uuid4())

def validate_url(url):
    """
    Validate if input is a valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def setup_webdriver():
    """
    Set up Chrome webdriver
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=375,812")  # Mobile viewport size
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1")
        
        # Use webdriver-manager to handle ChromeDriver automatically
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        return driver
    except Exception as e:
        print(f"Error setting up webdriver: {str(e)}")
        return None

def check_viewport_configuration(driver, url):
    """
    Check if page has a proper viewport meta tag
    """
    try:
        driver.get(url)
        # Wait for page to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check for viewport meta tag
        viewport_meta = driver.find_elements(By.XPATH, "//meta[@name='viewport']")
        if viewport_meta:
            content = viewport_meta[0].get_attribute("content")
            if content and ("width=device-width" in content or "initial-scale=1" in content):
                return {
                    "name": "Viewport Configuration",
                    "status": "pass",
                    "description": "Page has a <meta name=\"viewport\"> tag with width or initial-scale set."
                }
        
        return {
            "name": "Viewport Configuration",
            "status": "fail",
            "description": "Page is missing a proper <meta name=\"viewport\"> tag."
        }
    except Exception as e:
        print(f"Error checking viewport configuration: {str(e)}")
        return {
            "name": "Viewport Configuration",
            "status": "fail",
            "description": "Could not verify viewport configuration."
        }

def check_text_readability(driver, url):
    """
    Check if text is readable without zooming
    """
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check for font size using JavaScript
        font_size = driver.execute_script("""
            var paragraphs = document.querySelectorAll('p, div, span, h1, h2, h3, h4, h5, h6');
            if (paragraphs.length === 0) return 0;
            
            var totalSize = 0;
            var count = 0;
            
            for (var i = 0; i < paragraphs.length; i++) {
                var style = window.getComputedStyle(paragraphs[i]);
                if (style.fontSize && style.fontSize !== '0px') {
                    totalSize += parseFloat(style.fontSize);
                    count++;
                }
            }
            
            return count > 0 ? totalSize / count : 0;
        """)
        
        # Convert to pixels and check if it's at least 16px
        if font_size >= 16:
            return {
                "name": "Text Readability",
                "status": "pass",
                "description": "Text is legible without zooming."
            }
        
        return {
            "name": "Text Readability",
            "status": "fail",
            "description": "Text is too small and requires zooming to be readable."
        }
    except Exception as e:
        print(f"Error checking text readability: {str(e)}")
        return {
            "name": "Text Readability",
            "status": "fail",
            "description": "Could not verify text readability."
        }

def check_touch_targets(driver, url):
    """
    Check if buttons and links are large enough to be easily tapped
    """
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check for button and link sizes using JavaScript
        touch_targets_ok = driver.execute_script("""
            var buttons = document.querySelectorAll('button, a, input[type="button"], input[type="submit"], [role="button"]');
            if (buttons.length === 0) return true;
            
            for (var i = 0; i < buttons.length; i++) {
                var rect = buttons[i].getBoundingClientRect();
                var width = rect.width;
                var height = rect.height;
                
                // Check if element is visible and has a minimum size of 48x48px
                if (width > 0 && height > 0 && (width < 48 || height < 48)) {
                    return false;
                }
            }
            
            return true;
        """)
        
        if touch_targets_ok:
            return {
                "name": "Touch Targets",
                "status": "pass",
                "description": "Links and buttons are large enough to be easily tapped."
            }
        
        return {
            "name": "Touch Targets",
            "status": "fail",
            "description": "Some links or buttons are too small to be easily tapped."
        }
    except Exception as e:
        print(f"Error checking touch targets: {str(e)}")
        return {
            "name": "Touch Targets",
            "status": "fail",
            "description": "Could not verify touch targets."
        }

def check_content_sizing(driver, url):
    """
    Check if content fits to screen horizontally
    """
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check if horizontal scrolling is needed using JavaScript
        fits_screen = driver.execute_script("""
            return document.body.scrollWidth <= window.innerWidth;
        """)
        
        if fits_screen:
            return {
                "name": "Content Sizing",
                "status": "pass",
                "description": "Content fits to screen horizontally, avoiding the need for horizontal scrolling."
            }
        
        return {
            "name": "Content Sizing",
            "status": "fail",
            "description": "Content is too wide and requires horizontal scrolling on mobile devices."
        }
    except Exception as e:
        print(f"Error checking content sizing: {str(e)}")
        return {
            "name": "Content Sizing",
            "status": "fail",
            "description": "Could not verify content sizing."
        }

def check_plugin_compatibility(driver, url):
    """
    Check if page avoids using plugins that are not common on mobile platforms
    """
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Check for Flash, Silverlight, or other mobile-incompatible plugins
        has_flash = driver.execute_script("""
            var hasFlash = false;
            var objects = document.querySelectorAll('object, embed');
            
            for (var i = 0; i < objects.length; i++) {
                var type = objects[i].type || '';
                if (type.indexOf('flash') !== -1 || type.indexOf('x-shockwave-flash') !== -1) {
                    hasFlash = true;
                    break;
                }
            }
            
            return hasFlash;
        """)
        
        if not has_flash:
            return {
                "name": "Plugin Compatibility",
                "status": "pass",
                "description": "Page avoids using plugins that are not common on mobile platforms."
            }
        
        return {
            "name": "Plugin Compatibility",
            "status": "fail",
            "description": "Page uses plugins that are not supported on most mobile devices."
        }
    except Exception as e:
        print(f"Error checking plugin compatibility: {str(e)}")
        return {
            "name": "Plugin Compatibility",
            "status": "fail",
            "description": "Could not verify plugin compatibility."
        }

def check_page_speed(driver, url):
    """
    Check if page loads in a reasonable amount of time
    """
    try:
        start_time = time.time()
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Additional wait for page to fully render
        time.sleep(2)
        
        load_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if load_time <= 3000:  # 3 seconds or less is good
            return {
                "name": "Page Speed",
                "status": "pass",
                "description": "Page loads in a reasonable amount of time on mobile networks."
            }
        
        return {
            "name": "Page Speed",
            "status": "fail",
            "description": "Page takes too long to load on mobile networks."
        }
    except Exception as e:
        print(f"Error checking page speed: {str(e)}")
        return {
            "name": "Page Speed",
            "status": "fail",
            "description": "Could not verify page load time."
        }

def generate_recommendations(checks):
    """
    Generate recommendations based on failed checks
    """
    recommendations = []
    
    for check in checks:
        if check["status"] == "fail":
            if check["name"] == "Touch Targets":
                recommendations.append("Increase the size of buttons and links to be at least 48x48px for easier tapping.")
            elif check["name"] == "Text Readability":
                recommendations.append("Use a legible font size (at least 16px) and ensure good contrast for better readability.")
            elif check["name"] == "Page Speed":
                recommendations.append("Optimize images, leverage browser caching, and minimize redirects to improve load times.")
            elif check["name"] == "Viewport Configuration":
                recommendations.append("Add a viewport meta tag with width=device-width or initial-scale=1 to ensure proper rendering on mobile devices.")
            elif check["name"] == "Content Sizing":
                recommendations.append("Use responsive design techniques like flexible grids and media queries to ensure content fits on smaller screens.")
            elif check["name"] == "Plugin Compatibility":
                recommendations.append("Replace Flash or other mobile-incompatible plugins with HTML5 alternatives.")
    
    return recommendations

def calculate_mobile_friendliness_score(checks):
    """
    Calculate an overall mobile-friendliness score based on checks
    """
    passed_checks = sum(1 for check in checks if check["status"] == "pass")
    total_checks = len(checks)
    
    # Base score is the percentage of passed checks
    base_score = (passed_checks / total_checks) * 100
    
    # Adjust score based on critical checks
    critical_checks = ["Viewport Configuration", "Content Sizing"]
    failed_critical = sum(1 for check in checks if check["status"] == "fail" and check["name"] in critical_checks)
    
    # Deduct 15 points for each failed critical check
    adjusted_score = max(0, base_score - (failed_critical * 15))
    
    return round(adjusted_score)

def test_mobile_friendliness(url):
    """
    Main function to test if a website is mobile-friendly
    """
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    print(f"Starting mobile-friendliness test for: {url}")
    print(f"Session ID: {session_id}")
    
    # Initialize results
    results = {
        "status": "processing", 
        "message": "Testing mobile-friendliness...",
        "session_id": session_id
    }
    
    driver = None
    try:
        # Validate URL
        if not validate_url(url):
            raise ValueError("Invalid URL format")
        
        # Set up webdriver
        print("Setting up webdriver...")
        driver = setup_webdriver()
        
        if not driver:
            raise ValueError("Failed to set up webdriver")
        
        # Run all checks
        print("Running mobile-friendliness checks...")
        checks = [
            check_viewport_configuration(driver, url),
            check_text_readability(driver, url),
            check_touch_targets(driver, url),
            check_content_sizing(driver, url),
            check_plugin_compatibility(driver, url),
            check_page_speed(driver, url)
        ]
        
        # Generate recommendations
        recommendations = generate_recommendations(checks)
        
        # Calculate overall score
        overall_score = calculate_mobile_friendliness_score(checks)
        is_mobile_friendly = overall_score >= 80
        
        # Create final results
        results = {
            "status": "success",
            "url": url,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": {
                "overallScore": overall_score,
                "isMobileFriendly": is_mobile_friendly,
                "checks": checks,
                "recommendations": recommendations
            }
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    finally:
        # Clean up webdriver
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    # Always write results to file, even if there was an error
    try:
        # Try multiple locations for the results file
        locations = [
            f'results_{session_id}.json',
            'results.json',
            f'/tmp/results_{session_id}.json'
        ]
        
        for location in locations:
            try:
                directory = os.path.dirname(location)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                
                with open(location, 'w') as f:
                    json.dump(results, f)
                print(f"Results successfully written to {location}")
                return
            except Exception as e:
                print(f"Failed to write to {location}: {str(e)}")
                continue
        
        # Final fallback - output to stdout
        print(f"results={json.dumps(results)}")
        
    except Exception as file_error:
        print(f"ERROR writing results file: {str(file_error)}")
        # Final fallback - output to stdout
        print(f"results={json.dumps(results)}")
    
    return results

if __name__ == "__main__":
    url = os.environ.get("URL")
    if not url:
        print("ERROR: URL environment variable not set.")
        error_result = {
            "status": "error", 
            "message": "URL environment variable not set.",
            "session_id": os.environ.get("SESSION_ID", "unknown")
        }
        
        # Write error results to file
        try:
            # Try multiple locations for the results file
            session_id = os.environ.get("SESSION_ID", "unknown")
            locations = [
                f'results_{session_id}.json',
                'results.json',
                f'/tmp/results_{session_id}.json'
            ]
            
            for location in locations:
                try:
                    directory = os.path.dirname(location)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                    
                    with open(location, 'w') as f:
                        json.dump(error_result, f)
                    print(f"Error results written to {location}")
                    return
                except Exception as e:
                    print(f"Failed to write to {location}: {str(e)}")
                    continue
        except Exception as file_error:
            print(f"ERROR writing error results file: {str(file_error)}")
        
        print(f"results={json.dumps(error_result)}")
        sys.exit(1)
        
    mobile_results = test_mobile_friendliness(url)
    
    # The results are already printed in the function
    sys.exit(0)
