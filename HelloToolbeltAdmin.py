import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import json
from datetime import datetime, timedelta
import threading

# ============================================================================
# Configuration
# ============================================================================

# Update this to your Render URL after deployment
API_BASE_URL = "https://hellotoolbelt-auth.onrender.com/"  # CHANGE THIS

# For local development:
# API_BASE_URL = "http://localhost:8000"

# ============================================================================
# API Client
# ============================================================================

class APIClient:
    """Handles all communication with the auth server"""
    
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.username = None
    
    def _headers(self):
        """Get headers with auth token"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def login(self, username, password):
        """Login as admin"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login/admin",
                json={"username": username, "password": password},
                timeout=60  # Increased for Render free tier cold starts
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                self.username = data["username"]
                return True, data
            elif response.status_code == 403:
                try:
                    return False, response.json().get("detail", "Admin access required")
                except:
                    return False, "Admin access required"
            elif response.status_code == 401:
                try:
                    return False, response.json().get("detail", "Invalid credentials")
                except:
                    return False, "Invalid credentials"
            elif response.status_code == 502 or response.status_code == 503:
                return False, "Server is starting up. Please wait 30 seconds and try again."
            else:
                try:
                    return False, response.json().get("detail", f"Login failed (HTTP {response.status_code})")
                except:
                    return False, f"Login failed (HTTP {response.status_code}): {response.text[:100]}"
        except requests.exceptions.Timeout:
            return False, "Server is waking up (free tier). Please try again in 30 seconds."
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to server at {self.base_url}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def logout(self):
        """Logout and clear token"""
        if self.token:
            try:
                requests.post(
                    f"{self.base_url}/auth/logout",
                    headers=self._headers(),
                    timeout=15
                )
            except:
                pass
        self.token = None
        self.username = None
    
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
    
    def create_user(self, username, password, is_admin=False, notes=None):
        """Create a new user"""
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
    
    def update_user(self, user_id, is_admin=None, is_active=None, password=None, notes=None):
        """Update a user"""
        try:
            data = {}
            if is_admin is not None:
                data["is_admin"] = is_admin
            if is_active is not None:
                data["is_active"] = is_active
            if password:
                data["password"] = password
            if notes is not None:
                data["notes"] = notes
            
            response = requests.put(
                f"{self.base_url}/admin/users/{user_id}",
                headers=self._headers(),
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to update user")
        except Exception as e:
            return False, str(e)
    
    def delete_user(self, user_id):
        """Delete a user"""
        try:
            response = requests.delete(
                f"{self.base_url}/admin/users/{user_id}",
                headers=self._headers(),
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to delete user")
        except Exception as e:
            return False, str(e)
    
    def update_permissions(self, user_id, permissions):
        """Update all permissions for a user"""
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
    
    def get_tabs(self):
        """Get all tabs"""
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
    
    def get_audit_logs(self, username=None, action=None, start_date=None, end_date=None, limit=100, offset=0):
        """Get audit logs with filters"""
        try:
            params = {"limit": limit, "offset": offset}
            if username:
                params["username"] = username
            if action:
                params["action"] = action
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            response = requests.get(
                f"{self.base_url}/admin/audit-logs",
                headers=self._headers(),
                params=params,
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get("detail", "Failed to get audit logs")
        except Exception as e:
            return False, str(e)
    
    def get_audit_actions(self):
        """Get unique actions for filtering"""
        try:
            response = requests.get(
                f"{self.base_url}/admin/audit-logs/actions",
                headers=self._headers(),
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, []
        except:
            return False, []
    
    def export_audit_logs(self, username=None, action=None, start_date=None, end_date=None):
        """Export audit logs as CSV"""
        try:
            params = {}
            if username:
                params["username"] = username
            if action:
                params["action"] = action
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            response = requests.get(
                f"{self.base_url}/admin/audit-logs/export",
                headers=self._headers(),
                params=params,
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json().get("csv", "")
            return False, response.json().get("detail", "Failed to export")
        except Exception as e:
            return False, str(e)


# ============================================================================
# Login Window
# ============================================================================

class LoginWindow:
    """Login dialog for admin authentication"""
    
    def __init__(self, api_client, on_success):
        self.api = api_client
        self.on_success = on_success
        
        self.window = tk.Tk()
        self.window.title("HelloToolbelt Admin - Login")
        self.window.geometry("450x300")
        self.window.resizable(False, False)
        self.window.configure(bg="#2b2b2b")
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 225
        y = (self.window.winfo_screenheight() // 2) - 150
        self.window.geometry(f"+{x}+{y}")
        
        self._create_widgets()
        
        # Bind Enter key
        self.window.bind("<Return>", lambda e: self._login())
    
    def _create_widgets(self):
        # Title
        title = tk.Label(
            self.window,
            text="HelloToolbelt Admin",
            font=("Arial", 18, "bold"),
            fg="#ffffff",
            bg="#2b2b2b"
        )
        title.pack(pady=(30, 5))
        
        subtitle = tk.Label(
            self.window,
            text="Administrator Login",
            font=("Arial", 10),
            fg="#888888",
            bg="#2b2b2b"
        )
        subtitle.pack(pady=(0, 20))
        
        # Username
        frame = tk.Frame(self.window, bg="#2b2b2b")
        frame.pack(pady=5)
        
        tk.Label(frame, text="Username:", fg="#ffffff", bg="#2b2b2b", width=10, anchor="e").pack(side=tk.LEFT)
        self.username_entry = tk.Entry(frame, width=25, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        # Password
        frame2 = tk.Frame(self.window, bg="#2b2b2b")
        frame2.pack(pady=5)
        
        tk.Label(frame2, text="Password:", fg="#ffffff", bg="#2b2b2b", width=10, anchor="e").pack(side=tk.LEFT)
        self.password_entry = tk.Entry(frame2, width=25, show="●", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.password_entry.pack(side=tk.LEFT, padx=5)
        
        # Error label
        self.error_label = tk.Label(self.window, text="", fg="#ff6b6b", bg="#2b2b2b")
        self.error_label.pack(pady=10)
        
        # Setup ttk style for login button
        style = ttk.Style()
        style.configure("Login.TButton",
            padding=(20, 10),
            font=("Arial", 11)
        )
        
        # Login button
        self.login_btn = ttk.Button(
            self.window,
            text="Login",
            command=self._login,
            style="Login.TButton",
            width=15
        )
        self.login_btn.pack(pady=10)
        
        self.username_entry.focus()
    
    def _login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.config(text="Please enter username and password")
            return
        
        self.login_btn.config(state="disabled")
        self.login_btn.config(text="Logging in...")
        self.error_label.config(text="")
        self.window.update()
        
        success, result = self.api.login(username, password)
        
        if success:
            self.window.destroy()
            self.on_success()
        else:
            self.error_label.config(text=result)
            self.login_btn.config(state="normal")
            self.login_btn.config(text="Login")
    
    def run(self):
        self.window.mainloop()


# ============================================================================
# Main Admin Window
# ============================================================================

class AdminWindow:
    """Main admin interface"""
    
    def __init__(self, api_client):
        self.api = api_client
        self.users = []
        self.tabs = []
        self.selected_user = None
        
        self.window = tk.Tk()
        self.window.title(f"HelloToolbelt Admin - {self.api.username}")
        self.window.geometry("1100x800")
        self.window.configure(bg="#2b2b2b")
        self.window.minsize(900, 700)
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 550
        y = (self.window.winfo_screenheight() // 2) - 350
        self.window.geometry(f"+{x}+{y}")
        
        self._setup_styles()
        self._create_widgets()
        self._load_data()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Treeview styles
        style.configure("Treeview",
            background="#3c3c3c",
            foreground="#ffffff",
            fieldbackground="#3c3c3c",
            borderwidth=0
        )
        style.configure("Treeview.Heading",
            background="#4a4a4a",
            foreground="#ffffff",
            borderwidth=0
        )
        style.map("Treeview",
            background=[("selected", "#4a9eff")],
            foreground=[("selected", "#ffffff")]
        )
        
        # Custom button styles for macOS compatibility
        style.configure("Blue.TButton",
            background="#4a9eff",
            foreground="#000000",
            padding=(10, 5)
        )
        style.map("Blue.TButton",
            background=[("active", "#3a8eef")],
            foreground=[("active", "#000000")]
        )
        
        style.configure("Gray.TButton",
            background="#666666",
            foreground="#000000",
            padding=(10, 5)
        )
        style.map("Gray.TButton",
            background=[("active", "#555555")],
            foreground=[("active", "#000000")]
        )
        
        style.configure("Red.TButton",
            background="#dc3545",
            foreground="#000000",
            padding=(10, 5)
        )
        style.map("Red.TButton",
            background=[("active", "#c82333")],
            foreground=[("active", "#000000")]
        )
        
        style.configure("Dark.TButton",
            background="#555555",
            foreground="#000000",
            padding=(5, 3)
        )
        style.map("Dark.TButton",
            background=[("active", "#444444")],
            foreground=[("active", "#000000")]
        )
    
    def _create_widgets(self):
        """Create the main UI"""
        # Main container
        main_frame = tk.Frame(self.window, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section (Users and Details)
        top_frame = tk.Frame(main_frame, bg="#2b2b2b")
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - User list
        left_frame = tk.Frame(top_frame, bg="#3c3c3c", width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="Users", font=("Arial", 12, "bold"), fg="#ffffff", bg="#3c3c3c").pack(pady=10)
        
        # User listbox
        self.user_listbox = tk.Listbox(
            left_frame,
            bg="#2b2b2b",
            fg="#ffffff",
            selectbackground="#4a9eff",
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            font=("Arial", 10)
        )
        self.user_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.user_listbox.bind("<<ListboxSelect>>", self._on_user_select)
        
        # New user button
        ttk.Button(
            left_frame,
            text="+ New User",
            command=self._new_user_dialog,
            style="Blue.TButton"
        ).pack(pady=10)
        
        # Right panel - User details
        right_frame = tk.Frame(top_frame, bg="#3c3c3c")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_frame, text="User Details", font=("Arial", 12, "bold"), fg="#ffffff", bg="#3c3c3c").pack(pady=10)
        
        self.details_frame = tk.Frame(right_frame, bg="#3c3c3c")
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Placeholder when no user selected
        self.no_user_label = tk.Label(
            self.details_frame,
            text="Select a user to view details",
            fg="#888888",
            bg="#3c3c3c",
            font=("Arial", 11)
        )
        self.no_user_label.pack(expand=True)
        
        # Bottom section - Audit logs
        bottom_frame = tk.Frame(main_frame, bg="#3c3c3c", height=320)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        bottom_frame.pack_propagate(False)
        
        # Audit log header
        log_header = tk.Frame(bottom_frame, bg="#3c3c3c")
        log_header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(log_header, text="Audit Logs", font=("Arial", 12, "bold"), fg="#ffffff", bg="#3c3c3c").pack(side=tk.LEFT)
        
        ttk.Button(
            log_header,
            text="Export CSV",
            command=self._export_logs,
            style="Blue.TButton"
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            log_header,
            text="Refresh",
            command=self._load_logs,
            style="Gray.TButton"
        ).pack(side=tk.RIGHT, padx=5)
        
        # Filters - Row 1
        filter_frame = tk.Frame(bottom_frame, bg="#3c3c3c")
        filter_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(filter_frame, text="User:", fg="#ffffff", bg="#3c3c3c").pack(side=tk.LEFT)
        self.log_user_var = tk.StringVar(value="All")
        self.log_user_combo = ttk.Combobox(filter_frame, textvariable=self.log_user_var, width=15, state="readonly")
        self.log_user_combo.pack(side=tk.LEFT, padx=5)
        self.log_user_combo.bind("<<ComboboxSelected>>", lambda e: self._load_logs())
        
        tk.Label(filter_frame, text="Action:", fg="#ffffff", bg="#3c3c3c").pack(side=tk.LEFT, padx=(15, 0))
        self.log_action_var = tk.StringVar(value="All")
        self.log_action_combo = ttk.Combobox(filter_frame, textvariable=self.log_action_var, width=15, state="readonly")
        self.log_action_combo.pack(side=tk.LEFT, padx=5)
        self.log_action_combo.bind("<<ComboboxSelected>>", lambda e: self._load_logs())
        
        # Filters - Row 2 (Date Range)
        filter_frame2 = tk.Frame(bottom_frame, bg="#3c3c3c")
        filter_frame2.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        tk.Label(filter_frame2, text="From:", fg="#ffffff", bg="#3c3c3c").pack(side=tk.LEFT)
        self.start_date_var = tk.StringVar(value="")
        self.start_date_entry = tk.Entry(filter_frame2, textvariable=self.start_date_var, width=12, bg="#2b2b2b", fg="#ffffff", insertbackground="#ffffff")
        self.start_date_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(filter_frame2, text="(YYYY-MM-DD)", fg="#888888", bg="#3c3c3c", font=("Arial", 8)).pack(side=tk.LEFT)
        
        tk.Label(filter_frame2, text="To:", fg="#ffffff", bg="#3c3c3c").pack(side=tk.LEFT, padx=(15, 0))
        self.end_date_var = tk.StringVar(value="")
        self.end_date_entry = tk.Entry(filter_frame2, textvariable=self.end_date_var, width=12, bg="#2b2b2b", fg="#ffffff", insertbackground="#ffffff")
        self.end_date_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(filter_frame2, text="(YYYY-MM-DD)", fg="#888888", bg="#3c3c3c", font=("Arial", 8)).pack(side=tk.LEFT)
        
        ttk.Button(
            filter_frame2,
            text="Apply",
            command=self._load_logs,
            style="Blue.TButton",
            width=8
        ).pack(side=tk.LEFT, padx=(15, 5))
        
        ttk.Button(
            filter_frame2,
            text="Clear",
            command=self._clear_date_filters,
            style="Gray.TButton",
            width=8
        ).pack(side=tk.LEFT)
        
        # Quick date buttons
        filter_frame3 = tk.Frame(bottom_frame, bg="#3c3c3c")
        filter_frame3.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        tk.Label(filter_frame3, text="Quick:", fg="#ffffff", bg="#3c3c3c").pack(side=tk.LEFT)
        
        ttk.Button(filter_frame3, text="Today", command=lambda: self._set_date_range("today"),
                  style="Dark.TButton", width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame3, text="Yesterday", command=lambda: self._set_date_range("yesterday"),
                  style="Dark.TButton", width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame3, text="Last 7 Days", command=lambda: self._set_date_range("week"),
                  style="Dark.TButton", width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame3, text="Last 30 Days", command=lambda: self._set_date_range("month"),
                  style="Dark.TButton", width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame3, text="All Time", command=lambda: self._set_date_range("all"),
                  style="Dark.TButton", width=10).pack(side=tk.LEFT, padx=2)
        
        # Log treeview
        log_tree_frame = tk.Frame(bottom_frame, bg="#3c3c3c")
        log_tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("timestamp", "username", "action", "target")
        self.log_tree = ttk.Treeview(log_tree_frame, columns=columns, show="headings", height=8)
        
        self.log_tree.heading("timestamp", text="Timestamp")
        self.log_tree.heading("username", text="User")
        self.log_tree.heading("action", text="Action")
        self.log_tree.heading("target", text="Target")
        
        self.log_tree.column("timestamp", width=160)
        self.log_tree.column("username", width=120)
        self.log_tree.column("action", width=120)
        self.log_tree.column("target", width=300)
        
        scrollbar = ttk.Scrollbar(log_tree_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _load_data(self):
        """Load users and tabs from server"""
        # Load users
        success, result = self.api.get_users()
        if success:
            self.users = result
            self._update_user_list()
        else:
            messagebox.showerror("Error", f"Failed to load users: {result}")
        
        # Load tabs
        success, result = self.api.get_tabs()
        if success:
            self.tabs = [t["name"] for t in result]
        
        # Load audit log filters
        success, actions = self.api.get_audit_actions()
        self.log_action_combo["values"] = ["All"] + (actions if success else [])
        
        usernames = ["All"] + [u["username"] for u in self.users]
        self.log_user_combo["values"] = usernames
        
        # Load logs
        self._load_logs()
    
    def _update_user_list(self):
        """Update the user listbox"""
        self.user_listbox.delete(0, tk.END)
        for user in self.users:
            status = "●" if user["is_active"] else "○"
            admin = " [Admin]" if user["is_admin"] else ""
            notes = f" ({user['notes']})" if user.get("notes") else ""
            # Truncate notes if too long
            if len(notes) > 25:
                notes = notes[:22] + "...)"
            self.user_listbox.insert(tk.END, f"{status} {user['username']}{admin}{notes}")
    
    def _on_user_select(self, event):
        """Handle user selection"""
        selection = self.user_listbox.curselection()
        if not selection:
            return
        
        self.selected_user = self.users[selection[0]]
        self._show_user_details()
        
        # Filter audit logs to show only this user's logs
        self.log_user_var.set(self.selected_user["username"])
        self._load_logs()
    
    def _show_user_details(self):
        """Show details for selected user"""
        # Clear existing widgets
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        
        if not self.selected_user:
            self.no_user_label = tk.Label(
                self.details_frame,
                text="Select a user to view details",
                fg="#888888",
                bg="#3c3c3c"
            )
            self.no_user_label.pack(expand=True)
            return
        
        user = self.selected_user
        
        # Username
        row = tk.Frame(self.details_frame, bg="#3c3c3c")
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Username:", fg="#888888", bg="#3c3c3c", width=12, anchor="e").pack(side=tk.LEFT)
        tk.Label(row, text=user["username"], fg="#ffffff", bg="#3c3c3c", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        
        # Status
        row = tk.Frame(self.details_frame, bg="#3c3c3c")
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Status:", fg="#888888", bg="#3c3c3c", width=12, anchor="e").pack(side=tk.LEFT)
        
        self.active_var = tk.BooleanVar(value=user["is_active"])
        tk.Radiobutton(row, text="Active", variable=self.active_var, value=True, bg="#3c3c3c", fg="#ffffff",
                      selectcolor="#2b2b2b", activebackground="#3c3c3c").pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(row, text="Disabled", variable=self.active_var, value=False, bg="#3c3c3c", fg="#ffffff",
                      selectcolor="#2b2b2b", activebackground="#3c3c3c").pack(side=tk.LEFT)
        
        # Admin
        row = tk.Frame(self.details_frame, bg="#3c3c3c")
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Admin:", fg="#888888", bg="#3c3c3c", width=12, anchor="e").pack(side=tk.LEFT)
        
        self.admin_var = tk.BooleanVar(value=user["is_admin"])
        tk.Checkbutton(row, text="Administrator", variable=self.admin_var, bg="#3c3c3c", fg="#ffffff",
                      selectcolor="#2b2b2b", activebackground="#3c3c3c").pack(side=tk.LEFT, padx=10)
        
        # Last login
        row = tk.Frame(self.details_frame, bg="#3c3c3c")
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Last Login:", fg="#888888", bg="#3c3c3c", width=12, anchor="e").pack(side=tk.LEFT)
        last_login = user["last_login"] if user["last_login"] else "Never"
        tk.Label(row, text=last_login, fg="#ffffff", bg="#3c3c3c").pack(side=tk.LEFT, padx=10)
        
        # Notes
        row = tk.Frame(self.details_frame, bg="#3c3c3c")
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Notes:", fg="#888888", bg="#3c3c3c", width=12, anchor="e").pack(side=tk.LEFT)
        self.notes_var = tk.StringVar(value=user.get("notes", "") or "")
        self.notes_entry = tk.Entry(row, textvariable=self.notes_var, width=40, bg="#2b2b2b", fg="#ffffff", insertbackground="#ffffff")
        self.notes_entry.pack(side=tk.LEFT, padx=10)
        
        # Separator
        tk.Frame(self.details_frame, bg="#555555", height=1).pack(fill=tk.X, pady=15)
        
        # Permissions header
        tk.Label(self.details_frame, text="Tab Permissions", fg="#ffffff", bg="#3c3c3c",
                font=("Arial", 11, "bold")).pack(anchor="w")
        
        # Permissions checkboxes
        perm_frame = tk.Frame(self.details_frame, bg="#3c3c3c")
        perm_frame.pack(fill=tk.X, pady=10)
        
        self.perm_vars = {}
        for tab in self.tabs:
            var = tk.BooleanVar(value=user["permissions"].get(tab, False))
            self.perm_vars[tab] = var
            tk.Checkbutton(
                perm_frame,
                text=tab,
                variable=var,
                bg="#3c3c3c",
                fg="#ffffff",
                selectcolor="#2b2b2b",
                activebackground="#3c3c3c"
            ).pack(anchor="w", pady=2)
        
        # Buttons
        btn_frame = tk.Frame(self.details_frame, bg="#3c3c3c")
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(
            btn_frame,
            text="Save Changes",
            command=self._save_user,
            style="Blue.TButton"
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            btn_frame,
            text="Reset Password",
            command=self._reset_password,
            style="Gray.TButton"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            btn_frame,
            text="Delete User",
            command=self._delete_user,
            style="Red.TButton"
        ).pack(side=tk.RIGHT)
    
    def _save_user(self):
        """Save user changes"""
        if not self.selected_user:
            return
        
        # Update user info
        success, result = self.api.update_user(
            self.selected_user["id"],
            is_admin=self.admin_var.get(),
            is_active=self.active_var.get(),
            notes=self.notes_var.get()
        )
        
        if not success:
            messagebox.showerror("Error", f"Failed to update user: {result}")
            return
        
        # Update permissions
        perms = {tab: var.get() for tab, var in self.perm_vars.items()}
        success, result = self.api.update_permissions(self.selected_user["id"], perms)
        
        if not success:
            messagebox.showerror("Error", f"Failed to update permissions: {result}")
            return
        
        messagebox.showinfo("Success", "User updated successfully")
        self._load_data()
    
    def _reset_password(self):
        """Reset user password"""
        if not self.selected_user:
            return
        
        dialog = PasswordDialog(self.window, self.selected_user["username"])
        self.window.wait_window(dialog.window)
        
        if dialog.result:
            success, result = self.api.update_user(self.selected_user["id"], password=dialog.result)
            if success:
                messagebox.showinfo("Success", "Password reset successfully")
            else:
                messagebox.showerror("Error", f"Failed to reset password: {result}")
    
    def _delete_user(self):
        """Delete user"""
        if not self.selected_user:
            return
        
        if self.selected_user["username"] == self.api.username:
            messagebox.showerror("Error", "Cannot delete yourself")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete user '{self.selected_user['username']}'?\n\nThis cannot be undone."):
            success, result = self.api.delete_user(self.selected_user["id"])
            if success:
                self.selected_user = None
                self._load_data()
                self._show_user_details()
            else:
                messagebox.showerror("Error", f"Failed to delete user: {result}")
    
    def _new_user_dialog(self):
        """Show new user dialog"""
        dialog = NewUserDialog(self.window)
        self.window.wait_window(dialog.window)
        
        if dialog.result:
            success, result = self.api.create_user(
                dialog.result["username"],
                dialog.result["password"],
                dialog.result["is_admin"],
                dialog.result.get("notes")
            )
            if success:
                messagebox.showinfo("Success", "User created successfully")
                self._load_data()
            else:
                messagebox.showerror("Error", f"Failed to create user: {result}")
    
    def _load_logs(self):
        """Load audit logs"""
        # Clear existing
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        
        # Get filters
        username = None if self.log_user_var.get() == "All" else self.log_user_var.get()
        action = None if self.log_action_var.get() == "All" else self.log_action_var.get()
        
        # Get date filters
        start_date = self.start_date_var.get().strip() if self.start_date_var.get().strip() else None
        end_date = self.end_date_var.get().strip() if self.end_date_var.get().strip() else None
        
        # Add time component to dates for proper filtering
        if start_date:
            start_date = f"{start_date}T00:00:00"
        if end_date:
            end_date = f"{end_date}T23:59:59"
        
        success, logs = self.api.get_audit_logs(
            username=username, 
            action=action, 
            start_date=start_date,
            end_date=end_date,
            limit=500
        )
        
        if success:
            for log in logs:
                # Format timestamp for display
                timestamp = log["timestamp"]
                if "T" in timestamp:
                    timestamp = timestamp.replace("T", " ")[:19]
                self.log_tree.insert("", tk.END, values=(
                    timestamp,
                    log["username"],
                    log["action"],
                    log["target"] or ""
                ))
    
    def _clear_date_filters(self):
        """Clear date filter fields"""
        self.start_date_var.set("")
        self.end_date_var.set("")
        self._load_logs()
    
    def _set_date_range(self, range_type):
        """Set quick date ranges"""
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        if range_type == "today":
            self.start_date_var.set(today.strftime("%Y-%m-%d"))
            self.end_date_var.set(today.strftime("%Y-%m-%d"))
        elif range_type == "yesterday":
            yesterday = today - timedelta(days=1)
            self.start_date_var.set(yesterday.strftime("%Y-%m-%d"))
            self.end_date_var.set(yesterday.strftime("%Y-%m-%d"))
        elif range_type == "week":
            week_ago = today - timedelta(days=7)
            self.start_date_var.set(week_ago.strftime("%Y-%m-%d"))
            self.end_date_var.set(today.strftime("%Y-%m-%d"))
        elif range_type == "month":
            month_ago = today - timedelta(days=30)
            self.start_date_var.set(month_ago.strftime("%Y-%m-%d"))
            self.end_date_var.set(today.strftime("%Y-%m-%d"))
        elif range_type == "all":
            self.start_date_var.set("")
            self.end_date_var.set("")
        
        self._load_logs()
    
    def _export_logs(self):
        """Export logs to CSV file"""
        username = None if self.log_user_var.get() == "All" else self.log_user_var.get()
        action = None if self.log_action_var.get() == "All" else self.log_action_var.get()
        
        # Get date filters
        start_date = self.start_date_var.get().strip() if self.start_date_var.get().strip() else None
        end_date = self.end_date_var.get().strip() if self.end_date_var.get().strip() else None
        
        if start_date:
            start_date = f"{start_date}T00:00:00"
        if end_date:
            end_date = f"{end_date}T23:59:59"
        
        success, csv_data = self.api.export_audit_logs(
            username=username, 
            action=action,
            start_date=start_date,
            end_date=end_date
        )
        
        if not success:
            messagebox.showerror("Error", f"Failed to export: {csv_data}")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            with open(filename, "w") as f:
                f.write(csv_data)
            messagebox.showinfo("Success", f"Logs exported to {filename}")
    
    def _on_close(self):
        """Handle window close"""
        self.api.logout()
        self.window.destroy()
    
    def run(self):
        self.window.mainloop()


# ============================================================================
# Dialogs
# ============================================================================

def validate_password(password):
    """
    Validate password meets requirements:
    - At least 8 characters
    - Contains at least one number
    - Contains at least one special character
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character (!@#$%^&* etc)"
    
    return True, None


class NewUserDialog:
    """Dialog for creating new user"""
    
    def __init__(self, parent):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("New User")
        self.window.geometry("400x320")
        self.window.configure(bg="#2b2b2b")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center on parent
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 160
        self.window.geometry(f"+{x}+{y}")
        
        # Username
        row = tk.Frame(self.window, bg="#2b2b2b")
        row.pack(fill=tk.X, padx=20, pady=(20, 5))
        tk.Label(row, text="Username:", fg="#ffffff", bg="#2b2b2b", width=10, anchor="e").pack(side=tk.LEFT)
        self.username_entry = tk.Entry(row, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Password
        row = tk.Frame(self.window, bg="#2b2b2b")
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Password:", fg="#ffffff", bg="#2b2b2b", width=10, anchor="e").pack(side=tk.LEFT)
        self.password_entry = tk.Entry(row, show="●", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Password requirements hint
        hint_row = tk.Frame(self.window, bg="#2b2b2b")
        hint_row.pack(fill=tk.X, padx=20, pady=(0, 5))
        tk.Label(hint_row, text="(8+ chars, 1 number, 1 special character)", 
                fg="#888888", bg="#2b2b2b", font=("Arial", 9)).pack(side=tk.LEFT, padx=(95, 0))
        
        # Confirm password
        row = tk.Frame(self.window, bg="#2b2b2b")
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Confirm:", fg="#ffffff", bg="#2b2b2b", width=10, anchor="e").pack(side=tk.LEFT)
        self.confirm_entry = tk.Entry(row, show="●", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.confirm_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Notes
        row = tk.Frame(self.window, bg="#2b2b2b")
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Notes:", fg="#ffffff", bg="#2b2b2b", width=10, anchor="e").pack(side=tk.LEFT)
        self.notes_entry = tk.Entry(row, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.notes_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Admin checkbox
        row = tk.Frame(self.window, bg="#2b2b2b")
        row.pack(fill=tk.X, padx=20, pady=5)
        self.admin_var = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="Administrator", variable=self.admin_var, bg="#2b2b2b", fg="#ffffff",
                      selectcolor="#3c3c3c", activebackground="#2b2b2b").pack(side=tk.LEFT, padx=(90, 0))
        
        # Buttons
        btn_frame = tk.Frame(self.window, bg="#2b2b2b")
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
        
        # Validate password strength
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


class PasswordDialog:
    """Dialog for resetting password"""
    
    def __init__(self, parent, username):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"Reset Password - {username}")
        self.window.geometry("400x180")
        self.window.configure(bg="#2b2b2b")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center on parent
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 90
        self.window.geometry(f"+{x}+{y}")
        
        # New password
        row = tk.Frame(self.window, bg="#2b2b2b")
        row.pack(fill=tk.X, padx=20, pady=(20, 5))
        tk.Label(row, text="New Password:", fg="#ffffff", bg="#2b2b2b", width=12, anchor="e").pack(side=tk.LEFT)
        self.password_entry = tk.Entry(row, show="●", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Password requirements hint
        hint_row = tk.Frame(self.window, bg="#2b2b2b")
        hint_row.pack(fill=tk.X, padx=20, pady=(0, 5))
        tk.Label(hint_row, text="(8+ chars, 1 number, 1 special character)", 
                fg="#888888", bg="#2b2b2b", font=("Arial", 9)).pack(side=tk.LEFT, padx=(110, 0))
        
        # Confirm
        row = tk.Frame(self.window, bg="#2b2b2b")
        row.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(row, text="Confirm:", fg="#ffffff", bg="#2b2b2b", width=12, anchor="e").pack(side=tk.LEFT)
        self.confirm_entry = tk.Entry(row, show="●", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        self.confirm_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(self.window, bg="#2b2b2b")
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
        
        # Validate password strength
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
# Main Entry Point
# ============================================================================

def main():
    api = APIClient(API_BASE_URL)
    
    def on_login_success():
        admin_window = AdminWindow(api)
        admin_window.run()
    
    login_window = LoginWindow(api, on_login_success)
    login_window.run()


if __name__ == "__main__":
    main()