import os
import json
import sys
import uuid
import re
import requests
import subprocess
from datetime import datetime

def generate_session_id():
    return str(uuid.uuid4())

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    regex = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_video_info_api(video_id):
    """Get video information using YouTube Data API"""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise Exception("YouTube API key not configured")
    
    url = f"https://www.googleapis.com/youtube/v3/videos"
    params = {
        'part': 'snippet,statistics,contentDetails',
        'id': video_id,
        'key': api_key
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"YouTube API request failed: {response.status_code}")
    
    data = response.json()
    if not data.get('items'):
        raise Exception("Video not found")
    
    item = data['items'][0]
    snippet = item['snippet']
    statistics = item['statistics']
    content_details = item['contentDetails']
    
    duration_str = content_details.get('duration', 'PT0S')
    duration = parse_duration(duration_str)
    
    return {
        'id': item['id'],
        'title': snippet.get('title'),
        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url'),
        'duration': duration,
        'views': int(statistics.get('viewCount', 0)),
        'uploadDate': snippet.get('publishedAt'),
        'channel': snippet.get('channelTitle'),
        'description': snippet.get('description'),
        'qualities': ['360p', '480p', '720p', '1080p'],
        'availableFormats': []
    }

def parse_duration(duration_str):
    """Parse ISO 8601 duration string to seconds"""
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

def update_ytdlp():
    """Update yt-dlp to latest version"""
    try:
        print("Updating yt-dlp...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "yt-dlp"], 
                      check=True, capture_output=True)
        print("yt-dlp updated successfully")
        return True
    except Exception as e:
        print(f"Failed to update yt-dlp: {e}")
        return False

def get_video_info_ytdlp(url):
    """Get video information using yt-dlp with enhanced settings"""
    print(f"Fetching video info using yt-dlp for: {url}")
    
    # Update yt-dlp first
    update_ytdlp()
    
    import yt_dlp
    
    # Try multiple methods in sequence
    methods = [
        # Method 1: Standard with android client
        {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'configs'],
                }
            }
        },
        # Method 2: iOS client
        {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android'],
                }
            }
        },
        # Method 3: Age-gate bypass
        {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'age_limit': 21,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_embedded'],
                }
            }
        },
        # Method 4: Web with all clients
        {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android', 'ios', 'mweb'],
                }
            }
        }
    ]
    
    last_error = None
    
    for i, ydl_opts in enumerate(methods):
        try:
            print(f"\nTrying method {i+1}/{len(methods)}...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    continue
                
                # Extract available formats
                formats = info.get('formats', [])
                
                # Get unique qualities
                qualities = []
                for fmt in formats:
                    if fmt.get('vcodec') != 'none' and fmt.get('height'):
                        quality = f"{fmt['height']}p"
                        if quality not in qualities:
                            qualities.append(quality)
                
                qualities.sort(key=lambda x: int(x.replace('p', '')), reverse=True)
                
                # Get available formats
                available_formats = []
                for fmt in formats:
                    if fmt.get('ext') in ['mp4', 'webm', 'm4a']:
                        available_formats.append({
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'quality': fmt.get('format_note') or f"{fmt.get('height', 'unknown')}p",
                            'vcodec': fmt.get('vcodec'),
                            'acodec': fmt.get('acodec'),
                            'filesize': fmt.get('filesize')
                        })
                
                print(f"Successfully extracted video info using method {i+1}")
                
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration'),
                    'views': info.get('view_count'),
                    'uploadDate': info.get('upload_date'),
                    'channel': info.get('uploader'),
                    'description': info.get('description'),
                    'qualities': qualities or ['360p', '480p', '720p'],
                    'availableFormats': available_formats
                }
                
        except Exception as e:
            last_error = str(e)
            print(f"Method {i+1} failed: {last_error}")
            continue
    
    raise Exception(f"All methods failed. Last error: {last_error}")

def get_video_info(url):
    """Get video information (try API first, then yt-dlp)"""
    video_id = extract_video_id(url)
    if not video_id:
        raise Exception("Invalid YouTube URL")
    
    # Try YouTube API first if available
    try:
        print(f"Trying YouTube API for: {video_id}")
        return get_video_info_api(video_id)
    except Exception as e:
        print(f"API method failed: {str(e)}")
    
    # Fallback to yt-dlp
    print("Falling back to yt-dlp...")
    return get_video_info_ytdlp(url)

def download_video(url, quality, format_type, session_id):
    """Download YouTube video using enhanced yt-dlp"""
    print(f"Downloading: {url}, Quality: {quality}, Format: {format_type}")
    
    # Update yt-dlp
    update_ytdlp()
    
    import yt_dlp
    
    output_template = f'video_{session_id}.%(ext)s'
    
    # Base options
    base_opts = {
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [progress_hook],
    }
    
    # Format-specific options
    if format_type == 'mp3':
        base_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        if quality == 'highest':
            base_opts['format'] = 'bestvideo+bestaudio/best'
        else:
            height = quality.replace('p', '')
            base_opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
    
    # Try multiple extractor configurations
    extractor_configs = [
        {'youtube': {'player_client': ['android', 'web']}},
        {'youtube': {'player_client': ['ios', 'android']}},
        {'youtube': {'player_client': ['android_embedded']}},
        {'youtube': {'player_client': ['web', 'android', 'ios']}},
    ]
    
    last_error = None
    
    for i, extractor_args in enumerate(extractor_configs):
        try:
            print(f"\nTrying download method {i+1}/{len(extractor_configs)}...")
            
            ydl_opts = base_opts.copy()
            ydl_opts['extractor_args'] = extractor_args
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find downloaded file
            for file in os.listdir('.'):
                if file.startswith(f'video_{session_id}'):
                    print(f"Download successful: {file}")
                    return file
            
            raise Exception("Downloaded file not found")
            
        except Exception as e:
            last_error = str(e)
            print(f"Download method {i+1} failed: {last_error}")
            continue
    
    raise Exception(f"All download methods failed. Last error: {last_error}")

def progress_hook(d):
    """Progress hook for downloads"""
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '0.0%').strip('%')
        try:
            percent = float(percent_str)
            if percent % 10 == 0:  # Log every 10%
                print(f"Progress: {percent:.1f}%")
        except:
            pass
    elif d['status'] == 'finished':
        print("Download finished, processing...")

def main():
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    action = os.environ.get("ACTION", "info")
    video_url = os.environ.get("VIDEO_URL")
    
    if not video_url:
        error_msg = "VIDEO_URL environment variable not set"
        print(f"ERROR: {error_msg}")
        result = {"status": "error", "message": error_msg, "session_id": session_id}
        print(f"results={json.dumps(result)}")
        sys.exit(1)
    
    print(f"Session: {session_id}")
    print(f"Action: {action}")
    print(f"URL: {video_url}")
    
    try:
        if action == "info":
            video_info = get_video_info(video_url)
            
            result = {
                "status": "success",
                "session_id": session_id,
                "data": video_info
            }
            
            # Save to file
            output_file = f"video_info_{session_id}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            
            print(f"Saved to {output_file}")
            
        elif action == "download":
            quality = os.environ.get("QUALITY", "720p")
            format_type = os.environ.get("FORMAT", "mp4")
            
            downloaded_file = download_video(video_url, quality, format_type, session_id)
            
            result = {
                "status": "success",
                "session_id": session_id,
                "message": "Video downloaded successfully",
                "filename": downloaded_file
            }
            
            output_file = f"video_download_{session_id}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            
            print(f"Saved to {output_file}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        result = {
            "status": "error",
            "message": str(e),
            "session_id": session_id
        }
        
        output_file = f"error_{session_id}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
    
    print(f"results={json.dumps(result)}")
    return result

if __name__ == "__main__":
    main()
