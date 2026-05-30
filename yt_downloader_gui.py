"""
YouTube Downloader - Minimal GUI
A simple desktop application for downloading YouTube videos and playlists.
For personal and educational use only.
"""

import subprocess
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


def get_app_path():
    """Get the path where the app is running from (handles both frozen and source)."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - _MEIPASS is the temp extraction folder
        return Path(sys._MEIPASS)
    else:
        # Running from source
        return Path(__file__).parent


def get_user_tools_path():
    """Get writable path for user-updated tools (persists between runs)."""
    # Use AppData on Windows, ~/.local/share on Linux/Mac
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    else:
        base = Path.home() / '.local' / 'share'
    
    tools_path = base / 'YouTubeDownloader' / 'tools'
    tools_path.mkdir(parents=True, exist_ok=True)
    return tools_path


def get_tool_path(tool_name):
    """Get the full path to a bundled tool (yt-dlp, ffmpeg, ffprobe)."""
    # First check user's local tools folder (for updates)
    user_tools = get_user_tools_path()
    user_tool = user_tools / tool_name
    if user_tool.exists():
        return str(user_tool)
    
    # Then check bundled location
    app_path = get_app_path()
    
    # Check in the app directory first (bundled)
    tool_path = app_path / tool_name
    if tool_path.exists():
        return str(tool_path)
    
    # Check in tools subdirectory (development)
    tool_path = app_path / "tools" / tool_name
    if tool_path.exists():
        return str(tool_path)
    
    # Fall back to system PATH
    return tool_name


def get_local_version(tool_name, version_flag='--version'):
    """Get the version of a locally installed tool."""
    try:
        tool_path = get_tool_path(tool_name + ('.exe' if sys.platform == 'win32' else ''))
        result = subprocess.run([tool_path, version_flag], 
                               capture_output=True, text=True, timeout=10,
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        return result.stdout.strip().split('\n')[0]
    except Exception:
        return None


def get_latest_ytdlp_version():
    """Check GitHub for the latest yt-dlp version."""
    try:
        import urllib.request
        import json
        
        url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'YouTubeDownloader'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get('tag_name', '').strip()
    except Exception:
        return None


def get_latest_ffmpeg_version():
    """Check GitHub for the latest ffmpeg-builds version."""
    try:
        import urllib.request
        import json
        
        # BtbN releases use date-based tags
        url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'YouTubeDownloader'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get('tag_name', '').strip()
    except Exception:
        return None


class YouTubeDownloader:
    """Main application class for the YouTube Downloader GUI."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("650x550")
        self.root.resizable(True, True)
        self.root.minsize(550, 450)
        
        # Set icon if available
        self.setup_icon()
        
        # Default download path
        self.default_path = str(Path.home() / "Downloads" / "YouTube")
        
        # Track download process
        self.current_process = None
        self.is_downloading = False
        
        # Build the UI
        self.create_menu()
        self.create_widgets()
        
        # Check for yt-dlp on startup
        self.root.after(100, self.check_ytdlp_status)
        
        # Show welcome message
        self.root.after(200, self.show_welcome)
    
    def setup_icon(self):
        """Set application icon if available."""
        try:
            # For bundled exe, look in the same directory
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(__file__)
            icon_path = os.path.join(base_path, 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass  # Icon is optional
    
    def create_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📖 Instructions", command=self.show_instructions)
        help_menu.add_command(label="🔍 Check for Updates", command=self.check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ About", command=self.show_about)
    
    def show_instructions(self):
        """Show instructions dialog."""
        instructions = """
═══════════════════════════════════════════════════
           YOUTUBE DOWNLOADER - INSTRUCTIONS
═══════════════════════════════════════════════════

Hey Yotam!
I promised you the tool.
Here it is, hope it works :)

📥 HOW TO DOWNLOAD:
─────────────────────────────────────────────────
1. Copy a YouTube URL from your browser
2. Click "Paste" or press Ctrl+V in the URL field
3. Choose your options:
   • Video - Downloads video with audio
   • Audio Only - Extracts just the sound (MP3, etc.)
   • Playlist - Downloads all videos in a playlist
4. Select quality (for video) or format (for audio)
5. Choose where to save (default: Downloads/YouTube)
6. Click "⬇ Download" and wait for completion

═══════════════════════════════════════════════════

🔄 UPDATING THE TOOLS:
─────────────────────────────────────────────────
YouTube changes frequently, so yt-dlp needs updates.

• Click "🔍 Check Updates" to see if new versions exist
• If you see 🆕 (orange), an update is available
• Click "🔄 Update yt-dlp" to download the latest version
• Click "🔄 Update ffmpeg" if audio extraction fails

Updates are saved automatically and persist between 
app restarts. No admin rights needed!

═══════════════════════════════════════════════════

⚠️ TROUBLESHOOTING:
─────────────────────────────────────────────────
❌ "Download failed"
   → Click "🔄 Update yt-dlp" (YouTube may have changed)
   → Check if the video is available in your region

❌ "No audio" or "Format error"  
   → Click "🔄 Update ffmpeg"

❌ App won't start
   → Windows SmartScreen may block it
   → Click "More info" → "Run anyway"

═══════════════════════════════════════════════════

📁 WHERE ARE MY FILES?
─────────────────────────────────────────────────
• Downloads: Check the "Save to" folder (default is 
  your Downloads/YouTube folder)
• Click "📁 Open Folder" to open it directly
• Playlists create a subfolder with the playlist name

═══════════════════════════════════════════════════

⚖️ LEGAL NOTICE:
─────────────────────────────────────────────────
This tool is for PERSONAL and EDUCATIONAL use only.
Please respect copyright and YouTube's Terms of Service.
Only download content you have permission to download.

═══════════════════════════════════════════════════
"""
        # Create a new window for instructions
        instr_window = tk.Toplevel(self.root)
        instr_window.title("Instructions")
        instr_window.geometry("550x500")
        instr_window.resizable(True, True)
        
        # Text widget with scrollbar
        frame = ttk.Frame(instr_window, padding="10")
        frame.pack(fill="both", expand=True)
        
        text = tk.Text(frame, wrap="word", font=("Consolas", 10), bg="#1e1e1e", fg="#ffffff")
        text.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.configure(yscrollcommand=scrollbar.set)
        
        text.insert("1.0", instructions)
        text.configure(state="disabled")
        
        # Close button
        close_btn = ttk.Button(instr_window, text="Close", command=instr_window.destroy)
        close_btn.pack(pady=10)
    
    def show_about(self):
        """Show about dialog."""
        about_text = """YouTube Downloader

A simple tool for downloading YouTube videos 
and playlists for personal/educational use.

Powered by:
• yt-dlp - YouTube download engine
• ffmpeg - Audio/video processing

For personal and educational use only.
Please respect copyright laws.

I love piracy!!!
@omerfra

"""
        
        messagebox.showinfo("About", about_text)
    
    def show_welcome(self):
        """Show welcome message in log on startup."""
        self.log("═" * 50)
        self.log("  Welcome to YouTube Downloader!")
        self.log("═" * 50)
        self.log("")
        self.log("Quick Start:")
        self.log("  1. Paste a YouTube URL above")
        self.log("  2. Choose Video, Audio, or Playlist")
        self.log("  3. Click Download")
        self.log("")
        self.log("💡 Tip: Click '❓ Help / Instructions' for full guide")
        self.log("💡 Tip: If downloads fail, click '🔄 Update yt-dlp'")
        self.log("")
        self.log("─" * 50)
    
    def create_widgets(self):
        """Create all UI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # --- URL Input Section ---
        url_frame = ttk.LabelFrame(main_frame, text="YouTube URL", padding="5")
        url_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        url_frame.columnconfigure(0, weight=1)
        
        self.url_entry = ttk.Entry(url_frame, width=60)
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.url_entry.bind('<Return>', lambda e: self.start_download())
        
        paste_btn = ttk.Button(url_frame, text="Paste", width=8, command=self.paste_url)
        paste_btn.grid(row=0, column=1)
        
        # --- Download Options Section ---
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)
        
        # Download type
        ttk.Label(options_frame, text="Type:").grid(row=0, column=0, sticky="w", pady=2)
        self.download_type = tk.StringVar(value="video")
        type_frame = ttk.Frame(options_frame)
        type_frame.grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(type_frame, text="Video", variable=self.download_type, 
                        value="video").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(type_frame, text="Audio Only", variable=self.download_type, 
                        value="audio").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(type_frame, text="Playlist", variable=self.download_type, 
                        value="playlist").pack(side="left")
        
        # Quality selection
        ttk.Label(options_frame, text="Quality:").grid(row=1, column=0, sticky="w", pady=2)
        self.quality = tk.StringVar(value="best")
        quality_frame = ttk.Frame(options_frame)
        quality_frame.grid(row=1, column=1, sticky="w")
        qualities = [("Best", "best"), ("1080p", "1080"), ("720p", "720"), ("480p", "480")]
        for text, val in qualities:
            ttk.Radiobutton(quality_frame, text=text, variable=self.quality, 
                           value=val).pack(side="left", padx=(0, 10))
        
        # Audio format (for audio-only downloads)
        ttk.Label(options_frame, text="Audio Format:").grid(row=2, column=0, sticky="w", pady=2)
        self.audio_format = tk.StringVar(value="mp3")
        audio_frame = ttk.Frame(options_frame)
        audio_frame.grid(row=2, column=1, sticky="w")
        for fmt in ["mp3", "m4a", "wav", "flac"]:
            ttk.Radiobutton(audio_frame, text=fmt.upper(), variable=self.audio_format, 
                           value=fmt).pack(side="left", padx=(0, 10))
        
        # Output path
        ttk.Label(options_frame, text="Save to:").grid(row=3, column=0, sticky="w", pady=2)
        path_frame = ttk.Frame(options_frame)
        path_frame.grid(row=3, column=1, sticky="ew")
        path_frame.columnconfigure(0, weight=1)
        
        self.path_var = tk.StringVar(value=self.default_path)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        browse_btn = ttk.Button(path_frame, text="Browse", width=8, command=self.browse_folder)
        browse_btn.grid(row=0, column=1)
        
        # --- Action Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        button_frame.columnconfigure(0, weight=1)
        
        self.download_btn = ttk.Button(button_frame, text="⬇ Download", 
                                        command=self.start_download, style="Accent.TButton")
        self.download_btn.grid(row=0, column=0, pady=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="✕ Cancel", 
                                      command=self.cancel_download, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=10, pady=5)
        
        # --- Progress Section ---
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="gray")
        self.status_label.grid(row=1, column=0, sticky="w")
        
        # --- Log/Output Section ---
        log_frame = ttk.LabelFrame(main_frame, text="Output Log", padding="5")
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled",
                                 bg="#1e1e1e", fg="#cccccc", font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Clear log button
        log_buttons_frame = ttk.Frame(log_frame)
        log_buttons_frame.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        clear_btn = ttk.Button(log_buttons_frame, text="Clear Log", command=self.clear_log)
        clear_btn.pack(side="left", padx=(0, 10))
        
        help_btn = ttk.Button(log_buttons_frame, text="❓ Help / Instructions", command=self.show_instructions)
        help_btn.pack(side="left")
        
        # --- Bottom Toolbar ---
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.grid(row=5, column=0, sticky="ew")
        toolbar_frame.columnconfigure(1, weight=1)
        
        # Version info frame (left side)
        version_frame = ttk.Frame(toolbar_frame)
        version_frame.pack(side="left", fill="x", expand=True)
        
        # yt-dlp status indicator
        self.ytdlp_status = ttk.Label(version_frame, text="⏳ yt-dlp: checking...", foreground="gray")
        self.ytdlp_status.pack(side="left", padx=(0, 15))
        
        # ffmpeg status indicator
        self.ffmpeg_status = ttk.Label(version_frame, text="⏳ ffmpeg: checking...", foreground="gray")
        self.ffmpeg_status.pack(side="left")
        
        # Buttons frame (right side)
        buttons_frame = ttk.Frame(toolbar_frame)
        buttons_frame.pack(side="right")
        
        # Check for updates button
        self.check_updates_btn = ttk.Button(buttons_frame, text="🔍 Check Updates", 
                                             command=self.check_for_updates)
        self.check_updates_btn.pack(side="right", padx=(5, 0))
        
        # Update button
        self.update_btn = ttk.Button(buttons_frame, text="🔄 Update yt-dlp", 
                                      command=self.update_ytdlp, state="disabled")
        self.update_btn.pack(side="right", padx=(5, 0))
        
        # Update ffmpeg button
        self.update_ffmpeg_btn = ttk.Button(buttons_frame, text="🔄 Update ffmpeg", 
                                             command=self.update_ffmpeg, state="disabled")
        self.update_ffmpeg_btn.pack(side="right", padx=(5, 0))
        
        # Open folder button
        open_folder_btn = ttk.Button(buttons_frame, text="📁 Open Folder", 
                                      command=self.open_download_folder)
        open_folder_btn.pack(side="right")
    
    def log(self, message):
        """Add a message to the log."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
    def clear_log(self):
        """Clear the log text."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
    
    def paste_url(self):
        """Paste URL from clipboard."""
        try:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, self.root.clipboard_get())
        except tk.TclError:
            messagebox.showwarning("Paste", "Clipboard is empty or doesn't contain text.")
    
    def browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder:
            self.path_var.set(folder)
    
    def open_download_folder(self):
        """Open the download folder in file explorer."""
        path = self.path_var.get()
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        else:
            messagebox.showinfo("Folder", f"Folder doesn't exist yet:\n{path}")
    
    def check_ytdlp_status(self):
        """Check if yt-dlp is installed and get its version."""
        def check():
            # Check yt-dlp
            version = get_local_version('yt-dlp')
            if version:
                self.root.after(0, lambda v=version: self.update_ytdlp_status(True, v))
            else:
                self.root.after(0, lambda: self.update_ytdlp_status(False, None))
            
            # Check ffmpeg
            ffmpeg_version = get_local_version('ffmpeg', '-version')
            if ffmpeg_version:
                # Parse ffmpeg version (first line contains version info)
                # Example: "ffmpeg version 6.0-full_build-www.gyan.dev ..."
                parts = ffmpeg_version.split()
                if len(parts) >= 3:
                    ffmpeg_version = parts[2].split('-')[0]  # Get just the version number
                self.root.after(0, lambda v=ffmpeg_version: self.update_ffmpeg_status(True, v))
            else:
                self.root.after(0, lambda: self.update_ffmpeg_status(False, None))
        
        threading.Thread(target=check, daemon=True).start()
    
    def update_ffmpeg_status(self, installed, version):
        """Update the ffmpeg status indicator."""
        if installed:
            self.ffmpeg_status.configure(text=f"✅ ffmpeg: {version}", foreground="green")
            self.update_ffmpeg_btn.configure(state="normal")
        else:
            self.ffmpeg_status.configure(text="❌ ffmpeg: not found", foreground="red")
            self.update_ffmpeg_btn.configure(state="normal")
            self.log("WARNING: ffmpeg not found. Audio extraction may not work.")
    
    def check_for_updates(self):
        """Check if newer versions are available online."""
        self.check_updates_btn.configure(state="disabled")
        self.log("Checking for updates...")
        
        def check():
            results = []
            
            # Check yt-dlp
            local_ytdlp = get_local_version('yt-dlp')
            latest_ytdlp = get_latest_ytdlp_version()
            
            if local_ytdlp and latest_ytdlp:
                # Compare versions (yt-dlp uses date-based versions like 2024.01.01)
                local_clean = local_ytdlp.replace('.', '').replace('-', '')[:8]
                latest_clean = latest_ytdlp.replace('.', '').replace('-', '')[:8]
                
                if latest_clean > local_clean:
                    results.append(f"🆕 yt-dlp update available: {local_ytdlp} → {latest_ytdlp}")
                    self.root.after(0, lambda: self.ytdlp_status.configure(
                        text=f"🆕 yt-dlp: {local_ytdlp} (update available)", foreground="orange"))
                else:
                    results.append(f"✅ yt-dlp is up to date ({local_ytdlp})")
            elif latest_ytdlp:
                results.append(f"ℹ️ Latest yt-dlp: {latest_ytdlp}")
            else:
                results.append("⚠️ Could not check yt-dlp updates")
            
            # Check ffmpeg (just report latest, harder to compare versions)
            latest_ffmpeg = get_latest_ffmpeg_version()
            if latest_ffmpeg:
                results.append(f"ℹ️ Latest ffmpeg build: {latest_ffmpeg}")
            
            # Log results
            for r in results:
                self.root.after(0, lambda msg=r: self.log(msg))
            
            self.root.after(0, lambda: self.check_updates_btn.configure(state="normal"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def update_ytdlp_status(self, installed, version):
        """Update the yt-dlp status indicator."""
        if installed:
            self.ytdlp_status.configure(text=f"✅ yt-dlp {version}", foreground="green")
            self.update_btn.configure(state="normal")
        else:
            self.ytdlp_status.configure(text="❌ yt-dlp not found", foreground="red")
            self.update_btn.configure(state="normal", text="📥 Install yt-dlp")
            self.log("WARNING: yt-dlp is not installed or not in PATH.")
            self.log("Click 'Install yt-dlp' to install it.")
    
    def update_ytdlp(self):
        """Update yt-dlp (download latest version to user's local folder)."""
        self.update_btn.configure(state="disabled")
        self.log("Updating yt-dlp...")
        self.status_label.configure(text="Updating yt-dlp...", foreground="blue")
        
        def do_update():
            try:
                import urllib.request
                
                # Save to user's local tools folder (writable, persists between runs)
                tools_path = get_user_tools_path()
                ytdlp_exe = tools_path / ('yt-dlp.exe' if sys.platform == 'win32' else 'yt-dlp')
                
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                
                self.root.after(0, lambda: self.log("Downloading latest yt-dlp..."))
                
                # Download to a temp file first
                temp_path = tools_path / "yt-dlp_new.exe"
                urllib.request.urlretrieve(url, temp_path)
                
                # Replace the old one if exists
                if ytdlp_exe.exists():
                    ytdlp_exe.unlink()
                temp_path.rename(ytdlp_exe)
                
                self.root.after(0, lambda: self.log(f"✅ yt-dlp updated successfully!"))
                self.root.after(0, lambda: self.log(f"   Saved to: {ytdlp_exe}"))
                self.root.after(0, self.check_ytdlp_status)
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Update error: {e}"))
            finally:
                self.root.after(0, lambda: self.update_btn.configure(state="normal"))
                self.root.after(0, lambda: self.status_label.configure(text="Ready", foreground="gray"))
        
        threading.Thread(target=do_update, daemon=True).start()
    
    def update_ffmpeg(self):
        """Update ffmpeg (download latest version to user's local folder)."""
        self.update_ffmpeg_btn.configure(state="disabled")
        self.log("Updating ffmpeg (this may take a while, ~150MB)...")
        self.status_label.configure(text="Updating ffmpeg...", foreground="blue")
        
        def do_update():
            try:
                import urllib.request
                import zipfile
                
                tools_path = get_user_tools_path()
                ffmpeg_zip = tools_path / "ffmpeg_new.zip"
                ffmpeg_exe = tools_path / "ffmpeg.exe"
                ffprobe_exe = tools_path / "ffprobe.exe"
                
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                
                self.root.after(0, lambda: self.log("Downloading ffmpeg (~150MB)..."))
                urllib.request.urlretrieve(url, ffmpeg_zip)
                
                self.root.after(0, lambda: self.log("Extracting ffmpeg..."))
                
                with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                    for name in zip_ref.namelist():
                        if name.endswith('bin/ffmpeg.exe'):
                            with zip_ref.open(name) as src:
                                content = src.read()
                            if ffmpeg_exe.exists():
                                ffmpeg_exe.unlink()
                            ffmpeg_exe.write_bytes(content)
                            self.root.after(0, lambda: self.log("  ✅ Extracted ffmpeg.exe"))
                        elif name.endswith('bin/ffprobe.exe'):
                            with zip_ref.open(name) as src:
                                content = src.read()
                            if ffprobe_exe.exists():
                                ffprobe_exe.unlink()
                            ffprobe_exe.write_bytes(content)
                            self.root.after(0, lambda: self.log("  ✅ Extracted ffprobe.exe"))
                
                # Cleanup zip
                ffmpeg_zip.unlink()
                
                self.root.after(0, lambda: self.log(f"✅ ffmpeg updated successfully!"))
                self.root.after(0, lambda: self.log(f"   Saved to: {tools_path}"))
                self.root.after(0, self.check_ytdlp_status)
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ ffmpeg update error: {e}"))
            finally:
                self.root.after(0, lambda: self.update_ffmpeg_btn.configure(state="normal"))
                self.root.after(0, lambda: self.status_label.configure(text="Ready", foreground="gray"))
        
        threading.Thread(target=do_update, daemon=True).start()
    
    def build_command(self, url):
        """Build the yt-dlp command based on selected options."""
        output_path = self.path_var.get()
        os.makedirs(output_path, exist_ok=True)
        
        # Get paths to bundled tools
        ytdlp_path = get_tool_path('yt-dlp.exe' if sys.platform == 'win32' else 'yt-dlp')
        ffmpeg_path = get_tool_path('ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
        
        cmd = [ytdlp_path, '--newline', '--progress']
        
        # Add ffmpeg location if bundled
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if os.path.exists(ffmpeg_path):
            cmd.extend(['--ffmpeg-location', ffmpeg_dir])
        
        download_type = self.download_type.get()
        quality = self.quality.get()
        
        if download_type == "audio":
            # Audio-only download
            audio_fmt = self.audio_format.get()
            cmd.extend([
                '-x',  # Extract audio
                '--audio-format', audio_fmt,
                '--audio-quality', '0',  # Best quality
                '-o', os.path.join(output_path, '%(title)s.%(ext)s')
            ])
        elif download_type == "playlist":
            # Playlist download
            cmd.append('--yes-playlist')
            
            if quality != "best":
                cmd.extend(['-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'])
            
            cmd.extend(['-o', os.path.join(output_path, '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s')])
        else:
            # Single video download
            cmd.append('--no-playlist')
            
            if quality != "best":
                cmd.extend(['-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'])
            
            cmd.extend(['-o', os.path.join(output_path, '%(title)s.%(ext)s')])
        
        cmd.append(url)
        return cmd
    
    def start_download(self):
        """Start the download process."""
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showwarning("URL Required", "Please enter a YouTube URL.")
            return
        
        if not ('youtube.com' in url or 'youtu.be' in url):
            if not messagebox.askyesno("URL Check", 
                "This doesn't look like a YouTube URL. Continue anyway?"):
                return
        
        self.is_downloading = True
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.start(10)
        self.status_label.configure(text="Downloading...", foreground="blue")
        
        cmd = self.build_command(url)
        self.log(f"Command: {' '.join(cmd)}")
        self.log("-" * 50)
        
        def run_download():
            try:
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                for line in self.current_process.stdout:
                    if not self.is_downloading:
                        break
                    line = line.strip()
                    if line:
                        self.root.after(0, lambda l=line: self.log(l))
                
                self.current_process.wait()
                
                if self.current_process.returncode == 0:
                    self.root.after(0, self.download_complete)
                else:
                    self.root.after(0, lambda: self.download_error("Download failed. Check the log for details."))
                    
            except Exception as e:
                self.root.after(0, lambda: self.download_error(str(e)))
        
        threading.Thread(target=run_download, daemon=True).start()
    
    def download_complete(self):
        """Handle successful download completion."""
        self.is_downloading = False
        self.current_process = None
        self.progress_bar.stop()
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.status_label.configure(text="✅ Download complete!", foreground="green")
        self.log("=" * 50)
        self.log("✅ Download completed successfully!")
    
    def download_error(self, error_msg):
        """Handle download error."""
        self.is_downloading = False
        self.current_process = None
        self.progress_bar.stop()
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.status_label.configure(text="❌ Download failed", foreground="red")
        self.log(f"❌ Error: {error_msg}")
    
    def cancel_download(self):
        """Cancel the current download."""
        if self.current_process:
            self.is_downloading = False
            self.current_process.terminate()
            self.current_process = None
            self.progress_bar.stop()
            self.download_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            self.status_label.configure(text="Cancelled", foreground="orange")
            self.log("⚠️ Download cancelled by user.")


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Configure styles for a cleaner look
    style = ttk.Style()
    style.theme_use('clam')  # Use 'clam' theme for better cross-platform look
    
    app = YouTubeDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
