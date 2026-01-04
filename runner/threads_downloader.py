# runner/threads_downloader.py
import json
import os
import sys
import argparse
import subprocess
import re
import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import concurrent.futures
import threading
import time

# Thread-safe cache for storing video information
video_cache = {}
cache_lock = threading.Lock()

def extract_post_id(url):
    """Extract post ID from Threads URL"""
    # Handle different Threads URL formats
    patterns = [
        r'(?:threads\.net)\/.+/post\/(\w+)',
        r'(?:threads\.net)\/t\/(\w+)',  # Short URL format
        r'(?:threads\.net)\/@([\w\.]+)\/post\/(\w+)'  # Full format with username
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            # For patterns with username, return the post ID (second group)
            return match.group(2) if len(match.groups()) > 1 else match.group(1)
    
    return None

def get_video_info_with_ytdlp(url):
    """
    Uses yt-dlp with updated authentication methods to extract video information from a Threads URL.
    """
    # Try multiple approaches to get the video
    commands = [
        # First attempt: with Instagram API headers (Threads is part of Instagram)
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'User-Agent:Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            '--add-header', 'Accept-Language:en-US,en;q=0.9',
            '--add-header', 'Referer:https://www.threads.net/',
            '--extractor-args', 'instagram:api=mobile',
            url
        ],
        # Second attempt: with desktop user agent and different API
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            '--extractor-args', 'instagram:api=desktop',
            url
        ],
        # Third attempt: with cookies approach
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'User-Agent:Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            '--extractor-args', 'instagram:api=mobile',
            '--cookies', '/dev/null',  # This tells yt-dlp to use its own cookies
            url
        ],
        # Fourth attempt: basic approach
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            url
        ]
    ]
    
    for i, command in enumerate(commands):
        try:
            print(f"Attempt {i+1} with yt-dlp")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Add timeout to prevent hanging
            )
            video_data = json.loads(result.stdout)
            return video_data
        except subprocess.CalledProcessError as e:
            print(f"Attempt {i+1} failed with error: {e.stderr}")
            if "No video could be found" in e.stderr:
                # This means the post doesn't contain a video
                return {"no_video": True}
            if i < len(commands) - 1:
                continue
            else:
                return None
        except json.JSONDecodeError:
            print(f"Attempt {i+1} failed to parse JSON output")
            if i < len(commands) - 1:
                continue
            else:
                return None
        except subprocess.TimeoutExpired:
            print(f"Attempt {i+1} timed out")
            if i < len(commands) - 1:
                continue
            else:
                return None

def get_post_info_with_web_scraping(url):
    """
    Fallback method using web scraping to get basic post information.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract post text
            post_text_element = soup.find('div', {'data-testid': 'post-content'})
            post_text = post_text_element.get_text(strip=True) if post_text_element else ""
            
            # Extract author name
            author_name_element = soup.find('span', {'data-testid': 'user-name'})
            author_name = author_name_element.get_text(strip=True) if author_name_element else ""
            
            # Extract author handle
            author_handle_element = soup.find('span', {'data-testid': 'user-handle'})
            author_handle = author_handle_element.get_text(strip=True) if author_handle_element else ""
            
            # Extract images
            images = []
            image_elements = soup.find_all('img')
            for img in image_elements:
                src = img.get('src', '')
                alt = img.get('alt', '')
                if "profile_images" not in src and src.startswith("https://"):
                    images.append({"url": src, "alt": alt})
            
            # Check if there's a video player
            has_video = bool(soup.find('div', {'data-testid': 'videoPlayer'}))
            
            # Try to extract video URLs from script tags
            video_urls = []
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'video_url' in script.string:
                    # Try to extract video URLs from JavaScript
                    video_url_matches = re.findall(r'"video_url":"([^"]+)"', script.string)
                    video_urls.extend(video_url_matches)
            
            # Try to extract from Instagram's JSON data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if 'video' in data:
                        video_urls.append(data['video']['contentUrl'])
                except:
                    pass
            
            return {
                "post_text": post_text,
                "author_name": author_name,
                "author_handle": author_handle,
                "images": images,
                "has_video": has_video,
                "video_urls": video_urls
            }
        else:
            print(f"Web scraping request failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Web scraping method failed with error: {e}")
        return None

def get_video_info_with_instagram_api(url):
    """
    Fallback method using Instagram's API endpoints (Threads is part of Instagram).
    """
    try:
        # Extract post ID from URL
        post_id = extract_post_id(url)
        if not post_id:
            return None
        
        # Use Instagram's API (simplified approach)
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        }
        
        # Try to get post details
        api_url = f"https://www.instagram.com/api/v1/media/{post_id}/info/"
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return process_instagram_api_data(data, url)
        else:
            print(f"Instagram API request failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Instagram API method failed with error: {e}")
        return None

def process_instagram_api_data(data, original_url):
    """
    Process Instagram API response into the format expected by the React component.
    """
    try:
        items = data.get('items', [])
        if not items:
            return None
            
        item = items[0]
        user = item.get('user', {})
        carousel_media = item.get('carousel_media', [])
        
        # Process video media
        formats = []
        is_gif = False
        
        # Check if it's a carousel or single media
        media_list = carousel_media if carousel_media else [item]
        
        for media in media_list:
            if media.get('media_type') == 2:  # Video
                video_versions = media.get('video_versions', [])
                for v in video_versions:
                    quality = 'high'
                    if v.get('height', 1080) <= 480: quality = 'low'
                    elif v.get('height', 1080) <= 720: quality = 'medium'
                    
                    formats.append({
                        'quality': quality,
                        'resolution': f"{v.get('height', 0)}p",
                        'size': f"{v.get('width', 0)}x{v.get('height', 0)}",
                        'format': 'mp4',
                        'url': v.get('url')
                    })
            elif media.get('media_type') == 8:  # Carousel
                # Process each item in carousel
                for carousel_item in media.get('carousel_media', []):
                    if carousel_item.get('media_type') == 2:  # Video
                        video_versions = carousel_item.get('video_versions', [])
                        for v in video_versions:
                            quality = 'high'
                            if v.get('height', 1080) <= 480: quality = 'low'
                            elif v.get('height', 1080) <= 720: quality = 'medium'
                            
                            formats.append({
                                'quality': quality,
                                'resolution': f"{v.get('height', 0)}p",
                                'size': f"{v.get('width', 0)}x{v.get('height', 0)}",
                                'format': 'mp4',
                                'url': v.get('url')
                            })
        
        # Get preview image
        thumbnail = None
        if carousel_media:
            thumbnail = carousel_media[0].get('image_versions2', {}).get('candidates', [{}])[0].get('url')
        elif item.get('image_versions2'):
            thumbnail = item.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
        
        return {
            'title': item.get('caption', {}).get('text', '').split('\n')[0][:100],  # First line of caption, truncated
            'description': item.get('caption', {}).get('text', ''),
            'thumbnail': thumbnail,
            'duration': f"{item.get('video_duration', 0):.0f}" if item.get('video_duration') else '0:00',
            'author': {
                'name': user.get('full_name', 'Threads User'),
                'username': f"@{user.get('username', 'user')}",
                'avatar': user.get('profile_pic_url', 'https://picsum.photos/seed/avatar/100/100.jpg')
            },
            'formats': formats,
            'hashtags': [],
            'isGif': is_gif,
            'views': '0',  # Not available from API
            'uploadDate': datetime.fromtimestamp(item.get('taken_at', 0)).strftime('%Y-%m-%d') if item.get('taken_at') else '',
            'url': original_url
        }
    except Exception as e:
        print(f"Error processing Instagram API data: {e}")
        return None

def format_duration(seconds):
    """Formats duration in seconds to a human-readable string."""
    if not seconds:
        return "0:00"
    
    # If it's already formatted, return as is
    if isinstance(seconds, str) and ':' in seconds:
        return seconds
    
    # If it's a number, convert to MM:SS or HH:MM:SS format
    try:
        seconds_float = float(seconds)
        minutes = int(seconds_float) // 60
        seconds_int = int(seconds_float) % 60
        return f"{minutes}:{seconds_int:02d}"
    except:
        return "0:00"

def process_ytdlp_data(data, original_url):
    """
    Transforms the raw data from yt-dlp into the format expected by the React component.
    """
    if not data:
        return None

    # Check if yt-dlp reported no video
    if data.get("no_video"):
        return {
            'status': 'no_video',
            'message': 'This post does not contain a video or GIF.'
        }

    formats = []
    is_gif = False
    
    # Check if this is a GIF
    if data.get('description') and 'GIF' in data.get('description', '').upper():
        is_gif = True
    
    # Check for the main 'url' field
    if data.get('url'):
        formats.append({
            'quality': 'high',
            'resolution': f"{data.get('height', 'Unknown')}p",
            'size': f"{data.get('filesize_approx', 0) / (1024*1024):.1f} MB" if data.get('filesize_approx') else 'Unknown MB',
            'format': data.get('ext', 'mp4'),
            'url': data.get('url')
        })

    # If no direct URL, search the 'formats' list
    if not formats:
        sorted_formats = sorted(data.get('formats', []), key=lambda f: f.get('height', 0), reverse=True)
        seen_qualities = set()
        
        for f in sorted_formats:
            # We want a format that has both video and audio for a simple download
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                quality_label = f"{f.get('height', 'unknown')}p"
                if quality_label not in seen_qualities:
                    seen_qualities.add(quality_label)
                    quality = 'high'
                    if f.get('height', 1080) <= 480: quality = 'low'
                    elif f.get('height', 1080) <= 720: quality = 'medium'

                    formats.append({
                        'quality': quality,
                        'resolution': quality_label,
                        'size': f"{f.get('filesize_approx', 0) / (1024*1024):.1f} MB" if f.get('filesize_approx') else 'Unknown MB',
                        'format': f.get('ext', 'mp4'),
                        'url': f.get('url')
                    })
                    # We only need one format from this method to provide a download button
                    break 

    # If still no formats, it's likely not a downloadable video
    if not formats:
        # We still return the metadata so the user sees what was analyzed
        return {
            'title': data.get('title', 'Threads Content'),
            'description': data.get('description', 'Could not find a downloadable video for this URL.'),
            'thumbnail': data.get('thumbnail'),
            'duration': format_duration(data.get('duration')),
            'author': {
                'name': data.get('uploader', 'Threads User'),
                'username': data.get('uploader_id', '@user'),
                'avatar': data.get('uploader_avatar', 'https://picsum.photos/seed/avatar/100/100.jpg')
            },
            'formats': [], # The key part: an empty array
            'hashtags': [],
            'isGif': is_gif,
            'views': data.get('view_count', '0'),
            'uploadDate': data.get('upload_date', ''),
            'url': original_url
        }

    # SUCCESS: We found formats, return the full data
    description = data.get('description', '')
    hashtags = [f"#{tag}" for tag in description.split() if tag.startswith('#')][:5]

    return {
        'title': data.get('title', 'Threads Video'),
        'description': data.get('description', 'Check out this video from Threads!'),
        'thumbnail': data.get('thumbnail'),
        'duration': format_duration(data.get('duration')),
        'author': {
            'name': data.get('uploader', 'Threads User'),
            'username': data.get('uploader_id', '@user'),
            'avatar': data.get('uploader_avatar', 'https://picsum.photos/seed/avatar/100/100.jpg')
        },
        'formats': formats, # This will now be populated
        'hashtags': hashtags,
        'isGif': is_gif,
        'views': data.get('view_count', '0'),
        'uploadDate': data.get('upload_date', ''),
        'url': original_url
    }

def process_web_scraping_data(data, original_url):
    """
    Process web scraping data into the format expected by the React component.
    """
    if not data:
        return None
    
    # Get the first image as thumbnail if available
    thumbnail = data.get('images', [{}])[0].get('url') if data.get('images') else None
    
    # Create formats from video URLs if available
    formats = []
    if data.get('video_urls'):
        for i, video_url in enumerate(data.get('video_urls', [])):
            formats.append({
                'quality': 'medium',
                'resolution': 'Unknown',
                'size': 'Unknown',
                'format': 'mp4',
                'url': video_url
            })
    
    return {
        'title': data.get('post_text', '').split('\n')[0][:100],  # First line of post, truncated
        'description': data.get('post_text', ''),
        'thumbnail': thumbnail,
        'duration': '0:00',
        'author': {
            'name': data.get('author_name', 'Threads User'),
            'username': data.get('author_handle', '@user'),
            'avatar': 'https://picsum.photos/seed/avatar/100/100.jpg'
        },
        'formats': formats,  # Will be populated if video URLs are found
        'hashtags': [],
        'isGif': False,
        'views': '0',
        'uploadDate': '',
        'url': original_url,
        'has_video': data.get('has_video', False),
        'images': data.get('images', [])
    }

def get_cached_video_info(url):
    """Check if video info is already cached"""
    with cache_lock:
        if url in video_cache:
            cache_entry = video_cache[url]
            # Cache is valid for 1 hour
            if time.time() - cache_entry['timestamp'] < 3600:
                return cache_entry['data']
    return None

def cache_video_info(url, data):
    """Cache video info"""
    with cache_lock:
        video_cache[url] = {
            'data': data,
            'timestamp': time.time()
        }

def process_url_with_timeout(url, session_id, timeout=60):
    """Process URL with timeout to prevent hanging"""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(process_url, url, session_id)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"Processing URL {url} timed out")
            return {
                'status': 'error',
                'message': 'Processing timed out. Please try again.'
            }

def process_url(url, session_id):
    """Process a single URL and return the result"""
    # Check cache first
    cached_result = get_cached_video_info(url)
    if cached_result:
        print(f"Using cached result for {url}")
        return cached_result
    
    # Try yt-dlp first with multiple approaches
    raw_data = get_video_info_with_ytdlp(url)
    
    # Check if yt-dlp reported no video
    if raw_data and raw_data.get("no_video"):
        final_result = {
            'status': 'no_video',
            'message': 'This post does not contain a video or GIF.',
            'data': process_web_scraping_data(get_post_info_with_web_scraping(url), url)
        }
    # If yt-dlp fails, try Instagram API
    elif not raw_data:
        print("yt-dlp failed, trying Instagram API fallback")
        api_data = get_video_info_with_instagram_api(url)
        
        if api_data:
            final_result = {
                'status': 'success',
                'data': api_data
            }
        else:
            print("Instagram API failed, trying web scraping")
            scrape_data = get_post_info_with_web_scraping(url)
            
            if scrape_data:
                final_result = {
                    'status': 'no_video',
                    'message': 'Could not extract video information. This post may not contain a video or GIF, or the content may be private.',
                    'data': process_web_scraping_data(scrape_data, url)
                }
            else:
                final_result = {
                    'status': 'error',
                    'message': 'Could not extract video information. The URL may be invalid, private, or the content may not be a video.'
                }
    else:
        final_result = {
            'status': 'success',
            'data': process_ytdlp_data(raw_data, url)
        }
    
    # Cache the result
    cache_video_info(url, final_result)
    
    return final_result

def main():
    parser = argparse.ArgumentParser(description='Analyze Threads video using yt-dlp')
    parser.add_argument('--url', required=True, help='Threads URL to analyze')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    
    args = parser.parse_args()
    
    print(f"Analyzing URL: {args.url}")
    
    # Process the URL with timeout
    final_result = process_url_with_timeout(args.url, args.session_id)
    
    output_dir = 'artifacts'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"threads_results_{args.session_id}.json")
    
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"Results saved to {output_file}")
    if final_result.get('status') == 'success':
        print("Successfully processed content.")
    elif final_result.get('status') == 'no_video':
        print("Post processed, but no video/GIF found.")
    else:
        print("Processing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
