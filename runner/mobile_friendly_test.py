import os
import json
import time
import sys
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import uuid
from bs4 import BeautifulSoup
import socket

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

def get_page_content(url, timeout=10):
    """
    Get page content using requests with proper headers
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content': response.text,
            'url': response.url,
            'response_time': response.elapsed.total_seconds() * 1000  # in milliseconds
        }
    except requests.RequestException as e:
        print(f"Error fetching page: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def check_viewport_configuration(content, url):
    """
    Check if page has a proper viewport meta tag
    """
    try:
        soup = BeautifulSoup(content, 'html.parser')
        viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
        
        if viewport_meta and viewport_meta.get('content'):
            content = viewport_meta['content'].lower()
            if 'width=device-width' in content or 'initial-scale=1' in content:
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

def check_text_readability(content, url):
    """
    Check if text is readable without zooming (simplified check)
    """
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check for base font size in CSS
        style_tags = soup.find_all('style')
        has_small_font = False
        
        for style in style_tags:
            if style.string:
                # Look for font-size declarations
                font_matches = re.findall(r'font-size\s*:\s*([0-9.]+)(px|em|rem|%)', style.string, re.IGNORECASE)
                for match in font_matches:
                    try:
                        size = float(match.group(1))
                        if size < 14:  # Less than 14px is generally too small
                            has_small_font = True
                            break
                    except:
                        continue
        
        # Also check inline styles
        inline_styles = soup.find_all(style=True)
        for tag in inline_styles:
            if tag.get('style'):
                font_matches = re.findall(r'font-size\s*:\s*([0-9.]+)(px|em|rem|%)', tag['style'], re.IGNORECASE)
                for match in font_matches:
                    try:
                        size = float(match.group(1))
                        if size < 14:
                            has_small_font = True
                            break
                    except:
                        continue
        
        # Check for body text size
        body_tag = soup.find('body')
        if body_tag and body_tag.get('style'):
            font_matches = re.findall(r'font-size\s*:\s*([0-9.]+)(px|em|rem|%)', body_tag['style'], re.IGNORECASE)
            for match in font_matches:
                try:
                    size = float(match.group(1))
                    if size < 14:
                        has_small_font = True
                        break
                except:
                    continue
        
        if not has_small_font:
            return {
                "name": "Text Readability",
                "status": "pass",
                "description": "Text appears to be legible without zooming."
            }
        
        return {
            "name": "Text Readability",
            "status": "fail",
            "description": "Text may be too small and requires zooming to be readable."
        }
    except Exception as e:
        print(f"Error checking text readability: {str(e)}")
        return {
            "name": "Text Readability",
            "status": "fail",
            "description": "Could not verify text readability."
        }

def check_touch_targets(content, url):
    """
    Check if buttons and links are large enough (simplified check)
    """
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Count small interactive elements
        small_buttons = 0
        small_links = 0
        total_interactive = 0
        
        # Check buttons
        buttons = soup.find_all(['button', 'input'])
        for button in buttons:
            total_interactive += 1
            # Check for size in style
            style = button.get('style', '')
            if 'height' in style.lower() or 'width' in style.lower():
                # Extract height and width values
                height_match = re.search(r'height\s*:\s*([0-9.]+)(px|em|rem)', style, re.IGNORECASE)
                width_match = re.search(r'width\s*:\s*([0-9.]+)(px|em|rem)', style, re.IGNORECASE)
                
                if height_match and width_match:
                    try:
                        height = float(height_match.group(1))
                        width = float(width_match.group(1))
                        # Consider small if less than 44px in either dimension
                        if height < 44 or width < 44:
                            small_buttons += 1
                    except:
                        pass
        
        # Check links
        links = soup.find_all('a')
        for link in links:
            if link.get('href'):
                total_interactive += 1
                style = link.get('style', '')
                if 'height' in style.lower() or 'width' in style.lower():
                    height_match = re.search(r'height\s*:\s*([0-9.]+)(px|em|rem)', style, re.IGNORECASE)
                    width_match = re.search(r'width\s*:\s*([0-9.]+)(px|em|rem)', style, re.IGNORECASE)
                    
                    if height_match and width_match:
                        try:
                            height = float(height_match.group(1))
                            width = float(width_match.group(1))
                            if height < 44 or width < 44:
                                small_links += 1
                        except:
                            pass
        
        # Calculate percentage of properly sized elements
        if total_interactive > 0:
            small_percentage = ((small_buttons + small_links) / total_interactive) * 100
            if small_percentage <= 20:  # Less than 20% are too small
                return {
                    "name": "Touch Targets",
                    "status": "pass",
                    "description": "Links and buttons appear to be properly sized for touch interaction."
                }
        
        return {
            "name": "Touch Targets",
            "status": "fail",
            "description": "Some links or buttons may be too small for easy tapping."
        }
    except Exception as e:
        print(f"Error checking touch targets: {str(e)}")
        return {
            "name": "Touch Targets",
            "status": "fail",
            "description": "Could not verify touch targets."
        }

def check_content_sizing(content, url):
    """
    Check if content uses responsive design patterns
    """
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check for responsive meta tags
        has_viewport = bool(soup.find('meta', attrs={'name': 'viewport'}))
        
        # Check for media queries in CSS
        style_tags = soup.find_all('style')
        has_media_queries = False
        
        for style in style_tags:
            if style.string and '@media' in style.string:
                has_media_queries = True
                break
        
        # Check for responsive CSS classes
        responsive_classes = ['container', 'container-fluid', 'row', 'col', 'col-sm', 'col-md', 'col-lg', 'responsive', 'mobile']
        has_responsive_classes = any(
            soup.find(class_=cls) for cls in responsive_classes
        )
        
        # Check for flexible grid layouts
        has_flex = bool(soup.find(style=re.compile(r'display\s*:\s*flex')))
        
        # Check for percentage-based widths
        has_percent_width = bool(soup.find(style=re.compile(r'width\s*:\s*[0-9.]+%')))
        
        # Consider responsive if any indicators are present
        is_responsive = has_viewport or has_media_queries or has_responsive_classes or has_flex or has_percent_width
        
        if is_responsive:
            return {
                "name": "Content Sizing",
                "status": "pass",
                "description": "Content appears to use responsive design techniques."
            }
        
        return {
            "name": "Content Sizing",
            "status": "fail",
            "description": "Content may not be optimized for different screen sizes."
        }
    except Exception as e:
        print(f"Error checking content sizing: {str(e)}")
        return {
            "name": "Content Sizing",
            "status": "fail",
            "description": "Could not verify content sizing."
        }

def check_plugin_compatibility(content, url):
    """
    Check if page avoids using outdated plugins
    """
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check for Flash content
        flash_objects = soup.find_all(['object', 'embed'])
        has_flash = False
        
        for obj in flash_objects:
            if obj.get('type', '').lower() in ['application/x-shockwave-flash', 'application/x-flash']:
                has_flash = True
                break
            if 'flash' in obj.get('src', '').lower():
                has_flash = True
                break
        
        # Check for Java applets
        java_applets = soup.find_all('applet')
        has_java = len(java_applets) > 0
        
        # Check for Silverlight
        silverlight_objects = soup.find_all('object')
        has_silverlight = False
        for obj in silverlight_objects:
            if 'silverlight' in obj.get('type', '').lower():
                has_silverlight = True
                break
        
        if not has_flash and not has_java and not has_silverlight:
            return {
                "name": "Plugin Compatibility",
                "status": "pass",
                "description": "Page avoids using outdated plugins that are not mobile-friendly."
            }
        
        return {
            "name": "Plugin Compatibility",
            "status": "fail",
            "description": "Page uses plugins that may not be supported on mobile devices."
        }
    except Exception as e:
        print(f"Error checking plugin compatibility: {str(e)}")
        return {
            "name": "Plugin Compatibility",
            "status": "fail",
            "description": "Could not verify plugin compatibility."
        }

def check_page_speed(page_data, url):
    """
    Check page load time
    """
    try:
        response_time = page_data.get('response_time', 0)
        
        # Check response time
        if response_time <= 3000:  # 3 seconds or less is good
            return {
                "name": "Page Speed",
                "status": "pass",
                "description": "Page loads quickly on mobile networks."
            }
        elif response_time <= 5000:  # 5 seconds or less is acceptable
            return {
                "name": "Page Speed",
                "status": "pass",
                "description": "Page load time is acceptable for mobile users."
            }
        else:
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
                recommendations.append("Ensure buttons and links are at least 44x44px for easy tapping on mobile devices.")
            elif check["name"] == "Text Readability":
                recommendations.append("Use a base font size of at least 14px and ensure good color contrast for better readability.")
            elif check["name"] == "Page Speed":
                recommendations.append("Optimize images, minimize HTTP requests, and use browser caching to improve load times.")
            elif check["name"] == "Viewport Configuration":
                recommendations.append("Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> to ensure proper mobile rendering.")
            elif check["name"] == "Content Sizing":
                recommendations.append("Implement responsive design with CSS media queries and flexible layouts for different screen sizes.")
            elif check["name"] == "Plugin Compatibility":
                recommendations.append("Replace Flash and other outdated plugins with modern HTML5 alternatives.")
    
    return recommendations

def calculate_mobile_friendliness_score(checks):
    """
    Calculate an overall mobile-friendliness score
    """
    if not checks:
        return 50
    
    passed_checks = sum(1 for check in checks if check["status"] == "pass")
    total_checks = len(checks)
    
    # Base score is percentage of passed checks
    base_score = (passed_checks / total_checks) * 100
    
    # Adjust score based on critical checks
    critical_checks = ["Viewport Configuration", "Content Sizing"]
    failed_critical = sum(1 for check in checks if check["status"] == "fail" and check["name"] in critical_checks)
    
    # Deduct 20 points for each failed critical check
    adjusted_score = max(0, base_score - (failed_critical * 20))
    
    return round(adjusted_score)

def test_mobile_friendliness(url):
    """
    Main function to test if a website is mobile-friendly using free APIs
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
    
    try:
        # Validate URL
        if not validate_url(url):
            raise ValueError("Invalid URL format")
        
        print(f"Fetching page content for {url}...")
        page_data = get_page_content(url)
        
        if not page_data:
            raise ValueError("Failed to fetch page content")
        
        print("Running mobile-friendliness checks...")
        checks = [
            check_viewport_configuration(page_data['content'], url),
            check_text_readability(page_data['content'], url),
            check_touch_targets(page_data['content'], url),
            check_content_sizing(page_data['content'], url),
            check_plugin_compatibility(page_data['content'], url),
            check_page_speed(page_data, url)
        ]
        
        # Generate recommendations
        recommendations = generate_recommendations(checks)
        
        # Calculate overall score
        overall_score = calculate_mobile_friendliness_score(checks)
        is_mobile_friendly = overall_score >= 75  # Slightly lower threshold for API-based checks
        
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
                "recommendations": recommendations,
                "responseTime": page_data.get('response_time', 0),
                "statusCode": page_data.get('status_code', 0)
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
            
            print(f"results={json.dumps(error_result)}")
        except Exception as file_error:
            print(f"ERROR writing error results file: {str(file_error)}")
            print(f"results={json.dumps(error_result)}")
        
        sys.exit(1)
        
    mobile_results = test_mobile_friendliness(url)
    
    # The results are already printed in the function
    sys.exit(0)
