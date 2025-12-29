# File: runner/youtube_downloader.py

import os
import json
import time
import sys
import uuid
import re
import requests
import subprocess
from datetime import datetime

def generate_session_id():
    return str(uuid.uuid4())

def extract_video_id(url):
    """
    Extract video ID from YouTube URL
    """
    # Regular expression to extract YouTube video ID
    regex = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_video_info_api(video_id):
    """
    Get video information using YouTube Data API
    """
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
    
    # Parse duration
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
        'qualities': ['360p', '480p', '720p', '1080p'],  # Default qualities
        'availableFormats': []  # Will be populated by yt-dlp
    }

def parse_duration(duration_str):
    """
    Parse ISO 8601 duration string to seconds
    """
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

def get_video_info(url):
    """
    Get video information from YouTube (try API first, then yt-dlp)
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise Exception("Invalid YouTube URL")
    
    try:
        # Try YouTube API first
        print(f"Fetching video info using API for: {video_id}")
        return get_video_info_api(video_id)
    except Exception as e:
        print(f"API method failed: {str(e)}")
        # Fall back to yt-dlp
        print("Falling back to yt-dlp...")
        return get_video_info_ytdlp(url)

def get_video_info_ytdlp(url):
    """
    Get video information using yt-dlp with enhanced settings
    """
    print(f"Fetching video info using yt-dlp for: {url}")
    
    # First, update yt-dlp to the latest version
    try:
        print("Updating yt-dlp to the latest version...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to update yt-dlp: {e}")
    
    # Configure yt-dlp options with multiple fallback methods
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'no_check_certificate': True,
        'socket_timeout': 60,
        'retries': 3,
        'fragment_retries': 3,
        'file_access_retries': 3,
        'extractor_retries': 3,
        'retry_sleep_functions': {
            'http': lambda x: x * 2,
            'fragment': lambda x: x * 2,
            'file_access': lambda x: x * 2,
            'extractor': lambda x: x * 2,
        },
        'http_headers': {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    try:
        import yt_dlp
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract available formats
            formats = info.get('formats', [])
            
            # Get unique qualities
            qualities = []
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('height'):
                    quality = f"{fmt['height']}p"
                    if quality not in qualities:
                        qualities.append(quality)
            
            # Sort qualities (highest first)
            qualities.sort(key=lambda x: int(x.replace('p', '')), reverse=True)
            
            # Get available formats for download
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
            
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'views': info.get('view_count'),
                'uploadDate': info.get('upload_date'),
                'channel': info.get('uploader'),
                'description': info.get('description'),
                'qualities': qualities,
                'availableFormats': available_formats
            }
    except Exception as e:
        print(f"yt-dlp method failed: {str(e)}")
        # Try alternative method if first attempt fails
        try:
            print("Trying alternative method...")
            ydl_opts.update({
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'player_skip': ['configs', 'webpage'],
                    }
                }
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Process the info as before
                formats = info.get('formats', [])
                qualities = []
                for fmt in formats:
                    if fmt.get('vcodec') != 'none' and fmt.get('height'):
                        quality = f"{fmt['height']}p"
                        if quality not in qualities:
                            qualities.append(quality)
                
                qualities.sort(key=lambda x: int(x.replace('p', '')), reverse=True)
                
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
                
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration'),
                    'views': info.get('view_count'),
                    'uploadDate': info.get('upload_date'),
                    'channel': info.get('uploader'),
                    'description': info.get('description'),
                    'qualities': qualities,
                    'availableFormats': available_formats
                }
        except Exception as e2:
            print(f"Alternative method also failed: {str(e2)}")
            raise Exception(f"Failed to get video info: {str(e)}. Alternative also failed: {str(e2)}")

def download_video(url, quality, format_type, session_id):
    """
    Download YouTube video using enhanced yt-dlp settings
    """
    print(f"Downloading video: {url}, Quality: {quality}, Format: {format_type}")
    
    # First, update yt-dlp to the latest version
    try:
        print("Updating yt-dlp to the latest version...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to update yt-dlp: {e}")
    
    # Create output filename
    video_id = extract_video_id(url)
    output_template = f'video_{session_id}.%(ext)s'
    
    # Configure download options with robust settings
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'no_check_certificate': True,
        'socket_timeout': 60,
        'retries': 5,
        'fragment_retries': 5,
        'file_access_retries': 5,
        'extractor_retries': 5,
        'retry_sleep_functions': {
            'http': lambda x: x * 2,
            'fragment': lambda x: x * 2,
            'file_access': lambda x: x * 2,
            'extractor': lambda x: x * 2,
        },
        'http_headers': {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    # Set format based on user selection
    if format_type == 'mp3':
        # Audio only
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': '/usr/bin/ffmpeg',
        })
    else:
        # Video and audio
        if quality == 'highest':
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
        else:
            # Try to get the specific quality
            ydl_opts['format'] = f'best[height<={quality.replace("p", "")}]+bestaudio/best[height<={quality.replace("p", "")}]'
    
    try:
        import yt_dlp
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            # Find the downloaded file
            downloaded_file = None
            for file in os.listdir('.'):
                if file.startswith(f'video_{session_id}'):
                    downloaded_file = file
                    break
            
            if not downloaded_file:
                raise Exception("Downloaded file not found")
            
            return downloaded_file
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        # Try alternative method if first attempt fails
        try:
            print("Trying alternative download method...")
            ydl_opts.update({
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'player_skip': ['configs', 'webpage'],
                    }
                }
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_file = None
                for file in os.listdir('.'):
                    if file.startswith(f'video_{session_id}'):
                        downloaded_file = file
                        break
                
                if not downloaded_file:
                    raise Exception("Downloaded file not found")
                
                return downloaded_file
        except Exception as e2:
            print(f"Alternative download method also failed: {str(e2)}")
            raise Exception(f"Failed to download video: {str(e)}. Alternative also failed: {str(e2)}")

def progress_hook(d):
    """
    Progress hook for download progress
    """
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '0.0%').strip('%')
        try:
            percent = float(percent_str)
            print(f"Download progress: {percent:.1f}%")
        except:
            pass
    elif d['status'] == 'finished':
        print("Download completed")

def main():
    # Get session ID from environment variable
    session_id = os.environ.get("SESSION_ID", generate_session_id())
    
    # Get action type from environment variable
    action = os.environ.get("ACTION", "info")
    
    # Get video URL from environment variable
    video_url = os.environ.get("VIDEO_URL")
    
    if not video_url:
        print("ERROR: VIDEO_URL environment variable not set.")
        print(f"results={json.dumps({'status': 'error', 'message': 'VIDEO_URL environment variable not set.'})}")
        sys.exit(1)
    
    print(f"Session ID: {session_id}")
    print(f"Action: {action}")
    print(f"Video URL: {video_url}")
    
    results = {
        "status": "error", 
        "message": "Operation failed to start.",
        "session_id": session_id
    }
    
    try:
        if action == "info":
            # Get video information
            video_info = get_video_info(video_url)
            
            results = {
                "status": "success",
                "session_id": session_id,
                "data": video_info
            }
            
            # Save results to file with consistent naming
            output_file = f"video_info_{session_id}.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            
            print(f"Results saved to {output_file}")
            
        elif action == "download":
            # Download video
            quality = os.environ.get("QUALITY", "720p")
            format_type = os.environ.get("FORMAT", "mp4")
            
            downloaded_file = download_video(video_url, quality, format_type, session_id)
            
            results = {
                "status": "success",
                "session_id": session_id,
                "message": "Video downloaded successfully",
                "filename": downloaded_file
            }
            
            # Save results to file with consistent naming
            output_file = f"video_download_{session_id}.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            
            print(f"Results saved to {output_file}")
            print(f"Download completed: {downloaded_file}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
        
        # Save error results as well
        output_file = f"error_{session_id}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"Error results saved to {output_file}")
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    main()
