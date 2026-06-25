#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def get_duration(video_path):
    cmd = [
        'ffprobe', '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        str(video_path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None

def trim_video_in_place(video_path, max_duration=600):
    temp_path = video_path.with_name(video_path.stem + "_temp" + video_path.suffix)
    print(f"Trimming {video_path.name} to {max_duration} seconds...")
    # -c copy copies the video/audio streams directly without re-encoding (instantaneous)
    cmd = [
        'ffmpeg', '-y', '-i', str(video_path), 
        '-t', str(max_duration), 
        '-c', 'copy', 
        str(temp_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and temp_path.exists() and temp_path.stat().st_size > 0:
        # Replace original file
        video_path.unlink()
        temp_path.rename(video_path)
        print(f"✓ Successfully trimmed {video_path.name}")
        return True
    else:
        if temp_path.exists():
            temp_path.unlink()
        err_msg = res.stderr.decode(errors='ignore')
        print(f"✗ Failed to trim {video_path.name}: {err_msg}")
        return False

def main():
    # Load input dir from command line or default to the BBP2025 directory
    input_dir = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/Videos/BBP2025")
    if len(sys.argv) > 1:
        input_dir = Path(sys.argv[1])
        
    if not input_dir.exists():
        print(f"Directory not found: {input_dir}")
        sys.exit(1)
        
    print(f"Scanning directory: {input_dir}")
    video_extensions = {'.mp4', '.mkv', '.mov', '.avi', '.MP4', '.MKV', '.MOV'}
    videos = [p for p in input_dir.iterdir() if p.suffix in video_extensions]
    
    print(f"Found {len(videos)} video(s)")
    trimmed_count = 0
    skipped_count = 0
    
    for video in sorted(videos):
        duration = get_duration(video)
        if duration is None:
            print(f"Could not read duration for {video.name}, skipping.")
            continue
            
        print(f"Video: {video.name} | Duration: {duration:.2f}s ({duration/60:.2f}m)")
        if duration > 600:
            if trim_video_in_place(video):
                trimmed_count += 1
        else:
            skipped_count += 1
                
    print(f"\nDone! Trimmed {trimmed_count} video(s), skipped {skipped_count} video(s) already <= 10m.")

if __name__ == '__main__':
    main()
