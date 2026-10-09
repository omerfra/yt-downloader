"""
Build script for YouTube Downloader
Creates a standalone .exe with all dependencies bundled (including ffmpeg and yt-dlp),
plus a VST2 plugin (.dll) that shows the app inside a DAW.

Requirements:
    pip install pyinstaller yt-dlp requests

Usage:
    python build_exe.py
"""

import subprocess
import sys
import os
import shutil
import zipfile
import hashlib
import json
import urllib.request
from pathlib import Path

# URLs for bundled tools
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

# Portable C compiler used to build the VST2 plugin (no install needed)
ZIG_VERSION = "0.17.0"
ZIG_INDEX_URL = "https://ziglang.org/download/index.json"
PLUGIN_NAME = "YouTube Downloader.dll"

# Portable NSIS used to build the plugin installer (no install needed)
NSIS_VERSION = "3.13"
NSIS_URL = f"https://downloads.sourceforge.net/project/nsis/NSIS%203/{NSIS_VERSION}/nsis-{NSIS_VERSION}.zip"
NSIS_SHA256 = "ba63dffc4410ee89193e1cb5a41989991bd77c61068da17e3156d136b7b0b3d8"
INSTALLER_NAME = "YouTube Downloader VST Setup.exe"
APP_VERSION = "1.2.0"


def check_requirements():
    """Check if required packages are installed."""
    print("Checking requirements...")
    
    required = ['pyinstaller', 'yt-dlp']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Installing missing packages: {missing}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
    
    print("✅ All requirements satisfied.")


def download_file(url, dest_path, description="file"):
    """Download a file with progress indication."""
    print(f"Downloading {description}...")
    print(f"  URL: {url}")
    
    try:
        urllib.request.urlretrieve(url, dest_path)
        print(f"  ✅ Downloaded to {dest_path}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to download: {e}")
        return False


def download_ffmpeg(tools_dir):
    """Download and extract ffmpeg."""
    tools_dir = Path(tools_dir)
    tools_dir.mkdir(exist_ok=True)
    
    ffmpeg_zip = tools_dir / "ffmpeg.zip"
    ffmpeg_exe = tools_dir / "ffmpeg.exe"
    ffprobe_exe = tools_dir / "ffprobe.exe"
    
    # Check if already downloaded
    if ffmpeg_exe.exists() and ffprobe_exe.exists():
        print("✅ ffmpeg already downloaded.")
        return True
    
    # Download ffmpeg zip
    if not download_file(FFMPEG_URL, ffmpeg_zip, "ffmpeg"):
        return False
    
    # Extract ffmpeg.exe and ffprobe.exe
    print("Extracting ffmpeg...")
    try:
        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            # Find the bin folder in the zip
            for name in zip_ref.namelist():
                if name.endswith('bin/ffmpeg.exe'):
                    # Extract ffmpeg.exe
                    with zip_ref.open(name) as src, open(ffmpeg_exe, 'wb') as dst:
                        dst.write(src.read())
                    print(f"  ✅ Extracted ffmpeg.exe")
                elif name.endswith('bin/ffprobe.exe'):
                    # Extract ffprobe.exe
                    with zip_ref.open(name) as src, open(ffprobe_exe, 'wb') as dst:
                        dst.write(src.read())
                    print(f"  ✅ Extracted ffprobe.exe")
        
        # Clean up zip
        ffmpeg_zip.unlink()
        return ffmpeg_exe.exists() and ffprobe_exe.exists()
    except Exception as e:
        print(f"  ❌ Extraction failed: {e}")
        return False


def download_ytdlp(tools_dir):
    """Download yt-dlp executable."""
    tools_dir = Path(tools_dir)
    tools_dir.mkdir(exist_ok=True)
    
    ytdlp_exe = tools_dir / "yt-dlp.exe"
    
    # Check if already downloaded
    if ytdlp_exe.exists():
        print("✅ yt-dlp already downloaded.")
        return True
    
    return download_file(YTDLP_URL, ytdlp_exe, "yt-dlp")


def download_zig(tools_dir):
    """Download the Zig toolchain (used as a C compiler). Returns path to zig.exe or None."""
    zig_dir = Path(tools_dir) / "zig"
    existing = list(zig_dir.glob(f"zig-*-{ZIG_VERSION}/zig.exe"))
    if existing:
        print(f"✅ Zig {ZIG_VERSION} already downloaded.")
        return existing[0]

    zig_dir.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(ZIG_INDEX_URL, headers={'User-Agent': 'YouTubeDownloader'})
        with urllib.request.urlopen(req, timeout=30) as response:
            entry = json.loads(response.read().decode())[ZIG_VERSION]["x86_64-windows"]
    except Exception as e:
        print(f"  ❌ Could not look up Zig {ZIG_VERSION}: {e}")
        return None

    zig_zip = zig_dir / "zig.zip"
    if not download_file(entry["tarball"], zig_zip, f"Zig {ZIG_VERSION} compiler (~100MB)"):
        return None

    with open(zig_zip, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != entry["shasum"]:
        print("  ❌ Zig download checksum mismatch.")
        zig_zip.unlink()
        return None

    print("Extracting Zig...")
    with zipfile.ZipFile(zig_zip, 'r') as zip_ref:
        zip_ref.extractall(zig_dir)
    zig_zip.unlink()

    found = list(zig_dir.glob(f"zig-*-{ZIG_VERSION}/zig.exe"))
    return found[0] if found else None


def build_vst_plugin(tools_dir):
    """Compile the VST2 plugin into dist/ next to the .exe it launches."""
    print("\n" + "="*50)
    print("Building VST2 plugin...")
    print("="*50 + "\n")

    zig = download_zig(tools_dir)
    if not zig:
        print("\n⚠️ Could not get a C compiler. Skipping the VST2 plugin.")
        return False

    Path('dist').mkdir(exist_ok=True)
    result = subprocess.run([
        str(zig), 'cc',
        '-target', 'x86_64-windows-gnu',
        '-shared', '-O2', '-s',
        '-o', os.path.join('dist', PLUGIN_NAME),
        os.path.join('vst_plugin', 'plugin.c'),
        os.path.join('vst_plugin', 'plugin.def'),
        '-luser32', '-lgdi32',
    ])

    if result.returncode != 0:
        print("\n❌ VST2 plugin build failed. Check the errors above.")
        return False

    # The linker also emits an import library we don't need
    import_lib = Path('dist') / 'plugin.lib'
    if import_lib.exists():
        import_lib.unlink()

    print(f"✅ VST2 plugin built: dist/{PLUGIN_NAME}")
    return True


def download_nsis(tools_dir):
    """Download portable NSIS (installer builder). Returns path to makensis.exe or None."""
    nsis_dir = Path(tools_dir) / "nsis"
    makensis = nsis_dir / f"nsis-{NSIS_VERSION}" / "makensis.exe"
    if makensis.exists():
        print(f"✅ NSIS {NSIS_VERSION} already downloaded.")
        return makensis

    nsis_dir.mkdir(parents=True, exist_ok=True)
    nsis_zip = nsis_dir / "nsis.zip"
    if not download_file(NSIS_URL, nsis_zip, f"NSIS {NSIS_VERSION} installer builder (~2MB)"):
        return None

    with open(nsis_zip, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != NSIS_SHA256:
        print("  ❌ NSIS download checksum mismatch.")
        nsis_zip.unlink()
        return None

    print("Extracting NSIS...")
    with zipfile.ZipFile(nsis_zip, 'r') as zip_ref:
        zip_ref.extractall(nsis_dir)
    nsis_zip.unlink()
    return makensis if makensis.exists() else None


def build_installer(tools_dir):
    """Package the plugin + exe into dist/YouTube Downloader VST Setup.exe."""
    print("\n" + "="*50)
    print("Building plugin installer...")
    print("="*50 + "\n")

    makensis = download_nsis(tools_dir)
    if not makensis:
        print("\n⚠️ Could not get NSIS. Skipping the installer.")
        return False

    result = subprocess.run([
        str(makensis), '/V2',
        f'/DDIST_DIR={Path("dist").resolve()}',
        f'/DVERSION={APP_VERSION}',
        os.path.join('installer', 'installer.nsi'),
    ])

    if result.returncode != 0:
        print("\n❌ Installer build failed. Check the errors above.")
        return False

    print(f"✅ Installer built: dist/{INSTALLER_NAME}")
    return True


def get_ytdlp_path():
    """Find the yt-dlp executable path."""
    # Try to find yt-dlp in PATH or Scripts folder
    if sys.platform == 'win32':
        scripts_dir = Path(sys.executable).parent / 'Scripts'
        ytdlp_exe = scripts_dir / 'yt-dlp.exe'
        if ytdlp_exe.exists():
            return str(ytdlp_exe)
    
    # Try which/where
    try:
        result = subprocess.run(
            ['where' if sys.platform == 'win32' else 'which', 'yt-dlp'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except Exception:
        pass
    
    return None


def create_spec_file(tools_dir):
    """Create a PyInstaller spec file that bundles ffmpeg and yt-dlp."""
    tools_dir = Path(tools_dir).resolve()
    
    # Build the datas list for bundled tools
    datas_list = []
    for tool in ['ffmpeg.exe', 'ffprobe.exe', 'yt-dlp.exe']:
        tool_path = tools_dir / tool
        if tool_path.exists():
            datas_list.append(f"(r'{tool_path}', '.')")
    
    datas_str = ',\n        '.join(datas_list) if datas_list else ''
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['yt_downloader_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        {datas_str}
    ],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YouTube Downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add 'icon.ico' here if you have one
)
'''
    
    with open('yt_downloader.spec', 'w') as f:
        f.write(spec_content)
    
    print("✅ Created spec file with bundled tools.")


def build_exe():
    """Build the executable using PyInstaller."""
    print("\n" + "="*50)
    print("Building executable...")
    print("="*50 + "\n")
    
    # Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Cleaned {folder}/")
    
    # Build using spec file
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        'yt_downloader.spec'
    ])
    
    if result.returncode == 0:
        print("\n" + "="*50)
        print("✅ BUILD SUCCESSFUL!")
        print("="*50)
        print(f"\nYour executable is at: dist/YouTube Downloader.exe")
        print("\n📦 This is a FULLY PORTABLE executable that includes:")
        print("   - yt-dlp (YouTube downloader)")
        print("   - ffmpeg & ffprobe (audio/video processing)")
        print("\nNo additional installations needed on the target system!")
    else:
        print("\n❌ Build failed. Check the errors above.")
        return False
    
    return True


def main():
    """Main build process."""
    print("="*50)
    print("YouTube Downloader Build Script")
    print("="*50 + "\n")
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Create tools directory
    tools_dir = Path("tools")
    
    # Check and install requirements
    check_requirements()
    
    # Download bundled tools
    print("\n" + "="*50)
    print("Downloading dependencies...")
    print("="*50 + "\n")
    
    ffmpeg_ok = download_ffmpeg(tools_dir)
    ytdlp_ok = download_ytdlp(tools_dir)
    
    if not ffmpeg_ok:
        print("\n⚠️ Could not download ffmpeg. Build will continue but audio extraction may not work.")
    if not ytdlp_ok:
        print("\n⚠️ Could not download yt-dlp. Build will continue but users will need to install it.")
    
    # Create spec file with bundled tools
    create_spec_file(tools_dir)
    
    # Build
    if build_exe() and build_vst_plugin(tools_dir):
        if build_installer(tools_dir):
            print(f"\n🎛️ Share dist/{INSTALLER_NAME} - it installs the plugin into the user's VST2 folder.")
        else:
            print("\n🎛️ To use it in a DAW, copy BOTH files from dist/ into your VST2 plugin folder:")
            print(f"   - YouTube Downloader.exe")
            print(f"   - {PLUGIN_NAME}")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
