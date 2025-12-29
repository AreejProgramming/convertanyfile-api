# File: runner/youtube_downloader.py

import os
import json
import time
import sys
import uuid
import re
import yt_dlp
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

def get_video_info(url):
    """
    Get video information from YouTube
    """
    print(f"Fetching video info for: {url}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
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
        print(f"Error getting video info: {str(e)}")
        raise

def download_video(url, quality, format_type, session_id):
    """
    Download YouTube video
    """
    print(f"Downloading video: {url}, Quality: {quality}, Format: {format_type}")
    
    # Create output filename
    video_id = extract_video_id(url)
    output_template = f'video_{session_id}.%(ext)s'
    
    # Configure download options
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
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
            'ffmpeg_location': '/usr/bin/ffmpeg',  # Path to ffmpeg in GitHub Actions
        })
    else:
        # Video and audio
        if quality == 'highest':
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
        else:
            # Try to get the specific quality
            ydl_opts['format'] = f'best[height<={quality.replace("p", "")}]+bestaudio/best[height<={quality.replace("p", "")}]'
    
    try:
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
        raise

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
            
            # Save results to file
            with open(f"video_info_{session_id}.json", "w") as f:
                json.dump(results, f, indent=2)
            
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
            
            print(f"Download completed: {downloaded_file}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results = {
            "status": "error", 
            "message": str(e),
            "session_id": session_id
        }
    
    # Always output the results, even if there was an error
    print(f"results={json.dumps(results)}")
    return results

if __name__ == "__main__":
    main()
