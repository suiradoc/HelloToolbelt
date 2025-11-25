import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from datetime import datetime, timedelta
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
# Audit Logs API Client
# ============================================================================

class AuditLogsAPIClient:
    """Handles audit logs API communication - uses existing auth token"""
    
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
        """Get all users (for filter dropdown)"""
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
    
    def get_audit_logs(self, username=None, action=None, start_date=None, end_date=None, limit=500):
        """
        Get audit logs with filters
        
        Note: Timestamps returned by the API are assumed to be in UTC (Coordinated Universal Time).
        This is standard for backend authentication/audit systems. The timestamps are displayed
        as-is without timezone conversion. To verify the timezone, check the API response format
        for indicators like 'Z' suffix or '+00:00' offset.
        """
        try:
            params = {"limit": limit}
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
            return False, response.json().get("detail", "Failed to get logs")
        except Exception as e:
            return False, str(e)
    
    def get_audit_actions(self):
        """Get list of audit action types"""
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
                timeout=60
            )
            if response.status_code == 200:
                return True, response.text
            return False, response.json().get("detail", "Failed to export")
        except Exception as e:
            return False, str(e)


# ============================================================================
# Audit Logs Panel
# ============================================================================

class AuditLogsPanel:
    """Audit logs panel that can be embedded as a tab in HelloToolbelt"""
    
    # Tab color for HelloToolbelt integration (gold/orange to match admin theme)
    tab_color = '#d4a017'
    
    def __init__(self, parent_frame, auth_client, colors_func):
        """
        Initialize audit logs panel
        
        Args:
            parent_frame: The frame to build the UI in
            auth_client: The auth client from login (has token)
            colors_func: Function to get current color scheme
        """
        self.parent = parent_frame
        self.auth = auth_client
        self.get_colors = colors_func
        self.api = AuditLogsAPIClient(auth_client)
        
        self.users = []
        
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
        
        # Entry colors based on mode
        if self.is_dark_mode:
            self.entry_bg = '#2b2b2b'
            self.entry_fg = '#ffffff'
        else:
            self.entry_bg = '#ffffff'
            self.entry_fg = '#2c3e50'
    
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
        
        # Entry colors based on mode
        if is_dark_mode:
            self.entry_bg = '#2b2b2b'
            self.entry_fg = '#ffffff'
        else:
            self.entry_bg = '#ffffff'
            self.entry_fg = '#2c3e50'
        
        # Clear and recreate the interface
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        # Rebuild UI
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        """Create the audit logs UI"""
        # Main container
        self.main_frame = tk.Frame(self.parent, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header - use tab_color for consistency with the tab
        header_color = self.tab_color
        header_frame = tk.Frame(self.main_frame, bg=header_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        header_content = tk.Frame(header_frame, bg=header_color)
        header_content.pack(fill=tk.X, padx=20, pady=12)
        
        header_icon = tk.Label(header_content, text="📋", font=('Segoe UI', 18), 
                              bg=header_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_text_frame = tk.Frame(header_content, bg=header_color)
        header_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        header_title = tk.Label(header_text_frame, text="Audit Logs", font=self.title_font,
                               bg=header_color, fg='white')
        header_title.pack(anchor="w")
        
        header_subtitle = tk.Label(header_text_frame, text="View and export system activity logs",
                                  font=("Segoe UI", 9), bg=header_color, fg='#ecf0f1')
        header_subtitle.pack(anchor="w", pady=(2, 0))
        
        # Logs section
        logs_frame = tk.Frame(self.main_frame, bg=self.frame_bg)
        logs_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_audit_log_section(logs_frame)
    
    def _create_audit_log_section(self, parent):
        """Create the audit log section"""
        # Header
        log_header = tk.Frame(parent, bg=self.frame_bg)
        log_header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(log_header, text="Activity Logs", font=self.subtitle_font, 
                fg=self.text_color, bg=self.frame_bg).pack(side=tk.LEFT)
        
        ttk.Button(log_header, text="Export CSV", command=self._export_logs,
                  style="Blue.TButton").pack(side=tk.RIGHT)
        ttk.Button(log_header, text="Refresh", command=self._load_logs,
                  style="Gray.TButton").pack(side=tk.RIGHT, padx=5)
        
        # Filters - Row 1
        filter_frame = tk.Frame(parent, bg=self.frame_bg)
        filter_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(filter_frame, text="User:", fg=self.text_color, bg=self.frame_bg,
                font=self.label_font).pack(side=tk.LEFT)
        self.log_user_var = tk.StringVar(value="All")
        self.log_user_combo = ttk.Combobox(filter_frame, textvariable=self.log_user_var, width=15, state="readonly")
        self.log_user_combo.pack(side=tk.LEFT, padx=5)
        self.log_user_combo.bind("<<ComboboxSelected>>", lambda e: self._load_logs())
        
        tk.Label(filter_frame, text="Action:", fg=self.text_color, bg=self.frame_bg,
                font=self.label_font).pack(side=tk.LEFT, padx=(15, 0))
        self.log_action_var = tk.StringVar(value="All")
        self.log_action_combo = ttk.Combobox(filter_frame, textvariable=self.log_action_var, width=15, state="readonly")
        self.log_action_combo.pack(side=tk.LEFT, padx=5)
        self.log_action_combo.bind("<<ComboboxSelected>>", lambda e: self._load_logs())
        
        # Filters - Row 2 (Date Range)
        filter_frame2 = tk.Frame(parent, bg=self.frame_bg)
        filter_frame2.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        # Default to today's date
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        tk.Label(filter_frame2, text="From:", fg=self.text_color, bg=self.frame_bg,
                font=self.label_font).pack(side=tk.LEFT)
        self.start_date_var = tk.StringVar(value=today_str)
        self.start_date_entry = tk.Entry(filter_frame2, textvariable=self.start_date_var, width=12,
                                        bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.start_date_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(filter_frame2, text="(YYYY-MM-DD)", fg=self.text_secondary, bg=self.frame_bg, 
                font=("Segoe UI", 8)).pack(side=tk.LEFT)
        
        tk.Label(filter_frame2, text="To:", fg=self.text_color, bg=self.frame_bg,
                font=self.label_font).pack(side=tk.LEFT, padx=(15, 0))
        self.end_date_var = tk.StringVar(value=today_str)
        self.end_date_entry = tk.Entry(filter_frame2, textvariable=self.end_date_var, width=12,
                                      bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg)
        self.end_date_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame2, text="Apply", command=self._load_logs,
                  style="Blue.TButton", width=8).pack(side=tk.LEFT, padx=(15, 5))
        ttk.Button(filter_frame2, text="Reset", command=self._clear_date_filters,
                  style="Gray.TButton", width=8).pack(side=tk.LEFT)
        
        # Quick date buttons
        filter_frame3 = tk.Frame(parent, bg=self.frame_bg)
        filter_frame3.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        tk.Label(filter_frame3, text="Quick:", fg=self.text_color, bg=self.frame_bg,
                font=self.label_font).pack(side=tk.LEFT)
        
        for label, range_type in [("Today", "today"), ("Yesterday", "yesterday"), 
                                   ("Last 7 Days", "week"), ("Last 30 Days", "month"), ("All Time", "all")]:
            ttk.Button(filter_frame3, text=label, command=lambda r=range_type: self._set_date_range(r),
                      style="Gray.TButton", width=12 if "Days" in label else 10).pack(side=tk.LEFT, padx=2)
        
        # Log treeview
        log_tree_frame = tk.Frame(parent, bg=self.frame_bg)
        log_tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("timestamp", "username", "action", "target")
        self.log_tree = ttk.Treeview(log_tree_frame, columns=columns, show="headings", height=15)
        
        self.log_tree.heading("timestamp", text="Timestamp (UTC)")
        self.log_tree.heading("username", text="User")
        self.log_tree.heading("action", text="Action")
        self.log_tree.heading("target", text="Target")
        
        self.log_tree.column("timestamp", width=160)
        self.log_tree.column("username", width=120)
        self.log_tree.column("action", width=150)
        self.log_tree.column("target", width=300)
        
        scrollbar = ttk.Scrollbar(log_tree_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _load_data(self):
        """Load initial data (users, actions)"""
        def do_load():
            # Load users for filter
            success, result = self.api.get_users()
            if success:
                self.users = result
                
                # Update user combo
                def update_user_combo():
                    usernames = ["All"] + [u["username"] for u in self.users]
                    self.log_user_combo["values"] = usernames
                self.parent.after(0, update_user_combo)
            
            # Load audit log action types
            success, actions = self.api.get_audit_actions()
            self.parent.after(0, lambda: self.log_action_combo.configure(
                values=["All"] + (actions if success else [])))
            
            # Load logs
            self.parent.after(0, self._load_logs)
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _load_logs(self):
        """Load audit logs"""
        def do_load():
            # Clear existing
            self.parent.after(0, lambda: [self.log_tree.delete(item) for item in self.log_tree.get_children()])
            
            # Get filters
            username = None if self.log_user_var.get() == "All" else self.log_user_var.get()
            action = None if self.log_action_var.get() == "All" else self.log_action_var.get()
            
            # Get date filters
            start_date = self.start_date_var.get().strip() if self.start_date_var.get().strip() else None
            end_date = self.end_date_var.get().strip() if self.end_date_var.get().strip() else None
            
            if start_date:
                start_date = f"{start_date}T00:00:00"
            if end_date:
                end_date = f"{end_date}T23:59:59"
            
            success, logs = self.api.get_audit_logs(
                username=username, action=action, 
                start_date=start_date, end_date=end_date, limit=500
            )
            
            if success:
                def insert_logs():
                    for log in logs:
                        timestamp = log["timestamp"]
                        if "T" in timestamp:
                            timestamp = timestamp.replace("T", " ")[:19]
                        self.log_tree.insert("", tk.END, values=(
                            timestamp, log["username"], log["action"], log["target"] or ""
                        ))
                self.parent.after(0, insert_logs)
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _clear_date_filters(self):
        """Reset date filter fields to today (default)"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.start_date_var.set(today)
        self.end_date_var.set(today)
        self._load_logs()
    
    def _set_date_range(self, range_type):
        """Set quick date ranges"""
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
        """
        Export logs to CSV file
        
        Note: Timestamps in the exported CSV are in UTC (as returned by the API).
        The CSV column headers are controlled by the backend API.
        """
        username = None if self.log_user_var.get() == "All" else self.log_user_var.get()
        action = None if self.log_action_var.get() == "All" else self.log_action_var.get()
        
        start_date = self.start_date_var.get().strip() if self.start_date_var.get().strip() else None
        end_date = self.end_date_var.get().strip() if self.end_date_var.get().strip() else None
        
        if start_date:
            start_date = f"{start_date}T00:00:00"
        if end_date:
            end_date = f"{end_date}T23:59:59"
        
        def do_export():
            success, csv_data = self.api.export_audit_logs(
                username=username, action=action,
                start_date=start_date, end_date=end_date
            )
            
            if not success:
                self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to export: {csv_data}"))
                return
            
            def save_file():
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")],
                    initialfile=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
                
                if filename:
                    with open(filename, "w") as f:
                        f.write(csv_data)
                    messagebox.showinfo("Success", f"Logs exported to {filename}")
            
            self.parent.after(0, save_file)
        
        threading.Thread(target=do_export, daemon=True).start()

# ============================================================================
# Standalone Test Mode
# ============================================================================

if __name__ == "__main__":
    """
    Test mode for user_audit.py
    This allows you to run the module directly for testing
    """
    print("=" * 60)
    print("Audit Logs Module - Test Mode")
    print("=" * 60)
    print()
    
    # Create a test window
    root = tk.Tk()
    root.title("Audit Logs - Test Mode")
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
        panel = AuditLogsPanel(root, auth_client, mock_get_colors)
        
        print("✅ Audit Logs panel loaded successfully!")
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
        print(f"❌ Error loading Audit Logs panel: {e}")
        import traceback
        traceback.print_exc()