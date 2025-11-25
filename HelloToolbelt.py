import tkinter as tk
from tkinter import ttk, messagebox
import importlib.util
import sys
import os
import json
import threading
import time
import logging
from pathlib import Path
from contextlib import contextmanager
import hashlib
import subprocess
import tempfile
import shutil

# Auto-update imports
try:
    import urllib.request
    import urllib.error
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

# =============================================================================
# AUTO-UPDATE CONFIGURATION
# =============================================================================
# Change this to your GitHub repository (format: "username/repo-name")
GITHUB_REPO = "suiradoc/HelloToolbelt"
APP_VERSION = "2.1.2"  # Keep this in sync with self.version in MultiToolLauncher
AUTO_UPDATE_ENABLED = True  # Set to False to disable auto-update checks

# Check for authentication module
try:
    from auth_integration import require_auth, filter_tools_by_permission, AuthClient
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# Check for admin tab modules
try:
    from admin_tab import AdminTabPanel
    ADMIN_TAB_AVAILABLE = True
except ImportError:
    ADMIN_TAB_AVAILABLE = False

# Check for user management module
try:
    from user_managment import UserManagementPanel
    USER_MANAGEMENT_AVAILABLE = True
except ImportError:
    USER_MANAGEMENT_AVAILABLE = False

# Check for user audit module
try:
    from user_audit import AuditLogsPanel
    USER_AUDIT_AVAILABLE = True
except ImportError:
    USER_AUDIT_AVAILABLE = False

# Check for keyring availability
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# =============================================================================
# AUTO-UPDATE SYSTEM
# =============================================================================
class AutoUpdater:
    """
    Handles automatic updates from GitHub releases.
    Checks for new versions and downloads/installs updates.
    """
    
    def __init__(self, github_repo=GITHUB_REPO, current_version=APP_VERSION):
        self.github_repo = github_repo
        self.current_version = current_version
        self.latest_version = None
        self.download_url = None
        self.release_notes = None
    
    def _parse_version(self, version_str):
        """Parse version string to tuple for comparison (e.g., '2.1.2' -> (2, 1, 2))"""
        try:
            # Remove 'v' prefix if present
            clean_version = version_str.strip().lstrip('v')
            parts = clean_version.split('.')
            return tuple(int(p) for p in parts)
        except (ValueError, AttributeError):
            return (0, 0, 0)
    
    def check_for_updates(self, silent=False):
        """
        Check GitHub for the latest release.
        Returns True if a newer version is available.
        """
        if not URLLIB_AVAILABLE:
            return False
        
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
            
            request = urllib.request.Request(
                url,
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'HelloToolbelt-AutoUpdater'
                }
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            self.latest_version = data.get('tag_name', '').lstrip('v')
            self.release_notes = data.get('body', 'No release notes available.')
            
            # Find the appropriate asset (exe for Windows, app for Mac)
            assets = data.get('assets', [])
            for asset in assets:
                name = asset.get('name', '').lower()
                if sys.platform == 'win32' and name.endswith('.exe'):
                    self.download_url = asset.get('browser_download_url')
                    break
                elif sys.platform == 'darwin' and (name.endswith('.app.zip') or name.endswith('.dmg')):
                    self.download_url = asset.get('browser_download_url')
                    break
                elif name.endswith('.zip') or name.endswith('.tar.gz'):
                    # Fallback to generic archive
                    self.download_url = asset.get('browser_download_url')
            
            # Compare versions
            current = self._parse_version(self.current_version)
            latest = self._parse_version(self.latest_version)
            
            if latest > current:
                return True
            else:
                return False
                
        except urllib.error.URLError:
            return False
        except json.JSONDecodeError:
            return False
        except Exception:
            return False
    
    def show_update_dialog(self, parent=None):
        """Show a dialog asking the user if they want to update."""
        if not self.latest_version or not self.download_url:
            return False
        
        # Create a custom dialog for better appearance
        result = messagebox.askyesno(
            "Update Available",
            f"A new version of HelloToolbelt is available!\n\n"
            f"Current version: {self.current_version}\n"
            f"New version: {self.latest_version}\n\n"
            f"Release notes:\n{self.release_notes[:500]}{'...' if len(self.release_notes) > 500 else ''}\n\n"
            f"Would you like to download and install the update?",
            parent=parent
        )
        
        return result
    
    def download_update(self, progress_callback=None):
        """
        Download the update file.
        Returns the path to the downloaded file, or None on failure.
        """
        if not self.download_url:
            return None
        
        try:
            # Create temp directory for download
            temp_dir = tempfile.mkdtemp(prefix='hellotoolbelt_update_')
            filename = os.path.basename(self.download_url)
            download_path = os.path.join(temp_dir, filename)
            
            def report_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    progress = min(100, (block_num * block_size * 100) // total_size)
                    progress_callback(progress)
            
            urllib.request.urlretrieve(
                self.download_url, 
                download_path, 
                reporthook=report_progress
            )
            
            return download_path
            
        except Exception:
            return None
    
    def install_update(self, download_path):
        """
        Install the downloaded update.
        This will close the current application and launch the installer.
        """
        if not download_path or not os.path.exists(download_path):
            return False
        
        try:
            if sys.platform == 'win32':
                return self._install_windows(download_path)
            elif sys.platform == 'darwin':
                return self._install_macos(download_path)
            else:
                # Open file manager to the download location
                if sys.platform.startswith('linux'):
                    subprocess.Popen(['xdg-open', os.path.dirname(download_path)])
                return False
                
        except Exception:
            return False
    
    def _install_windows(self, download_path):
        """Windows-specific installation logic"""
        try:
            # Get the current executable path
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                current_exe = os.path.abspath(__file__)
            
            current_dir = os.path.dirname(current_exe)
            
            # Create a batch script to replace the executable
            batch_script = f'''@echo off
echo Updating HelloToolbelt...
echo Please wait...

:: Wait for the main application to close
timeout /t 3 /nobreak > NUL

:: Backup current version
if exist "{current_exe}" (
    move /Y "{current_exe}" "{current_exe}.backup" > NUL 2>&1
)

:: Copy new version
copy /Y "{download_path}" "{current_exe}" > NUL 2>&1

:: Check if copy was successful
if exist "{current_exe}" (
    echo Update successful!
    :: Clean up backup
    del /F /Q "{current_exe}.backup" > NUL 2>&1
    :: Start the new version
    start "" "{current_exe}"
) else (
    echo Update failed! Restoring backup...
    move /Y "{current_exe}.backup" "{current_exe}" > NUL 2>&1
    start "" "{current_exe}"
)

:: Clean up the downloaded file
rmdir /S /Q "{os.path.dirname(download_path)}" > NUL 2>&1

:: Delete this batch file
(goto) 2>nul & del "%~f0"
'''
            
            # Write batch script
            batch_path = os.path.join(tempfile.gettempdir(), 'hellotoolbelt_update.bat')
            with open(batch_path, 'w') as f:
                f.write(batch_script)
            
            # Launch the batch script and exit
            subprocess.Popen(
                ['cmd', '/c', batch_path],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            return True
            
        except Exception:
            return False
    
    def _install_macos(self, download_path):
        """macOS-specific installation logic"""
        try:
            # For macOS, we'll extract and replace the app bundle
            if download_path.endswith('.zip'):
                # Clear quarantine from downloaded zip first
                subprocess.run(['xattr', '-dr', 'com.apple.quarantine', download_path], capture_output=True)
                
                # Extract the zip
                extract_dir = tempfile.mkdtemp(prefix='hellotoolbelt_extract_')
                shutil.unpack_archive(download_path, extract_dir)
                
                # Find the .app bundle
                for item in os.listdir(extract_dir):
                    if item.endswith('.app'):
                        new_app_path = os.path.join(extract_dir, item)
                        break
                else:
                    return False
                
                # Get current app path
                if getattr(sys, 'frozen', False):
                    current_app = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
                else:
                    return False
                
                # Create shell script to replace the app
                script = f'''#!/bin/bash
sleep 3
rm -rf "{current_app}"
cp -R "{new_app_path}" "{os.path.dirname(current_app)}/"
xattr -dr com.apple.quarantine "{current_app}"
rm -rf "{extract_dir}"
rm -rf "{os.path.dirname(download_path)}"
open "{current_app}"
rm -- "$0"
'''
                script_path = os.path.join(tempfile.gettempdir(), 'hellotoolbelt_update.sh')
                with open(script_path, 'w') as f:
                    f.write(script)
                os.chmod(script_path, 0o755)
                
                subprocess.Popen(['bash', script_path])
                return True
                
            elif download_path.endswith('.dmg'):
                # Just open the DMG for manual installation
                subprocess.Popen(['open', download_path])
                messagebox.showinfo(
                    "Update Downloaded",
                    "The update has been downloaded and the installer has been opened.\n\n"
                    "Please drag the new version to your Applications folder to complete the update."
                )
                return False  # Don't auto-exit, user needs to do manual installation
                
        except Exception:
            return False

def check_for_updates_on_startup():
    """
    Check for updates when the application starts.
    This runs before the main UI is shown.
    Returns True if an update was initiated (app should exit).
    """
    if not AUTO_UPDATE_ENABLED:
        return False
    
    if GITHUB_REPO == "yourusername/HelloToolbelt":
        return False
    
    try:
        updater = AutoUpdater()
        
        # Check for updates silently
        if updater.check_for_updates(silent=True):
            # Create a temporary root window for the dialog
            temp_root = tk.Tk()
            temp_root.withdraw()  # Hide the temporary window
            
            # Ask user if they want to update
            if updater.show_update_dialog(temp_root):
                # Show progress dialog
                progress_window = tk.Toplevel(temp_root)
                progress_window.title("Downloading Update")
                progress_window.geometry("400x150")
                progress_window.resizable(False, False)
                progress_window.transient(temp_root)
                
                # Center the progress window
                progress_window.update_idletasks()
                x = (progress_window.winfo_screenwidth() // 2) - 200
                y = (progress_window.winfo_screenheight() // 2) - 75
                progress_window.geometry(f"+{x}+{y}")
                
                # Progress UI
                tk.Label(
                    progress_window, 
                    text="Downloading HelloToolbelt update...",
                    font=('Segoe UI', 12)
                ).pack(pady=20)
                
                progress_var = tk.DoubleVar()
                progress_bar = ttk.Progressbar(
                    progress_window, 
                    variable=progress_var, 
                    maximum=100,
                    length=350
                )
                progress_bar.pack(pady=10)
                
                progress_label = tk.Label(
                    progress_window, 
                    text="0%",
                    font=('Segoe UI', 10)
                )
                progress_label.pack()
                
                def update_progress(percent):
                    progress_var.set(percent)
                    progress_label.config(text=f"{percent}%")
                    progress_window.update()
                
                # Download the update
                download_path = updater.download_update(progress_callback=update_progress)
                
                if download_path:
                    progress_window.destroy()
                    
                    # Install the update
                    if updater.install_update(download_path):
                        temp_root.destroy()
                        sys.exit(0)  # Exit so the update can proceed
                        return True
                    else:
                        messagebox.showinfo(
                            "Update Downloaded",
                            f"The update has been downloaded to:\n{download_path}\n\n"
                            "Please install it manually.",
                            parent=temp_root
                        )
                else:
                    progress_window.destroy()
                    messagebox.showerror(
                        "Update Failed",
                        "Failed to download the update. Please try again later.",
                        parent=temp_root
                    )
            
            temp_root.destroy()
        
        return False
        
    except Exception:
        return False

class CredentialManager:
    """
    Centralized credential management using a SINGLE keychain entry.
    All credentials are stored as a JSON blob to minimize keychain prompts.
    """
    
    def __init__(self, keyring_available=False):
        self.keyring_available = keyring_available
        self._service_name = "HelloToolbelt"
        self._key_name = "credentials"  # Single key for all credentials
        self._cache = None  # Cache to avoid repeated keychain access
    
    def _get_all_credentials(self):
        """Get all credentials from the single keychain entry"""
        if self._cache is not None:
            return self._cache
        
        if not self.keyring_available:
            return {}
        
        try:
            import keyring
            data = keyring.get_password(self._service_name, self._key_name)
            if data:
                self._cache = json.loads(data)
                return self._cache
        except Exception as e:
            pass
        
        return {}
    
    def _save_all_credentials(self, credentials):
        """Save all credentials to the single keychain entry"""
        if not self.keyring_available:
            return False
        
        try:
            import keyring
            keyring.set_password(self._service_name, self._key_name, json.dumps(credentials))
            self._cache = credentials  # Update cache
            return True
        except Exception as e:
            pass
            return False
    
    def store_aws_credentials(self, access_key, secret_key, region):
        """Store AWS credentials"""
        credentials = self._get_all_credentials()
        credentials['aws_access_key_id'] = access_key
        credentials['aws_secret_access_key'] = secret_key
        credentials['aws_region'] = region
        return self._save_all_credentials(credentials)
    
    def store_db_credentials(self, password):
        """Store database credentials"""
        if not password:
            return False
        credentials = self._get_all_credentials()
        credentials['db_password'] = password
        return self._save_all_credentials(credentials)
    
    def get_aws_credentials(self):
        """Retrieve AWS credentials"""
        credentials = self._get_all_credentials()
        return (
            credentials.get('aws_access_key_id'),
            credentials.get('aws_secret_access_key'),
            credentials.get('aws_region')
        )
    
    def get_db_credentials(self):
        """Retrieve database credentials"""
        credentials = self._get_all_credentials()
        return credentials.get('db_password')
    
    def delete_aws_credentials(self):
        """Delete ONLY AWS credentials - does not touch DB credentials"""
        credentials = self._get_all_credentials()
        results = {}
        
        for key in ['aws_access_key_id', 'aws_secret_access_key', 'aws_region']:
            if key in credentials:
                del credentials[key]
                results[key] = True
            else:
                results[key] = False
        
        self._save_all_credentials(credentials)
        return results
    
    def delete_db_credentials(self):
        """Delete ONLY database credentials - does not touch AWS credentials"""
        credentials = self._get_all_credentials()
        
        if 'db_password' in credentials:
            del credentials['db_password']
            self._save_all_credentials(credentials)
            return True
        return False

class LoadingScreen:
    """Simple loading screen with heartbeat animation for auth mode"""
    
    def __init__(self):
        self.splash = tk.Toplevel()
        self.splash.withdraw()  # Hide immediately while setting up
        self.splash.title("Loading HelloToolbelt")
        self.splash.geometry("300x200")
        self.splash.resizable(False, False)
        self.splash.configure(bg="#2b2b2b")
        
        # Initialize window
        self.splash.update_idletasks()
        
        # Set borderless window (wrap for macOS compatibility)
        try:
            self.splash.overrideredirect(True)
        except tk.TclError:
            pass
        
        # Animation state
        self._animation_running = True
        self._cycle_start = time.time()
        self._icon_images = {}
        self._icon_loaded = False
        self._after_id = None
        self._dot_index = 0
        self._last_dot_update = time.time()
        
        self.center_splash()
        self.create_splash_content()
        self.splash.deiconify()
        self.splash.lift()
        
        # Start heartbeat animation
        self._animate_heartbeat()
    
    def center_splash(self):
        """Center the splash screen on the display"""
        self.splash.update_idletasks()
        width = 300
        height = 200
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.splash.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_splash_content(self):
        """Create the loading screen content with heartbeat animation"""
        # Create canvas for animation
        self.canvas = tk.Canvas(
            self.splash,
            width=300,
            height=200,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Try to load icon with multiple sizes for heartbeat effect
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            macos_resources = os.path.join(base_path, '..', 'Resources')
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            macos_resources = base_path
        
        icon_paths = [
            os.path.join(base_path, 'icon.icns'),
            os.path.join(base_path, 'icon.png'),
            os.path.join(macos_resources, 'icon.icns'),
            os.path.join(macos_resources, 'icon.png'),
            os.path.join(os.getcwd(), 'icon.icns'),
            os.path.join(os.getcwd(), 'icon.png'),
            'icon.icns',
            'icon.png',
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    
                    # Create multiple sizes for heartbeat animation
                    sizes = {'normal': 64, 'beat1': 76, 'beat2': 70}
                    for state, size in sizes.items():
                        resized = img.resize((size, size), Image.Resampling.LANCZOS)
                        self._icon_images[state] = ImageTk.PhotoImage(resized)
                    
                    self._icon_loaded = True
                    break
                except Exception as e:
                    pass
        
        # Create icon
        if self._icon_loaded and self._icon_images:
            self._icon_item = self.canvas.create_image(150, 80, image=self._icon_images['normal'])
        else:
            # Fallback to emoji
            self._icon_item = self.canvas.create_text(150, 80, text="🔧", font=("Segoe UI", 48), fill="#4a9eff")
        
        # App name
        self.canvas.create_text(150, 130, text="HelloToolbelt", font=("Segoe UI", 16, "bold"), fill="#ffffff")
        
        # Loading text
        self._loading_text = self.canvas.create_text(150, 160, text="Loading...", font=("Segoe UI", 12), fill="#888888")
        
        # Small pulse dot
        self._pulse_dot = self.canvas.create_oval(145, 180, 155, 190, fill="#e74c3c", outline="")
        
        self._dot_states = ["Loading", "Loading.", "Loading..", "Loading..."]
    
    def _animate_heartbeat(self):
        """Animate the heartbeat effect"""
        if not self._animation_running:
            return
        
        try:
            current_time = time.time()
            cycle_time = (current_time - self._cycle_start) * 1000
            
            if cycle_time > 900:
                self._cycle_start = current_time
                cycle_time = 0
            
            # Heartbeat sequence
            heartbeat_sequence = [('beat1', 0), ('normal', 80), ('beat2', 160), ('normal', 240)]
            
            current_state = 'normal'
            for state, timing in heartbeat_sequence:
                if cycle_time >= timing:
                    current_state = state
            
            # Animate icon
            if self._icon_loaded and self._icon_images:
                self.canvas.itemconfig(self._icon_item, image=self._icon_images[current_state])
            else:
                if current_state == 'beat1':
                    self.canvas.itemconfig(self._icon_item, font=("Segoe UI", 54))
                elif current_state == 'beat2':
                    self.canvas.itemconfig(self._icon_item, font=("Segoe UI", 51))
                else:
                    self.canvas.itemconfig(self._icon_item, font=("Segoe UI", 48))
            
            # Animate pulse dot
            if current_state == 'beat1':
                self.canvas.coords(self._pulse_dot, 143, 178, 157, 192)
                self.canvas.itemconfig(self._pulse_dot, fill="#ff6b6b")
            elif current_state == 'beat2':
                self.canvas.coords(self._pulse_dot, 144, 179, 156, 191)
                self.canvas.itemconfig(self._pulse_dot, fill="#ff5252")
            else:
                self.canvas.coords(self._pulse_dot, 145, 180, 155, 190)
                self.canvas.itemconfig(self._pulse_dot, fill="#e74c3c")
            
            # Animate loading dots
            if current_time - self._last_dot_update > 0.4:
                self._dot_index = (self._dot_index + 1) % len(self._dot_states)
                self.canvas.itemconfig(self._loading_text, text=self._dot_states[self._dot_index])
                self._last_dot_update = current_time
            
            # Schedule next frame and track the callback ID
            if self._animation_running:
                self._after_id = self.splash.after(30, self._animate_heartbeat)
        except tk.TclError:
            self._animation_running = False
    
    def destroy(self):
        """Close the loading screen"""
        self._animation_running = False
        
        # Cancel any pending animation callback
        if self._after_id:
            try:
                self.splash.after_cancel(self._after_id)
            except:
                pass
        
        try:
            self.splash.destroy()
        except tk.TclError:
            pass
        except Exception as e:
            pass

class SplashScreen:
    """Splash screen with heartbeat animation"""
    
    def __init__(self):
        self.splash = tk.Tk()
        self.splash.withdraw()  # Hide immediately to prevent flash
        self.splash.title("HelloToolbelt")
        self.splash.configure(bg='#2b2b2b')
        self.splash.resizable(False, False)
        self.splash.update_idletasks()
        
        # Set borderless window (wrap for macOS compatibility)
        try:
            self.splash.overrideredirect(True)
        except tk.TclError:
            pass
        
        # Animation state
        self._animation_running = True
        self._cycle_start = time.time()
        self._icon_images = {}  # Store different sized versions for heartbeat
        self._icon_loaded = False
        self._after_id = None  # Track the scheduled callback
        
        self.center_splash()
        self.set_icon()
        self.create_splash_content()
        self.splash.deiconify()
        self.splash.lift()
        self.splash.attributes('-topmost', True)
        
        # Start heartbeat animation
        self._animate_heartbeat()

    def center_splash(self):
        """Center the splash screen on the display"""
        self.splash.update_idletasks()
        width = 400
        height = 320
        x = (self.splash.winfo_screenwidth() // 2) - (width // 2)
        y = (self.splash.winfo_screenheight() // 2) - (height // 2)
        self.splash.geometry(f'{width}x{height}+{x}+{y}')

    def set_icon(self):
        """Set the application icon if available"""
        try:
            icon_paths = [
                'icon.icns', 'icon.ico',
                os.path.join(os.path.dirname(__file__), 'icon.icns'),
                os.path.join(os.path.dirname(__file__), 'icon.ico'),
                os.path.join(os.getcwd(), 'icon.icns'),
                os.path.join(os.getcwd(), 'icon.ico')
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    if icon_path.endswith('.icns') and sys.platform == 'darwin':
                        self.splash.iconbitmap(icon_path)
                        break
                    elif icon_path.endswith('.ico'):
                        self.splash.iconbitmap(icon_path)
                        break
        except Exception as e:
            pass
    
    def _load_heartbeat_icons(self):
        """Load icon in multiple sizes for heartbeat animation"""
        # Get the base path
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            macos_resources = os.path.join(base_path, '..', 'Resources')
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            macos_resources = base_path
        
        icon_paths = [
            os.path.join(base_path, 'icon.icns'),
            os.path.join(base_path, 'icon.png'),
            os.path.join(macos_resources, 'icon.icns'),
            os.path.join(macos_resources, 'icon.png'),
            os.path.join(os.getcwd(), 'icon.icns'),
            os.path.join(os.getcwd(), 'icon.png'),
            'icon.icns',
            'icon.png',
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    
                    # Create multiple sizes for heartbeat animation
                    # Normal: 64, Beat1 (lub): 74, Beat2 (dub): 70
                    sizes = {
                        'normal': 64,
                        'beat1': 76,   # First beat (larger)
                        'beat2': 70,   # Second beat (slightly smaller)
                    }
                    
                    for name, size in sizes.items():
                        resized = img.resize((size, size), Image.Resampling.LANCZOS)
                        self._icon_images[name] = ImageTk.PhotoImage(resized, master=self.splash)
                    
                    self._icon_loaded = True
                    return True
                except Exception as e:
                    pass
                    continue
        
        return False
    
    def create_splash_content(self):
        """Create the content for the splash screen with heartbeat animation"""
        # Main canvas for animation
        self.canvas = tk.Canvas(
            self.splash, 
            width=400, 
            height=320, 
            bg='#2b2b2b', 
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Load icons for heartbeat
        self._load_heartbeat_icons()
        
        # Icon position
        icon_y = 80
        
        if self._icon_loaded:
            self._icon_item = self.canvas.create_image(
                200, icon_y, 
                image=self._icon_images['normal']
            )
        else:
            # Fallback to heart emoji if no icon
            self._icon_item = self.canvas.create_text(
                200, icon_y, 
                text="🔧", 
                font=("Segoe UI", 48), 
                fill="#ffffff"
            )
        
        # App name
        self.canvas.create_text(
            200, 145,
            text="HelloToolbelt",
            font=("Segoe UI", 24, "bold"),
            fill="#ffffff"
        )
        
        # Version
        self.canvas.create_text(
            200, 175,
            text="Version 2.1.2",
            font=("Segoe UI", 12),
            fill="#cccccc"
        )
        
        # Loading text (will be animated)
        self._loading_text = self.canvas.create_text(
            200, 220,
            text="Loading...",
            font=("Segoe UI", 11),
            fill="#4a90e2"
        )
        
        # Progress bar background
        self._progress_bg = self.canvas.create_rectangle(
            60, 250, 340, 258,
            fill="#404040",
            outline=""
        )
        
        # Progress bar fill
        self._progress_fill = self.canvas.create_rectangle(
            60, 250, 60, 258,
            fill="#4a90e2",
            outline=""
        )
        
        # Small heartbeat indicator
        self._pulse_dot = self.canvas.create_oval(
            195, 285, 205, 295,
            fill="#e74c3c",
            outline=""
        )
    
    def _animate_heartbeat(self):
        """Animate the heartbeat effect"""
        if not self._animation_running:
            return
        
        try:
            current_time = time.time()
            cycle_time = (current_time - self._cycle_start) * 1000  # Convert to ms
            
            # Reset cycle every 900ms (heartbeat rhythm ~67 BPM)
            if cycle_time > 900:
                self._cycle_start = current_time
                cycle_time = 0
            
            # Heartbeat sequence: lub-dub pattern
            # beat1 at 0ms, normal at 80ms, beat2 at 160ms, normal at 240ms, rest...
            heartbeat_sequence = [
                ('beat1', 0),
                ('normal', 80),
                ('beat2', 160),
                ('normal', 240),
            ]
            
            current_state = 'normal'
            for state, timing in heartbeat_sequence:
                if cycle_time >= timing:
                    current_state = state
            
            # Apply heartbeat animation to icon
            if self._icon_loaded and self._icon_images:
                self.canvas.itemconfig(self._icon_item, image=self._icon_images[current_state])
            else:
                # Animate the emoji with font size
                if current_state == 'beat1':
                    self.canvas.itemconfig(self._icon_item, font=("Segoe UI", 54))
                elif current_state == 'beat2':
                    self.canvas.itemconfig(self._icon_item, font=("Segoe UI", 51))
                else:
                    self.canvas.itemconfig(self._icon_item, font=("Segoe UI", 48))
            
            # Animate pulse dot (small red dot that pulses with heartbeat)
            if current_state == 'beat1':
                self.canvas.coords(self._pulse_dot, 193, 283, 207, 297)
                self.canvas.itemconfig(self._pulse_dot, fill="#ff6b6b")
            elif current_state == 'beat2':
                self.canvas.coords(self._pulse_dot, 194, 284, 206, 296)
                self.canvas.itemconfig(self._pulse_dot, fill="#ff5252")
            else:
                self.canvas.coords(self._pulse_dot, 195, 285, 205, 295)
                self.canvas.itemconfig(self._pulse_dot, fill="#e74c3c")
            
            # Schedule next frame (~33 FPS) and track the callback ID
            if self._animation_running:
                self._after_id = self.splash.after(30, self._animate_heartbeat)
            
        except tk.TclError:
            # Window destroyed
            self._animation_running = False
        except Exception as e:
            pass
            self._animation_running = False
    
    def update_progress(self, percentage):
        """Update the progress bar"""
        try:
            # Calculate progress bar width (280px total width: 60 to 340)
            progress_width = 60 + int((percentage / 100) * 280)
            self.canvas.coords(self._progress_fill, 60, 250, progress_width, 258)
            self.splash.update()
        except Exception as e:
            pass
    
    def update_status(self, text, percentage=None):
        """Update the loading status text and optionally progress"""
        try:
            self.canvas.itemconfig(self._loading_text, text=text)
            if percentage is not None:
                self.update_progress(percentage)
            self.splash.update()
        except tk.TclError:
            pass
        except Exception as e:
            pass
    
    def destroy(self):
        """Close the splash screen with smooth fade out"""
        self._animation_running = False
        
        # Cancel any pending animation callback
        if self._after_id:
            try:
                self.splash.after_cancel(self._after_id)
            except:
                pass
        
        try:
            # Fade out animation for smoother transition
            if sys.platform == 'darwin':
                for alpha in range(10, 0, -1):
                    try:
                        self.splash.attributes('-alpha', alpha / 10.0)
                        self.splash.update()
                        time.sleep(0.02)
                    except tk.TclError:
                        break
                    except Exception as e:
                        pass
                        break
            self.splash.destroy()
        except tk.TclError:
            pass
        except Exception as e:
            pass

class PasswordDialog:
    def __init__(self, parent, colors):
        self.result = None
        self.colors = colors
        self.parent = parent
        
        # Ensure parent window is properly updated before creating dialog
        try:
            parent.update_idletasks()
        except:
            pass
        
        # Create modal dialog with larger size
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Tier 3 Access")
        self.dialog.configure(bg=colors['bg'])
        self.dialog.resizable(False, False)
        
        # Make it modal and ensure it appears on top
        self.dialog.transient(parent)
        
        # Set larger initial size before centering
        self.dialog.geometry("500x350")  # Increased from 400x250
        
        # Center the dialog BEFORE making it modal
        self.center_dialog()
        
        # Now make it modal and bring to front
        self.dialog.grab_set()
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.focus_force()
        
        # Create UI first
        self.create_ui()
        
        # Focus on password entry after UI is created - with multiple attempts
        self.dialog.after(50, self.focus_password_entry)
        self.dialog.after(150, self.focus_password_entry)
        self.dialog.after(300, self.focus_password_entry)
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Bind Enter and Escape keys to the dialog itself as backup
        self.dialog.bind('<Return>', lambda e: self.submit())
        self.dialog.bind('<KP_Enter>', lambda e: self.submit())  # Keypad Enter
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
    def focus_password_entry(self):
        """Focus on password entry field"""
        try:
            # Ensure the dialog is visible and on top
            self.dialog.lift()
            self.dialog.focus_force()
            
            # Focus the password entry
            self.password_entry.focus_set()
            self.password_entry.icursor(0)
            
            # Make sure it has keyboard focus
            self.password_entry.selection_clear()
            
        except Exception as e:
            pass
    
    def center_dialog(self):
        """Center the dialog on the main window or screen"""
        try:
            # Force geometry update
            self.dialog.update_idletasks()
            
            # Get dialog dimensions - updated for larger size
            dialog_width = 500   # Increased from 400
            dialog_height = 350  # Increased from 250
            
            # Try to center on the main window first
            try:
                # Get main window position and size
                main_x = self.parent.winfo_rootx()
                main_y = self.parent.winfo_rooty()
                main_width = self.parent.winfo_width()
                main_height = self.parent.winfo_height()
                
                # Calculate center position relative to main window
                x = main_x + (main_width // 2) - (dialog_width // 2)
                y = main_y + (main_height // 2) - (dialog_height // 2)
                
            except Exception as e:
                pass
                # Fallback to screen center
                screen_width = self.dialog.winfo_screenwidth()
                screen_height = self.dialog.winfo_screenheight()
                x = (screen_width // 2) - (dialog_width // 2)
                y = (screen_height // 2) - (dialog_height // 2)
            
            # Ensure dialog stays on screen
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            # Clamp to screen boundaries with some margin
            margin = 50
            x = max(margin, min(x, screen_width - dialog_width - margin))
            y = max(margin, min(y, screen_height - dialog_height - margin))
            
            # Set the geometry with new size
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            
            # Force update and bring to front
            self.dialog.update_idletasks()
            self.dialog.lift()
            self.dialog.attributes('-topmost', True)
            
        except Exception as e:
            pass
            # Emergency fallback - larger size
            self.dialog.geometry("500x350+100+100")
    
    def create_ui(self):
        """Create the password dialog UI"""
        # Main container with reduced padding
        main_frame = tk.Frame(self.dialog, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)  # Reduced padding
        
        # Header with icon
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 15))  # Reduced bottom padding
        
        icon_label = tk.Label(header_frame, 
                            text="🔐", 
                            font=('Segoe UI', 20),  # Smaller icon
                            bg=self.colors['bg'],
                            fg=self.colors['fg'])
        icon_label.pack(side=tk.LEFT, padx=(0, 10))  # Less spacing
        
        title_label = tk.Label(header_frame, 
                             text="Tier 3 Access Required", 
                             font=('Segoe UI', 14, 'bold'),  # Smaller font
                             fg=self.colors['fg'],
                             bg=self.colors['bg'])
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Description with less space
        desc_label = tk.Label(main_frame,
                            text="Enter password to access Tier 3 tools:",
                            font=('Segoe UI', 10),  # Smaller font
                            fg=self.colors['text_secondary'],
                            bg=self.colors['bg'])
        desc_label.pack(anchor='w', pady=(0, 15))  # Less padding
        
        # Password frame
        password_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        password_frame.pack(fill=tk.X, pady=(0, 15))  # Less padding
        
        password_label = tk.Label(password_frame,
                                text="Password:",
                                font=('Segoe UI', 10, 'bold'),  # Smaller font
                                fg=self.colors['fg'],
                                bg=self.colors['bg'])
        password_label.pack(anchor='w', pady=(0, 5))  # Less padding
        
        self.password_entry = tk.Entry(password_frame,
                                     font=('Segoe UI', 11),  # Smaller font
                                     show="*",
                                     bg=self.colors['frame_bg'],
                                     fg=self.colors['fg'],
                                     relief='solid',
                                     bd=1,  # Thinner border
                                     insertbackground=self.colors['fg'])
        self.password_entry.pack(fill=tk.X, ipady=4)  # Less internal padding
        
        # Bind Enter key directly to the password entry field
        self.password_entry.bind('<Return>', lambda e: self.submit())
        self.password_entry.bind('<KP_Enter>', lambda e: self.submit())  # Keypad Enter
        
        # Error label (initially hidden) with less space
        self.error_label = tk.Label(main_frame,
                                  text="",
                                  font=('Segoe UI', 9),  # Smaller font
                                  fg=self.colors['danger'],
                                  bg=self.colors['bg'])
        self.error_label.pack(anchor='w', pady=(5, 0))  # Less padding
        
        # Button frame with less space
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X, pady=(15, 0))  # Less top padding
        
        # Cancel button with smaller size
        cancel_btn = tk.Button(button_frame,
                             text="Cancel",
                             command=self.cancel,
                             bg=self.colors['frame_bg'],
                             fg='#000000',  # Black text
                             font=('Segoe UI', 10),  # Smaller font
                             relief='solid',
                             bd=1,
                             padx=15,  # Less padding
                             pady=6,   # Less padding
                             cursor='hand2')
        cancel_btn.pack(side=tk.LEFT)
        
        # Submit button with smaller size
        submit_btn = tk.Button(button_frame,
                             text="Submit",
                             command=self.submit,
                             bg=self.colors['primary'],
                             fg='#000000',  # Black text
                             font=('Segoe UI', 10, 'bold'),  # Smaller font
                             relief='flat',
                             bd=0,
                             padx=15,  # Less padding
                             pady=6,   # Less padding
                             cursor='hand2')
        submit_btn.pack(side=tk.RIGHT)
        
        # Bind Enter key to submit button as well
        submit_btn.bind('<Return>', lambda e: self.submit())
        submit_btn.bind('<KP_Enter>', lambda e: self.submit())
        
        # Add hover effects with black text
        def on_submit_enter(e):
            submit_btn.config(bg='#2980b9' if not self.colors.get('is_dark') else '#5a9de8', fg='#000000')
        
        def on_submit_leave(e):
            submit_btn.config(bg=self.colors['primary'], fg='#000000')
        
        def on_cancel_enter(e):
            cancel_btn.config(bg=self.colors['secondary_bg'], fg='#000000')
        
        def on_cancel_leave(e):
            cancel_btn.config(bg=self.colors['frame_bg'], fg='#000000')
        
        submit_btn.bind("<Enter>", on_submit_enter)
        submit_btn.bind("<Leave>", on_submit_leave)
        cancel_btn.bind("<Enter>", on_cancel_enter)
        cancel_btn.bind("<Leave>", on_cancel_leave)
    
    def submit(self):
        """Handle password submission"""
        try:
            password = self.password_entry.get()
            
            if not password:
                self.show_error("Please enter a password")
                return
            
            # Check password (you can change this password)
            if self.verify_password(password):
                pass
                self.result = True
                self.dialog.destroy()
            else:
                pass
                self.show_error("Incorrect password")
                self.password_entry.delete(0, tk.END)
                self.password_entry.focus_set()
        except Exception as e:
            pass
            self.result = False
            try:
                self.dialog.destroy()
            except:
                pass
    
    def verify_password(self, password):
        """Verify the entered password"""
        # You can change this password to whatever you want
        # For security, we're using a simple hash comparison
        correct_password = "tier3access"  # Change this to your desired password
        return password == correct_password
    
    def show_error(self, message):
        """Show error message"""
        self.error_label.config(text=message)
    
    def cancel(self):
        """Handle dialog cancellation"""
        try:
            pass
            self.result = False
            self.dialog.destroy()
        except Exception as e:
            pass
            self.result = False
    
    def wait_for_result(self):
        """Wait for dialog result"""
        try:
            pass
            self.dialog.wait_window()
            return self.result
        except Exception as e:
            pass
            return False

class MultiToolLauncher:
    def __init__(self, root, splash=None, auth=None, loading_callback=None):
        self.splash = splash
        self.root = root
        self.auth = auth  # Store auth client for permission checks and logging
        self.loading_callback = loading_callback  # Callback for loading progress bar
        
        # Keep window hidden (already withdrawn in main)
        # Don't set title/geometry yet to prevent flash
        
        # Version information
        self.version = APP_VERSION  # Uses the global APP_VERSION constant for auto-update
        
        # Initialize callback tracking for cleanup
        self._scheduled_callbacks = set()
        self._destroyed = False
        
        # Update splash or loading bar
        self._update_loading(10, "Initializing...")
        
        # Add stability improvements FIRST
        self._tool_cleanup_lock = threading.Lock()
        self._settings_lock = threading.Lock()
        self._loading_tools = set()
        
        # Setup logging
        self.setup_logging()
        
        self._update_loading(20, "Setting up configuration...")
        
        # Settings file path - FIXED for PyInstaller
        self.settings_file = self.get_settings_file_path()
        
        # Load settings and initialize dark mode state
        self.load_settings()
        
        self._update_loading(30, "Loading settings...")
        
        # Initialize tier setting - always Tier 3 now (auth controls access)
        self.tier3_unlocked = True
        self.current_tier = 'Tier 3'
        
        # Initialize shared credentials system
        self.keyring_available = KEYRING_AVAILABLE
        self.init_shared_credentials()
        
        # Configure enhanced styling
        self.setup_styles()
        
        self._update_loading(40, "Setting up interface...")
        
        # Set root background color based on loaded settings
        colors = self.get_colors()
        self.root.configure(bg=colors['bg'])
        
        # Set main window icon
        self.set_main_window_icon()
        
        # Check if we should show welcome popup (do this before creating UI)
        self.check_and_show_welcome()
        
        self._update_loading(50, "Creating main interface...")
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Track tab loading states and pending renders
        self.tab_loaded = {}
        self.tab_pending_render = {}
        self.last_selected_tab = None
        
        # Track subtab loading states (for nested Client Setup notebook)
        self.subtab_loaded = {}
        self.last_selected_subtab = None
        self.client_notebook = None  # Will be set if Client Setup tabs exist
        
        # Track File Tools subtab loading states (for nested File Tools notebook)
        self.file_tools_subtab_loaded = {}
        self.last_selected_file_tools_subtab = None
        self.file_tools_notebook = None  # Will be set if File Tools tabs exist
        
        # Track Admin subtab loading states (for nested Admin notebook)
        self.admin_subtab_loaded = {}
        self.last_selected_admin_subtab = None
        self.admin_notebook = None  # Will be set if Admin tabs exist
        
        # Track tool-specific colors for dynamic tab styling
        self.tool_tab_colors = {}  # Maps tab_index or tool_name to primary_color
        
        # Hardcoded color mappings for tools (fallback if tool doesn't set primary_color)
        self.default_tool_colors = {
            'Shipping Map': '#a34ae2',  # Purple
            'DLQ Fetcher': '#c70c0c',   # Red
            'Options': '#1e3a5f',        # Dark Blue
            'Admin': '#d4a017',          # Yellow/Gold
        }
        
        # Bind tab change event for lazy loading
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
        
        # Tool configurations - modify these paths to match your script locations
        self.tools = [
            {
                'name': 'Config',
                'file': 'configurator_tool.py',
                'class': 'CSVConfigApp', 
                'description': 'Create the JSON configurations for Eligibility and Formatting files',
                'icon': '⚙️'
            },
            {
                'name': 'CronJob',
                'file': 'Cron_tool.py',
                'class': 'CronJobGenerator',
                'description': 'Generate Kubernetes CronJob YAML configurations',
                'icon': '⏰'
            },
            {
                'name': 'Eligibility Search',
                'file': 'eligibility_tool.py',
                'class': 'EligibilitySearchTool',
                'description': 'Search and analyze eligibility data with age and term date validation',
                'icon': '🔍'
            },
            {
                'name': 'Multi-File Column Search',
                'file': 'multisearch_tool.py', 
                'class': 'MultiFileColumnSearchTool',
                'description': 'Search across multiple files for specific column values',
                'icon': '📂'
            },
            {
                'name': 'Base64',
                'file': 'Base64_Tool.py',
                'class': 'Base64Tool',
                'description': 'Encode and decode Base64 strings',
                'icon': '🔐'
            },
            {
                'name': 'DLQ Fetcher',
                'file': 'DLQ_Tool.py',
                'class': 'DLQFetcherTool',
                'description': 'Run DLQ Fetcher JAR with queue selection and formatted output',
                'icon': '📨'
            },
            {
            'name': 'Bill Hunter',
            'file': 'bill_hunter.py',
            'class': 'FileParserGUI',
            'description': 'Match unbillable users from client files with PostgreSQL query results',
            'icon': '🎯'
            },
            {
            'name': 'Shipping Map',
            'file': 'shipping_map.py',
            'class': 'ZipcodeHeatmapTool',
            'description': 'Interactive shipping route and location mapper',
            'icon': '🗺️'
            },
            {
            'name': 'Report Builder',
            'file': 'hedis.py',
            'class': 'FileUploaderApp',
            'description': 'Build and generate custom reports from data files',
            'icon': '📊'
            }
        ]
        
        self._update_loading(60, "Loading tools...")
        
        # Store loaded tools
        self.loaded_tools = {}
        
        # Filter tools based on user permissions (if auth is available)
        if self.auth:
            original_count = len(self.tools)
            self.tools = filter_tools_by_permission(self.tools, self.auth)
            filtered_count = len(self.tools)
            self.log_info(f"Filtered tools: {filtered_count}/{original_count} available for user {self.auth.username}")
            self.auth.log_action("APP_STARTED", f"User: {self.auth.username}")
        
        self._update_loading(70, "Creating tool tabs...")
        
        # Create tabs for each tool based on tier
        self.create_tool_tabs()
        
        self._update_loading(80, "Setting up options...")
        
        # Add admin tab if user is admin and any admin module is available
        if self.auth and self.auth.is_admin and (ADMIN_TAB_AVAILABLE or USER_MANAGEMENT_AVAILABLE or USER_AUDIT_AVAILABLE):
            pass
            self.create_admin_tab()
        
        # Add options tab (will be moved to end after creation)
        self.create_options_tab()
        
        # Move options tab to the end
        self.move_options_tab_to_end()
        
        self._update_loading(90, "Finalizing interface...")
        
        # Pre-render all tabs to eliminate flash on first view
        self.pre_render_all_tabs()
        
        # Set window icon and center it
        self.center_window()
        
        # Save settings when app closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self._update_loading(100, "Ready!")
        
        # Destroy splash if it exists
        if self.splash:
            try:
                self.splash.destroy()
            except Exception as e:
                pass
        
        # Show main window directly
        try:
            self.root.title("Hello Toolbelt")
            self.root.geometry("1200x1200")
            
            # Auto-maximize window to fullscreen
            try:
                # Try to maximize the window (works on most platforms)
                self.root.state('zoomed')
            except tk.TclError:
                # If 'zoomed' doesn't work (some Linux systems), try alternative
                try:
                    self.root.attributes('-zoomed', True)
                except:
                    # If that doesn't work either, just use the geometry size
                    pass
            
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception as e:
            pass
        
    def _update_loading(self, value, status_text):
        """Update either splash screen or loading callback with progress"""
        if self.loading_callback:
            try:
                self.loading_callback(value, status_text)
            except:
                pass
        elif self.splash:
            try:
                self.splash.update_status(status_text, value)
            except:
                pass

    def safe_after(self, delay, callback):
        """Safe wrapper for root.after() that tracks callbacks for cleanup"""
        if self._destroyed:
            return None
        
        try:
            # Create a wrapper that removes itself from tracking
            def wrapper():
                if not self._destroyed:
                    try:
                        callback()
                    except Exception as e:
                        self.log_error("Error in scheduled callback", e)
                # Remove from tracking set
                self._scheduled_callbacks.discard(callback_id)
            
            callback_id = self.root.after(delay, wrapper)
            self._scheduled_callbacks.add(callback_id)
            return callback_id
        except Exception as e:
            self.log_error("Error scheduling callback", e)
            return None

    def cancel_all_callbacks(self):
        """Cancel all scheduled callbacks"""
        for callback_id in list(self._scheduled_callbacks):
            try:
                self.root.after_cancel(callback_id)
            except tk.TclError:
                # Callback may have already executed or window destroyed
                pass
            except Exception as e:
                self.log_error(f"Error canceling callback {callback_id}", e)
        self._scheduled_callbacks.clear()

    def emergency_show_window(self):
        """Emergency fallback to show main window if needed"""
        try:
            if not self.root.winfo_viewable():
                pass
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.update()
            # Window is already visible, no action needed
        except Exception as e:
            pass

    def set_main_window_icon(self):
        """Set the main window icon"""
        try:
            # First, check if running on macOS
            if sys.platform == 'darwin':
                # On macOS, try .icns first
                icon_paths = [
                    'icon.icns',
                    os.path.join(os.path.dirname(__file__), 'icon.icns'),
                    os.path.join(os.getcwd(), 'icon.icns')
                ]
                
                for icon_path in icon_paths:
                    if os.path.exists(icon_path):
                        try:
                            # On macOS, iconbitmap works with .icns
                            self.root.iconbitmap(icon_path)
                            self.log_info(f"Successfully set icon: {icon_path}")
                            return
                        except Exception as e:
                            self.log_error(f"Failed to set .icns icon: {icon_path}", e)
                            # Try alternative method with tk.call
                            try:
                                # This is a more reliable method on macOS
                                self.root.tk.call('wm', 'iconphoto', self.root._w, 
                                                tk.PhotoImage(file=self._convert_icns_to_png(icon_path)))
                                self.log_info(f"Set icon using iconphoto: {icon_path}")
                                return
                            except Exception as e2:
                                self.log_error(f"iconphoto also failed", e2)
            else:
                # On Windows/Linux, use .ico
                icon_paths = [
                    'icon.ico',
                    os.path.join(os.path.dirname(__file__), 'icon.ico'),
                    os.path.join(os.getcwd(), 'icon.ico')
                ]
                
                for icon_path in icon_paths:
                    if os.path.exists(icon_path):
                        try:
                            self.root.iconbitmap(icon_path)
                            self.log_info(f"Successfully set icon: {icon_path}")
                            return
                        except Exception as e:
                            self.log_error(f"Failed to set icon: {icon_path}", e)
            
            self.log_info("No suitable icon file found")
                            
        except Exception as e:
            self.log_error("Critical error setting main window icon", e)

    def _convert_icns_to_png(self, icns_path):
        """Helper to convert .icns to PNG for iconphoto on macOS"""
        try:
            from PIL import Image
            import tempfile
            
            # Load the .icns file
            image = Image.open(icns_path)
            
            # Create a temporary PNG file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_png = temp_file.name
            
            # Save as PNG
            image.save(temp_png, 'PNG')
            
            return temp_png
        except ImportError:
            # Fallback if PIL is not available
            if sys.platform == 'darwin':
                import subprocess
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_png = temp_file.name
                
                subprocess.run(['sips', '-s', 'format', 'png', icns_path, '--out', temp_png],
                            capture_output=True)
                
                return temp_png
        except Exception as e:
            self.log_error("Error converting icns to png", e)
            return None

    def show_main_window(self):
        """Show the main window and close splash"""
        try:
            self.log_info("Showing main window...")
            
            if self.splash:
                try:
                    self.splash.destroy()
                    self.splash = None
                    self.log_info("Splash screen closed")
                except Exception as e:
                    self.log_error("Error closing splash screen", e)
            
            # Set window properties before showing
            self.root.title("Hello Toolbelt")
            self.root.geometry("1200x1200")
            
            # Show and focus main window
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            
            # Force updates
            self.root.update_idletasks()
            self.root.update()
            
            self.log_info("Main window displayed")
            
        except Exception as e:
            self.log_error("Error showing main window", e)
            # Ensure main window shows even if splash fails
            try:
                self.root.title("Hello Toolbelt")
                self.root.geometry("1200x1200")
                self.root.deiconify()
                self.root.lift()
                self.root.update()
            except Exception as e2:
                self.log_error("Critical error showing main window", e2)

    def setup_logging(self):
        """Setup logging for debugging stability issues"""
        try:
            # Create logs directory if it doesn't exist
            log_dir = os.path.join(os.path.expanduser('~'), 'HelloToolbelt', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, 'hellotoolbelt.log')
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger('HelloToolbelt')
            self.logger.info("HelloToolbelt started successfully")
        except Exception as e:
            # Fallback if logging setup fails
            self.logger = None

    def log_error(self, message, exception=None):
        """Safe error logging"""
        if self.logger:
            if exception:
                self.logger.error(f"{message}: {str(exception)}")
            else:
                self.logger.error(message)
        else:
            pass

    def log_info(self, message):
        """Safe info logging"""
        if self.logger:
            self.logger.info(message)
        else:
            pass

    @contextmanager
    def safe_settings_access(self):
        """Thread-safe settings file access"""
        acquired = False
        try:
            acquired = self._settings_lock.acquire(timeout=5.0)
            if not acquired:
                raise TimeoutError("Could not acquire settings lock")
            yield
        finally:
            if acquired:
                self._settings_lock.release()

    def get_settings_file_path(self):
        """Thread-safe settings file path with proper error handling"""
        try:
            # Check if we're running as a PyInstaller bundle
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                if sys.platform.startswith('win'):
                    app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
                    settings_dir = os.path.join(app_data, 'HelloToolbelt')
                elif sys.platform.startswith('darwin'):
                    settings_dir = os.path.expanduser('~/Library/Application Support/HelloToolbelt')
                else:
                    settings_dir = os.path.expanduser('~/.config/HelloToolbelt')
                
                # Thread-safe directory creation
                try:
                    os.makedirs(settings_dir, exist_ok=True)
                except OSError as e:
                    self.log_error(f"Could not create settings directory: {settings_dir}", e)
                    # Fallback to user home
                    settings_dir = os.path.expanduser('~')
                
                return os.path.join(settings_dir, 'toolbelt_settings.json')
            else:
                # Running as script - use original location
                script_dir = os.path.dirname(__file__)
                return os.path.join(script_dir, "toolbelt_settings.json")
        except Exception as e:
            self.log_error("Error determining settings path", e)
            # Ultimate fallback
            return os.path.join(os.path.expanduser('~'), '.toolbelt_settings.json')

    def load_settings(self):
        """Enhanced settings loading with error recovery"""
        default_settings = {
            'is_dark_mode': False,
            'window_geometry': '1200x900',
            'dlq_file_path': ''
        }
        
        try:
            with self.safe_settings_access():
                if os.path.exists(self.settings_file):
                    with open(self.settings_file, 'r') as f:
                        settings = json.load(f)
                        
                    # Validate settings structure
                    for key, default_value in default_settings.items():
                        if key not in settings:
                            settings[key] = default_value
                            self.log_info(f"Added missing setting: {key}")
                    
                    self.is_dark_mode = settings.get('is_dark_mode', False)
                    self.dlq_file_path = settings.get('dlq_file_path', '')
                    
                    # Tier is now controlled by auth - always Tier 3
                    self.tier3_unlocked = True
                    self.current_tier = 'Tier 3'
                    
                    # Check for welcome popup status for this version
                    shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
                    setattr(self, shown_welcome_key, settings.get(shown_welcome_key, False))
                    
                    # Apply window geometry safely
                    geometry = settings.get('window_geometry', '1200x900')
                    try:
                        self.root.geometry(geometry)
                    except Exception as e:
                        self.log_error("Invalid geometry, using default", e)
                        self.root.geometry('1200x900')
                        
                else:
                    # Apply defaults for new installation
                    self.is_dark_mode = default_settings['is_dark_mode']
                    self.current_tier = 'Tier 3'  # Auth controls access now
                    self.tier3_unlocked = True
                    self.dlq_file_path = default_settings['dlq_file_path']
                    # First time opening, welcome should show
                    shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
                    setattr(self, shown_welcome_key, False)
                    self.log_info(f"New installation - settings file will be created at: {self.settings_file}")
                    
        except Exception as e:
            self.log_error("Error loading settings, using defaults", e)
            self.is_dark_mode = default_settings['is_dark_mode']
            self.current_tier = 'Tier 3'  # Auth controls access now
            self.tier3_unlocked = True
            self.dlq_file_path = default_settings['dlq_file_path']
            # Default to not shown for safety
            shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
            setattr(self, shown_welcome_key, False)

    def save_settings(self):
        """Thread-safe settings saving with error handling"""
        try:
            with self.safe_settings_access():
                # Ensure the directory exists
                settings_dir = os.path.dirname(self.settings_file)
                os.makedirs(settings_dir, exist_ok=True)
                
                settings = {
                    'is_dark_mode': self.is_dark_mode,
                    'window_geometry': self.root.geometry(),
                    'dlq_file_path': getattr(self, 'dlq_file_path', '')
                }
                
                # Add welcome popup status
                shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
                settings[shown_welcome_key] = getattr(self, shown_welcome_key, True)
                
                # Write to temporary file first, then rename for atomicity
                temp_file = self.settings_file + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                
                # Atomic rename
                if os.path.exists(self.settings_file):
                    backup_file = self.settings_file + '.bak'
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(self.settings_file, backup_file)
                
                os.rename(temp_file, self.settings_file)
                
                # Clean up backup after successful write
                backup_file = self.settings_file + '.bak'
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                
                self.log_info(f"Settings saved to: {self.settings_file}")
                
        except Exception as e:
            self.log_error("Error saving settings", e)
            # Try to restore from backup if it exists
            backup_file = self.settings_file + '.bak'
            if os.path.exists(backup_file):
                try:
                    if os.path.exists(self.settings_file):
                        os.remove(self.settings_file)
                    os.rename(backup_file, self.settings_file)
                    self.log_info("Restored settings from backup")
                except Exception as restore_error:
                    self.log_error("Could not restore settings backup", restore_error)

    def get_colors(self):
        """Get color scheme based on current mode"""
        if self.is_dark_mode:
            return {
                'bg': '#2b2b2b',
                'fg': '#ffffff',
                'frame_bg': '#3c3c3c',
                'header_bg': '#4a4a4a',
                'secondary_bg': '#404040',
                'tertiary_bg': '#353535',
                'text_secondary': '#cccccc',
                'primary': '#4a90e2',
                'success': '#27ae60',
                'danger': '#e74c3c',
                'warning': '#f39c12',
                'slider_bg': '#505050',
                'slider_active': '#6a6a6a',
                'slider_thumb': '#ffffff'
            }
        else:
            return {
                'bg': '#ffffff',
                'fg': '#2c3e50',
                'frame_bg': '#f8f9fa',
                'header_bg': '#e9ecef',
                'secondary_bg': '#f8f9fa',
                'tertiary_bg': '#ffffff',
                'text_secondary': '#34495e',
                'primary': '#3498db',
                'success': '#27ae60',
                'danger': '#e74c3c',
                'warning': '#f39c12',
                'slider_bg': '#e0e0e0',
                'slider_active': '#d0d0d0',
                'slider_thumb': '#3498db'
            }

    def setup_styles(self):
        """Configure enhanced styling for the application"""
        style = ttk.Style()
        colors = self.get_colors()
        
        # Use a modern theme as base
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        else:
            style.theme_use('default')
        
        # Configure custom notebook style
        style.configure('Custom.TNotebook', 
                       background=colors['secondary_bg'],
                       borderwidth=0,
                       relief='flat')
        
        # Configure custom notebook tab style
        tab_bg = '#e8e8e8' if not self.is_dark_mode else '#505050'
        tab_active = '#d0d0d0' if not self.is_dark_mode else '#606060'
        
        style.configure('Custom.TNotebook.Tab',
                       padding=[12, 6],
                       background=tab_bg,
                       foreground=colors['fg'],
                       borderwidth=1,
                       relief='raised',
                       focuscolor='none')
        
        # Configure selected tab style
        style.map('Custom.TNotebook.Tab',
                 background=[('selected', colors['primary']),
                           ('active', tab_active),
                           ('!active', tab_bg)],
                 foreground=[('selected', 'white'),
                           ('active', colors['fg']),
                           ('!active', colors['fg'])],
                 relief=[('selected', 'solid'),
                        ('active', 'raised'),
                        ('!active', 'raised')])
        
        # Configure frame styles
        style.configure('Tool.TFrame',
                       background=colors['bg'],
                       relief='flat',
                       borderwidth=0)
        
        # Configure label styles
        style.configure('Heading.TLabel',
                       background=colors['bg'],
                       foreground=colors['fg'],
                       font=('Segoe UI', 14, 'bold'))
        
        style.configure('SubHeading.TLabel',
                       background=colors['bg'],
                       foreground=colors['text_secondary'],
                       font=('Segoe UI', 11, 'bold'))
        
        style.configure('Body.TLabel',
                       background=colors['bg'],
                       foreground=colors['fg'],
                       font=('Segoe UI', 10))

    def init_shared_credentials(self):
        """Initialize shared credentials for all tools with CredentialManager"""
        # Initialize credential manager for secure, isolated credential storage
        self.credential_manager = CredentialManager(keyring_available=KEYRING_AVAILABLE)
        
        # Database configuration variables
        self.db_host = tk.StringVar(value='localhost')
        self.db_port = tk.StringVar(value='5432')
        self.db_name = tk.StringVar(value='')
        self.db_user = tk.StringVar(value='')
        self.db_password = tk.StringVar(value='')
        
        # AWS configuration variables
        self.aws_access_key = tk.StringVar(value='')
        self.aws_secret_key = tk.StringVar(value='')
        self.aws_region = tk.StringVar(value='us-east-1')
        
        # Track if credentials have been loaded from keyring
        self._credentials_loaded = False
        
        # Load non-sensitive config from files (no keyring access)
        self._load_config_files_only()
    
    def _load_config_files_only(self):
        """Load configuration from files only, no keyring access"""
        try:
            # Load DB config from file (not password)
            config_file = os.path.join(os.path.expanduser('~'), '.hellotoolbelt_db_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.db_host.set(config.get('host', 'localhost'))
                    self.db_port.set(config.get('port', '5432'))
                    self.db_name.set(config.get('database', ''))
                    self.db_user.set(config.get('username', ''))
            
            # Load AWS config from file (not secret key)
            aws_config_file = os.path.join(os.path.expanduser('~'), '.hellotoolbelt_aws_config.json')
            if os.path.exists(aws_config_file):
                with open(aws_config_file, 'r') as f:
                    aws_config = json.load(f)
                    self.aws_region.set(aws_config.get('region', 'us-east-1'))
        except Exception as e:
            pass
    
    def ensure_credentials_loaded(self):
        """Load credentials from keyring if not already loaded. Call this when credentials are needed."""
        if self._credentials_loaded:
            return
        
        self._credentials_loaded = True
        
        # Now load from keyring
        self.load_db_config()
        self.load_aws_credentials()
    
    def load_db_config(self):
        """Load database configuration from file and password from keyring"""
        try:
            config_file = os.path.join(os.path.expanduser('~'), '.hellotoolbelt_db_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.db_host.set(config.get('host', 'localhost'))
                    self.db_port.set(config.get('port', '5432'))
                    self.db_name.set(config.get('database', ''))
                    self.db_user.set(config.get('username', ''))
            
            # Load password using CredentialManager
            password = self.credential_manager.get_db_credentials()
            if password:
                self.db_password.set(password)
            else:
                pass
                
        except Exception as e:
            pass
    
    def save_db_config(self):
        """Save database configuration to file and password to keyring"""
        try:
            config = {
                'host': self.db_host.get(),
                'port': self.db_port.get(),
                'database': self.db_name.get(),
                'username': self.db_user.get()
            }
            config_file = os.path.join(os.path.expanduser('~'), '.hellotoolbelt_db_config.json')
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Save password using CredentialManager
            password = self.db_password.get().strip()
            
            if password:
                success = self.credential_manager.store_db_credentials(password)
                if success:
                    pass
                    messagebox.showinfo("Saved", "Database configuration saved!\n\n(Password stored securely in system keychain)")
                else:
                    pass
                    messagebox.showinfo("Saved", "Database configuration saved!\n\n(Password saved in memory only)")
            else:
                pass
                messagebox.showinfo("Saved", "Database configuration saved!\n\n(No password provided)")
                
        except Exception as e:
            pass
            messagebox.showerror("Error", f"Could not save config:\n{str(e)}")
    
    def test_db_connection(self):
        """Test the PostgreSQL database connection"""
        try:
            import psycopg2
        except ImportError:
            messagebox.showerror("Error", 
                               "psycopg2 is not installed.\n\n"
                               "To install, run:\n"
                               "pip install psycopg2-binary")
            return
        
        host = self.db_host.get().strip()
        port = self.db_port.get().strip()
        database = self.db_name.get().strip()
        user = self.db_user.get().strip()
        password = self.db_password.get().strip()
        
        if not all([host, port, database, user, password]):
            messagebox.showwarning("Missing Information", 
                                 "Please fill in all database fields!")
            return
        
        # Create test window
        test_window = tk.Toplevel(self.root)
        test_window.title("Testing Database Connection")
        test_window.geometry("400x150")
        test_window.transient(self.root)
        test_window.grab_set()
        
        tk.Label(test_window, text="Testing Database Connection...", 
                font=('Segoe UI', 11, 'bold')).pack(pady=20)
        
        progress = ttk.Progressbar(test_window, mode='indeterminate', length=300)
        progress.pack(pady=10)
        progress.start()
        
        status_label = tk.Label(test_window, text="Connecting...", font=('Segoe UI', 9))
        status_label.pack(pady=10)
        
        def test_connection():
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password
                )
                conn.close()
                
                progress.stop()
                test_window.destroy()
                messagebox.showinfo("Success! ✅", 
                                  "Database connection successful!\n\n"
                                  "All tools can now use these credentials.")
            except Exception as e:
                progress.stop()
                test_window.destroy()
                messagebox.showerror("Connection Failed", 
                                   f"Could not connect to database:\n\n{str(e)}")
        
        # Run test in thread
        test_thread = threading.Thread(target=test_connection, daemon=True)
        test_thread.start()
    
    def save_aws_credentials(self):
        """Save AWS credentials to system keychain AND ~/.aws/credentials for boto3"""
        import os
        from pathlib import Path
        
        access_key = self.aws_access_key.get().strip()
        secret_key = self.aws_secret_key.get().strip()
        region = self.aws_region.get().strip() or "us-east-1"
        
        if not access_key or not secret_key:
            messagebox.showwarning("Missing Credentials", 
                                "Please enter both Access Key ID and Secret Access Key!")
            return
        
        # Save to keyring using CredentialManager (isolated from DB credentials)
        keyring_success = self.credential_manager.store_aws_credentials(access_key, secret_key, region)
        if not keyring_success:
            self.log_info("Keyring not available or failed to save AWS credentials")
        
        # IMPORTANT: Also save to ~/.aws/credentials for boto3
        try:
            # Create .aws directory if it doesn't exist
            aws_dir = Path.home() / '.aws'
            aws_dir.mkdir(exist_ok=True)
            
            credentials_file = aws_dir / 'credentials'
            config_file = aws_dir / 'config'
            
            # Read existing credentials file
            existing_profiles = {}
            if credentials_file.exists():
                with open(credentials_file, 'r') as f:
                    current_profile = None
                    for line in f:
                        line = line.strip()
                        if line.startswith('[') and line.endswith(']'):
                            current_profile = line[1:-1]
                            existing_profiles[current_profile] = {}
                        elif '=' in line and current_profile:
                            key, value = line.split('=', 1)
                            existing_profiles[current_profile][key.strip()] = value.strip()
            
            # Update default profile with new credentials
            existing_profiles['default'] = {
                'aws_access_key_id': access_key,
                'aws_secret_access_key': secret_key
            }
            
            # Write back to credentials file
            with open(credentials_file, 'w') as f:
                for profile_name, profile_creds in existing_profiles.items():
                    f.write(f'[{profile_name}]\n')
                    for key, value in profile_creds.items():
                        f.write(f'{key} = {value}\n')
                    f.write('\n')
            
            # Set permissions to be readable only by user (security)
            os.chmod(credentials_file, 0o600)
            
            # Update config file with region
            config_content = f"""[default]
    region = {region}
    output = json
    """
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            os.chmod(config_file, 0o600)
            
            messagebox.showinfo("Success", 
                            f"✅ AWS credentials saved successfully!\n\n"
                            f"📍 Saved to:\n"
                            f"   • System Keychain (secure)\n"
                            f"   • {credentials_file}\n"
                            f"   • {config_file}\n\n"
                            f"🔧 All tools and boto3 can now access AWS!")
            
            self.log_info(f"AWS credentials saved to {credentials_file}")
            
        except Exception as e:
            error_msg = str(e)
            messagebox.showerror("Error Saving Credentials", 
                            f"Failed to save AWS credentials:\n{error_msg}\n\n"
                            f"Credentials were saved to keychain but not to AWS config.")
            self.log_error("Failed to save AWS credentials file", e)
    
    def load_aws_credentials(self):
        """Load AWS credentials from keychain or ~/.aws/credentials"""
        from pathlib import Path
        
        # Try CredentialManager first
        access_key, secret_key, region = self.credential_manager.get_aws_credentials()
        
        if access_key and secret_key:
            self.aws_access_key.set(access_key)
            self.aws_secret_key.set(secret_key)
            if region:
                self.aws_region.set(region)
            self.log_info("Loaded AWS credentials from keyring")
            return
        
        # Fall back to reading from ~/.aws/credentials
        try:
            credentials_file = Path.home() / '.aws' / 'credentials'
            config_file = Path.home() / '.aws' / 'config'
            
            if credentials_file.exists():
                access_key = None
                secret_key = None
                
                with open(credentials_file, 'r') as f:
                    in_default_profile = False
                    for line in f:
                        line = line.strip()
                        if line == '[default]':
                            in_default_profile = True
                        elif line.startswith('['):
                            in_default_profile = False
                        elif in_default_profile and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if key == 'aws_access_key_id':
                                access_key = value
                            elif key == 'aws_secret_access_key':
                                secret_key = value
                
                if access_key and secret_key:
                    self.aws_access_key.set(access_key)
                    self.aws_secret_key.set(secret_key)
                    self.log_info("Loaded AWS credentials from ~/.aws/credentials")
            
            # Load region from config
            if config_file.exists():
                with open(config_file, 'r') as f:
                    in_default_profile = False
                    for line in f:
                        line = line.strip()
                        if line == '[default]':
                            in_default_profile = True
                        elif line.startswith('['):
                            in_default_profile = False
                        elif in_default_profile and line.startswith('region'):
                            _, region = line.split('=', 1)
                            self.aws_region.set(region.strip())
                            break
        except Exception as e:
            self.log_error("Error loading AWS credentials from file", e)
    
    def clear_aws_credentials(self):
        """Clear AWS credentials from keychain, UI, and ~/.aws/credentials
        NOTE: This ONLY deletes AWS credentials - DB credentials are NOT affected"""
        from pathlib import Path
        
        # First warning
        messagebox.showwarning("⚠️ Warning", 
                              "You are about to clear all AWS credentials!\n\n"
                              "This will permanently remove AWS credentials from:\n"
                              "• System keychain\n"
                              "• ~/.aws/credentials\n"
                              "• ~/.aws/config\n"
                              "• HelloToolbelt UI\n\n"
                              "⚠️ NOTE: Your database credentials will NOT be affected.\n"
                              "⚠️ This action cannot be undone!")
        
        # Confirmation dialog
        if not messagebox.askyesno("Confirm Clear", 
                                "Are you sure you want to clear all AWS credentials?\n\n"
                                "This will remove AWS credentials from:\n"
                                "• System keychain\n"
                                "• ~/.aws/credentials\n"
                                "• ~/.aws/config\n\n"
                                "Database credentials will remain safe."):
            self.log_info("AWS credential clear cancelled by user")
            return
        
        # Clear from keyring using CredentialManager (ONLY AWS credentials)
        self.log_info("Starting AWS credential deletion...")
        deletion_results = self.credential_manager.delete_aws_credentials()
        
        # Log deletion results
        for key, success in deletion_results.items():
            if success:
                self.log_info(f"✓ Successfully deleted {key} from keyring")
            else:
                self.log_error(f"✗ Failed to delete {key} from keyring", None)
        
        # Clear from ~/.aws files
        try:
            credentials_file = Path.home() / '.aws' / 'credentials'
            config_file = Path.home() / '.aws' / 'config'
            
            # Remove default profile from credentials
            if credentials_file.exists():
                self.log_info(f"Clearing default profile from {credentials_file}")
                lines = []
                skip_section = False
                with open(credentials_file, 'r') as f:
                    for line in f:
                        if line.strip() == '[default]':
                            skip_section = True
                            continue
                        elif line.strip().startswith('['):
                            skip_section = False
                        
                        if not skip_section:
                            lines.append(line)
                
                with open(credentials_file, 'w') as f:
                    f.writelines(lines)
                self.log_info("✓ Cleared default profile from credentials file")
            
            # Remove default profile from config
            if config_file.exists():
                self.log_info(f"Clearing default profile from {config_file}")
                lines = []
                skip_section = False
                with open(config_file, 'r') as f:
                    for line in f:
                        if line.strip() == '[default]':
                            skip_section = True
                            continue
                        elif line.strip().startswith('['):
                            skip_section = False
                        
                        if not skip_section:
                            lines.append(line)
                
                with open(config_file, 'w') as f:
                    f.writelines(lines)
                self.log_info("✓ Cleared default profile from config file")
                
        except Exception as e:
            self.log_error("Error clearing AWS credential files", e)
        
        # Clear from UI
        self.aws_access_key.set('')
        self.aws_secret_key.set('')
        self.aws_region.set('us-east-1')
        self.log_info("✓ Cleared AWS credentials from UI")
        
        messagebox.showinfo("Cleared", 
                        "✅ AWS credentials have been cleared from:\n"
                        "   • System keychain (AWS only)\n"
                        "   • ~/.aws/credentials\n"
                        "   • ~/.aws/config\n"
                        "   • HelloToolbelt UI\n\n"
                        "✅ Database credentials remain intact.")
        
        self.log_info("Successfully cleared all AWS credentials (DB credentials unaffected)")

    def prompt_for_tier3_password(self):
        """Prompt user for Tier 3 password"""
        try:
            colors = self.get_colors()
            
            # Ensure main window is properly displayed and focused
            self.root.update_idletasks()
            self.root.lift()  # Bring main window to front first
            
            # Small delay to ensure main window is settled
            self.root.after(50, lambda: self._create_password_dialog(colors))
            
            # Wait a moment for the dialog to be created
            self.root.update()
            
            return getattr(self, '_dialog_result', False)
            
        except Exception as e:
            self.log_error("Error creating password dialog", e)
            return False
    
    def _create_password_dialog(self, colors):
        """Helper method to create the password dialog"""
        try:
            dialog = PasswordDialog(self.root, colors)
            
            result = dialog.wait_for_result()
            
            self._dialog_result = result
            
            # Continue with the tier change logic
            self._handle_password_result(result)
            
        except Exception as e:
            pass
            self._dialog_result = False
            self._handle_password_result(False)
    
    def _handle_password_result(self, success):
        """Handle the result of the password dialog"""
        try:
            if success:
                # Password correct, unlock Tier 3 permanently and set current tier
                self.tier3_unlocked = True  # Mark as permanently unlocked
                self.current_tier = 'Tier 3'
                
                # Save settings immediately to persist the unlock
                self.save_settings()
                
                # Refresh tabs for new tier
                self.refresh_tabs_for_tier()
                
                # Show success message
                try:
                    messagebox.showinfo("Access Granted", 
                                      "Tier 3 access granted and saved! All tools are now available.\n\nTier 3 will remain unlocked for future sessions.",
                                      parent=self.root)
                except Exception as e:
                    pass
                    
            else:
                # Password incorrect or cancelled, revert selection
                self.tier_var.set(self.current_tier)
                
                # Show failure message
                try:
                    messagebox.showwarning("Access Denied", 
                                         "Incorrect password or access cancelled.\nRemaining on current tier.",
                                         parent=self.root)
                except Exception as e:
                    pass
        except Exception as e:
            pass
            # Revert to current tier on any error
            try:
                self.tier_var.set(self.current_tier)
            except:
                pass

    def on_tier_change(self, event=None):
        """Handle tier selection change with password protection"""
        try:
            new_tier = self.tier_var.get()
            
            if new_tier != self.current_tier:
                # If trying to switch to Tier 3, check if already unlocked or require password
                if new_tier == 'Tier 3':
                    if self.tier3_unlocked:
                        # Already unlocked, allow immediate access
                        self.current_tier = new_tier
                        self.refresh_tabs_for_tier()
                        self.save_settings()  # Save the tier preference
                    else:
                        # Not unlocked yet, require password
                        self.prompt_for_tier3_password()
                    
                else:
                    # Switching from Tier 3 to Tier 2 (no password needed, but Tier 3 stays unlocked)
                    self.current_tier = new_tier
                    self.refresh_tabs_for_tier()
                    self.save_settings()  # Save the tier preference
            else:
                pass
                
        except Exception as e:
            self.log_error("Error handling tier change", e)
            # Revert to previous tier on error
            try:
                self.tier_var.set(self.current_tier)
            except tk.TclError as e:
                self.log_error("Failed to revert tier variable", e)
            except Exception as e:
                self.log_error("Unexpected error reverting tier", e)

    def get_tools_for_tier(self):
        """Get the list of tools based on current tier"""
        # Tier 2 gets access to all File Tools
        tier_2_tools = ['Eligibility Search', 'Multi-File Column Search', 'Report Builder']
        
        if self.current_tier == 'Tier 2':
            return [tool for tool in self.tools if tool['name'] in tier_2_tools]
        else:  # Tier 3
            return self.tools

    def create_tool_tabs(self):
        """Create a tab for each tool with enhanced styling based on tier"""
        colors = self.get_colors()
        
        # Get tools for current tier
        tools_to_show = self.get_tools_for_tier()
        
        # Define which tools should be in the Client Setup subtabs
        client_setup_tools = ['Config', 'CronJob', 'Base64']
        
        # Define which tools should be in the File Tools subtabs
        file_tools = ['Eligibility Search', 'Multi-File Column Search', 'Report Builder']
        
        # Separate tools into groups
        client_setup_configs = [tool for tool in tools_to_show if tool['name'] in client_setup_tools]
        file_tools_configs = [tool for tool in tools_to_show if tool['name'] in file_tools]
        other_tools = [tool for tool in tools_to_show if tool['name'] not in client_setup_tools and tool['name'] not in file_tools]
        
        # Create Client Setup tab with subtabs if there are any client setup tools
        if client_setup_configs:
            pass
            self._create_nested_tab_group(
                group_name="⚙️ Client Setup",
                tools=client_setup_configs,
                notebook_attr='client_notebook',
                event_handler=self.on_subtab_changed
            )
        
        # Create File Tools tab with subtabs if there are any file tools
        if file_tools_configs:
            pass
            self._create_nested_tab_group(
                group_name="📁 File Tools",
                tools=file_tools_configs,
                notebook_attr='file_tools_notebook',
                event_handler=self.on_file_tools_subtab_changed
            )
        
        # Create regular tabs for other tools
        for tool_config in other_tools:
            pass
            # Create tab frame with styling
            tab_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
            
            # Add tab with icon and name
            tab_text = f"{tool_config.get('icon', '🔧')} {tool_config['name']}"
            self.notebook.add(tab_frame, text=tab_text)
            
            # Create a container frame with padding and styling
            container_frame = tk.Frame(tab_frame, bg=colors['bg'], relief='flat', bd=0)
            container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Try to load and instantiate the tool
            success = self.load_tool_in_tab(container_frame, tool_config)
            
            if not success:
                # If loading failed, show error message
                self.create_error_tab(container_frame, tool_config)
        
    def _create_nested_tab_group(self, group_name, tools, notebook_attr, event_handler):
        """Helper method to create a nested notebook tab group"""
        colors = self.get_colors()
        
        # Create main group tab
        group_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
        self.notebook.add(group_frame, text=group_name)
        
        # Create a notebook for subtabs
        nested_notebook = ttk.Notebook(group_frame, style='Custom.TNotebook')
        nested_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Store reference to nested notebook
        setattr(self, notebook_attr, nested_notebook)
        
        # Bind tab change event for subtabs
        nested_notebook.bind('<<NotebookTabChanged>>', event_handler)
        
        # Add subtabs for each tool
        for tool_config in tools:
            pass
            # Create subtab frame
            subtab_frame = ttk.Frame(nested_notebook, style='Tool.TFrame')
            
            # Add subtab with icon and name
            subtab_text = f"{tool_config.get('icon', '🔧')} {tool_config['name']}"
            nested_notebook.add(subtab_frame, text=subtab_text)
            
            # Create a container frame with padding and styling
            container_frame = tk.Frame(subtab_frame, bg=colors['bg'], relief='flat', bd=0)
            container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Try to load and instantiate the tool
            success = self.load_tool_in_tab(container_frame, tool_config)
            
            if not success:
                # If loading failed, show error message
                self.create_error_tab(container_frame, tool_config)
        
    def refresh_tabs_for_tier(self):
        """Refresh tabs based on tier selection"""
        try:
            # Clear all existing tabs except options
            tabs_to_remove = []
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Options" not in tab_text:
                    tabs_to_remove.append(i)
            
            # Remove tabs in reverse order to maintain indices
            for i in reversed(tabs_to_remove):
                self.notebook.forget(i)
            
            # Clean up loaded tools safely
            tool_names = list(self.loaded_tools.keys())
            for tool_name in tool_names:
                self.safe_tool_cleanup(tool_name)
            
            # Recreate tool tabs for new tier
            self.create_tool_tabs()
            
            # Move options tab back to the end
            self.move_options_tab_to_end()
            
            # Save settings
            self.save_settings()
        except Exception as e:
            self.log_error("Error refreshing tabs for tier", e)

    def on_subtab_changed(self, event):
        """Handle subtab change events in Client Setup nested notebook"""
        try:
            # Show busy cursor immediately
            self.root.config(cursor="watch")
            self.root.update_idletasks()
            
            # Get currently selected subtab
            if not hasattr(self, 'client_notebook'):
                self.root.config(cursor="")
                return
                
            selected_subtab = self.client_notebook.select()
            if not selected_subtab:
                self.root.config(cursor="")
                return
                
            subtab_index = self.client_notebook.index(selected_subtab)
            
            # Skip if it's the same subtab
            if self.last_selected_subtab == subtab_index:
                self.root.config(cursor="")
                return
                
            self.last_selected_subtab = subtab_index
            
            # Get subtab name for logging
            subtab_text = self.client_notebook.tab(subtab_index, "text")
            
            # Log subtab access to audit trail
            if self.auth:
                # Clean up the subtab text (remove emoji)
                clean_subtab_name = subtab_text.strip()
                for emoji in ['⚙️', '⏰', '🔐', '🔧']:
                    clean_subtab_name = clean_subtab_name.replace(emoji, '').strip()
                self.auth.log_action("OPENED_TOOL", f"Client Setup > {clean_subtab_name}")
            
            # Update subtab color dynamically based on tool
            self.update_subtab_color(self.client_notebook, subtab_index)
            
            # Check if already loaded
            if subtab_index not in self.subtab_loaded:
                self.subtab_loaded[subtab_index] = True
            else:
                # Force canvas and scroll region updates for ScrollableFrame widgets
                try:
                    subtab_id = self.client_notebook.tabs()[subtab_index]
                    subtab_frame = self.client_notebook.nametowidget(subtab_id)
                    
                    # Find and update any ScrollableFrame canvases
                    self._force_canvas_update(subtab_frame)
                    
                    # Force immediate visual update for macOS
                    self.root.update()
                except Exception as e:
                    self.log_error(f"Error forcing subtab screen update", e)
            
            # Reset cursor
            self.root.config(cursor="")
            
        except Exception as e:
            self.log_error("Error in subtab change handler", e)
            self.root.config(cursor="")

    def on_file_tools_subtab_changed(self, event):
        """Handle subtab change events in File Tools nested notebook"""
        try:
            # Show busy cursor immediately
            self.root.config(cursor="watch")
            self.root.update_idletasks()
            
            # Get currently selected subtab
            if not hasattr(self, 'file_tools_notebook'):
                self.root.config(cursor="")
                return
                
            selected_subtab = self.file_tools_notebook.select()
            if not selected_subtab:
                self.root.config(cursor="")
                return
                
            subtab_index = self.file_tools_notebook.index(selected_subtab)
            
            # Skip if it's the same subtab
            if self.last_selected_file_tools_subtab == subtab_index:
                self.root.config(cursor="")
                return
                
            self.last_selected_file_tools_subtab = subtab_index
            
            # Get subtab name for logging
            subtab_text = self.file_tools_notebook.tab(subtab_index, "text")
            
            # Log subtab access to audit trail
            if self.auth:
                # Clean up the subtab text (remove emoji)
                clean_subtab_name = subtab_text.strip()
                for emoji in ['🔍', '📂', '📊', '🔧']:
                    clean_subtab_name = clean_subtab_name.replace(emoji, '').strip()
                self.auth.log_action("OPENED_TOOL", f"File Tools > {clean_subtab_name}")
            
            # Update subtab color dynamically based on tool
            self.update_subtab_color(self.file_tools_notebook, subtab_index)
            
            # Check if already loaded
            if subtab_index not in self.file_tools_subtab_loaded:
                self.file_tools_subtab_loaded[subtab_index] = True
            else:
                # Force canvas and scroll region updates for ScrollableFrame widgets
                try:
                    subtab_id = self.file_tools_notebook.tabs()[subtab_index]
                    subtab_frame = self.file_tools_notebook.nametowidget(subtab_id)
                    
                    # Find and update any ScrollableFrame canvases
                    self._force_canvas_update(subtab_frame)
                    
                    # Force immediate visual update for macOS
                    self.root.update()
                except Exception as e:
                    self.log_error(f"Error forcing file tools subtab screen update", e)
            
            # Reset cursor
            self.root.config(cursor="")
            
        except Exception as e:
            self.log_error("Error in file tools subtab change handler", e)
            self.root.config(cursor="")

    def on_admin_subtab_changed(self, event):
        """Handle subtab change events in Admin nested notebook"""
        try:
            # Show busy cursor immediately
            self.root.config(cursor="watch")
            self.root.update_idletasks()
            
            # Get currently selected subtab
            if not hasattr(self, 'admin_notebook'):
                self.root.config(cursor="")
                return
                
            selected_subtab = self.admin_notebook.select()
            if not selected_subtab:
                self.root.config(cursor="")
                return
                
            subtab_index = self.admin_notebook.index(selected_subtab)
            
            # Skip if it's the same subtab
            if self.last_selected_admin_subtab == subtab_index:
                self.root.config(cursor="")
                return
                
            self.last_selected_admin_subtab = subtab_index
            
            # Get subtab name for logging
            subtab_text = self.admin_notebook.tab(subtab_index, "text")
            
            # Log subtab access to audit trail
            if self.auth:
                # Clean up the subtab text (remove emoji)
                clean_subtab_name = subtab_text.strip()
                for emoji in ['👥', '📋']:
                    clean_subtab_name = clean_subtab_name.replace(emoji, '').strip()
                self.auth.log_action("OPENED_TOOL", f"Admin > {clean_subtab_name}")
            
            # Update subtab color dynamically based on tool
            self.update_subtab_color(self.admin_notebook, subtab_index)
            
            # Check if already loaded
            if subtab_index not in self.admin_subtab_loaded:
                self.admin_subtab_loaded[subtab_index] = True
            else:
                # Force canvas and scroll region updates for ScrollableFrame widgets
                try:
                    subtab_id = self.admin_notebook.tabs()[subtab_index]
                    subtab_frame = self.admin_notebook.nametowidget(subtab_id)
                    
                    # Find and update any ScrollableFrame canvases
                    self._force_canvas_update(subtab_frame)
                    
                    # Force immediate visual update
                    self.root.update()
                except Exception as e:
                    self.log_error(f"Error forcing admin subtab screen update", e)
            
            # Reset cursor
            self.root.config(cursor="")
            
        except Exception as e:
            self.log_error("Error in admin subtab change handler", e)
            self.root.config(cursor="")

    def on_tab_changed(self, event):
        """Handle tab change events with immediate rendering"""
        try:
            # Show busy cursor immediately for user feedback
            self.root.config(cursor="watch")
            self.root.update_idletasks()
            
            # Get currently selected tab
            selected_tab = self.notebook.select()
            if not selected_tab:
                self.root.config(cursor="")
                return
                
            tab_index = self.notebook.index(selected_tab)
            
            # Skip if it's the same tab
            if self.last_selected_tab == tab_index:
                self.root.config(cursor="")
                return
                
            self.last_selected_tab = tab_index
            
            # Get tab name for logging
            tab_text = self.notebook.tab(tab_index, "text")
            
            # Log tab access to audit trail
            if self.auth:
                # Clean up the tab text (remove emoji)
                clean_tab_name = tab_text.strip()
                for emoji in ['⚙️', '📁', '📨', '🎯', '🗺️', '⚡']:
                    clean_tab_name = clean_tab_name.replace(emoji, '').strip()
                self.auth.log_action("OPENED_TAB", clean_tab_name)
            
            # Update tab color dynamically based on tool
            self.update_tab_color(tab_index)
            
            # Check if this tab contains a nested notebook (Client Setup or File Tools)
            # and update the color of the currently selected subtab
            if "Client Setup" in tab_text and hasattr(self, 'client_notebook') and self.client_notebook:
                try:
                    selected_subtab = self.client_notebook.select()
                    if selected_subtab:
                        subtab_index = self.client_notebook.index(selected_subtab)
                        self.update_subtab_color(self.client_notebook, subtab_index)
                except tk.TclError:
                    # Notebook widget not ready or destroyed
                    pass
                except Exception as e:
                    self.log_error("Error updating Client Setup subtab color", e)
            elif "File Tools" in tab_text and hasattr(self, 'file_tools_notebook') and self.file_tools_notebook:
                try:
                    selected_subtab = self.file_tools_notebook.select()
                    if selected_subtab:
                        subtab_index = self.file_tools_notebook.index(selected_subtab)
                        self.update_subtab_color(self.file_tools_notebook, subtab_index)
                except tk.TclError:
                    # Notebook widget not ready or destroyed
                    pass
                except Exception as e:
                    self.log_error("Error updating File Tools subtab color", e)
            elif "Admin" in tab_text and hasattr(self, 'admin_notebook') and self.admin_notebook:
                try:
                    selected_subtab = self.admin_notebook.select()
                    if selected_subtab:
                        subtab_index = self.admin_notebook.index(selected_subtab)
                        self.update_subtab_color(self.admin_notebook, subtab_index)
                except tk.TclError:
                    # Notebook widget not ready or destroyed
                    pass
                except Exception as e:
                    self.log_error("Error updating Admin subtab color", e)
            
            # Render immediately if not already loaded
            if tab_index not in self.tab_loaded:
                self._render_tab_content_fast(tab_index)
            else:
                # Force canvas and scroll region updates for ScrollableFrame widgets
                try:
                    tab_id = self.notebook.tabs()[tab_index]
                    tab_frame = self.notebook.nametowidget(tab_id)
                    
                    # Find and update any ScrollableFrame canvases
                    self._force_canvas_update(tab_frame)
                    
                    # Force immediate visual update for macOS
                    self.root.update()
                except Exception as e:
                    self.log_error(f"Error forcing screen update", e)
            
            # Reset cursor
            self.root.config(cursor="")
            
        except Exception as e:
            self.log_error("Error in tab change handler", e)
            self.root.config(cursor="")
    
    def _render_tab_content_fast(self, tab_index):
        """Fast render tab content without delays"""
        try:
            # Mark as loaded first to prevent duplicate renders
            self.tab_loaded[tab_index] = True
            
            # Get the tab frame
            tab_id = self.notebook.tabs()[tab_index]
            tab_frame = self.notebook.nametowidget(tab_id)
            
            # Quick, aggressive render without batching delays
            self._force_render_recursive(tab_frame)
            
        except Exception as e:
            self.log_error(f"Error rendering tab {tab_index}", e)
    
    def _force_canvas_update(self, widget):
        """Recursively find and update all Canvas widgets (fixes ScrollableFrame blank issue)"""
        try:
            # Check if this widget is a Canvas
            if isinstance(widget, tk.Canvas):
                # Force canvas to recalculate and redraw
                widget.update_idletasks()
                widget.update()
                # Force scroll region recalculation
                bbox = widget.bbox("all")
                if bbox:
                    widget.configure(scrollregion=bbox)
            
            # Check if this is a ScrollableFrame and call its update method
            if hasattr(widget, 'force_scroll_update'):
                widget.force_scroll_update()
            
            # Also check for 'canvas' attribute (ScrollableFrame pattern)
            if hasattr(widget, 'canvas') and isinstance(widget.canvas, tk.Canvas):
                widget.canvas.update_idletasks()
                widget.canvas.update()
                bbox = widget.canvas.bbox("all")
                if bbox:
                    widget.canvas.configure(scrollregion=bbox)
            
            # Check children recursively
            try:
                for child in widget.winfo_children():
                    self._force_canvas_update(child)
            except tk.TclError:
                # Widget may have been destroyed
                pass
            except Exception as e:
                self.log_error("Error updating child widget in canvas", e)
                
        except tk.TclError:
            # Widget not available - this is expected during tab switching
            pass
        except Exception as e:
            # Log unexpected errors but don't break tab switching
            self.log_error("Unexpected error in canvas update", e)

    def update_tab_color(self, tab_index):
        """Update the selected tab color based on the tool's primary color"""
        try:
            # Get the tab's text to find the tool name
            tab_text = self.notebook.tab(tab_index, "text")
            
            # Extract tool name from tab text (remove emoji icon)
            tool_name = None
            
            # First check in tool_tab_colors
            for name in self.tool_tab_colors.keys():
                if name in tab_text:
                    tool_name = name
                    break
            
            # If not found, check default_tool_colors
            if not tool_name:
                for name in self.default_tool_colors.keys():
                    if name in tab_text:
                        tool_name = name
                        break
            
            # If we found a matching tool with a custom color, use it
            custom_color = None
            if tool_name:
                if tool_name in self.tool_tab_colors:
                    custom_color = self.tool_tab_colors[tool_name]
                elif tool_name in self.default_tool_colors:
                    custom_color = self.default_tool_colors[tool_name]
            
            if custom_color:
                # Get the style
                style = ttk.Style()
                
                # Update the selected tab color to match the tool's primary color
                style.map('Custom.TNotebook.Tab',
                         background=[('selected', custom_color),
                                   ('active', '#d0d0d0' if not self.is_dark_mode else '#606060'),
                                   ('!active', '#e8e8e8' if not self.is_dark_mode else '#505050')],
                         foreground=[('selected', 'white'),
                                   ('active', self.get_colors()['fg']),
                                   ('!active', self.get_colors()['fg'])],
                         relief=[('selected', 'solid'),
                                ('active', 'raised'),
                                ('!active', 'raised')])
            else:
                # Use default color scheme
                colors = self.get_colors()
                style = ttk.Style()
                style.map('Custom.TNotebook.Tab',
                         background=[('selected', colors['primary']),
                                   ('active', '#d0d0d0' if not self.is_dark_mode else '#606060'),
                                   ('!active', '#e8e8e8' if not self.is_dark_mode else '#505050')],
                         foreground=[('selected', 'white'),
                                   ('active', colors['fg']),
                                   ('!active', colors['fg'])],
                         relief=[('selected', 'solid'),
                                ('active', 'raised'),
                                ('!active', 'raised')])
                
        except Exception as e:
            # Silently ignore errors to not break tab display
            pass

    def update_subtab_color(self, notebook, subtab_index):
        """Update the selected subtab color based on the tool's primary color"""
        try:
            # Get the subtab's text to find the tool name
            subtab_text = notebook.tab(subtab_index, "text")
            
            # Extract tool name from tab text (remove emoji icon)
            tool_name = None
            
            # First check in tool_tab_colors
            for name in self.tool_tab_colors.keys():
                if name in subtab_text:
                    tool_name = name
                    break
            
            # If not found, check default_tool_colors
            if not tool_name:
                for name in self.default_tool_colors.keys():
                    if name in subtab_text:
                        tool_name = name
                        break
            
            # If we found a matching tool with a custom color, use it
            custom_color = None
            if tool_name:
                if tool_name in self.tool_tab_colors:
                    custom_color = self.tool_tab_colors[tool_name]
                elif tool_name in self.default_tool_colors:
                    custom_color = self.default_tool_colors[tool_name]
            
            if custom_color:
                # Get the style
                style = ttk.Style()
                
                # Update the selected tab color to match the tool's primary color
                style.map('Custom.TNotebook.Tab',
                         background=[('selected', custom_color),
                                   ('active', '#d0d0d0' if not self.is_dark_mode else '#606060'),
                                   ('!active', '#e8e8e8' if not self.is_dark_mode else '#505050')],
                         foreground=[('selected', 'white'),
                                   ('active', self.get_colors()['fg']),
                                   ('!active', self.get_colors()['fg'])],
                         relief=[('selected', 'solid'),
                                ('active', 'raised'),
                                ('!active', 'raised')])
            else:
                # Use default color scheme
                colors = self.get_colors()
                style = ttk.Style()
                style.map('Custom.TNotebook.Tab',
                         background=[('selected', colors['primary']),
                                   ('active', '#d0d0d0' if not self.is_dark_mode else '#606060'),
                                   ('!active', '#e8e8e8' if not self.is_dark_mode else '#505050')],
                         foreground=[('selected', 'white'),
                                   ('active', colors['fg']),
                                   ('!active', colors['fg'])],
                         relief=[('selected', 'solid'),
                                ('active', 'raised'),
                                ('!active', 'raised')])
                
        except Exception as e:
            # Silently ignore errors to not break tab display
            pass

    def _force_render_recursive(self, widget, max_depth=10, current_depth=0):
        """Recursively force immediate rendering of all widgets"""
        try:
            if current_depth > max_depth:
                return
            
            # Force immediate update
            widget.update_idletasks()
            
            # Process all children immediately
            for child in widget.winfo_children():
                self._force_render_recursive(child, max_depth, current_depth + 1)
                
        except tk.TclError:
            # Widget was destroyed during recursion - this is fine
            pass
        except Exception as e:
            # Log unexpected errors but continue rendering
            if current_depth == 0:  # Only log at top level to avoid spam
                self.log_error("Error in recursive render", e)

    def pre_render_all_tabs(self):
        """Pre-render all tabs efficiently at startup"""
        try:
            # Get the currently selected tab
            current_tab = self.notebook.index(self.notebook.select())
            
            # Pre-render ALL tabs to eliminate blank screens
            num_tabs = self.notebook.index("end")
            
            for i in range(num_tabs):
                # Mark as loaded
                self.tab_loaded[i] = True
                
                # Get tab frame and render
                tab_id = self.notebook.tabs()[i]
                tab_frame = self.notebook.nametowidget(tab_id)
                self._force_render_recursive(tab_frame)
            
            # Also pre-render Client Setup subtabs if they exist and notebook is not None
            if hasattr(self, 'client_notebook') and self.client_notebook is not None:
                current_subtab = self.client_notebook.index(self.client_notebook.select())
                num_subtabs = self.client_notebook.index("end")
                
                for i in range(num_subtabs):
                    # Mark as loaded
                    self.subtab_loaded[i] = True
                    
                    # Get subtab frame and render
                    subtab_id = self.client_notebook.tabs()[i]
                    subtab_frame = self.client_notebook.nametowidget(subtab_id)
                    self._force_render_recursive(subtab_frame)
                
                # Return to original subtab
                self.client_notebook.select(current_subtab)
                
                # Update initial subtab color and tracking
                self.update_subtab_color(self.client_notebook, current_subtab)
                self.last_selected_subtab = current_subtab
            
            # Also pre-render File Tools subtabs if they exist and notebook is not None
            if hasattr(self, 'file_tools_notebook') and self.file_tools_notebook is not None:
                current_file_tools_subtab = self.file_tools_notebook.index(self.file_tools_notebook.select())
                num_file_tools_subtabs = self.file_tools_notebook.index("end")
                
                for i in range(num_file_tools_subtabs):
                    # Mark as loaded
                    self.file_tools_subtab_loaded[i] = True
                    
                    # Get subtab frame and render
                    subtab_id = self.file_tools_notebook.tabs()[i]
                    subtab_frame = self.file_tools_notebook.nametowidget(subtab_id)
                    self._force_render_recursive(subtab_frame)
                
                # Return to original subtab
                self.file_tools_notebook.select(current_file_tools_subtab)
                
                # Update initial subtab color and tracking
                self.update_subtab_color(self.file_tools_notebook, current_file_tools_subtab)
                self.last_selected_file_tools_subtab = current_file_tools_subtab
            
            # Also pre-render Admin subtabs if they exist and notebook is not None
            if hasattr(self, 'admin_notebook') and self.admin_notebook is not None:
                current_admin_subtab = self.admin_notebook.index(self.admin_notebook.select())
                num_admin_subtabs = self.admin_notebook.index("end")
                
                for i in range(num_admin_subtabs):
                    # Mark as loaded
                    self.admin_subtab_loaded[i] = True
                    
                    # Get subtab frame and render
                    subtab_id = self.admin_notebook.tabs()[i]
                    subtab_frame = self.admin_notebook.nametowidget(subtab_id)
                    self._force_render_recursive(subtab_frame)
                
                # Return to original subtab
                self.admin_notebook.select(current_admin_subtab)
                
                # Update initial subtab color and tracking
                self.update_subtab_color(self.admin_notebook, current_admin_subtab)
                self.last_selected_admin_subtab = current_admin_subtab
            
            # Return to the original tab
            self.notebook.select(current_tab)
            self.root.update_idletasks()
            
            # Update the initial tab color - THIS WAS MISSING!
            self.update_tab_color(current_tab)
            self.last_selected_tab = current_tab
            
            self.log_info("Pre-rendered all tabs successfully")
            
        except Exception as e:
            self.log_error("Error pre-rendering tabs", e)
    
    def _force_render_widgets(self, widget):
        """Recursively force render all widgets in a container"""
        try:
            widget.update_idletasks()
            for child in widget.winfo_children():
                self._force_render_widgets(child)
        except Exception:
            pass

    def create_options_tab_content(self, options_frame):
        """Create the content for the options tab"""
        # Ensure credentials are loaded when viewing Options (for DB/AWS settings)
        self.ensure_credentials_loaded()
        
        colors = self.get_colors()
        
        # Main container with canvas for scrolling
        main_container = tk.Frame(options_frame, bg=colors['bg'], relief='flat', bd=0)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_container, bg=colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=colors['bg'])
        
        # Configure canvas to scale with window
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_canvas_configure(event):
            # Make the scrollable frame match the canvas width
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Options content with enhanced styling
        content_frame = tk.Frame(scrollable_frame, bg=colors['bg'], padx=40, pady=40)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header section with dark blue background
        options_dark_blue = '#1e3a5f'  # Dark blue to match Options tab
        header_frame = tk.Frame(content_frame, bg=options_dark_blue, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        header_content = tk.Frame(header_frame, bg=options_dark_blue)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        # Title with icon
        title_icon = tk.Label(header_content, 
                            text="ℹ️", 
                            font=('Segoe UI', 20),
                            bg=options_dark_blue, 
                            fg='white')
        title_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        title = tk.Label(header_content, 
                        text="HelloToolbelt Options", 
                        font=('Segoe UI', 16, 'bold'),
                        fg='white',
                        bg=options_dark_blue)
        title.pack(side=tk.LEFT, anchor='w')
        
        # ============ THEME SECTION ============
        # Theme Settings section (full width now that tier is removed)
        options_dark_blue = '#1e3a5f'  # Dark blue to match Options tab
        theme_section = tk.Frame(content_frame, bg=options_dark_blue, relief='flat', bd=0)
        theme_section.pack(fill=tk.X, pady=(0, 30))
        
        theme_content = tk.Frame(theme_section, bg=options_dark_blue)
        theme_content.pack(fill=tk.X, padx=20, pady=20)
        
        theme_label = tk.Label(theme_content,
                            text="Theme Settings",
                            font=('Segoe UI', 14, 'bold'),
                            fg='white',
                            bg=options_dark_blue)
        theme_label.pack(anchor='w', pady=(0, 10))
        
        # Theme description
        theme_desc = tk.Label(theme_content,
                            text="Toggle between light and dark themes. Your preference will be remembered.",
                            font=('Segoe UI', 10),
                            fg='white',
                            bg=options_dark_blue,
                            wraplength=500)
        theme_desc.pack(anchor='w', pady=(0, 15))
        
        # Container for slider and labels
        slider_frame = tk.Frame(theme_content, bg=options_dark_blue)
        slider_frame.pack(anchor='w')
        
        # Light mode label
        light_label = tk.Label(slider_frame,
                            text="Light",
                            font=('Segoe UI', 10, 'bold'),
                            fg='white',
                            bg=options_dark_blue)
        light_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Theme slider with dark blue background
        slider = self.create_theme_slider(slider_frame, bg_color=options_dark_blue)
        slider.pack(side=tk.LEFT, padx=(0, 10))
        
        # Dark mode label
        dark_label = tk.Label(slider_frame,
                            text="Dark",
                            font=('Segoe UI', 10, 'bold'),
                            fg='white',
                            bg=options_dark_blue)
        dark_label.pack(side=tk.LEFT)
        
        # ============ CHANGE PASSWORD SECTION (only if auth is available) ============
        if self.auth:
            password_section = tk.Frame(content_frame, bg=colors['frame_bg'], relief='solid', bd=1)
            password_section.pack(fill=tk.X, pady=(0, 20))
            
            # Track if password section is expanded
            self.password_section_expanded = tk.BooleanVar(value=False)
            
            # Clickable header
            password_header = tk.Frame(password_section, bg=colors['header_bg'], cursor='hand2')
            password_header.pack(fill=tk.X)
            
            password_header_content = tk.Frame(password_header, bg=colors['header_bg'])
            password_header_content.pack(fill=tk.X, pady=15, padx=20)
            
            # Expand/collapse icon
            self.password_expand_icon = tk.Label(password_header_content, text="▶", 
                                           font=('Segoe UI', 12), bg=colors['header_bg'], fg=colors['fg'])
            self.password_expand_icon.pack(side=tk.LEFT, padx=(0, 10))
            
            password_label = tk.Label(password_header_content, text="🔐 Change Password", 
                               font=('Segoe UI', 14, 'bold'), bg=colors['header_bg'], fg=colors['fg'])
            password_label.pack(side=tk.LEFT, anchor='w')
            
            # Show logged in user
            user_label = tk.Label(password_header_content, text=f"(Logged in as: {self.auth.username})", 
                               font=('Segoe UI', 10), bg=colors['header_bg'], fg=colors['text_secondary'])
            user_label.pack(side=tk.RIGHT)
            
            # Password content (initially hidden)
            self.password_content_frame = tk.Frame(password_section, bg=colors['frame_bg'])
            
            password_info = tk.Label(self.password_content_frame, 
                                 text="Change your HelloToolbelt login password. Requirements: 8+ characters, one number, one special character.",
                                 font=('Segoe UI', 10), bg=colors['frame_bg'], fg=colors['text_secondary'], 
                                 wraplength=700, justify=tk.LEFT)
            password_info.pack(pady=(15, 15), padx=20, anchor='w')
            
            # Password form
            password_form = tk.Frame(self.password_content_frame, bg=colors['frame_bg'])
            password_form.pack(fill=tk.X, pady=(0, 10), padx=20)
            
            # Current password
            tk.Label(password_form, text="Current Password:", font=('Segoe UI', 10, 'bold'),
                    bg=colors['frame_bg'], fg=colors['fg']).grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
            self.current_password_var = tk.StringVar()
            current_pw_entry = tk.Entry(password_form, textvariable=self.current_password_var, 
                                       font=('Segoe UI', 10), width=30, show="●")
            current_pw_entry.grid(row=0, column=1, sticky="w", pady=(0, 10))
            
            # New password
            tk.Label(password_form, text="New Password:", font=('Segoe UI', 10, 'bold'),
                    bg=colors['frame_bg'], fg=colors['fg']).grid(row=1, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
            self.new_password_var = tk.StringVar()
            new_pw_entry = tk.Entry(password_form, textvariable=self.new_password_var, 
                                   font=('Segoe UI', 10), width=30, show="●")
            new_pw_entry.grid(row=1, column=1, sticky="w", pady=(0, 10))
            
            # Confirm new password
            tk.Label(password_form, text="Confirm New Password:", font=('Segoe UI', 10, 'bold'),
                    bg=colors['frame_bg'], fg=colors['fg']).grid(row=2, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
            self.confirm_password_var = tk.StringVar()
            confirm_pw_entry = tk.Entry(password_form, textvariable=self.confirm_password_var, 
                                       font=('Segoe UI', 10), width=30, show="●")
            confirm_pw_entry.grid(row=2, column=1, sticky="w", pady=(0, 10))
            
            # Status message
            self.password_status_var = tk.StringVar()
            self.password_status_label = tk.Label(password_form, textvariable=self.password_status_var,
                                                  font=('Segoe UI', 10), bg=colors['frame_bg'], fg=colors['fg'])
            self.password_status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 10))
            
            # Change password button
            change_pw_btn = tk.Button(password_form, text="Change Password", 
                                     font=('Segoe UI', 10, 'bold'),
                                     bg=colors['primary'], fg='#000000',
                                     command=self._change_password)
            change_pw_btn.grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 10))
            
            # Toggle function for password section
            def toggle_password_section(event=None):
                if self.password_section_expanded.get():
                    self.password_content_frame.pack_forget()
                    self.password_expand_icon.config(text="▶")
                    self.password_section_expanded.set(False)
                else:
                    self.password_content_frame.pack(fill=tk.X)
                    self.password_expand_icon.config(text="▼")
                    self.password_section_expanded.set(True)
            
            # Bind click to toggle
            password_header.bind("<Button-1>", toggle_password_section)
            password_header_content.bind("<Button-1>", toggle_password_section)
            password_label.bind("<Button-1>", toggle_password_section)
            self.password_expand_icon.bind("<Button-1>", toggle_password_section)
        
        # ============ DATABASE CONFIGURATION SECTION (COLLAPSIBLE) ============
        db_section = tk.Frame(content_frame, bg=colors['frame_bg'], relief='solid', bd=1)
        db_section.pack(fill=tk.X, pady=(0, 20))
        
        # Track if database section is expanded
        self.db_section_expanded = tk.BooleanVar(value=False)
        
        # Clickable header
        db_header = tk.Frame(db_section, bg=colors['header_bg'], cursor='hand2')
        db_header.pack(fill=tk.X)
        
        db_header_content = tk.Frame(db_header, bg=colors['header_bg'])
        db_header_content.pack(fill=tk.X, pady=15, padx=20)
        
        # Expand/collapse icon
        self.db_expand_icon = tk.Label(db_header_content, text="▶", 
                                       font=('Segoe UI', 12), bg=colors['header_bg'], fg=colors['fg'])
        self.db_expand_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        db_label = tk.Label(db_header_content, text="🗄️ PostgreSQL Database Configuration", 
                           font=('Segoe UI', 14, 'bold'), bg=colors['header_bg'], fg=colors['fg'])
        db_label.pack(side=tk.LEFT, anchor='w')
        
        # Database content (initially hidden)
        self.db_content_frame = tk.Frame(db_section, bg=colors['frame_bg'])
        
        info_label = tk.Label(self.db_content_frame, 
                             text="Configure database credentials for tools that need database access (like Bill Hunter).",
                             font=('Segoe UI', 10), bg=colors['frame_bg'], fg=colors['text_secondary'], 
                             wraplength=700, justify=tk.LEFT)
        info_label.pack(pady=(15, 15), padx=20, anchor='w')
        
        # Grid layout for database fields
        db_grid = tk.Frame(self.db_content_frame, bg=colors['frame_bg'])
        db_grid.pack(fill=tk.X, pady=(0, 10), padx=20)
        
        # Row 0: Host and Port
        tk.Label(db_grid, text="Host:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        host_entry = tk.Entry(db_grid, textvariable=self.db_host, font=('Segoe UI', 10), width=40)
        host_entry.grid(row=0, column=1, sticky="ew", padx=(0, 20), pady=(0, 10))
        
        tk.Label(db_grid, text="Port:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=0, column=2, sticky="w", pady=(0, 10), padx=(0, 10))
        port_entry = tk.Entry(db_grid, textvariable=self.db_port, font=('Segoe UI', 10), width=15)
        port_entry.grid(row=0, column=3, sticky="ew", pady=(0, 10))
        
        # Row 1: Database Name
        tk.Label(db_grid, text="Database:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=1, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        db_entry = tk.Entry(db_grid, textvariable=self.db_name, font=('Segoe UI', 10), width=40)
        db_entry.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Row 2: Username and Password
        tk.Label(db_grid, text="Username:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=2, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        user_entry = tk.Entry(db_grid, textvariable=self.db_user, font=('Segoe UI', 10), width=40)
        user_entry.grid(row=2, column=1, sticky="ew", padx=(0, 20), pady=(0, 10))
        
        tk.Label(db_grid, text="Password:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=2, column=2, sticky="w", pady=(0, 10), padx=(0, 10))
        password_entry = tk.Entry(db_grid, textvariable=self.db_password, font=('Segoe UI', 10), 
                                 width=25, show="*")
        password_entry.grid(row=2, column=3, sticky="ew", pady=(0, 10))
        
        db_grid.columnconfigure(1, weight=2)
        db_grid.columnconfigure(3, weight=1)
        
        # Button frame for Save and Test buttons
        button_frame = tk.Frame(self.db_content_frame, bg=colors['frame_bg'])
        button_frame.pack(pady=(5, 20), padx=20)
        
        # Save button
        save_btn = tk.Button(button_frame, text="💾 Save Configuration", 
                            command=self.save_db_config, bg=colors['success'], fg='black',
                            font=('Segoe UI', 10, 'bold'), padx=20, pady=8, relief='flat', bd=0, cursor="hand2")
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Test Connection button
        test_btn = tk.Button(button_frame, text="🔌 Test Connection", 
                            command=self.test_db_connection, bg=colors['primary'], fg='black',
                            font=('Segoe UI', 10, 'bold'), padx=20, pady=8, relief='flat', bd=0, cursor="hand2")
        test_btn.pack(side=tk.LEFT)
        
        # Bind click events to header for expand/collapse
        def toggle_db_section(event=None):
            if self.db_section_expanded.get():
                # Collapse
                self.db_content_frame.pack_forget()
                self.db_expand_icon.config(text="▶")
                self.db_section_expanded.set(False)
            else:
                # Expand
                self.db_content_frame.pack(fill=tk.X, after=db_header)
                self.db_expand_icon.config(text="▼")
                self.db_section_expanded.set(True)
        
        db_header.bind("<Button-1>", toggle_db_section)
        db_header_content.bind("<Button-1>", toggle_db_section)
        self.db_expand_icon.bind("<Button-1>", toggle_db_section)
        db_label.bind("<Button-1>", toggle_db_section)
        
        # ============ AWS CREDENTIALS SECTION (COLLAPSIBLE) ============
        aws_section = tk.Frame(content_frame, bg=colors['frame_bg'], relief='solid', bd=1)
        aws_section.pack(fill=tk.X, pady=(0, 20))
        
        # Track if AWS section is expanded
        self.aws_section_expanded = tk.BooleanVar(value=False)
        
        # Clickable header
        aws_header = tk.Frame(aws_section, bg=colors['header_bg'], cursor='hand2')
        aws_header.pack(fill=tk.X)
        
        aws_header_content = tk.Frame(aws_header, bg=colors['header_bg'])
        aws_header_content.pack(fill=tk.X, pady=15, padx=20)
        
        # Expand/collapse icon
        self.aws_expand_icon = tk.Label(aws_header_content, text="▶", 
                                        font=('Segoe UI', 12), bg=colors['header_bg'], fg=colors['fg'])
        self.aws_expand_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        aws_label = tk.Label(aws_header_content, text="☁️ AWS Credentials Configuration", 
                           font=('Segoe UI', 14, 'bold'), bg=colors['header_bg'], fg=colors['fg'])
        aws_label.pack(side=tk.LEFT, anchor='w')
        
        # AWS content (initially hidden)
        self.aws_content_frame = tk.Frame(aws_section, bg=colors['frame_bg'])
        
        aws_info = tk.Label(self.aws_content_frame, 
                           text="Configure AWS credentials for S3 access and other AWS services.",
                           font=('Segoe UI', 10), bg=colors['frame_bg'], fg=colors['text_secondary'], 
                           wraplength=700, justify=tk.LEFT)
        aws_info.pack(pady=(15, 15), padx=20, anchor='w')
        
        # AWS grid
        aws_grid = tk.Frame(self.aws_content_frame, bg=colors['frame_bg'])
        aws_grid.pack(fill=tk.X, pady=(0, 10), padx=20)
        
        tk.Label(aws_grid, text="Access Key ID:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        aws_access_entry = tk.Entry(aws_grid, textvariable=self.aws_access_key, font=('Segoe UI', 10), width=50)
        aws_access_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10))
        
        tk.Label(aws_grid, text="Secret Access Key:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=1, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        aws_secret_entry = tk.Entry(aws_grid, textvariable=self.aws_secret_key, font=('Segoe UI', 10), 
                                    width=50, show="*")
        aws_secret_entry.grid(row=1, column=1, sticky="ew", pady=(0, 10))
        
        tk.Label(aws_grid, text="Region:", font=('Segoe UI', 10, 'bold'),
                bg=colors['frame_bg'], fg=colors['fg']).grid(row=2, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        aws_region_entry = tk.Entry(aws_grid, textvariable=self.aws_region, font=('Segoe UI', 10), width=50)
        aws_region_entry.grid(row=2, column=1, sticky="ew", pady=(0, 10))
        
        aws_grid.columnconfigure(1, weight=1)
        
        # AWS buttons
        aws_button_frame = tk.Frame(self.aws_content_frame, bg=colors['frame_bg'])
        aws_button_frame.pack(pady=(10, 0), padx=20)
        
        save_aws_btn = tk.Button(aws_button_frame, text="💾 Save AWS Credentials", 
                                command=self.save_aws_credentials, bg=colors['success'], fg='black',
                                font=('Segoe UI', 10, 'bold'), padx=20, pady=8, relief='flat', bd=0, cursor="hand2")
        save_aws_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_aws_btn = tk.Button(aws_button_frame, text="🗑️ Clear Credentials", 
                                 command=self.clear_aws_credentials, bg=colors['danger'], fg='black',
                                 font=('Segoe UI', 10, 'bold'), padx=20, pady=8, relief='flat', bd=0, cursor="hand2")
        clear_aws_btn.pack(side=tk.LEFT)
        
        # Keyring status
        keyring_status_text = "✅ Credentials stored securely in system keychain" if self.keyring_available else "⚠️ Install 'keyring' package for secure credential storage"
        keyring_status_color = colors['success'] if self.keyring_available else colors['warning']
        
        keyring_status = tk.Label(self.aws_content_frame, text=keyring_status_text,
                                 font=('Segoe UI', 9), bg=colors['frame_bg'], fg=keyring_status_color,
                                 wraplength=700, justify=tk.LEFT)
        keyring_status.pack(pady=(10, 20), padx=20, anchor='w')
        
        # Bind click events to header for expand/collapse
        def toggle_aws_section(event=None):
            if self.aws_section_expanded.get():
                # Collapse
                self.aws_content_frame.pack_forget()
                self.aws_expand_icon.config(text="▶")
                self.aws_section_expanded.set(False)
            else:
                # Expand
                self.aws_content_frame.pack(fill=tk.X, after=aws_header)
                self.aws_expand_icon.config(text="▼")
                self.aws_section_expanded.set(True)
        
        aws_header.bind("<Button-1>", toggle_aws_section)
        aws_header_content.bind("<Button-1>", toggle_aws_section)
        self.aws_expand_icon.bind("<Button-1>", toggle_aws_section)
        aws_label.bind("<Button-1>", toggle_aws_section)
        
        # Creator section at bottom
        creator_section = tk.Frame(content_frame, bg=colors['secondary_bg'], relief='solid', bd=1)
        creator_section.pack(fill=tk.X, pady=(30, 0))
        
        creator_content = tk.Frame(creator_section, bg=colors['secondary_bg'])
        creator_content.pack(fill=tk.X, padx=20, pady=20)
        
        creator_label = tk.Label(creator_content,
                            text="Created and Maintained by Tier 3 Support",
                            font=('Segoe UI', 14, 'bold'),
                            fg=colors['fg'],
                            bg=colors['secondary_bg'])
        creator_label.pack(anchor='w')
        
        bug_text = "Please reach out to Cody White if you find bugs or have ideas on additional features."
        
        bug_info = tk.Label(creator_content,
                        text=bug_text,
                        font=('Segoe UI', 10),
                        fg=colors['text_secondary'],
                        bg=colors['secondary_bg'],
                        justify=tk.LEFT,
                        wraplength=600)
        bug_info.pack(anchor='w', pady=(5, 0))
        
        # Version section at bottom
        version_section = tk.Frame(content_frame, bg=colors['tertiary_bg'], relief='solid', bd=1, cursor='hand2')
        version_section.pack(fill=tk.X, pady=(15, 0))
        
        version_content = tk.Frame(version_section, bg=colors['tertiary_bg'], cursor='hand2')
        version_content.pack(fill=tk.X, padx=20, pady=15)
        
        version_label = tk.Label(version_content,
                            text=f"Version {self.version}",
                            font=('Segoe UI', 12, 'bold'),
                            fg=colors['fg'],
                            bg=colors['tertiary_bg'],
                            cursor='hand2')
        version_label.pack(anchor='w')
        
        version_info = tk.Label(version_content,
                            text="For release notes click me!",
                            font=('Segoe UI', 9),
                            fg=colors['text_secondary'],
                            bg=colors['tertiary_bg'],
                            cursor='hand2')
        version_info.pack(anchor='w', pady=(2, 0))
        
        # Make entire version section clickable to show welcome popup
        def on_version_click(event):
            # Only show welcome popup when manually clicked, not during theme changes
            if not getattr(self, '_theme_changing', False):
                self.show_welcome_popup()
        
        def on_version_enter(event):
            if not getattr(self, '_theme_changing', False):
                version_section.config(bg=colors['primary'])
                version_content.config(bg=colors['primary'])
                version_label.config(bg=colors['primary'], fg='white')
                version_info.config(bg=colors['primary'], fg='white')
        
        def on_version_leave(event):
            if not getattr(self, '_theme_changing', False):
                version_section.config(bg=colors['tertiary_bg'])
                version_content.config(bg=colors['tertiary_bg'])
                version_label.config(bg=colors['tertiary_bg'], fg=colors['fg'])
                version_info.config(bg=colors['tertiary_bg'], fg=colors['text_secondary'])
        
        # Bind events to all components of the version section
        for widget in [version_section, version_content, version_label, version_info]:
            widget.bind("<Button-1>", on_version_click)
            widget.bind("<Enter>", on_version_enter)
            widget.bind("<Leave>", on_version_leave)
        
        # Pack content frame directly - no scrolling needed
        content_frame.pack(fill=tk.BOTH, expand=True)

    # Add remaining methods that were in the original but need to be included
    def safe_tool_cleanup(self, tool_name):
        """Safely cleanup tool resources"""
        with self._tool_cleanup_lock:
            if tool_name in self.loaded_tools:
                try:
                    tool_instance = self.loaded_tools[tool_name]
                    
                    # Call cleanup method if it exists
                    if hasattr(tool_instance, 'cleanup'):
                        tool_instance.cleanup()
                    
                    # Destroy widget tree
                    if hasattr(tool_instance, 'root'):
                        try:
                            tool_instance.root.destroy()
                        except Exception:
                            pass  # Widget may already be destroyed
                    
                    # Remove from loaded tools
                    del self.loaded_tools[tool_name]
                    self.log_info(f"Cleaned up tool: {tool_name}")
                    
                except Exception as e:
                    self.log_error(f"Error cleaning up tool {tool_name}", e)

    def _change_password(self):
        """Handle password change request"""
        if not self.auth:
            return
        
        current_pw = self.current_password_var.get()
        new_pw = self.new_password_var.get()
        confirm_pw = self.confirm_password_var.get()
        
        # Clear previous status
        self.password_status_var.set("")
        
        # Validation
        if not current_pw:
            self.password_status_var.set("Please enter your current password")
            self.password_status_label.config(fg='#ff6b6b')
            return
        
        if not new_pw:
            self.password_status_var.set("Please enter a new password")
            self.password_status_label.config(fg='#ff6b6b')
            return
        
        # Validate password strength
        if len(new_pw) < 8:
            self.password_status_var.set("Password must be at least 8 characters")
            self.password_status_label.config(fg='#ff6b6b')
            return
        
        if not any(c.isdigit() for c in new_pw):
            self.password_status_var.set("Password must contain at least one number")
            self.password_status_label.config(fg='#ff6b6b')
            return
        
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        if not any(c in special_chars for c in new_pw):
            self.password_status_var.set("Password must contain a special character (!@#$%^&* etc)")
            self.password_status_label.config(fg='#ff6b6b')
            return
        
        if new_pw != confirm_pw:
            self.password_status_var.set("New passwords do not match")
            self.password_status_label.config(fg='#ff6b6b')
            return
        
        # Show progress
        self.password_status_var.set("Changing password...")
        self.password_status_label.config(fg=self.get_colors()['fg'])
        self.root.update()
        
        # Make the request in a thread
        def do_change():
            success, message = self.auth.change_password(current_pw, new_pw)
            
            # Update UI in main thread
            self.root.after(0, lambda: self._handle_password_change_result(success, message))
        
        import threading
        threading.Thread(target=do_change, daemon=True).start()
    
    def _handle_password_change_result(self, success, message):
        """Handle the result of password change"""
        if success:
            self.password_status_var.set("✓ Password changed successfully!")
            self.password_status_label.config(fg='#4ade80')  # Green
            # Clear the fields
            self.current_password_var.set("")
            self.new_password_var.set("")
            self.confirm_password_var.set("")
            # Log the action
            if self.auth:
                self.auth.log_action("PASSWORD_CHANGED")
        else:
            self.password_status_var.set(f"✗ {message}")
            self.password_status_label.config(fg='#ff6b6b')  # Red

    def on_closing(self):
        """Enhanced cleanup on application close"""
        try:
            self.log_info("Application closing - starting cleanup")
            self._destroyed = True
            
            # Logout from auth server if authenticated
            if hasattr(self, 'auth') and self.auth:
                try:
                    self.auth.log_action("LOGOUT")
                    self.auth.logout()
                    self.log_info("Logged out from auth server")
                except Exception as e:
                    self.log_error("Error logging out from auth server", e)
            
            self.save_settings()
            
            # Clean up all tools
            tool_names = list(self.loaded_tools.keys())
            for tool_name in tool_names:
                self.safe_tool_cleanup(tool_name)
            
            self.root.quit()
            self.root.destroy()
            self.log_info("Application cleanup completed")
            
        except Exception as e:
            self.log_error("Error during application cleanup", e)
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass

    def center_window(self):
        """Center the main window on screen"""
        try:
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (width // 2)
            y = (self.root.winfo_screenheight() // 2) - (height // 2)
            self.root.geometry(f'{width}x{height}+{x}+{y}')
        except Exception as e:
            self.log_error("Error centering window", e)

    def load_tool_module_safe(self, file_path):
        """Safely load a Python module with timeout and error handling"""
        try:
            pass
            if not os.path.exists(file_path):
                self.log_error(f"Tool file does not exist: {file_path}")
                return None
            
            # Check file size (prevent loading extremely large files)
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                self.log_error(f"Tool file too large: {file_path} ({file_size} bytes)")
                return None
            
            spec = importlib.util.spec_from_file_location("tool_module", file_path)
            if not spec or not spec.loader:
                self.log_error(f"Could not create module spec for: {file_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            
            # Execute module loading
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            self.log_error(f"Error loading module {file_path}", e)
            return None

    def load_tool_in_tab(self, parent_frame, tool_config):
        """Enhanced tool loading with comprehensive error handling"""
        tool_name = tool_config['name']
        
        # Prevent concurrent loading of the same tool
        if tool_name in self._loading_tools:
            self.log_info(f"Tool {tool_name} is already being loaded")
            return False
        
        self._loading_tools.add(tool_name)
        
        try:
            colors = self.get_colors()
            
            # Get the script file path with multiple fallback locations
            script_paths = [
                tool_config['file'],
                os.path.join(os.path.dirname(os.path.abspath(__file__)), tool_config['file']),
                os.path.join(os.getcwd(), tool_config['file'])
            ]
            
            script_path = None
            for path in script_paths:
                if os.path.exists(path):
                    script_path = path
                    break
            
            if not script_path:
                self.log_error(f"Tool script not found in any location: {script_paths}")
                self._loading_tools.discard(tool_name)
                return False
            
            # Load the module with timeout protection
            module = self.load_tool_module_safe(script_path)
            if not module:
                self._loading_tools.discard(tool_name)
                return False
            
            # Get the class with validation
            tool_class = getattr(module, tool_config['class'], None)
            if not tool_class:
                self.log_error(f"Class {tool_config['class']} not found in {tool_config['file']}")
                self._loading_tools.discard(tool_name)
                return False
            
            # Enhanced MockRoot with better compatibility
            class EnhancedMockRoot(tk.Frame):
                def __init__(self, parent, hellotoolbelt_instance):
                    super().__init__(parent, bg=colors['bg'], relief='flat', bd=0)
                    self.pack(fill=tk.BOTH, expand=True)
                    self._title = ""
                    self._current_bg = colors['bg']
                    self._current_fg = colors['fg']
                    self._destroyed = False
                    
                    # Store reference to HelloToolbelt instance for tools to access
                    self._hellotoolbelt = hellotoolbelt_instance
                    
                    # Ensure credentials are loaded from keyring when tool is instantiated
                    hellotoolbelt_instance.ensure_credentials_loaded()
                    
                    # Also expose shared credentials directly on root for compatibility
                    self.db_host = hellotoolbelt_instance.db_host
                    self.db_port = hellotoolbelt_instance.db_port
                    self.db_name = hellotoolbelt_instance.db_name
                    self.db_user = hellotoolbelt_instance.db_user
                    self.db_password = hellotoolbelt_instance.db_password
                    self.aws_access_key = hellotoolbelt_instance.aws_access_key
                    self.aws_secret_key = hellotoolbelt_instance.aws_secret_key
                    self.aws_region = hellotoolbelt_instance.aws_region
                    self.keyring_available = hellotoolbelt_instance.keyring_available
                    # Pass access tier information to tools
                    self.current_tier = hellotoolbelt_instance.current_tier
                    self.tier3_unlocked = hellotoolbelt_instance.tier3_unlocked
                    # Pass auth for audit logging
                    self.auth = hellotoolbelt_instance.auth
                
                def log_file_access(self, filename, action="OPENED_FILE"):
                    """Log file access to audit trail. Tools can call this method."""
                    if self._hellotoolbelt.auth:
                        # Get just the filename, not the full path for privacy
                        import os
                        basename = os.path.basename(filename) if filename else "unknown"
                        self._hellotoolbelt.auth.log_action(action, basename)
                
                def log_action(self, action, target=None):
                    """Log any action to audit trail. Tools can call this method."""
                    if self._hellotoolbelt.auth:
                        self._hellotoolbelt.auth.log_action(action, target)
                    
                def title(self, text=None):
                    if text is not None:
                        self._title = text
                    return self._title
                
                def minsize(self, width=None, height=None):
                    pass
                
                def geometry(self, geometry=None):
                    pass
                
                def protocol(self, protocol, callback):
                    pass
                
                def mainloop(self):
                    pass
                
                def quit(self):
                    pass
                
                def destroy(self):
                    if not self._destroyed:
                        self._destroyed = True
                        try:
                            super().destroy()
                        except Exception:
                            pass
                
                def configure(self, **kwargs):
                    if 'bg' in kwargs:
                        self._current_bg = kwargs['bg']
                    try:
                        super().configure(**kwargs)
                    except Exception:
                        pass
                
                def cget(self, key):
                    if key == 'bg':
                        return getattr(self, '_current_bg', colors['bg'])
                    elif key == 'fg':
                        return getattr(self, '_current_fg', colors['fg'])
                    try:
                        return super().cget(key)
                    except Exception:
                        return None
                
                def winfo_rgb(self, color):
                    try:
                        return parent_frame.winfo_rgb(color)
                    except Exception:
                        return (0, 0, 0)
            
            # Create the mock root for the tool
            tool_root = EnhancedMockRoot(parent_frame, self)
            
            # Instantiate the tool with error handling
            try:
                pass
                tool_instance = tool_class(tool_root)
            except Exception as e:
                self.log_error(f"Error instantiating tool {tool_name}", e)
                tool_root.destroy()
                self._loading_tools.discard(tool_name)
                return False
            
            # Configure tool for dark mode if supported
            if hasattr(tool_instance, 'is_dark_mode'):
                tool_instance.is_dark_mode = self.is_dark_mode
            
            # Force immediate and complete rendering of tool interface
            # Wrap in try/except to prevent hangs
            try:
                tool_root.update_idletasks()
            except Exception as e:
                pass
            
            try:
                parent_frame.update_idletasks()
            except Exception as e:
                pass
            
            # Skip the update() calls as they can cause event loop issues
            # tool_root.update()
            # parent_frame.update()
            
            # Recursively update all child widgets
            self._force_render_recursive(tool_root)
            
            # Store reference to the tool
            self.loaded_tools[tool_name] = tool_instance
            
            # Capture tool's primary color if available for dynamic tab styling
            if hasattr(tool_instance, 'primary_color'):
                self.tool_tab_colors[tool_name] = tool_instance.primary_color
            elif tool_name in self.default_tool_colors:
                # Use hardcoded default color if tool doesn't provide one
                self.tool_tab_colors[tool_name] = self.default_tool_colors[tool_name]
            
            self.log_info(f"Successfully loaded tool: {tool_name}")
            
            return True
            
        except Exception as e:
            self.log_error(f"Critical error loading {tool_name}", e)
            return False
        finally:
            # Always remove from loading set
            self._loading_tools.discard(tool_name)

    def create_error_tab(self, parent_frame, tool_config):
        """Create an enhanced error tab when a tool fails to load"""
        colors = self.get_colors()
        
        error_frame = tk.Frame(parent_frame, bg=colors['bg'], relief='flat', bd=0)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Error icon and title frame
        title_frame = tk.Frame(error_frame, bg=colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Error icon
        icon_label = tk.Label(title_frame, 
                             text="⚠", 
                             font=('Segoe UI', 24),
                             bg=colors['bg'],
                             fg=colors['danger'])
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Error title
        title_label = tk.Label(title_frame, 
                              text=f"Failed to Load: {tool_config['name']}", 
                              font=('Segoe UI', 16, 'bold'),
                              fg=colors['danger'],
                              bg=colors['bg'])
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Error details frame with subtle border
        details_frame = tk.Frame(error_frame, bg=colors['frame_bg'], relief='solid', bd=1)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Error message
        error_msg = f"""Unable to load the tool from: {tool_config['file']}

Possible reasons:
• File not found in the current directory
• Python import error in the script
• Missing dependencies
• Class name mismatch (looking for: {tool_config['class']})

Tool Description:
{tool_config['description']}

To fix this:
1. Ensure {tool_config['file']} is in the same directory as this launcher
2. Check that the script runs independently without errors
3. Verify the class name matches: {tool_config['class']}"""
        
        error_text = tk.Text(details_frame, 
                           wrap=tk.WORD, 
                           bg=colors['frame_bg'],
                           fg=colors['fg'],
                           relief='flat',
                           bd=0,
                           font=('Segoe UI', 10),
                           selectbackground=colors['primary'],
                           selectforeground='white',
                           padx=20,
                           pady=20)
        error_text.pack(fill=tk.BOTH, expand=True)
        error_text.insert('1.0', error_msg.strip())
        error_text.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = tk.Frame(error_frame, bg=colors['bg'])
        button_frame.pack(fill=tk.X)
        
        # Retry button with modern styling
        retry_btn = tk.Button(button_frame, 
                            text="🔄 Retry Loading", 
                            command=lambda: self.retry_load_tool(parent_frame, tool_config),
                            bg=colors['primary'],
                            fg='white',
                            font=('Segoe UI', 11, 'bold'),
                            relief='flat',
                            bd=0,
                            padx=20,
                            pady=10,
                            cursor='hand2')
        retry_btn.pack(side=tk.RIGHT)

    def retry_load_tool(self, parent_frame, tool_config):
        """Retry loading a failed tool"""
        # Clear the current tab content
        for widget in parent_frame.winfo_children():
            try:
                widget.destroy()
            except Exception as e:
                self.log_error(f"Error destroying widget during retry", e)
        
        # Try loading again
        success = self.load_tool_in_tab(parent_frame, tool_config)
        
        if not success:
            # Still failed, recreate error tab
            self.create_error_tab(parent_frame, tool_config)

    def create_admin_tab(self):
        """Create the admin tab with subtabs for user management and audit logs (only for admin users)"""
        # Check if we have the new subtab modules
        has_subtabs = USER_MANAGEMENT_AVAILABLE or USER_AUDIT_AVAILABLE
        
        if has_subtabs:
            # Create admin tab with subtabs
            admin_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
            self.notebook.add(admin_frame, text="👥 Admin")
            
            # Create a notebook for admin subtabs
            self.admin_notebook = ttk.Notebook(admin_frame, style='Custom.TNotebook')
            self.admin_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Bind tab change event for admin subtabs
            self.admin_notebook.bind('<<NotebookTabChanged>>', self.on_admin_subtab_changed)
            
            # Add User Management subtab
            if USER_MANAGEMENT_AVAILABLE:
                try:
                    pass
                    user_mgmt_frame = ttk.Frame(self.admin_notebook, style='Tool.TFrame')
                    self.admin_notebook.add(user_mgmt_frame, text="👥 User Management")
                    
                    # Create container frame
                    colors = self.get_colors()
                    container_frame = tk.Frame(user_mgmt_frame, bg=colors['bg'], relief='flat', bd=0)
                    container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    
                    # Create the user management panel
                    self.user_management_panel = UserManagementPanel(container_frame, self.auth, self.get_colors)
                    
                except Exception as e:
                    self.log_error("Error creating user management panel", e)
                    error_label = tk.Label(
                        container_frame,
                        text=f"Error loading user management:\n{str(e)}",
                        fg="#ff6b6b",
                        bg=colors['bg'],
                        font=("Arial", 12)
                    )
                    error_label.pack(expand=True)
            
            # Add Audit Logs subtab
            if USER_AUDIT_AVAILABLE:
                try:
                    pass
                    audit_frame = ttk.Frame(self.admin_notebook, style='Tool.TFrame')
                    self.admin_notebook.add(audit_frame, text="📋 Audit Logs")
                    
                    # Create container frame
                    colors = self.get_colors()
                    container_frame = tk.Frame(audit_frame, bg=colors['bg'], relief='flat', bd=0)
                    container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    
                    # Create the audit logs panel
                    self.audit_logs_panel = AuditLogsPanel(container_frame, self.auth, self.get_colors)
                    
                except Exception as e:
                    self.log_error("Error creating audit logs panel", e)
                    error_label = tk.Label(
                        container_frame,
                        text=f"Error loading audit logs:\n{str(e)}",
                        fg="#ff6b6b",
                        bg=colors['bg'],
                        font=("Arial", 12)
                    )
                    error_label.pack(expand=True)
            
            # Register Admin tab color (use gold for admin)
            self.tool_tab_colors['Admin'] = '#d4a017'
            
            # Register subtab colors so they match the admin theme
            self.tool_tab_colors['User Management'] = '#d4a017'
            self.tool_tab_colors['Audit Logs'] = '#d4a017'
            
        elif ADMIN_TAB_AVAILABLE:
            # Fallback to old single admin tab if subtab modules not available
            admin_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
            self.notebook.add(admin_frame, text="👥 Admin")
            
            # Create the admin panel inside the frame
            try:
                self.admin_panel = AdminTabPanel(admin_frame, self.auth, self.get_colors)
                
                # Register Admin tab color from the panel
                if hasattr(self.admin_panel, 'tab_color'):
                    self.tool_tab_colors['Admin'] = self.admin_panel.tab_color
                elif hasattr(self.admin_panel, 'primary_color'):
                    self.tool_tab_colors['Admin'] = self.admin_panel.primary_color
                elif 'Admin' in self.default_tool_colors:
                    self.tool_tab_colors['Admin'] = self.default_tool_colors['Admin']
                    
            except Exception as e:
                self.log_error("Error creating admin panel", e)
                # Show error message in the tab
                colors = self.get_colors()
                error_label = tk.Label(
                    admin_frame,
                    text=f"Error loading admin panel:\n{str(e)}",
                    fg="#ff6b6b",
                    bg=colors['bg'],
                    font=("Arial", 12)
                )
                error_label.pack(expand=True)

    def create_options_tab(self):
        """Create an enhanced options/help tab"""
        options_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
        self.notebook.add(options_frame, text="ℹ️ Options")
        
        # Register Options tab color
        self.tool_tab_colors['Options'] = self.default_tool_colors.get('Options', '#1e3a5f')
        
        self.create_options_tab_content(options_frame)

    def move_options_tab_to_end(self):
        """Move the Options tab to the rightmost position"""
        try:
            # Find the options tab
            options_tab_index = None
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Options" in tab_text:
                    options_tab_index = i
                    break
            
            if options_tab_index is not None:
                # Get the tab frame
                options_tab = self.notebook.nametowidget(self.notebook.tabs()[options_tab_index])
                tab_text = self.notebook.tab(options_tab_index, "text")
                
                # Remove the tab from its current position
                self.notebook.forget(options_tab_index)
                
                # Add it back at the end
                self.notebook.add(options_tab, text=tab_text)
        except Exception as e:
            self.log_error("Error moving options tab", e)

    def refresh_options_tab(self):
        """Refresh the options tab styling"""
        try:
            self._theme_changing = True
            
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Options" in tab_text:
                    tab_frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                    for widget in tab_frame.winfo_children():
                        try:
                            widget.destroy()
                        except Exception:
                            pass
                    self.create_options_tab_content(tab_frame)
                    break
        except Exception as e:
            self.log_error("Error refreshing options tab", e)
        finally:
            def reset_flag():
                time.sleep(0.5)
                self._theme_changing = False
            
            threading.Thread(target=reset_flag, daemon=True).start()

    def toggle_dark_mode(self):
        """Toggle between light and dark mode"""
        self.is_dark_mode = not self.is_dark_mode
        
        # Save settings immediately
        self.save_settings()
        
        # Update styles
        self.setup_styles()
        
        # Update root background
        colors = self.get_colors()
        self.root.configure(bg=colors['bg'])
        
        # Refresh all tabs
        self.refresh_all_tabs()
        
        # Refresh admin panel(s) if they exist
        if hasattr(self, 'admin_panel') and self.admin_panel is not None:
            try:
                if hasattr(self.admin_panel, 'refresh_styling'):
                    self.admin_panel.refresh_styling(self.is_dark_mode)
            except Exception as e:
                self.log_error("Error refreshing admin panel", e)
        
        # Refresh user management panel if it exists
        if hasattr(self, 'user_management_panel') and self.user_management_panel is not None:
            try:
                if hasattr(self.user_management_panel, 'refresh_styling'):
                    self.user_management_panel.refresh_styling(self.is_dark_mode)
            except Exception as e:
                self.log_error("Error refreshing user management panel", e)
        
        # Refresh audit logs panel if it exists
        if hasattr(self, 'audit_logs_panel') and self.audit_logs_panel is not None:
            try:
                if hasattr(self.audit_logs_panel, 'refresh_styling'):
                    self.audit_logs_panel.refresh_styling(self.is_dark_mode)
            except Exception as e:
                self.log_error("Error refreshing audit logs panel", e)
        
        # Update options tab specifically (but don't trigger welcome popup)
        self.refresh_options_tab()

    def refresh_all_tabs(self):
        """Enhanced tab refreshing with proper error handling"""
        colors = self.get_colors()
        
        failed_tools = []
        
        for tool_name, tool_instance in self.loaded_tools.items():
            try:
                # Update the MockRoot colors first
                if hasattr(tool_instance, 'root'):
                    try:
                        tool_instance.root.configure(bg=colors['bg'])
                        tool_instance.root._current_bg = colors['bg']
                        tool_instance.root._current_fg = colors['fg']
                    except Exception as e:
                        self.log_error(f"Error updating root colors for {tool_name}", e)
                
                # Check if the tool has a method to refresh its styling
                if hasattr(tool_instance, 'refresh_styling'):
                    try:
                        tool_instance.refresh_styling(self.is_dark_mode)
                    except Exception as e:
                        self.log_error(f"Error refreshing styling for {tool_name}", e)
                        failed_tools.append(tool_name)
                        
                elif hasattr(tool_instance, 'setup_adaptive_styling'):
                    try:
                        tool_instance.is_dark_mode = self.is_dark_mode
                        tool_instance.setup_adaptive_styling()
                        
                        # Try to refresh the interface if possible
                        if hasattr(tool_instance, '_create_main_interface'):
                            # Clear and recreate the interface safely
                            for widget in tool_instance.root.winfo_children():
                                try:
                                    widget.destroy()
                                except Exception:
                                    pass
                            tool_instance._create_main_interface()
                    except Exception as e:
                        self.log_error(f"Error with adaptive styling for {tool_name}", e)
                        failed_tools.append(tool_name)
                        
            except Exception as e:
                self.log_error(f"Critical error refreshing tool {tool_name}", e)
                failed_tools.append(tool_name)
        
        # Clean up failed tools
        for tool_name in failed_tools:
            self.safe_tool_cleanup(tool_name)
            self.log_info(f"Removed failed tool: {tool_name}")

    def create_theme_slider(self, parent, bg_color=None):
        """Create a simplified custom theme slider widget"""
        colors = self.get_colors()
        
        # Use provided bg_color or fall back to primary color
        slider_bg = bg_color if bg_color else colors['primary']
        
        # Container frame for the slider
        slider_container = tk.Frame(parent, bg=slider_bg, width=60, height=30)
        slider_container.pack_propagate(False)
        
        # Create canvas for custom slider
        canvas = tk.Canvas(slider_container, 
                          width=60, 
                          height=30, 
                          bg=slider_bg,
                          highlightthickness=0,
                          relief='flat')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Slider track
        track_y = 15
        track_start = 8
        track_end = 52
        track_height = 14
        
        # Draw rounded track background
        canvas.create_oval(track_start, track_y - track_height//2,
                          track_start + track_height, track_y + track_height//2,
                          fill=colors['slider_bg'], outline="")
        canvas.create_rectangle(track_start + track_height//2, track_y - track_height//2,
                               track_end - track_height//2, track_y + track_height//2,
                               fill=colors['slider_bg'], outline="")
        canvas.create_oval(track_end - track_height, track_y - track_height//2,
                          track_end, track_y + track_height//2,
                          fill=colors['slider_bg'], outline="")
        
        # Slider thumb
        thumb_radius = 10
        thumb_x = track_end - thumb_radius if self.is_dark_mode else track_start + thumb_radius
        
        # Create thumb with shadow effect
        # Shadow (using a darker solid color instead of transparency)
        shadow_color = '#d0d0d0' if not self.is_dark_mode else '#1a1a1a'
        canvas.create_oval(thumb_x - thumb_radius + 1, track_y - thumb_radius + 1,
                          thumb_x + thumb_radius + 1, track_y + thumb_radius + 1,
                          fill=shadow_color, outline="")
        
        # Main thumb
        thumb = canvas.create_oval(thumb_x - thumb_radius, track_y - thumb_radius,
                                  thumb_x + thumb_radius, track_y + thumb_radius,
                                  fill=colors['slider_thumb'], outline="", width=0)
        
        # Animation variables
        self.slider_animating = False
        self.slider_canvas = canvas
        self.slider_thumb = thumb
        self.slider_track_start = track_start + thumb_radius
        self.slider_track_end = track_end - thumb_radius
        self.slider_track_y = track_y
        self.slider_thumb_radius = thumb_radius
        
        def animate_slider(target_x, callback=None):
            """Animate slider movement with smooth easing"""
            if self.slider_animating or self._destroyed:
                return
                
            self.slider_animating = True
            current_coords = canvas.coords(thumb)
            current_x = (current_coords[0] + current_coords[2]) / 2
            
            # Animation with easing for smoother motion
            start_time = time.time()
            duration = 0.2  # 200ms animation
            
            def move_step():
                nonlocal current_x
                if self._destroyed:
                    self.slider_animating = False
                    return
                
                elapsed = time.time() - start_time
                progress = min(elapsed / duration, 1.0)
                
                # Ease out cubic for smooth deceleration
                eased_progress = 1 - pow(1 - progress, 3)
                
                if progress < 1.0:
                    # Calculate position based on easing
                    start_x = current_coords[0] + thumb_radius
                    current_x = start_x + (target_x - start_x) * eased_progress
                    
                    try:
                        # Update shadow
                        canvas.coords(canvas.find_all()[-2], 
                                     current_x - thumb_radius + 1, track_y - thumb_radius + 1,
                                     current_x + thumb_radius + 1, track_y + thumb_radius + 1)
                        # Update thumb
                        canvas.coords(thumb, 
                                     current_x - thumb_radius, track_y - thumb_radius,
                                     current_x + thumb_radius, track_y + thumb_radius)
                        # 60 FPS for smoother animation
                        canvas.after(16, move_step)
                    except Exception:
                        self.slider_animating = False
                else:
                    try:
                        # Final position
                        canvas.coords(canvas.find_all()[-2], 
                                     target_x - thumb_radius + 1, track_y - thumb_radius + 1,
                                     target_x + thumb_radius + 1, track_y + thumb_radius + 1)
                        canvas.coords(thumb, 
                                     target_x - thumb_radius, track_y - thumb_radius,
                                     target_x + thumb_radius, track_y + thumb_radius)
                        self.slider_animating = False
                        if callback:
                            callback()
                    except Exception:
                        self.slider_animating = False
            
            move_step()
        
        def on_slider_click(event):
            """Handle slider click"""
            if self.slider_animating:
                return
                
            # Determine which side was clicked
            click_x = event.x
            middle = (self.slider_track_start + self.slider_track_end) / 2
            
            if click_x < middle and self.is_dark_mode:
                # Switch to light mode
                target_x = self.slider_track_start
                animate_slider(target_x, lambda: self.toggle_dark_mode())
            elif click_x > middle and not self.is_dark_mode:
                # Switch to dark mode
                target_x = self.slider_track_end
                animate_slider(target_x, lambda: self.toggle_dark_mode())
        
        def on_slider_hover(event):
            """Handle slider hover"""
            canvas.config(cursor="hand2")
        
        def on_slider_leave(event):
            """Handle slider leave"""
            canvas.config(cursor="")
        
        # Bind events
        canvas.bind("<Button-1>", on_slider_click)
        canvas.bind("<Enter>", on_slider_hover)
        canvas.bind("<Leave>", on_slider_leave)
        
        return slider_container

    # Add remaining necessary methods (simplified versions to focus on the password system)
    def check_and_show_welcome(self):
        """Check if this is the first time opening this version and show welcome popup"""
        pass  # Simplified for this example
    
    def show_welcome_popup(self):
        """Show the welcome popup with version info and changelog"""
        pass  # Simplified for this example

def run_app(auth=None):
    """Run the main application after authentication"""
    try:
        # Now create main application
        root = tk.Tk()
        root.withdraw()  # Hide before any geometry is set
        
        # Use LoadingScreen for auth mode, SplashScreen for non-auth mode
        splash = LoadingScreen() if auth else SplashScreen()
        
        if not auth:
            for i in range(5):
                splash.splash.update()
                time.sleep(0.1)
        
        # Initialize the app (splash will continue animating during initialization)
        app = MultiToolLauncher(root, splash, auth)
        
        # App will handle closing splash and showing main window
        root.mainloop()
        
    except Exception as e:
        pass
        import traceback
        traceback.print_exc()
        
        try:
            if 'splash' in locals() and splash:
                splash.destroy()
        except:
            pass
        
        try:
            if 'root' in locals():
                root.deiconify()
                root.mainloop()
        except Exception as e2:
            pass
            try:
                simple_root = tk.Tk()
                simple_root.title("HelloToolbelt - Error")
                simple_root.geometry("400x200")
                tk.Label(simple_root, 
                        text="HelloToolbelt encountered an error during startup.\n\nCheck console for details.",
                        justify=tk.CENTER,
                        font=('Arial', 12)).pack(expand=True)
                simple_root.mainloop()
            except:
                pass

def main():
    """Main entry point with authentication"""
    
    # Check for updates before starting the main application
    if check_for_updates_on_startup():
        # Update initiated, app will restart
        return
    
    if AUTH_AVAILABLE:
        # Show login window first
        def on_login_success(auth):
            """Called after successful login"""
            run_app(auth)
        
        require_auth(on_login_success)
    else:
        # No auth module available, run without authentication
        run_app(None)

if __name__ == "__main__":
    main()