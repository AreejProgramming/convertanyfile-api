import yt_dlp
import sys
import os
import re
import requests

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in filenames"""
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "untitled"

def get_invidious_instances():
    """Get a list of available Invidious instances"""
    try:
        response = requests.get("https://api.invidious.io/instances.json")
        if response.status_code == 200:
            instances = response.json()
            # Filter for https instances that are up
            return [instance[0] for instance in instances if instance[1].get('https', True) and instance[1].get('status', 200) == 200]
    except:
        pass
    
    # Fallback to hardcoded instances
    return [
        "https://yewtu.be",
        "https://invidious.snopyta.org",
        "https://yewtu.be",
        "https://tube.cadence.moe",
        "https://invidious.kavin.rocks"
    ]

def download_video_with_invidious(url, quality='720p', format='mp4', output_path='.'):
    """
    Downloads a video using an Invidious instance to bypass YouTube restrictions.
    """
    try:
        # Extract video ID from URL
        video_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})', url)
        if not video_id_match:
            raise Exception("Invalid YouTube URL")
        
        video_id = video_id_match.group(1)
        
        # Get list of Invidious instances
        instances = get_invidious_instances()
        
        for instance in instances:
            try:
                print(f"Trying Invidious instance: {instance}")
                
                # Get video info from Invidious
                api_url = f"{instance}/api/v1/videos/{video_id}"
                response = requests.get(api_url, timeout=10)
                
                if response.status_code != 200:
                    continue
                
                video_data = response.json()
                title = video_data.get('title', video_id)
                safe_title = sanitize_filename(title)
                
                # Find the best quality format
                formats = video_data.get('formatStreams', [])
                if not formats:
                    continue
                
                best_format = None
                if format == 'mp3':
                    # Find audio-only format
                    audio_formats = [f for f in formats if f.get('type', '').startswith('audio')]
                    if audio_formats:
                        best_format = audio_formats[0]
                else:
                    # Find video format with the requested quality
                    target_height = int(quality.replace('p', ''))
                    video_formats = [f for f in formats if f.get('type', '').startswith('video')]
                    
                    if video_formats:
                        # Find format with closest height to target
                        best_format = min(video_formats, key=lambda x: abs(int(x.get('qualityLabel', '0p').replace('p', '')) - target_height))
                
                if not best_format:
                    continue
                
                # Download the video
                download_url = best_format.get('url')
                if not download_url:
                    continue
                
                file_ext = 'mp3' if format == 'mp3' else 'mp4'
                filename = f"{safe_title}.{file_ext}"
                file_path = os.path.join(output_path, filename)
                
                # Download the file
                print(f"Downloading from: {download_url}")
                with requests.get(download_url, stream=True) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                
                print(f"Successfully downloaded: {filename}")
                return filename
                
            except Exception as e:
                print(f"Error with instance {instance}: {e}")
                continue
        
        raise Exception("All Invidious instances failed")
        
    except Exception as e:
        print(f"Invidious download failed: {e}")
        return None

def download_video_with_yt_dlp_fallback(url, quality='720p', format='mp4', output_path='.'):
    """
    Fallback method using yt-dlp with basic configuration.
    """
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'format': f'best[height<={quality.replace("p", "")}]/best' if format != 'mp3' else 'bestaudio/best',
        'no_warnings': False,
        'quiet': False,
        'ignoreerrors': True,
        'extract_flat': False,
    }
    
    if format == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    print(f"Attempting fallback download with yt-dlp: {url} | Quality: {quality} | Format: {format}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            
            if not info_dict:
                raise Exception("Failed to extract video information")
            
            video_title = info_dict.get('title', None)
            if not video_title:
                video_id = info_dict.get('id', None)
                video_title = video_id if video_id else "video"
            
            safe_title = sanitize_filename(video_title)
            video_ext = info_dict.get('ext', format if format != 'mp3' else 'mp3')
            
            filename = f"{safe_title}.{video_ext}"
            print(f"Successfully downloaded: {filename}")
            return filename
    except Exception as e:
        print(f"Fallback download failed: {e}")
        return None

def download_video(url, quality='720p', format='mp4', output_path='.'):
    """
    Downloads a video from a given YouTube URL with specified quality and format.
    First tries with Invidious, then falls back to yt-dlp.
    """
    # First try with the Invidious method
    result = download_video_with_invidious(url, quality, format, output_path)
    if result:
        return result
    
    # If Invidious method fails, try with yt-dlp as a fallback
    return download_video_with_yt_dlp_fallback(url, quality, format, output_path)

if __name__ == "__main__":
    # Expecting 3 arguments: url, quality, format
    if len(sys.argv) < 4:
        print("Error: Please provide a URL, quality, and format as arguments.")
        sys.exit(1)
    
    video_url = sys.argv[1]
    selected_quality = sys.argv[2]
    selected_format = sys.argv[3]
    
    # Create a directory to store the video
    output_dir = "video_output"
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded_file = download_video(video_url, selected_quality, selected_format, output_dir)
    
    if downloaded_file:
        print(f"Download complete. File saved to: {os.path.join(output_dir, downloaded_file)}")
    else:
        print("Download failed.")
        sys.exit(1)
