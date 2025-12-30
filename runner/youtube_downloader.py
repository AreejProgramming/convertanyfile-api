import os
import json
import sys
import uuid
import re
import requests

def generate_session_id():
    return str(uuid.uuid4())

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    regex = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

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

def get_video_info_api(video_id):
    """Get video information using YouTube Data API"""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise Exception("YouTube API key not configured. Please add YOUTUBE_API_KEY to your repository secrets.")
    
    url = f"https://www.googleapis.com/youtube/v3/videos"
    params = {
        'part': 'snippet,statistics,contentDetails',
        'id': video_id,
        'key': api_key
    }
    
    print(f"Fetching video info from YouTube API...")
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise Exception(f"YouTube API request failed: {response.status_code} - {response.text}")
    
    data = response.json()
    if not data.get('items'):
        raise Exception("Video not found or is private/unavailable")
    
    item = data['items'][0]
    snippet = item['snippet']
    statistics = item['statistics']
    content_details = item['contentDetails']
    
    duration_str = content_details.get('duration', 'PT0S')
    duration = parse_duration(duration_str)
    
    # Generate quality options
    qualities = ['144p', '240p', '360p', '480p', '720p', '1080p']
    
    # Create download URLs (these are third-party service suggestions)
    download_options = []
    for quality in qualities:
        download_options.append({
            'quality': quality,
            'format': 'mp4',
            'note': f'Use third-party services like y2mate.com or saveform.net to download in {quality}'
        })
    
    # Add MP3 option
    download_options.append({
        'quality': 'audio',
        'format': 'mp3',
        'note': 'Use third-party services to extract audio'
    })
    
    return {
        'id': item['id'],
        'title': snippet.get('title'),
        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url') or snippet.get('thumbnails', {}).get('default', {}).get('url'),
        'duration': duration,
        'views': int(statistics.get('viewCount', 0)),
        'uploadDate': snippet.get('publishedAt', '').split('T')[0],
        'channel': snippet.get('channelTitle'),
        'description': snippet.get('description', '')[:500] + ('...' if len(snippet.get('description', '')) > 500 else ''),
        'qualities': qualities,
        'availableFormats': download_options,
        'videoUrl': f"https://www.youtube.com/watch?v={video_id}",
        'embedUrl': f"https://www.youtube.com/embed/{video_id}",
        'directDownloadNote': 'Due to YouTube restrictions, direct downloads from GitHub Actions are not possible. The video information is provided for reference.'
    }

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
        video_id = extract_video_id(video_url)
        if not video_id:
            raise Exception("Invalid YouTube URL")
        
        if action == "info":
            video_info = get_video_info_api(video_id)
            
            result = {
                "status": "success",
                "session_id": session_id,
                "data": video_info
            }
            
            output_file = f"video_info_{session_id}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            
            print(f"✓ Video info saved to {output_file}")
            
        elif action == "download":
            result = {
                "status": "info",
                "session_id": session_id,
                "message": "Direct downloads are not available due to YouTube's bot protection. Please use the video URL with third-party download services.",
                "videoUrl": video_url,
                "suggestions": [
                    "y2mate.com",
                    "saveform.net", 
                    "9xbuddy.com",
                    "ytmp3.cc (for audio)"
                ]
            }
            
            output_file = f"video_download_{session_id}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
        
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
