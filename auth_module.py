"""
HelloToolbelt Authentication Module
Add this to your HelloToolbelt application for login and permission checking.

Integration steps:
1. Import this module in HelloToolbelt.py
2. Call show_login() before creating the main app
3. Use check_permission() to show/hide tabs
4. Call log_action() to log user activity
"""

import tkinter as tk
from tkinter import messagebox
import requests
import json
import threading
import os

# ============================================================================
# Configuration
# ============================================================================

# Update this to your Render URL after deployment
API_BASE_URL = "https://your-app-name.onrender.com"  # CHANGE THIS

# For local development:
# API_BASE_URL = "http://localhost:8000"

# ============================================================================
# Global Auth State
# ============================================================================

class AuthState:
    """Global authentication state"""
    token = None
    username = None
    is_admin = False
    permissions = {}
    
    @classmethod
    def is_authenticated(cls):
        return cls.token is not None
    
    @classmethod
    def has_permission(cls, tab_name):
        """Check if user has access to a tab"""
        if cls.is_admin:
            return True
        return cls.permissions.get(tab_name, False)
    
    @classmethod
    def clear(cls):
        cls.token = None
        cls.username = None
        cls.is_admin = False
        cls.permissions = {}


# ============================================================================
# API Functions
# ============================================================================

def _headers():
    """Get request headers with auth token"""
    headers = {"Content-Type": "application/json"}
    if AuthState.token:
        headers["Authorization"] = f"Bearer {AuthState.token}"
    return headers


def login(username, password):
    """
    Authenticate user with the server.
    Returns (success: bool, error_message: str or None)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            AuthState.token = data["token"]
            AuthState.username = data["username"]
            AuthState.is_admin = data["is_admin"]
            AuthState.permissions = data["permissions"]
            return True, None
        else:
            error = response.json().get("detail", "Login failed")
            return False, error
            
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to authentication server.\nPlease check your internet connection."
    except requests.exceptions.Timeout:
        return False, "Connection timed out. Please try again."
    except Exception as e:
        return False, f"Login error: {str(e)}"


def logout():
    """Logout and clear authentication state"""
    if AuthState.token:
        try:
            requests.post(
                f"{API_BASE_URL}/auth/logout",
                headers=_headers(),
                timeout=5
            )
        except:
            pass  # Ignore logout errors
    AuthState.clear()


def verify_token():
    """
    Verify current token is still valid.
    Returns (valid: bool, updated_permissions: dict or None)
    """
    if not AuthState.token:
        return False, None
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/verify",
            headers=_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            AuthState.permissions = data["permissions"]
            AuthState.is_admin = data["is_admin"]
            return True, data["permissions"]
        return False, None
        
    except:
        return False, None


def log_action(action, target=None):
    """
    Log a user action to the server.
    
    Args:
        action: Action type (e.g., "OPENED_TAB", "OPENED_FILE", "EXPORTED_DATA")
        target: Target of action (e.g., tab name, filename)
    
    This runs in a background thread to not block the UI.
    """
    if not AuthState.token:
        return
    
    def _log():
        try:
            requests.post(
                f"{API_BASE_URL}/audit/log",
                headers=_headers(),
                json={"action": action, "target": target},
                timeout=5
            )
        except:
            pass  # Don't interrupt user for logging failures
    
    thread = threading.Thread(target=_log, daemon=True)
    thread.start()


# ============================================================================
# Permission Checking
# ============================================================================

def check_permission(tab_name):
    """
    Check if current user has permission to access a tab.
    
    Args:
        tab_name: Name of the tab to check
    
    Returns:
        bool: True if user has access, False otherwise
    """
    return AuthState.has_permission(tab_name)


def get_permitted_tabs(all_tabs):
    """
    Filter a list of tabs to only those the user can access.
    
    Args:
        all_tabs: List of all tab names
    
    Returns:
        List of tab names the user has permission to access
    """
    return [tab for tab in all_tabs if check_permission(tab)]


# ============================================================================
# Login Dialog
# ============================================================================

class LoginDialog:
    """Login window that must be completed before app loads"""
    
    def __init__(self, on_success, on_cancel=None):
        """
        Args:
            on_success: Callback function called after successful login
            on_cancel: Callback function called if login window is closed
        """
        self.on_success = on_success
        self.on_cancel = on_cancel
        self.success = False
        
        self.window = tk.Tk()
        self.window.title("HelloToolbelt - Login")
        self.window.geometry("400x280")
        self.window.resizable(False, False)
        self.window.configure(bg="#2b2b2b")
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 200
        y = (self.window.winfo_screenheight() // 2) - 140
        self.window.geometry(f"+{x}+{y}")
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._create_widgets()
        
        # Bind Enter key
        self.window.bind("<Return>", lambda e: self._login())
    
    def _create_widgets(self):
        # Title
        title = tk.Label(
            self.window,
            text="HelloToolbelt",
            font=("Arial", 20, "bold"),
            fg="#ffffff",
            bg="#2b2b2b"
        )
        title.pack(pady=(30, 5))
        
        subtitle = tk.Label(
            self.window,
            text="Please sign in to continue",
            font=("Arial", 10),
            fg="#888888",
            bg="#2b2b2b"
        )
        subtitle.pack(pady=(0, 25))
        
        # Username
        frame = tk.Frame(self.window, bg="#2b2b2b")
        frame.pack(pady=8)
        
        tk.Label(
            frame,
            text="Username:",
            fg="#ffffff",
            bg="#2b2b2b",
            width=10,
            anchor="e"
        ).pack(side=tk.LEFT)
        
        self.username_entry = tk.Entry(
            frame,
            width=25,
            bg="#3c3c3c",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Arial", 11)
        )
        self.username_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        
        # Password
        frame2 = tk.Frame(self.window, bg="#2b2b2b")
        frame2.pack(pady=8)
        
        tk.Label(
            frame2,
            text="Password:",
            fg="#ffffff",
            bg="#2b2b2b",
            width=10,
            anchor="e"
        ).pack(side=tk.LEFT)
        
        self.password_entry = tk.Entry(
            frame2,
            width=25,
            show="●",
            bg="#3c3c3c",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Arial", 11)
        )
        self.password_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        
        # Error label
        self.error_label = tk.Label(
            self.window,
            text="",
            fg="#ff6b6b",
            bg="#2b2b2b",
            font=("Arial", 9),
            wraplength=350
        )
        self.error_label.pack(pady=10)
        
        # Login button
        self.login_btn = tk.Button(
            self.window,
            text="Sign In",
            command=self._login,
            bg="#4a9eff",
            fg="#ffffff",
            activebackground="#3a8eef",
            activeforeground="#ffffff",
            font=("Arial", 11),
            width=15,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.login_btn.pack(pady=15)
        
        # Focus username field
        self.username_entry.focus()
    
    def _login(self):
        """Handle login attempt"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.config(text="Please enter username and password")
            return
        
        # Disable button during login
        self.login_btn.config(state=tk.DISABLED, text="Signing in...")
        self.error_label.config(text="")
        self.window.update()
        
        # Attempt login
        success, error = login(username, password)
        
        if success:
            self.success = True
            self.window.destroy()
            self.on_success()
        else:
            self.error_label.config(text=error)
            self.login_btn.config(state=tk.NORMAL, text="Sign In")
    
    def _on_close(self):
        """Handle window close button"""
        if self.on_cancel:
            self.on_cancel()
        self.window.destroy()
    
    def run(self):
        """Run the login dialog"""
        self.window.mainloop()
        return self.success


def show_login(on_success, on_cancel=None):
    """
    Display login dialog and authenticate user.
    
    Args:
        on_success: Function to call after successful login
        on_cancel: Function to call if user closes login window
    
    Returns:
        bool: True if login successful, False if cancelled
    """
    dialog = LoginDialog(on_success, on_cancel)
    return dialog.run()


# ============================================================================
# Integration Helper for HelloToolbelt
# ============================================================================

class SecureTabManager:
    """
    Helper class to manage tab visibility based on permissions.
    
    Usage in HelloToolbelt:
        tab_manager = SecureTabManager(notebook)
        tab_manager.add_tab("Client Setup", client_setup_frame)
        tab_manager.add_tab("File Tools", file_tools_frame)
        tab_manager.apply_permissions()
    """
    
    def __init__(self, notebook):
        """
        Args:
            notebook: ttk.Notebook widget
        """
        self.notebook = notebook
        self.tabs = {}  # {tab_name: frame}
    
    def add_tab(self, name, frame):
        """Register a tab"""
        self.tabs[name] = frame
    
    def apply_permissions(self):
        """Show only tabs user has permission to access"""
        # First, remove all tabs
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        
        # Add back only permitted tabs
        for name, frame in self.tabs.items():
            if check_permission(name):
                self.notebook.add(frame, text=name)
                log_action("TAB_AVAILABLE", name)
    
    def on_tab_changed(self, event):
        """
        Call this when tab selection changes to log it.
        Bind to: notebook.bind("<<NotebookTabChanged>>", tab_manager.on_tab_changed)
        """
        try:
            current_tab = event.widget.tab(event.widget.select(), "text")
            log_action("OPENED_TAB", current_tab)
        except:
            pass


# ============================================================================
# Example Integration
# ============================================================================

"""
EXAMPLE: How to integrate into HelloToolbelt.py

1. Add imports at top of file:
   from auth_module import (
       show_login, logout, log_action, check_permission,
       AuthState, SecureTabManager
   )

2. Modify the main() function:

   def main():
       def start_app():
           # Your existing app initialization
           root = tk.Tk()
           app = MultiToolLauncher(root)
           
           # Log startup
           log_action("APP_STARTED")
           
           root.mainloop()
           
           # Logout when app closes
           logout()
       
       def on_cancel():
           # User closed login window
           import sys
           sys.exit(0)
       
       # Show login first
       show_login(on_success=start_app, on_cancel=on_cancel)

3. Modify tab creation to respect permissions:
   
   In your MultiToolLauncher.__init__ or wherever tabs are created:
   
   # Only add tabs user has permission for
   if check_permission("Client Setup"):
       self.notebook.add(client_setup_frame, text="Client Setup")
   
   if check_permission("File Tools"):
       self.notebook.add(file_tools_frame, text="File Tools")
   
   # etc...

4. Log file operations:
   
   When user opens a file:
       log_action("OPENED_FILE", filename)
   
   When user exports data:
       log_action("EXPORTED_DATA", export_filename)
   
   When user performs significant actions:
       log_action("GENERATED_REPORT", report_name)

5. Add logout on window close:
   
   def on_closing():
       logout()
       root.destroy()
   
   root.protocol("WM_DELETE_WINDOW", on_closing)

6. Display username in window (optional):
   
   root.title(f"HelloToolbelt - {AuthState.username}")
"""


# ============================================================================
# Standalone Test
# ============================================================================

if __name__ == "__main__":
    # Test the login dialog
    def on_success():
        print(f"Logged in as: {AuthState.username}")
        print(f"Is admin: {AuthState.is_admin}")
        print(f"Permissions: {AuthState.permissions}")
        
        # Test logging
        log_action("TEST_ACTION", "test_target")
        print("Logged test action")
        
        # Cleanup
        logout()
        print("Logged out")
    
    def on_cancel():
        print("Login cancelled")
    
    show_login(on_success, on_cancel)
