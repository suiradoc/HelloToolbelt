import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading

# ============================================================================
# Configuration - Uses same URL as auth_integration
# ============================================================================

try:
    from auth_integration import AUTH_SERVER_URL
    API_BASE_URL = AUTH_SERVER_URL
except ImportError:
    API_BASE_URL = "https://hellotoolbelt-auth.onrender.com"


# ============================================================================
# User Management API Client
# ============================================================================

class UserManagementAPIClient:
    """Handles user management API communication - uses existing auth token"""
    
    def __init__(self, auth_client):
        """Initialize with existing auth client from login"""
        self.auth = auth_client
        self.base_url = API_BASE_URL.rstrip("/")
    
    def _headers(self):
        """Get headers with auth token"""
        headers = {"Content-Type": "application/json"}
        if self.auth and self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        return headers
    
    def get_users(self):
        """Get all users"""
        try:
            response = requests.get(
                f"{self.base_url}/admin/users",
                headers=self._headers(),
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to get users")
        except Exception as e:
            return False, str(e)
    
    def get_tabs(self):
        """Get all available tabs"""
        try:
            response = requests.get(
                f"{self.base_url}/admin/tabs",
                headers=self._headers(),
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to get tabs")
        except Exception as e:
            return False, str(e)
    
    def create_user(self, username, password, is_admin=False, notes=None):
        """Create new user"""
        try:
            data = {"username": username, "password": password, "is_admin": is_admin}
            if notes:
                data["notes"] = notes
            response = requests.post(
                f"{self.base_url}/admin/users",
                headers=self._headers(),
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to create user")
        except Exception as e:
            return False, str(e)
    
    def update_user(self, user_id, **kwargs):
        """Update user"""
        try:
            response = requests.put(
                f"{self.base_url}/admin/users/{user_id}",
                headers=self._headers(),
                json=kwargs,
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to update user")
        except Exception as e:
            return False, str(e)
    
    def delete_user(self, user_id):
        """Delete user"""
        try:
            response = requests.delete(
                f"{self.base_url}/admin/users/{user_id}",
                headers=self._headers(),
                timeout=30
            )
            if response.status_code == 200:
                return True, "User deleted"
            return False, response.json().get("detail", "Failed to delete user")
        except Exception as e:
            return False, str(e)
    
    def update_permissions(self, user_id, permissions):
        """Update user permissions"""
        try:
            response = requests.put(
                f"{self.base_url}/admin/permissions/bulk",
                headers=self._headers(),
                json={"user_id": user_id, "permissions": permissions},
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to update permissions")
        except Exception as e:
            return False, str(e)


# ============================================================================
# Password Validation
# ============================================================================

def validate_password(password):
    """Validate password meets requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"
    return True, None


# ============================================================================
# Dialogs
# ============================================================================

class NewUserDialog:
    """Dialog for creating new user"""
    
    def __init__(self, parent, user_panel=None):
        self.result = None
        self.user_panel = user_panel
        
        # Get colors from user panel if available
        if user_panel:
            self.bg_color = user_panel.frame_bg
            self.entry_bg = user_panel.entry_bg
            self.entry_fg = user_panel.entry_fg
            self.text_color = user_panel.text_color
            self.text_secondary = user_panel.text_secondary
        else:
            self.bg_color = "#2b2b2b"
            self.entry_bg = "#3c3c3c"
            self.entry_fg = "#ffffff"
            self.text_color = "#ffffff"
            self.text_secondary = "#888888"
        
        self.window = tk.Toplevel(parent)
        self.window.title("New User")
        self.window.geometry("400x320")
        self.window.configure(bg=self.bg_color)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center on parent
        self.window.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 160
        self.window.geometry(f"+{x}+{y}")
        
        # Username
        row = tk.Frame(self.window, bg=self.bg_color)
        row.pack(fill=tk.X, padx=20, pady=(20, 5))
        tk.Label(row, text="Username:", fg=self.text_color, bg=self.bg_color, width=10, anchor="e").pack(side=tk.LEFT)
        self.username_entry = tk.Entry(row, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Password
        row = tk.Frame(self.window, bg=self.bg_color)
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Password:", fg=self.text_color, bg=self.bg_color, width=10, anchor="e").pack(side=tk.LEFT)
        self.password_entry = tk.Entry(row, show="●", bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Password hint
        hint_row = tk.Frame(self.window, bg=self.bg_color)
        hint_row.pack(fill=tk.X, padx=20, pady=(0, 5))
        tk.Label(hint_row, text="(8+ chars, 1 number, 1 special)", 
                fg=self.text_secondary, bg=self.bg_color, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(95, 0))
        
        # Confirm password
        row = tk.Frame(self.window, bg=self.bg_color)
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Confirm:", fg=self.text_color, bg=self.bg_color, width=10, anchor="e").pack(side=tk.LEFT)
        self.confirm_entry = tk.Entry(row, show="●", bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.confirm_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Notes
        row = tk.Frame(self.window, bg=self.bg_color)
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Notes:", fg=self.text_color, bg=self.bg_color, width=10, anchor="e").pack(side=tk.LEFT)
        self.notes_entry = tk.Entry(row, bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.notes_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Admin checkbox
        row = tk.Frame(self.window, bg=self.bg_color)
        row.pack(fill=tk.X, padx=20, pady=5)
        self.admin_var = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="Administrator", variable=self.admin_var, bg=self.bg_color, fg=self.text_color,
                      selectcolor=self.entry_bg, activebackground=self.bg_color).pack(side=tk.LEFT, padx=(90, 0))
        
        # Buttons
        btn_frame = tk.Frame(self.window, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Button(btn_frame, text="Create", command=self._create,
                  style="Blue.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Cancel", command=self.window.destroy,
                  style="Gray.TButton").pack(side=tk.RIGHT, padx=10)
    
    def _create(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        notes = self.notes_entry.get().strip()
        
        if not username:
            messagebox.showerror("Error", "Username is required")
            return
        if not password:
            messagebox.showerror("Error", "Password is required")
            return
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            messagebox.showerror("Error", error_msg)
            return
        
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return
        
        self.result = {
            "username": username,
            "password": password,
            "is_admin": self.admin_var.get(),
            "notes": notes if notes else None
        }
        self.window.destroy()


class PasswordResetDialog:
    """Dialog for resetting password"""
    
    def __init__(self, parent, username, user_panel=None):
        self.result = None
        self.user_panel = user_panel
        
        # Get colors from user panel if available
        if user_panel:
            self.bg_color = user_panel.frame_bg
            self.entry_bg = user_panel.entry_bg
            self.entry_fg = user_panel.entry_fg
            self.text_color = user_panel.text_color
            self.text_secondary = user_panel.text_secondary
        else:
            self.bg_color = "#2b2b2b"
            self.entry_bg = "#3c3c3c"
            self.entry_fg = "#ffffff"
            self.text_color = "#ffffff"
            self.text_secondary = "#888888"
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"Reset Password - {username}")
        self.window.geometry("400x180")
        self.window.configure(bg=self.bg_color)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center on parent
        self.window.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 90
        self.window.geometry(f"+{x}+{y}")
        
        # New password
        row = tk.Frame(self.window, bg=self.bg_color)
        row.pack(fill=tk.X, padx=20, pady=(20, 5))
        tk.Label(row, text="New Password:", fg=self.text_color, bg=self.bg_color, width=12, anchor="e").pack(side=tk.LEFT)
        self.password_entry = tk.Entry(row, show="●", bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Password hint
        hint_row = tk.Frame(self.window, bg=self.bg_color)
        hint_row.pack(fill=tk.X, padx=20, pady=(0, 5))
        tk.Label(hint_row, text="(8+ chars, 1 number, 1 special)", 
                fg=self.text_secondary, bg=self.bg_color, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(110, 0))
        
        # Confirm
        row = tk.Frame(self.window, bg=self.bg_color)
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Confirm:", fg=self.text_color, bg=self.bg_color, width=12, anchor="e").pack(side=tk.LEFT)
        self.confirm_entry = tk.Entry(row, show="●", bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.confirm_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(self.window, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Button(btn_frame, text="Reset", command=self._reset,
                  style="Blue.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Cancel", command=self.window.destroy,
                  style="Gray.TButton").pack(side=tk.RIGHT, padx=10)
    
    def _reset(self):
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        
        if not password:
            messagebox.showerror("Error", "Password is required")
            return
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            messagebox.showerror("Error", error_msg)
            return
        
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return
        
        self.result = password
        self.window.destroy()


# ============================================================================
# User Management Panel
# ============================================================================

class UserManagementPanel:
    """User management panel that can be embedded as a tab in HelloToolbelt"""
    
    # Tab color for HelloToolbelt integration (yellow/gold for admin)
    tab_color = '#d4a017'
    
    def __init__(self, parent_frame, auth_client, colors_func):
        """
        Initialize user management panel
        
        Args:
            parent_frame: The frame to build the UI in
            auth_client: The auth client from login (has token)
            colors_func: Function to get current color scheme
        """
        self.parent = parent_frame
        self.auth = auth_client
        self.get_colors = colors_func
        self.api = UserManagementAPIClient(auth_client)
        
        self.users = []
        self.tabs = []
        self.selected_user = None
        
        # Setup adaptive styling
        self.setup_adaptive_styling()
        
        # Build the UI
        self._create_widgets()
        self._load_data()
    
    def setup_adaptive_styling(self):
        """Setup styling that adapts to system theme (light/dark mode)"""
        # Get colors from HelloToolbelt's get_colors function
        colors = self.get_colors()
        
        # Use HelloToolbelt's bg color directly
        parent_bg = colors.get('bg', '#2b2b2b')
        
        # Determine if we're in dark mode by checking background brightness
        try:
            if parent_bg.startswith('#'):
                r = int(parent_bg[1:3], 16)
                g = int(parent_bg[3:5], 16)
                b = int(parent_bg[5:7], 16)
            else:
                r, g, b = 43, 43, 43  # Default dark
            
            # Calculate brightness (perceived luminance)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            self.is_dark_mode = brightness < 128
        except:
            # Fallback to dark mode
            self.is_dark_mode = True
        
        # Fonts
        self.title_font = ("Segoe UI", 16, "bold")  # Slightly larger for better visibility
        self.subtitle_font = ("Segoe UI", 11, "bold")
        self.label_font = ("Segoe UI", 10)
        self.text_font = ("Segoe UI", 10)
        
        # Use colors from HelloToolbelt's get_colors() for consistency
        self.bg_color = colors.get('bg', '#2b2b2b')
        self.frame_bg = colors.get('frame_bg', '#3c3c3c')
        self.header_bg = colors.get('header_bg', '#4a4a4a')
        self.text_color = colors.get('fg', '#ffffff')
        self.text_secondary = colors.get('text_secondary', '#cccccc')
        self.primary_color = colors.get('primary', '#4a90e2')
        self.success_color = colors.get('success', '#27ae60')
        self.danger_color = colors.get('danger', '#e74c3c')
        
        # Entry/listbox colors based on mode
        if self.is_dark_mode:
            self.entry_bg = '#2b2b2b'
            self.entry_fg = '#ffffff'
            self.listbox_bg = '#2b2b2b'
            self.listbox_fg = '#ffffff'
            self.select_bg = '#4a9eff'
            self.select_fg = '#ffffff'
        else:
            self.entry_bg = '#ffffff'
            self.entry_fg = '#2c3e50'
            self.listbox_bg = '#ffffff'
            self.listbox_fg = '#2c3e50'
            self.select_bg = '#3498db'
            self.select_fg = '#ffffff'
    
    def refresh_styling(self, is_dark_mode):
        """Refresh styling when dark mode is toggled from HelloToolbelt"""
        self.is_dark_mode = is_dark_mode
        
        # Get updated colors from HelloToolbelt
        colors = self.get_colors()
        
        # Use colors from HelloToolbelt's get_colors() for consistency
        self.bg_color = colors.get('bg', '#2b2b2b' if is_dark_mode else '#ffffff')
        self.frame_bg = colors.get('frame_bg', '#3c3c3c' if is_dark_mode else '#f8f9fa')
        self.header_bg = colors.get('header_bg', '#4a4a4a' if is_dark_mode else '#e9ecef')
        self.text_color = colors.get('fg', '#ffffff' if is_dark_mode else '#2c3e50')
        self.text_secondary = colors.get('text_secondary', '#cccccc' if is_dark_mode else '#34495e')
        self.primary_color = colors.get('primary', '#4a90e2' if is_dark_mode else '#3498db')
        self.success_color = colors.get('success', '#27ae60')
        self.danger_color = colors.get('danger', '#e74c3c')
        
        # Entry/listbox colors based on mode
        if is_dark_mode:
            self.entry_bg = '#2b2b2b'
            self.entry_fg = '#ffffff'
            self.listbox_bg = '#2b2b2b'
            self.listbox_fg = '#ffffff'
            self.select_bg = '#4a9eff'
            self.select_fg = '#ffffff'
        else:
            self.entry_bg = '#ffffff'
            self.entry_fg = '#2c3e50'
            self.listbox_bg = '#ffffff'
            self.listbox_fg = '#2c3e50'
            self.select_bg = '#3498db'
            self.select_fg = '#ffffff'
        
        # Clear and recreate the interface
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        # Rebuild UI
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        """Create the user management UI"""
        # Main container
        self.main_frame = tk.Frame(self.parent, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header - use tab_color for consistency with the tab
        header_color = self.tab_color
        header_frame = tk.Frame(self.main_frame, bg=header_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        header_content = tk.Frame(header_frame, bg=header_color)
        header_content.pack(fill=tk.X, padx=20, pady=12)
        
        header_icon = tk.Label(header_content, text="👥", font=('Segoe UI', 18), 
                              bg=header_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_text_frame = tk.Frame(header_content, bg=header_color)
        header_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        header_title = tk.Label(header_text_frame, text="User Management", font=self.title_font,
                               bg=header_color, fg='white')
        header_title.pack(anchor="w")
        
        header_subtitle = tk.Label(header_text_frame, text="Manage users, permissions, and account settings",
                                  font=("Segoe UI", 9), bg=header_color, fg='#ecf0f1')
        header_subtitle.pack(anchor="w", pady=(2, 0))
        
        # Main section (Users and Details)
        content_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - User list
        left_frame = tk.Frame(content_frame, bg=self.frame_bg, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="Users", font=self.subtitle_font, 
                fg=self.text_color, bg=self.frame_bg).pack(pady=10)
        
        # User listbox with scrollbar
        listbox_frame = tk.Frame(left_frame, bg=self.frame_bg)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.user_listbox = tk.Listbox(
            listbox_frame,
            bg=self.listbox_bg,
            fg=self.listbox_fg,
            selectbackground=self.select_bg,
            selectforeground=self.select_fg,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.header_bg,
            highlightcolor=self.primary_color,
            font=self.text_font,
            yscrollcommand=scrollbar.set
        )
        self.user_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.user_listbox.yview)
        self.user_listbox.bind("<<ListboxSelect>>", self._on_user_select)
        
        # New user button
        ttk.Button(
            left_frame,
            text="+ New User",
            command=self._new_user_dialog,
            style="Blue.TButton"
        ).pack(pady=10)
        
        # Refresh button
        ttk.Button(
            left_frame,
            text="↻ Refresh",
            command=self._load_data,
            style="Gray.TButton"
        ).pack(pady=(0, 10))
        
        # Right panel - User details
        right_frame = tk.Frame(content_frame, bg=self.frame_bg)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_frame, text="User Details", font=self.subtitle_font, 
                fg=self.text_color, bg=self.frame_bg).pack(pady=10)
        
        self.details_frame = tk.Frame(right_frame, bg=self.frame_bg)
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Placeholder when no user selected
        self.no_user_label = tk.Label(
            self.details_frame,
            text="Select a user to view details",
            fg=self.text_secondary,
            bg=self.frame_bg,
            font=self.label_font
        )
        self.no_user_label.pack(expand=True)
    
    def _load_data(self):
        """Load users and tabs from server"""
        # Remember currently selected username to reselect after refresh
        selected_username = self.selected_user["username"] if self.selected_user else None
        
        # Load in thread to avoid blocking UI
        def do_load():
            # Load users
            success, result = self.api.get_users()
            if success:
                self.users = result
                self.parent.after(0, lambda: self._update_user_list_and_reselect(selected_username))
            
            # Load tabs
            success, result = self.api.get_tabs()
            if success:
                self.tabs = [t["name"] for t in result]
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _update_user_list(self):
        """Update the user listbox"""
        self.user_listbox.delete(0, tk.END)
        for user in self.users:
            status = "●" if user["is_active"] else "○"
            admin = " [Admin]" if user["is_admin"] else ""
            notes = f" ({user['notes']})" if user.get("notes") else ""
            if len(notes) > 20:
                notes = notes[:17] + "...)"
            self.user_listbox.insert(tk.END, f"{status} {user['username']}{admin}{notes}")
    
    def _update_user_list_and_reselect(self, username_to_select=None):
        """Update user list and reselect a user by username"""
        self._update_user_list()
        
        # Reselect the user by username if provided
        if username_to_select:
            for i, user in enumerate(self.users):
                if user["username"] == username_to_select:
                    self.user_listbox.selection_clear(0, tk.END)
                    self.user_listbox.selection_set(i)
                    self.user_listbox.see(i)
                    # Update selected_user with FRESH data from the new list
                    self.selected_user = user
                    self._show_user_details()
                    break
    
    def _on_user_select(self, event):
        """Handle user selection"""
        selection = self.user_listbox.curselection()
        if not selection:
            return
        
        self.selected_user = self.users[selection[0]]
        self._show_user_details()
    
    def _show_user_details(self):
        """Show details for selected user"""
        # Clear existing widgets
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        
        if not self.selected_user:
            self.no_user_label = tk.Label(
                self.details_frame,
                text="Select a user to view details",
                fg=self.text_secondary,
                bg=self.frame_bg,
                font=self.label_font
            )
            self.no_user_label.pack(expand=True)
            return
        
        user = self.selected_user
        
        # Check if this is the protected main admin user
        is_main_admin = user["username"].lower() == "admin"
        
        # Username
        row = tk.Frame(self.details_frame, bg=self.frame_bg)
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Username:", fg=self.text_secondary, bg=self.frame_bg, 
                width=12, anchor="e", font=self.label_font).pack(side=tk.LEFT)
        tk.Label(row, text=user["username"], fg=self.text_color, bg=self.frame_bg, 
                font=self.subtitle_font).pack(side=tk.LEFT, padx=10)
        
        # Show protected notice for main admin
        if is_main_admin:
            notice_frame = tk.Frame(self.details_frame, bg="#d4a017", relief='flat')
            notice_frame.pack(fill=tk.X, pady=10, padx=5)
            tk.Label(
                notice_frame,
                text="🔒 This is the main administrator account and cannot be modified or deleted.",
                fg="white",
                bg="#d4a017",
                font=self.label_font,
                pady=8,
                padx=10
            ).pack()
        
        # Status
        row = tk.Frame(self.details_frame, bg=self.frame_bg)
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Status:", fg=self.text_secondary, bg=self.frame_bg, 
                width=12, anchor="e", font=self.label_font).pack(side=tk.LEFT)
        
        self.active_var = tk.BooleanVar(value=user["is_active"])
        active_rb = tk.Radiobutton(row, text="Active", variable=self.active_var, value=True, bg=self.frame_bg, 
                      fg=self.text_color, selectcolor=self.entry_bg, activebackground=self.frame_bg,
                      font=self.label_font, state=tk.DISABLED if is_main_admin else tk.NORMAL)
        active_rb.pack(side=tk.LEFT, padx=10)
        disabled_rb = tk.Radiobutton(row, text="Disabled", variable=self.active_var, value=False, bg=self.frame_bg, 
                      fg=self.text_color, selectcolor=self.entry_bg, activebackground=self.frame_bg,
                      font=self.label_font, state=tk.DISABLED if is_main_admin else tk.NORMAL)
        disabled_rb.pack(side=tk.LEFT)
        
        # Admin
        row = tk.Frame(self.details_frame, bg=self.frame_bg)
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Admin:", fg=self.text_secondary, bg=self.frame_bg, 
                width=12, anchor="e", font=self.label_font).pack(side=tk.LEFT)
        
        self.admin_var = tk.BooleanVar(value=user["is_admin"])
        admin_cb = tk.Checkbutton(row, text="Administrator", variable=self.admin_var, bg=self.frame_bg, 
                      fg=self.text_color, selectcolor=self.entry_bg, activebackground=self.frame_bg,
                      font=self.label_font, state=tk.DISABLED if is_main_admin else tk.NORMAL)
        admin_cb.pack(side=tk.LEFT, padx=10)
        
        # Last login
        row = tk.Frame(self.details_frame, bg=self.frame_bg)
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Last Login:", fg=self.text_secondary, bg=self.frame_bg, 
                width=12, anchor="e", font=self.label_font).pack(side=tk.LEFT)
        last_login = user["last_login"] if user["last_login"] else "Never"
        if "T" in str(last_login):
            last_login = last_login.replace("T", " ")[:19]
        tk.Label(row, text=last_login, fg=self.text_color, bg=self.frame_bg,
                font=self.label_font).pack(side=tk.LEFT, padx=10)
        
        # Notes
        row = tk.Frame(self.details_frame, bg=self.frame_bg)
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Notes:", fg=self.text_secondary, bg=self.frame_bg, 
                width=12, anchor="e", font=self.label_font).pack(side=tk.LEFT)
        self.notes_var = tk.StringVar(value=user.get("notes", "") or "")
        self.notes_entry = tk.Entry(row, textvariable=self.notes_var, width=40, 
                                   bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg,
                                   font=self.text_font, state=tk.DISABLED if is_main_admin else tk.NORMAL)
        self.notes_entry.pack(side=tk.LEFT, padx=10)
        
        # Separator
        tk.Frame(self.details_frame, bg=self.header_bg, height=1).pack(fill=tk.X, pady=15)
        
        # Permissions header
        tk.Label(self.details_frame, text="Tab Permissions", fg=self.text_color, bg=self.frame_bg,
                font=self.subtitle_font).pack(anchor="w")
        
        # Permissions checkboxes
        perm_frame = tk.Frame(self.details_frame, bg=self.frame_bg)
        perm_frame.pack(fill=tk.X, pady=10)
        
        self.perm_vars = {}
        for tab in self.tabs:
            var = tk.BooleanVar(value=user["permissions"].get(tab, False))
            self.perm_vars[tab] = var
            cb = tk.Checkbutton(
                perm_frame,
                text=tab,
                variable=var,
                bg=self.frame_bg,
                fg=self.text_color,
                selectcolor=self.entry_bg,
                activebackground=self.frame_bg,
                font=self.label_font,
                state=tk.DISABLED if is_main_admin else tk.NORMAL
            )
            cb.pack(anchor="w", pady=2)
        
        # Buttons (only show if not the main admin)
        if not is_main_admin:
            btn_frame = tk.Frame(self.details_frame, bg=self.frame_bg)
            btn_frame.pack(fill=tk.X, pady=20)
            
            ttk.Button(btn_frame, text="Save Changes", command=self._save_user,
                      style="Blue.TButton").pack(side=tk.LEFT)
            ttk.Button(btn_frame, text="Reset Password", command=self._reset_password,
                      style="Gray.TButton").pack(side=tk.LEFT, padx=10)
            ttk.Button(btn_frame, text="Delete User", command=self._delete_user,
                      style="Red.TButton").pack(side=tk.RIGHT)
    
    def _save_user(self):
        """Save user changes"""
        if not self.selected_user:
            return
        
        # Capture current values to avoid race conditions with async refresh
        user_id = self.selected_user["id"]
        username = self.selected_user["username"]
        
        # Protect main admin user
        if username.lower() == "admin":
            messagebox.showerror("Error", "The main admin account cannot be modified.")
            return
        
        is_admin = self.admin_var.get()
        is_active = self.active_var.get()
        notes = self.notes_var.get()
        perms = {tab: var.get() for tab, var in self.perm_vars.items()}
        
        def do_save():
            # Update user info (without permissions)
            success, result = self.api.update_user(
                user_id,
                is_admin=is_admin,
                is_active=is_active,
                notes=notes
            )
            
            if not success:
                self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to update user: {result}"))
                return
            
            # Update permissions via the dedicated permissions endpoint
            success, result = self.api.update_permissions(user_id, perms)
            
            if not success:
                self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to update permissions: {result}"))
                return
            
            self.parent.after(0, lambda: messagebox.showinfo("Success", "User updated successfully"))
            self.parent.after(0, self._load_data)
        
        threading.Thread(target=do_save, daemon=True).start()
    
    def _reset_password(self):
        """Reset user password"""
        if not self.selected_user:
            return
        
        # Capture user data to avoid race conditions
        user_id = self.selected_user["id"]
        username = self.selected_user["username"]
        
        # Protect main admin user
        if username.lower() == "admin":
            messagebox.showerror("Error", "The main admin account password cannot be reset from here.")
            return
        
        dialog = PasswordResetDialog(self.parent, username, self)
        self.parent.wait_window(dialog.window)
        
        if dialog.result:
            new_password = dialog.result
            def do_reset():
                success, result = self.api.update_user(user_id, password=new_password)
                if success:
                    self.parent.after(0, lambda: messagebox.showinfo("Success", "Password reset successfully"))
                else:
                    self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to reset password: {result}"))
            
            threading.Thread(target=do_reset, daemon=True).start()
    
    def _delete_user(self):
        """Delete user"""
        if not self.selected_user:
            return
        
        # Capture user data to avoid race conditions
        user_id = self.selected_user["id"]
        username = self.selected_user["username"]
        
        # Protect main admin user
        if username.lower() == "admin":
            messagebox.showerror("Error", "The main admin account cannot be deleted.")
            return
        
        if username == self.auth.username:
            messagebox.showerror("Error", "Cannot delete yourself")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete user '{username}'?\n\nThis cannot be undone."):
            def do_delete():
                success, result = self.api.delete_user(user_id)
                if success:
                    self.selected_user = None
                    self.parent.after(0, self._load_data)
                    self.parent.after(0, self._show_user_details)
                else:
                    self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to delete user: {result}"))
            
            threading.Thread(target=do_delete, daemon=True).start()
    
    def _new_user_dialog(self):
        """Show new user dialog"""
        dialog = NewUserDialog(self.parent, self)
        self.parent.wait_window(dialog.window)
        
        if dialog.result:
            new_username = dialog.result["username"]
            
            def do_create():
                success, result = self.api.create_user(
                    dialog.result["username"],
                    dialog.result["password"],
                    dialog.result["is_admin"],
                    dialog.result.get("notes")
                )
                if success:
                    self.parent.after(0, lambda: messagebox.showinfo("Success", "User created successfully"))
                    # Select the newly created user after data loads
                    self.parent.after(0, lambda: self._load_data_and_select(new_username))
                else:
                    self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to create user: {result}"))
            
            threading.Thread(target=do_create, daemon=True).start()
    
    def _load_data_and_select(self, username_to_select):
        """Load data and then select a specific user by username"""
        def do_load():
            # Load users
            success, result = self.api.get_users()
            if success:
                self.users = result
                self.parent.after(0, lambda: self._update_user_list_and_reselect(username_to_select))
            
            # Load tabs
            success, result = self.api.get_tabs()
            if success:
                self.tabs = [t["name"] for t in result]
        
        threading.Thread(target=do_load, daemon=True).start()

# ============================================================================
# Standalone Test Mode
# ============================================================================

if __name__ == "__main__":
    """
    Test mode for user_managment.py
    This allows you to run the module directly for testing
    """
    print("=" * 60)
    print("User Management Module - Test Mode")
    print("=" * 60)
    print()
    
    # Create a test window
    root = tk.Tk()
    root.title("User Management - Test Mode")
    root.geometry("1000x700")
    
    # Mock auth client for testing
    class MockAuthClient:
        def __init__(self):
            self.token = "test_token"
            self.username = "test_admin"
            self.is_admin = True
        
        def log_action(self, action, target):
            print(f"[AUDIT LOG] {action}: {target}")
    
    # Mock colors function
    def mock_get_colors():
        return {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'frame_bg': '#3c3c3c',
            'header_bg': '#4a4a4a',
            'text_secondary': '#cccccc',
            'primary': '#4a90e2',
            'success': '#27ae60',
            'danger': '#e74c3c'
        }
    
    # Create test panel
    try:
        auth_client = MockAuthClient()
        panel = UserManagementPanel(root, auth_client, mock_get_colors)
        
        print("✅ User Management panel loaded successfully!")
        print()
        print("Test Mode Info:")
        print(f"  - Using mock authentication")
        print(f"  - API calls will fail (expected)")
        print(f"  - UI should render correctly")
        print(f"  - Test theme, layout, and controls")
        print()
        print("Close the window to exit test mode.")
        print("=" * 60)
        
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error loading User Management panel: {e}")
        import traceback
        traceback.print_exc()