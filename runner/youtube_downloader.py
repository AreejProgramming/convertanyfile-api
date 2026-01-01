# download_video.py

import yt_dlp
import sys
import os

def download_video(url, output_path='.'):
    """
    Downloads the best video from a given YouTube URL.
    """
    # Set download options
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'), # Save with title as filename
        'format': 'bestvideo+bestaudio/best', # Download best video and audio, or best combined
        'no_warnings': False,
    }

    print(f"Attempting to download video from: {url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', None)
            video_ext = info_dict.get('ext', None)
            filename = f"{video_title}.{video_ext}"
            print(f"Successfully downloaded: {filename}")
            return filename
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please provide a YouTube URL as an argument.")
        sys.exit(1)
    
    video_url = sys.argv[1]
    # Create a directory to store the video
    output_dir = "video_output"
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded_file = download_video(video_url, output_dir)
    
    if downloaded_file:
        print(f"Download complete. File saved to: {os.path.join(output_dir, downloaded_file)}")
    else:
        print("Download failed.")
        sys.exit(1)
