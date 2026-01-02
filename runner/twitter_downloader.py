import json
import os
import sys
import argparse
import subprocess
import re
import requests
from datetime import datetime
from urllib.parse import urlparse

def extract_tweet_id(url):
    """Extract tweet ID from Twitter/X URL"""
    tweet_id_match = re.search(r'(?:twitter\.com|x\.com)/\w+/status/(\d+)', url)
    return tweet_id_match.group(1) if tweet_id_match else None

def get_video_info_with_ytdlp(url):
    """
    Uses yt-dlp with updated authentication methods to extract video information from a Twitter/X URL.
    """
    # Try multiple approaches to get the video
    commands = [
        # First attempt: with cookies if available
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'Authorization:Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            url
        ],
        # Second attempt: with user agent
        [
            'yt-dlp',
            '--no-warnings',
            '--simulate',
            '--print-json',
            '--add-header', 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            url
        ],
        # Third attempt: basic approach
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
                check=True
            )
            video_data = json.loads(result.stdout)
            return video_data
        except subprocess.CalledProcessError as e:
            print(f"Attempt {i+1} failed with error: {e.stderr}")
            if "No video could be found" in e.stderr:
                # This means the tweet doesn't contain a video
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

def get_tweet_info_with_web_scraping(url):
    """
    Fallback method using web scraping to get basic tweet information.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            html = response.text
            
            # Extract tweet text
            tweet_text_match = re.search(r'<div[^>]*data-testid="tweetText"[^>]*>(.*?)</div>', html, re.DOTALL)
            tweet_text = tweet_text_match.group(1).strip() if tweet_text_match else ""
            
            # Clean up HTML tags
            tweet_text = re.sub(r'<[^>]+>', '', tweet_text)
            
            # Extract author name
            author_name_match = re.search(r'<span[^>]*data-testid="User-Name"[^>]*>(.*?)</span>', html, re.DOTALL)
            author_name = author_name_match.group(1).strip() if author_name_match else ""
            author_name = re.sub(r'<[^>]+>', '', author_name)
            
            # Extract author handle
            author_handle_match = re.search(r'<span[^>]*data-testid="UserScreenName"[^>]*>(.*?)</span>', html, re.DOTALL)
            author_handle = author_handle_match.group(1).strip() if author_handle_match else ""
            author_handle = re.sub(r'<[^>]+>', '', author_handle)
            
            # Extract images
            images = []
            image_matches = re.findall(r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>', html)
            for src, alt in image_matches:
                if "profile_images" not in src and src.startswith("https://"):
                    images.append({"url": src, "alt": alt})
            
            # Check if there's a video player
            has_video = bool(re.search(r'<div[^>]*data-testid="videoPlayer"[^>]*>', html))
            
            return {
                "tweet_text": tweet_text,
                "author_name": author_name,
                "author_handle": author_handle,
                "images": images,
                "has_video": has_video
            }
        else:
            print(f"Web scraping request failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Web scraping method failed with error: {e}")
        return None

def get_video_info_with_twitter_api(url):
    """
    Fallback method using Twitter's public API endpoints.
    """
    try:
        # Extract tweet ID from URL
        tweet_id = extract_tweet_id(url)
        if not tweet_id:
            return None
        
        # Use Twitter's GraphQL API (simplified approach)
        headers = {
            'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to get tweet details
        api_url = f"https://api.twitter.com/2/tweets/{tweet_id}?expansions=attachments.media_keys,author_id&media.fields=url,preview_image_url,width,height,type,duration_ms&user.fields=name,username,profile_image_url"
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return process_twitter_api_data(data, url)
        else:
            print(f"Twitter API request failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Twitter API method failed with error: {e}")
        return None

def process_twitter_api_data(data, original_url):
    """
    Process Twitter API response into the format expected by the React component.
    """
    try:
        tweet = data.get('data', {})
        includes = data.get('includes', {})
        users = includes.get('users', [])
        media = includes.get('media', [])
        
        # Find the author
        author_id = tweet.get('author_id')
        author = next((u for u in users if u.get('id') == author_id), {})
        
        # Find media
        attachments = tweet.get('attachments', {})
        media_keys = attachments.get('media_keys', [])
        tweet_media = [m for m in media if m.get('media_key') in media_keys]
        
        # Process video media
        formats = []
        is_gif = False
        
        for m in tweet_media:
            if m.get('type') == 'video':
                # Get video info
                variants = m.get('variants', [])
                for v in variants:
                    if v.get('content_type') == 'video/mp4':
                        bitrate = v.get('bitrate', 0)
                        quality = 'medium'
                        if bitrate > 1000000: quality = 'high'
                        elif bitrate < 500000: quality = 'low'
                        
                        formats.append({
                            'quality': quality,
                            'resolution': f"{m.get('height', 0)}p",
                            'size': f"{v.get('bitrate', 0) / 1000:.0f} kbps",
                            'format': 'mp4',
                            'url': v.get('url')
                        })
            elif m.get('type') == 'animated_gif':
                is_gif = True
                variants = m.get('variants', [])
                for v in variants:
                    if v.get('content_type') == 'video/mp4':
                        formats.append({
                            'quality': 'high',
                            'resolution': f"{m.get('height', 0)}p",
                            'size': 'Unknown',
                            'format': 'mp4',
                            'url': v.get('url')
                        })
        
        # Get preview image
        thumbnail = None
        if tweet_media:
            thumbnail = tweet_media[0].get('preview_image_url')
        
        return {
            'title': tweet.get('text', '').split('\n')[0][:100],  # First line of tweet, truncated
            'description': tweet.get('text', ''),
            'thumbnail': thumbnail,
            'duration': '0:00',  # Not available from API
            'author': {
                'name': author.get('name', 'Twitter User'),
                'username': f"@{author.get('username', 'user')}",
                'avatar': author.get('profile_image_url', 'https://picsum.photos/seed/avatar/100/100.jpg')
            },
            'formats': formats,
            'hashtags': [],
            'isGif': is_gif,
            'views': '0',  # Not available from API
            'uploadDate': tweet.get('created_at', ''),
            'url': original_url
        }
    except Exception as e:
        print(f"Error processing Twitter API data: {e}")
        return None

def format_duration(seconds):
    """Formats duration in seconds to a human-readable string."""
    if not seconds:
        return "0:00"
    minutes = int(seconds) // 60
    seconds = int(seconds) % 60
    return f"{minutes}:{seconds:02d}"

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
            'message': 'This tweet does not contain a video or GIF.'
        }

    print("--- DEBUG: yt-dlp raw data keys ---")
    print(list(data.keys()))
    print("--- DEBUG: Checking for direct 'url' key ---")
    print(f"Direct URL found: {'url' in data}")

    formats = []
    is_gif = False
    
    # Check if this is a GIF
    if data.get('description') and 'GIF' in data.get('description', '').upper():
        is_gif = True
    
    # Check for the main 'url' field
    if data.get('url'):
        print("--- DEBUG: Using direct URL from yt-dlp ---")
        formats.append({
            'quality': 'high',
            'resolution': f"{data.get('height', 'Unknown')}p",
            'size': f"{data.get('filesize_approx', 0) / (1024*1024):.1f} MB" if data.get('filesize_approx') else 'Unknown MB',
            'format': data.get('ext', 'mp4'),
            'url': data.get('url')
        })

    # If no direct URL, search the 'formats' list
    if not formats:
        print("--- DEBUG: Direct URL not found, searching formats list ---")
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
        print("--- DEBUG: No suitable video formats found. This might be an image or an unsupported video type. ---")
        # We still return the metadata so the user sees what was analyzed
        return {
            'title': data.get('title', 'Twitter/X Content'),
            'description': data.get('description', 'Could not find a downloadable video for this URL.'),
            'thumbnail': data.get('thumbnail'),
            'duration': format_duration(data.get('duration')),
            'author': {
                'name': data.get('uploader', 'Twitter/X User'),
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
        'title': data.get('title', 'Twitter/X Video'),
        'description': data.get('description', 'Check out this video from Twitter/X!'),
        'thumbnail': data.get('thumbnail'),
        'duration': format_duration(data.get('duration')),
        'author': {
            'name': data.get('uploader', 'Twitter/X User'),
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
    
    return {
        'title': data.get('tweet_text', '').split('\n')[0][:100],  # First line of tweet, truncated
        'description': data.get('tweet_text', ''),
        'thumbnail': thumbnail,
        'duration': '0:00',
        'author': {
            'name': data.get('author_name', 'Twitter User'),
            'username': data.get('author_handle', '@user'),
            'avatar': 'https://picsum.photos/seed/avatar/100/100.jpg'
        },
        'formats': [],  # No download formats available from web scraping
        'hashtags': [],
        'isGif': False,
        'views': '0',
        'uploadDate': '',
        'url': original_url,
        'has_video': data.get('has_video', False),
        'images': data.get('images', [])
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze Twitter/X video using yt-dlp')
    parser.add_argument('--url', required=True, help='Twitter/X URL to analyze')
    parser.add_argument('--session_id', required=True, help='Session ID for tracking')
    
    args = parser.parse_args()
    
    print(f"Analyzing URL: {args.url}")
    
    # Try yt-dlp first with multiple approaches
    raw_data = get_video_info_with_ytdlp(args.url)
    
    # Check if yt-dlp reported no video
    if raw_data and raw_data.get("no_video"):
        final_result = {
            'status': 'no_video',
            'message': 'This tweet does not contain a video or GIF.',
            'data': process_web_scraping_data(get_tweet_info_with_web_scraping(args.url), args.url)
        }
    # If yt-dlp fails, try Twitter API
    elif not raw_data:
        print("yt-dlp failed, trying Twitter API fallback")
        api_data = get_video_info_with_twitter_api(args.url)
        
        if api_data:
            final_result = {
                'status': 'success',
                'data': api_data
            }
        else:
            print("Twitter API failed, trying web scraping")
            scrape_data = get_tweet_info_with_web_scraping(args.url)
            
            if scrape_data:
                final_result = {
                    'status': 'no_video',
                    'message': 'Could not extract video information. This tweet may not contain a video or GIF, or the content may be private.',
                    'data': process_web_scraping_data(scrape_data, args.url)
                }
            else:
                final_result = {
                    'status': 'error',
                    'message': 'Could not extract video information. The URL may be invalid, private, or the content may not be a video. Twitter/X has recently changed their API, which may be causing this issue.'
                }
    else:
        final_result = {
            'status': 'success',
            'data': process_ytdlp_data(raw_data, args.url)
        }

    output_dir = 'artifacts'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"twitter_results_{args.session_id}.json")
    
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"Results saved to {output_file}")
    if final_result.get('status') == 'success':
        print("Successfully processed content.")
    elif final_result.get('status') == 'no_video':
        print("Tweet processed, but no video/GIF found.")
    else:
        print("Processing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
