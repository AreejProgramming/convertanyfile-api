import yt_dlp
import sys
import os
import re
import random

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

def get_random_proxy():
    """Get a random proxy from a list of free proxies"""
    proxies = [
        # Add your own proxy list here
        # Format: "http://ip:port" or "socks5://ip:port"
    ]
    
    if proxies:
        return random.choice(proxies)
    return None

def download_video_with_proxy(url, quality='720p', format='mp4', output_path='.'):
    """
    Downloads a video using yt-dlp with a proxy to bypass YouTube restrictions.
    """
    proxy = get_random_proxy()
    
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'format': f'best[height<={quality.replace("p", "")}]/best' if format != 'mp3' else 'bestaudio/best',
        'no_warnings': False,
        'quiet': False,
        'ignoreerrors': True,
        'extract_flat': False,
        'socket_timeout': 60,
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy
        print(f"Using proxy: {proxy}")
    
    if format == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    print(f"Attempting download with yt-dlp: {url} | Quality: {quality} | Format: {format}")
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
        print(f"Proxy download failed: {e}")
        return None

def download_video(url, quality='720p', format='mp4', output_path='.'):
    """
    Downloads a video from a given YouTube URL with specified quality and format.
    """
    return download_video_with_proxy(url, quality, format, output_path)

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
