# YouTube Downloader

A minimal app for downloading YouTube videos, playlists and audio for personal and educational use.
Use it on its own, or **inside your DAW as a VST2 plugin**.

## Download

Get the latest version from the [**Releases page**](https://github.com/omerfra/yt-downloader/releases/latest)
(Windows 64-bit):

| File | What it is |
|------|------------|
| `YouTube.Downloader.VST.Setup.exe` | **Installer**: adds the VST2 plugin to your DAW, plus an optional Start Menu shortcut for the standalone app. Recommended for most people. |
| `YouTube.Downloader.exe` | **Portable app**: just run it, no installation. Doesn't include the DAW plugin. |

Both are unsigned, so Windows SmartScreen may say "Windows protected your PC" the first time.
Click **More info → Run anyway**.

## Features

- 🎥 Download single videos or entire playlists
- 🎵 Extract audio only (MP3, M4A, WAV, FLAC)
- 📊 Quality selection (Best, 1080p, 720p, 480p)
- 🎛️ **VST2 plugin**: the full downloader inside your DAW's plugin window
- 📁 Custom download folder selection
- 💾 Remembers your last folder and options between runs
- ⌨️ Ctrl+V works in any keyboard layout (Hebrew, Russian, etc.)
- 🔄 Built-in yt-dlp and ffmpeg updates
- 📋 Real-time progress log
- ⏹️ Cancel downloads in progress
- 📦 **Fully portable**: all dependencies bundled (ffmpeg, yt-dlp)

## Using It Inside Your DAW (VST2 plugin)

### Install

1. Close your DAW.
2. Run **`YouTube.Downloader.VST.Setup.exe`** and click **Next**.
3. Choose your VST2 plugins folder. The installer suggests the folder where your other VST2
   plugins already are (or where you installed it last time), so you can usually keep it.
   The plugin goes into a `YouTube Downloader` folder inside it.
4. Click **Install**, then open your DAW and **rescan plugins**.
5. Add **YouTube Downloader** as an effect on any track and open its window. The full
   downloader appears inside it.

If your DAW doesn't find the plugin, add the folder shown on the installer's last page to the
DAW's VST2 plugin folders.

### Repair, update or uninstall

- **Run the installer again** on a computer that already has the plugin to choose:
  - **Repair**: reinstalls into the same folder (also how you update to a newer version).
  - **Uninstall**: removes the plugin, its shortcuts and the Windows Apps entry.
- Or uninstall **YouTube Downloader VST Plugin** from **Windows Settings → Apps**.

Close your DAW first; the installer won't remove the plugin while a DAW has it loaded.

### Good to know

- Audio passes through unchanged, so it's safe on any track.
- Downloads keep running when you close the plugin window. Removing the plugin (or closing the
  DAW) closes the downloader.
- Tip: choose **Audio Only → WAV** and set "Save to" to your project's samples folder, then drag
  the file into your arrangement.
- Some DAWs grab keyboard shortcuts while a plugin window is focused. If typing in the URL box
  triggers DAW commands, use the **Paste** button instead.
- Works in DAWs that still support VST2 (Ableton Live, FL Studio, Reaper, Bitwig, Studio One...).
  Cubase/Nuendo 14+ no longer load VST2 plugins.

## Usage

1. **Paste a YouTube URL**: use the Paste button or Ctrl+V
2. **Select download type:**
   - Video: downloads video with audio
   - Audio Only: extracts just the audio
   - Playlist: downloads all videos in a playlist
3. **Choose quality** (for video downloads)
4. **Select audio format and bitrate** (for audio-only downloads)
5. **Choose download folder** or use the default
6. **Click Download**

Your folder and options are saved automatically and restored next time.
For a full guide, click **❓ Help / Instructions** in the app.

## Updating yt-dlp

YouTube frequently changes their platform, so yt-dlp needs regular updates:

- Click the **"🔄 Update yt-dlp"** button in the bottom toolbar
- The app will download the latest version automatically

Updates are saved to `%LOCALAPPDATA%\YouTubeDownloader\tools` and persist between runs.

## Building From Source

### Run from source (development)

1. **Install Python 3.8+** from [python.org](https://python.org)
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application:**
   ```bash
   python yt_downloader_gui.py
   ```

### Build the .exe, plugin and installer (Windows)

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```
2. **Run the build script:**
   ```bash
   python build_exe.py
   ```

The first run downloads everything it needs into `tools/` (nothing is installed system-wide):
**yt-dlp** (~10MB), **ffmpeg + ffprobe** (~150MB), the portable [Zig](https://ziglang.org)
C compiler for the plugin (~100MB) and the [NSIS](https://nsis.sourceforge.io) installer builder
(~2MB). Zig and NSIS downloads are checksum-verified.

Output in `dist/`:
- `YouTube Downloader.exe`: the portable app
- `YouTube Downloader.dll`: the VST2 plugin (needs the .exe in the same folder)
- `YouTube Downloader VST Setup.exe`: the installer containing both

**Manual plugin install:** copy **both** `YouTube Downloader.dll` and `YouTube Downloader.exe`
into the same folder inside your VST2 plugins folder.

## Troubleshooting

### Download fails
1. Update yt-dlp (YouTube changes frequently)
2. Check if the video/playlist is available in your region
3. Verify the URL is correct

### "No audio" or "Format error"
- Click **"🔄 Update ffmpeg"**

### The plugin doesn't show up in my DAW
- Rescan plugins after installing
- Make sure the DAW scans the folder you installed to (shown on the installer's last page)
- Make sure your DAW supports VST2 (see above) and is 64-bit

### The plugin window says "Could not find YouTube Downloader.exe"
- The `.dll` and `.exe` must be in the same folder. Run the installer and choose **Repair**.

### The installer says the plugin is in use
- Close your DAW (and the standalone app) and try again

### "yt-dlp not found" (when running from source)
- Run: `pip install yt-dlp`
- Or use the build script to create a bundled .exe

### Build fails
- Make sure you have a working internet connection (the first build downloads its tools)
- Try running as administrator if there are permission issues

## What's Bundled in the .exe

The standalone executable includes:
- **yt-dlp**: the core download engine. Since it's based on yt-dlp, it can download from all the
  sites yt-dlp supports: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
- **ffmpeg**: for video/audio processing and format conversion
- **ffprobe**: for media file analysis

Total size: ~150MB (includes everything needed)

## File Structure

```
yt_downloader/
├── yt_downloader_gui.py   # Main application
├── build_exe.py           # Build script (downloads tools, builds .exe, plugin and installer)
├── requirements.txt       # Python dependencies (for dev only)
├── README.md              # This file
├── installer/
│   └── installer.nsi      # NSIS script for the plugin installer
├── vst_plugin/            # VST2 plugin that embeds the app in a DAW
│   ├── plugin.c           # Plugin source (pass-through effect + editor window)
│   ├── plugin.def         # DLL exports
│   ├── vst2_abi.h         # Minimal VST2 interface declarations
│   └── test_host.c        # Tiny test host for checking the plugin without a DAW
└── tools/                 # Downloaded tools (created by build script)
    ├── ffmpeg.exe
    ├── ffprobe.exe
    ├── yt-dlp.exe
    ├── zig/               # Portable C compiler for the plugin
    └── nsis/              # Portable installer builder
```

## Legal Notice

This tool is for **personal and educational use only**.
Please respect copyright laws and YouTube's Terms of Service.
Only download content you have permission to download.

## License

MIT License - Free for personal use.
