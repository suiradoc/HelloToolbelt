"""
HelloToolbelt Authentication Integration
Add this file to the same directory as HelloToolbelt.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import os
import sys
import json
import time

# ============================================================================
# Configuration - UPDATE THIS URL TO YOUR RENDER URL
# ============================================================================

API_BASE_URL = "https://hellotoolbelt-auth.onrender.com"  # CHANGE THIS TO YOUR URL

# ============================================================================
# Auth API Client
# ============================================================================

class AuthClient:
    """Handles authentication with the HelloToolbelt auth server"""
    
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.username = None
        self.permissions = {}
        self.is_admin = False
        self.can_s3_download = False
    
    def login(self, username, password):
        """Login and get permissions"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password},
                timeout=60  # Long timeout for Render cold starts
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                self.username = data["username"]
                self.is_admin = data.get("is_admin", False)
                self.permissions = data.get("permissions", {})
                self.can_s3_download = data.get("can_s3_download", False)
                return True, data
            elif response.status_code == 401:
                return False, "Invalid username or password"
            elif response.status_code == 403:
                return False, "Account is disabled"
            elif response.status_code == 502 or response.status_code == 503:
                return False, "Server is starting up. Please wait 30 seconds and try again."
            else:
                try:
                    return False, response.json().get("detail", f"Login failed (HTTP {response.status_code})")
                except:
                    return False, f"Login failed (HTTP {response.status_code})"
        except requests.exceptions.Timeout:
            return False, "Server is waking up. Please wait 30 seconds and try again."
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to server.\nCheck your internet connection."
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def change_password(self, current_password, new_password):
        """Change the user's password"""
        if not self.token:
            return False, "Not logged in"
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/change-password",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "current_password": current_password,
                    "new_password": new_password
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return True, "Password changed successfully"
            elif response.status_code == 401:
                return False, "Current password is incorrect"
            elif response.status_code == 400:
                try:
                    return False, response.json().get("detail", "Invalid password")
                except:
                    return False, "Invalid password"
            else:
                try:
                    return False, response.json().get("detail", f"Failed (HTTP {response.status_code})")
                except:
                    return False, f"Failed (HTTP {response.status_code})"
        except requests.exceptions.Timeout:
            return False, "Request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to server."
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def logout(self):
        """Logout and clear session"""
        if self.token:
            try:
                requests.post(
                    f"{self.base_url}/auth/logout",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10
                )
            except:
                pass
        self.token = None
        self.username = None
        self.permissions = {}
        self.is_admin = False
        self.can_s3_download = False
    
    def has_permission(self, tab_name):
        """Check if user has permission for a tab"""
        if self.is_admin:
            return True
        return self.permissions.get(tab_name, False)
    
    def log_action(self, action, target=None):
        """Log an action to the audit server (non-blocking)"""
        if not self.token:
            return
        
        def _log():
            try:
                requests.post(
                    f"{self.base_url}/audit/log",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"action": action, "target": target},
                    timeout=10
                )
            except:
                pass
        
        threading.Thread(target=_log, daemon=True).start()
    
    def get_allowed_tabs(self, all_tabs):
        """Filter tabs based on permissions"""
        if self.is_admin:
            return all_tabs
        return [tab for tab in all_tabs if self.permissions.get(tab, False)]


# ============================================================================
# Login Window with Heartbeat Loading Animation
# ============================================================================

class LoginWindow:
    """Login window for HelloToolbelt with heartbeat loading animation"""
    
    # Config file for saving username
    CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.hellotoolbelt_login.json')
    
    # Tab name mapping from HelloToolbelt tool names to server tab names
    TAB_MAPPING = {
        'Client Setup': 'Client Setup',
        'File Tools': 'File Tools',
        'Multi-File Column Search': 'File Tools',
        'Base64': 'File Tools',
        'DLQ Fetcher': 'DLQ Fetcher',
        'Bill Hunter': 'Bill Hunter',
        'Shipping Map': 'Shipping Map',
        'Report Builder': 'File Tools',
    }
    
    def __init__(self, on_success):
        self.auth = AuthClient()
        self.on_success = on_success
        self.result = False
        self._loading_mode = False
        self._animation_running = False
        self._after_id = None
        self._cycle_start = 0
        self._icon_images = {}
        self._icon_loaded = False
        
        self.window = tk.Tk()
        self.window.withdraw()  # Hide window initially while setting up
        self.window.title("HelloToolbelt - Login")
        self.window.geometry("500x550")
        self.window.resizable(False, False)
        self.window.configure(bg="#2b2b2b")
        
        # Load saved username
        self.saved_username = self._load_saved_username()
        
        # Create main frame that we can swap out for loading
        self.main_frame = tk.Frame(self.window, bg="#2b2b2b")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create all widgets
        self._create_widgets()
        
        # Center window on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 250
        y = (self.window.winfo_screenheight() // 2) - 275
        self.window.geometry(f"500x550+{x}+{y}")
        
        # Bind Enter key
        self.window.bind("<Return>", lambda e: self._login())
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Force update and show window
        self.window.update()
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        
        # Set focus on appropriate field AFTER window is shown
        if self.saved_username:
            self.password_entry.focus_set()
        else:
            self.username_entry.focus_set()
    
    def _load_saved_username(self):
        """Load saved username from config file"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get('username', '')
        except Exception:
            pass
        return ''
    
    def _save_username(self, username):
        """Save username to config file"""
        try:
            config = {'username': username}
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Could not save username: {e}")
    
    def _create_widgets(self):
        # Content frame inside main_frame
        content_frame = tk.Frame(self.main_frame, bg="#2b2b2b")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=40)
        
        # Try to load custom icon, fallback to emoji
        self._icon_loaded = False
        icon_label = None
        
        # Get the base path - handles both normal and PyInstaller bundled apps
        if getattr(sys, 'frozen', False):
            # Running as compiled app
            base_path = os.path.dirname(sys.executable)
            # Also check inside the .app bundle for macOS
            macos_resources = os.path.join(base_path, '..', 'Resources')
        else:
            # Running as script
            base_path = os.path.dirname(os.path.abspath(__file__))
            macos_resources = base_path
        
        # Try to find and load the icon
        icon_paths = [
            os.path.join(base_path, 'icon.icns'),
            os.path.join(base_path, 'icon.png'),
            os.path.join(macos_resources, 'icon.icns'),
            os.path.join(macos_resources, 'icon.png'),
            os.path.join(os.path.dirname(__file__), 'icon.icns'),
            os.path.join(os.path.dirname(__file__), 'icon.png'),
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
                    # Resize to 80x80 for login window
                    img = img.resize((80, 80), Image.Resampling.LANCZOS)
                    self.icon_photo = ImageTk.PhotoImage(img)
                    icon_label = tk.Label(
                        content_frame,
                        image=self.icon_photo,
                        bg="#2b2b2b"
                    )
                    icon_label.pack(pady=(0, 10))
                    self._icon_loaded = True
                    break
                except Exception as e:
                    print(f"Could not load icon {icon_path}: {e}")
                    continue
        
        # Fallback to emoji if icon didn't load
        if not self._icon_loaded:
            tk.Label(
                content_frame,
                text="🔧",
                font=("Arial", 48),
                bg="#2b2b2b",
                fg="#ffffff"
            ).pack(pady=(0, 10))
        
        tk.Label(
            content_frame,
            text="HelloToolbelt",
            font=("Arial", 24, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        ).pack(pady=(0, 5))
        
        tk.Label(
            content_frame,
            text="Please log in to continue",
            font=("Arial", 11),
            bg="#2b2b2b",
            fg="#888888"
        ).pack(pady=(0, 30))
        
        # Form frame for better alignment
        form_frame = tk.Frame(content_frame, bg="#2b2b2b")
        form_frame.pack(fill=tk.X, padx=20)
        
        # Username
        username_label_frame = tk.Frame(form_frame, bg="#2b2b2b")
        username_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(
            username_label_frame,
            text="Username",
            font=("Arial", 11, "bold"),
            bg="#2b2b2b",
            fg="#ffffff",
            anchor="w"
        ).pack(side=tk.LEFT)
        
        self.username_entry = tk.Entry(
            form_frame,
            font=("Arial", 12),
            bg="#3c3c3c",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat"
        )
        self.username_entry.pack(fill=tk.X, ipady=8, pady=(0, 5))
        
        # Remember username checkbox
        self.remember_var = tk.BooleanVar(value=bool(self.saved_username))
        remember_frame = tk.Frame(form_frame, bg="#2b2b2b")
        remember_frame.pack(fill=tk.X, pady=(0, 20))
        
        remember_cb = tk.Checkbutton(
            remember_frame,
            text="Remember username",
            variable=self.remember_var,
            font=("Arial", 9),
            bg="#2b2b2b",
            fg="#888888",
            activebackground="#2b2b2b",
            activeforeground="#888888",
            selectcolor="#3c3c3c",
            cursor="hand2"
        )
        remember_cb.pack(side=tk.LEFT)
        
        # Password
        password_label_frame = tk.Frame(form_frame, bg="#2b2b2b")
        password_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(
            password_label_frame,
            text="Password",
            font=("Arial", 11, "bold"),
            bg="#2b2b2b",
            fg="#ffffff",
            anchor="w"
        ).pack(side=tk.LEFT)
        
        self.password_entry = tk.Entry(
            form_frame,
            font=("Arial", 12),
            bg="#3c3c3c",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            show="●"
        )
        self.password_entry.pack(fill=tk.X, ipady=8, pady=(0, 15))
        
        # Error label
        self.error_label = tk.Label(
            form_frame,
            text="",
            font=("Arial", 10),
            bg="#2b2b2b",
            fg="#ff6b6b",
            wraplength=350
        )
        self.error_label.pack(fill=tk.X, pady=(5, 10))
        
        # Login button
        self.login_btn = tk.Button(
            form_frame,
            text="Login",
            font=("Arial", 12, "bold"),
            bg="#4a9eff",
            fg="#000000",
            activebackground="#3a8eef",
            activeforeground="#000000",
            relief="flat",
            cursor="hand2",
            command=self._login
        )
        self.login_btn.pack(fill=tk.X, ipady=10, pady=(10, 0))
        
        # Pre-fill saved username if available
        if self.saved_username:
            self.username_entry.insert(0, self.saved_username)
    
    def _create_loading_screen(self):
        """Replace the login form with a loading screen with heartbeat animation"""
        # Clear the main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Create canvas for animation
        self.canvas = tk.Canvas(
            self.main_frame,
            width=500,
            height=550,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
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
            'icon.icns',
            'icon.png',
        ]
        
        self._icon_loaded = False
        self._icon_images = {}
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    
                    # Create multiple sizes for heartbeat effect
                    sizes = {'normal': 80, 'beat1': 88, 'beat2': 84}
                    for name, size in sizes.items():
                        resized = img.resize((size, size), Image.Resampling.LANCZOS)
                        self._icon_images[name] = ImageTk.PhotoImage(resized, master=self.window)
                    
                    self._icon_loaded = True
                    break
                except Exception as e:
                    continue
        
        # Icon (centered, higher up)
        if self._icon_loaded:
            self._icon_item = self.canvas.create_image(250, 180, image=self._icon_images['normal'])
        else:
            self._icon_item = self.canvas.create_text(
                250, 180,
                text="🔧",
                font=("Segoe UI", 48),
                fill="white"
            )
        
        # Title
        self.canvas.create_text(
            250, 280,
            text="HelloToolbelt",
            font=("Segoe UI", 24, "bold"),
            fill="white"
        )
        
        # Loading text with animated dots
        self._loading_text = self.canvas.create_text(
            250, 330,
            text="Loading",
            font=("Segoe UI", 14),
            fill="#888888"
        )
        
        # Pulse dot (small indicator that pulses with heartbeat)
        self._pulse_dot = self.canvas.create_oval(
            245, 365, 255, 375,
            fill="#e74c3c",
            outline=""
        )
        
        # Animation state
        self._dot_states = ["Loading", "Loading.", "Loading..", "Loading..."]
        self._dot_index = 0
        self._last_dot_update = time.time()
        self._cycle_start = time.time()
        self._animation_running = True
        self._loading_mode = True
        
        # Start animation
        self._animate_heartbeat()
    
    def _animate_heartbeat(self):
        """Animate the heartbeat effect"""
        if not self._animation_running:
            return
        
        try:
            current_time = time.time()
            cycle_time = current_time - self._cycle_start
            
            # Heartbeat pattern: beat1 -> beat2 -> rest -> rest (repeats every 0.8 seconds)
            cycle_position = (cycle_time % 0.8)
            
            if cycle_position < 0.1:
                current_state = 'beat1'
            elif cycle_position < 0.2:
                current_state = 'beat2'
            elif cycle_position < 0.3:
                current_state = 'beat1'
            else:
                current_state = 'normal'
            
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
            
            # Animate pulse dot
            if current_state == 'beat1':
                self.canvas.coords(self._pulse_dot, 243, 363, 257, 377)
                self.canvas.itemconfig(self._pulse_dot, fill="#ff6b6b")
            elif current_state == 'beat2':
                self.canvas.coords(self._pulse_dot, 244, 364, 256, 376)
                self.canvas.itemconfig(self._pulse_dot, fill="#ff5252")
            else:
                self.canvas.coords(self._pulse_dot, 245, 365, 255, 375)
                self.canvas.itemconfig(self._pulse_dot, fill="#e74c3c")
            
            # Animate loading dots
            if current_time - self._last_dot_update > 0.4:
                self._dot_index = (self._dot_index + 1) % len(self._dot_states)
                self.canvas.itemconfig(self._loading_text, text=self._dot_states[self._dot_index])
                self._last_dot_update = current_time
            
            # Schedule next frame and track the callback ID
            if self._animation_running:
                self._after_id = self.window.after(30, self._animate_heartbeat)
        except tk.TclError:
            self._animation_running = False
    
    def _login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.config(text="Please enter username and password")
            return
        
        self.login_btn.config(state=tk.DISABLED, text="Logging in...")
        self.error_label.config(text="")
        self.window.update()
        
        # Save or clear username based on checkbox
        if self.remember_var.get():
            self._save_username(username)
        else:
            # Clear saved username
            try:
                if os.path.exists(self.CONFIG_FILE):
                    os.remove(self.CONFIG_FILE)
            except:
                pass
        
        # Login in thread to not freeze UI
        def do_login():
            success, result = self.auth.login(username, password)
            
            # Update UI in main thread
            self.window.after(0, lambda: self._handle_login_result(success, result))
        
        threading.Thread(target=do_login, daemon=True).start()
    
    def _handle_login_result(self, success, result):
        if success:
            self.result = True
            self.auth.log_action("LOGIN")
            # Store auth for later use
            self._auth_result = self.auth
            self._success_callback = self.on_success
            
            # Transition to loading screen with heartbeat
            self._create_loading_screen()
            self.window.update()
            
            # Schedule the actual app loading to happen after a brief moment
            # This allows the loading screen to render
            self.window.after(100, self._finish_login)
        else:
            self.error_label.config(text=result)
            self.login_btn.config(state=tk.NORMAL, text="Login")
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()
    
    def _finish_login(self):
        """Complete the login process - called after loading screen is shown"""
        # Stop the mainloop so the app can continue
        # But keep animation running - it will continue in background
        self.window.quit()
    
    def destroy_loading(self):
        """Called by the main app when it's ready to show itself"""
        self._animation_running = False
        if self._after_id:
            try:
                self.window.after_cancel(self._after_id)
            except:
                pass
        try:
            self.window.destroy()
        except:
            pass
    
    def keep_alive(self):
        """Call this periodically during loading to keep animation running"""
        if self._loading_mode and self._animation_running:
            try:
                self.window.update()
            except:
                pass
    
    def _on_close(self):
        self.result = False
        self._auth_result = None
        self._animation_running = False
        if self._after_id:
            try:
                self.window.after_cancel(self._after_id)
            except:
                pass
        self.window.destroy()
    
    def run(self):
        self.window.mainloop()
        # After mainloop exits, call success callback if login was successful
        if self.result and hasattr(self, '_success_callback') and hasattr(self, '_auth_result'):
            # Pass both auth and the login window so it can be destroyed later
            self._success_callback(self._auth_result, self)
        return self.result


# ============================================================================
# Helper function to integrate with HelloToolbelt
# ============================================================================

def require_auth(on_success):
    """
    Show login window and call on_success with auth client if successful.
    
    Usage in HelloToolbelt.py main():
        from auth_integration import require_auth
        
        def start_app(auth, login_window):
            # auth.username - logged in user
            # auth.permissions - dict of tab permissions
            # auth.has_permission("Tab Name") - check permission
            # auth.log_action("ACTION", "target") - log to audit
            # login_window.destroy_loading() - call when app is ready
            # login_window.keep_alive() - call during loading to animate
            # Start the normal app...
        
        require_auth(start_app)
    """
    login = LoginWindow(on_success)
    login.run()


# ============================================================================
# Tab filtering helper
# ============================================================================

def filter_tools_by_permission(tools, auth):
    """
    Filter the tools list based on user permissions.
    
    Args:
        tools: List of tool dicts with 'name' key
        auth: AuthClient instance
    
    Returns:
        Filtered list of tools user has permission to access
    """
    print(f"[AUTH] Filtering tools for user: {auth.username}")
    print(f"[AUTH] Is admin: {auth.is_admin}")
    print(f"[AUTH] Permissions: {auth.permissions}")
    
    if auth.is_admin:
        print(f"[AUTH] Admin user - returning all {len(tools)} tools")
        return tools
    
    # Map tool names to server tab names
    # Client Setup contains: Config, CronJob, Base64
    # File Tools contains: Eligibility Search, Multi-File Column Search, Report Builder
    # Other tabs are standalone: DLQ Fetcher, Bill Hunter, Shipping Map
    tab_mapping = {
        # Client Setup subtabs
        'Config': 'Client Setup',
        'CronJob': 'Client Setup',
        'Base64': 'Client Setup',
        # File Tools subtabs
        'Eligibility Search': 'File Tools',
        'Multi-File Column Search': 'File Tools',
        'Report Builder': 'File Tools',
        # Standalone tabs
        'DLQ Fetcher': 'DLQ Fetcher',
        'Bill Hunter': 'Bill Hunter',
        'Shipping Map': 'Shipping Map',
    }
    
    filtered = []
    for tool in tools:
        tool_name = tool.get('name', '')
        server_tab = tab_mapping.get(tool_name, tool_name)
        has_access = auth.permissions.get(server_tab, False)
        print(f"[AUTH] Tool '{tool_name}' -> Tab '{server_tab}' -> Access: {has_access}")
        if has_access:
            filtered.append(tool)
    
    print(f"[AUTH] Filtered result: {len(filtered)}/{len(tools)} tools available")
    return filtered