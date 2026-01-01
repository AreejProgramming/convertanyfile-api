# download_video.py (in your GitHub repository)

import yt_dlp
import sys
import os

def download_video(url, quality='720p', format='mp4', output_path='.'):
    """
    Downloads a video from a given YouTube URL with specified quality and format.
    """
    # Construct the format string for yt-dlp
    if format == 'mp3':
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'no_warnings': False,
        }
    else: # mp4 or other video formats
        # Note: yt-dlp handles quality selection with 'height' or a specific format code.
        # For simplicity, we'll use a general 'best' filter.
        # More advanced logic would be needed to map '720p' to a specific format code.
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': f'best[height<={quality.replace("p", "")}]/best', # e.g., best[height<=720]/best
            'no_warnings': False,
        }

    print(f"Attempting to download: {url} | Quality: {quality} | Format: {format}")
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
