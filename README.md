# YouTube Downloader

A minimal GUI application for downloading YouTube videos and playlists for personal and educational use.

## Features

- 🎥 Download single videos or entire playlists
- 🎵 Extract audio only (MP3, M4A, WAV, FLAC)
- 📊 Quality selection (Best, 1080p, 720p, 480p)
- 📁 Custom download folder selection
- 🔄 Built-in yt-dlp update functionality
- 📋 Real-time progress log
- ⏹️ Cancel downloads in progress
- 📦 **Fully portable** - all dependencies bundled (ffmpeg, yt-dlp)

## Quick Start

### Option 1: Run from Source (For Development)

1. **Install Python 3.8+** from [python.org](https://python.org)

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python yt_downloader_gui.py
   ```

### Option 2: Build Standalone .exe (Windows) - RECOMMENDED

1. **Install Python requirements:**
   ```bash
   pip install pyinstaller
   ```

2. **Run the build script:**
   ```bash
   python build_exe.py
   ```
   
   The build script will automatically:
   - Download the latest **yt-dlp.exe** (~10MB)
   - Download and extract **ffmpeg** + **ffprobe** (~150MB)
   - Bundle everything into a single portable executable

3. **Find your executable at:** `dist/YouTube Downloader.exe`

The resulting .exe is **fully portable** - it includes yt-dlp and ffmpeg, so you won't need to install anything!

## Usage

1. **Paste a YouTube URL** - Use the Paste button or Ctrl+V
2. **Select download type:**
   - Video: Downloads video with audio
   - Audio Only: Extracts just the audio
   - Playlist: Downloads all videos in a playlist
3. **Choose quality** (for video downloads)
4. **Select audio format** (for audio-only downloads)
5. **Choose download folder** or use the default
6. **Click Download**

## Updating yt-dlp

YouTube frequently changes their platform, so yt-dlp needs regular updates:

- Click the **"🔄 Update yt-dlp"** button in the bottom toolbar
- The app will download the latest version automatically

## Troubleshooting

### "yt-dlp not found" (when running from source)
- Run: `pip install yt-dlp`
- Or use the build script to create a bundled .exe

### Download fails
1. Update yt-dlp (YouTube changes frequently)
2. Check if the video/playlist is available in your region
3. Verify the URL is correct

### Build fails
- Make sure you have a working internet connection (to download ffmpeg/yt-dlp)
- Try running as administrator if there are permission issues

## What's Bundled in the .exe

The standalone executable includes:
- **yt-dlp**: The core YouTube download engine - Notice that since it's based on yt-dlp it can download from all the sites the project supports.
  You can find the full list here: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
- **ffmpeg**: For video/audio processing and format conversion
- **ffprobe**: For media file analysis

Total size: ~80-100MB (includes everything needed)

## File Structure

```
yt_downloader/
├── yt_downloader_gui.py   # Main application
├── build_exe.py           # Build script (downloads deps & creates .exe)
├── requirements.txt       # Python dependencies (for dev only)
├── README.md              # This file
└── tools/                 # Downloaded tools (created by build script)
    ├── ffmpeg.exe
    ├── ffprobe.exe
    └── yt-dlp.exe
```

## Legal Notice

This tool is for **personal and educational use only**. 
Please respect copyright laws and YouTube's Terms of Service.
Only download content you have permission to download.

## License

MIT License - Free for personal use.
