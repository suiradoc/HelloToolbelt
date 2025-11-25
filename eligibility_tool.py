import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, date
import dateutil.parser as date_parser
import re
from collections import Counter
import tempfile
import threading

# AWS SDK imports - boto3 instead of AWS CLI subprocess
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("WARNING: boto3 not installed. S3 features will not work. Install with: pip install boto3")

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg_color='#ffffff', *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Store parent reference
        self.parent = parent
        
        # Create container
        container = tk.Frame(self, bg=bg_color)
        container.pack(fill="both", expand=True)
        
        # Canvas and scrollbars (removed horizontal scrollbar)
        self.canvas = tk.Canvas(container, highlightthickness=0, bg=bg_color)
        self.scrollbar_v = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        # Scrollable frame
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        
        # Configure canvas (removed horizontal scrolling)
        self.canvas.configure(yscrollcommand=self.scrollbar_v.set)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Pack components (removed horizontal scrollbar packing)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_v.pack(side="right", fill="y")
        
        # Scrolling state
        self.canvas_has_focus = False
        
        # Bind events
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Setup scrolling based on environment
        self._setup_scrolling()
        
    def _setup_scrolling(self):
        """Setup scrolling - works for both standalone and HelloToolbelt"""
        # Check if we're in HelloToolbelt
        self.in_toolbelt = self._detect_hellotoolbelt()
        
        # Always bind enter/leave for focus tracking
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        
        # Bind mouse wheel events
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Linux support
        self.canvas.bind("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind("<Button-5>", self._on_mousewheel_linux)
        
        # Also bind to the scrollable frame itself
        self._bind_mousewheel_to_children(self.scrollable_frame)
        
    def _detect_hellotoolbelt(self):
        """Detect if we're running inside HelloToolbelt - cached version"""
        # Cache the result to avoid repeated expensive checks
        if hasattr(self, '_hellotoolbelt_detected'):
            return self._hellotoolbelt_detected
            
        try:
            current_parent = self.parent
            depth = 0
            max_depth = 5  # Limit search depth for performance
            
            while current_parent and depth < max_depth:
                # Look for HelloToolbelt MockRoot characteristics
                if (hasattr(current_parent, '_title') and 
                    hasattr(current_parent, 'pack') and 
                    hasattr(current_parent, '_current_bg')):
                    self._hellotoolbelt_detected = True
                    return True
                try:
                    current_parent = current_parent.master
                    depth += 1
                except:
                    break
            
            self._hellotoolbelt_detected = False
            return False
        except:
            self._hellotoolbelt_detected = False
            return False
        
    def _bind_mousewheel_to_children(self, widget):
        """Bind mousewheel only to immediate children - defer deep binding"""
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel_linux)
            widget.bind("<Button-5>", self._on_mousewheel_linux)
            
            # Only bind immediate children, not recursive
            # This significantly speeds up initialization
            for child in widget.winfo_children():
                try:
                    child.bind("<MouseWheel>", self._on_mousewheel)
                    child.bind("<Button-4>", self._on_mousewheel_linux)
                    child.bind("<Button-5>", self._on_mousewheel_linux)
                except Exception:
                    pass
        except Exception:
            pass
    
    def _on_enter(self, event):
        """Mouse entered canvas"""
        self.canvas_has_focus = True
        try:
            self.canvas.focus_set()
        except:
            pass
        
    def _on_leave(self, event):
        """Mouse left canvas"""
        self.canvas_has_focus = False
        
    def _on_mousewheel(self, event):
        """Universal mouse wheel handler"""
        # In HelloToolbelt mode, only scroll if we have focus
        if self.in_toolbelt and not self.canvas_has_focus:
            return "break"
        
        return self._do_scroll(event)
        
    def _on_mousewheel_linux(self, event):
        """Linux scroll wheel support"""
        if self.in_toolbelt and not self.canvas_has_focus:
            return "break"
        
        # Convert Linux button events to scroll
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            return "break"
        
        return self._do_scroll_with_delta(delta)
    
    def _do_scroll(self, event):
        """Perform the actual scrolling"""
        try:
            # Calculate delta
            if hasattr(event, 'delta'):
                delta = int(-1 * (event.delta / 120))
            else:
                return "break"
            
            return self._do_scroll_with_delta(delta)
            
        except Exception:
            return "break"
    
    def _do_scroll_with_delta(self, delta):
        """Perform scrolling with given delta"""
        try:
            # Limit scroll speed
            delta = max(-3, min(3, delta))
            
            # Get current scroll position
            current_top, current_bottom = self.canvas.yview()
            
            # Get canvas and scrollable frame dimensions
            canvas_height = self.canvas.winfo_height()
            self.canvas.update_idletasks()  # Ensure geometry is up to date
            
            # Get the bounding box of all items in canvas
            bbox = self.canvas.bbox("all")
            if not bbox:
                # No content to scroll
                return "break"
            
            # Calculate total content height
            content_height = bbox[3] - bbox[1]  # bottom - top
            
            # If content fits entirely in canvas, don't allow scrolling
            if content_height <= canvas_height:
                return "break"
            
            # Calculate scroll boundaries more precisely
            # current_top and current_bottom are fractions (0.0 to 1.0)
            scroll_top = current_top
            scroll_bottom = current_bottom
            
            # Prevent scrolling up if already at top
            if delta < 0 and scroll_top <= 0.0:
                return "break"
                
            # Prevent scrolling down if already at bottom
            if delta > 0 and scroll_bottom >= 1.0:
                return "break"
            
            # Perform scroll
            self.canvas.yview_scroll(delta, "units")
            return "break"
            
        except Exception as e:
            print(f"Scroll error: {e}")
            return "break"
        
    def check_scroll_needed(self):
        """Check if scrolling is needed and update scrollbar visibility"""
        try:
            self.canvas.update_idletasks()
            bbox = self.canvas.bbox("all")
            if not bbox:
                # Hide scrollbar if no content
                self.scrollbar_v.pack_forget()
                return False
            
            canvas_height = self.canvas.winfo_height()
            content_height = bbox[3] - bbox[1]
            
            # Show/hide scrollbars based on need
            if content_height > canvas_height:
                self.scrollbar_v.pack(side="right", fill="y")
                return True
            else:
                self.scrollbar_v.pack_forget()
                return False
        except Exception:
            return False
    
    def _on_frame_configure(self, event):
        """Update scroll region when frame size changes"""
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Check if scrollbars are needed after content change
            self.canvas.after_idle(self.check_scroll_needed)
        except Exception:
            pass
        
    def _on_canvas_configure(self, event):
        """Update canvas window size when canvas is resized"""
        try:
            canvas_width = event.width
            # Ensure the scrollable frame matches the canvas width to prevent horizontal scrolling
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
            # Also update scroll region when canvas is resized
            self.canvas.after_idle(self._update_scroll_region)
            # Check if scrollbars are needed after resize
            self.canvas.after_idle(self.check_scroll_needed)
        except Exception:
            pass
    
    def _update_scroll_region(self):
        """Force update the scroll region"""
        try:
            self.canvas.update_idletasks()
            bbox = self.canvas.bbox("all")
            if bbox:
                # Only set the scroll region for vertical scrolling
                self.canvas.configure(scrollregion=(0, bbox[1], 0, bbox[3]))
        except Exception:
            pass
    
    def force_scroll_update(self):
        """Public method to force scroll region update and rebind events"""
        self.canvas.after_idle(self._update_scroll_region)
        # Rebind mousewheel to any new children
        self.canvas.after_idle(lambda: self._bind_mousewheel_to_children(self.scrollable_frame))

class S3FileBrowserWidget(tk.Frame):
    """Integrated S3 file browser widget for BillHunter tab"""
    def __init__(self, parent, bucket="s3.hello.do.integration", initial_prefix="clients/", 
                 profile="default", on_file_select=None, bg_color='#ffffff', auto_load=True, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        
        self.bucket = bucket
        self.profile = profile
        self.current_prefix = initial_prefix
        self.on_file_select = on_file_select  # Callback when file is selected
        self.bg_color = bg_color
        
        # Store all items for filtering
        self.all_items = []  # Store (text, values, tags) tuples
        
        # Track sort state for columns
        self.sort_reverse = {}
        self.current_sort_column = None
        
        # Styling
        self.frame_bg = '#f8f9fa'
        self.header_bg = '#e9ecef'
        self.primary_color = '#0a9640'
        
        self._build_ui()
        
        # Load initial folder after a short delay (if auto_load is True)
        if auto_load:
            self.after(500, lambda: self.load_folder(self.current_prefix))
    
    def _build_ui(self):
        """Build the S3 browser UI"""
        # Container frame
        container = tk.Frame(self, bg=self.frame_bg, relief='solid', bd=1)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(container, bg=self.header_bg)
        header.pack(fill=tk.X)
        
        header_content = tk.Frame(header, bg=self.header_bg)
        header_content.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(header_content, text="☁️ S3 File Browser", 
                font=('Segoe UI', 11, 'bold'), bg=self.header_bg).pack(side=tk.LEFT)
        
        # Search/Filter box for current folder
        search_frame = tk.Frame(header_content, bg=self.header_bg)
        search_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        tk.Label(search_frame, text="🔍", bg=self.header_bg, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 3))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_current_view())
        
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, 
                                     font=('Segoe UI', 9), width=20,
                                     relief='solid', bd=1)
        self.search_entry.pack(side=tk.LEFT)
        self.search_entry.insert(0, "Filter files...")
        self.search_entry.bind('<FocusIn>', self._on_search_focus_in)
        self.search_entry.bind('<FocusOut>', self._on_search_focus_out)
        self.search_entry.config(fg='gray')
        
        clear_search_btn = tk.Button(search_frame, text="✕", command=self.clear_filter,
                                     bg=self.header_bg, font=('Segoe UI', 9),
                                     padx=3, pady=0, relief='flat', bd=0, cursor="hand2")
        clear_search_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Refresh button
        self.refresh_btn = tk.Button(header_content, text="🔄", command=self.refresh,
                                     bg=self.header_bg, font=('Segoe UI', 10),
                                     padx=8, pady=2, relief='flat', bd=0, cursor="hand2")
        self.refresh_btn.pack(side=tk.RIGHT)
        
        # Path display and navigation
        nav_frame = tk.Frame(container, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, padx=10, pady=8)
        
        # Back button
        self.back_btn = tk.Button(nav_frame, text="⬆️", command=self.go_up,
                                  bg='#e9ecef', font=('Segoe UI', 9),
                                  padx=8, pady=3, relief='flat', bd=0, cursor="hand2",
                                  state=tk.DISABLED)
        self.back_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Path label
        path_container = tk.Frame(nav_frame, bg='#e9ecef', relief='solid', bd=1)
        path_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.path_label = tk.Label(path_container, text=f"s3://{self.bucket}/{self.current_prefix}", 
                                   font=('Segoe UI', 9), bg='#e9ecef', fg='#0a9640',
                                   anchor='w', padx=8, pady=4)
        self.path_label.pack(fill=tk.X)
        
        # Tree view frame
        tree_frame = tk.Frame(container, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.tree = ttk.Treeview(tree_frame, 
                                columns=('Type', 'Size', 'Modified'),
                                yscrollcommand=vsb.set,
                                xscrollcommand=hsb.set,
                                height=12)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure columns
        self.tree.heading('#0', text='Name', command=lambda: self.sort_tree_column('#0'))
        self.tree.heading('Type', text='Type', command=lambda: self.sort_tree_column('Type'))
        self.tree.heading('Size', text='Size', command=lambda: self.sort_tree_column('Size'))
        self.tree.heading('Modified', text='Modified', command=lambda: self.sort_tree_column('Modified'))
        
        self.tree.column('#0', width=300)
        self.tree.column('Type', width=80)
        self.tree.column('Size', width=100)
        self.tree.column('Modified', width=150)
        
        # Pack
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind events
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Status bar
        status_frame = tk.Frame(container, bg=self.frame_bg)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.status_label = tk.Label(status_frame, text="Ready", 
                                     font=('Segoe UI', 9), bg=self.frame_bg, fg='gray',
                                     anchor='w')
        self.status_label.pack(side=tk.LEFT)
        
        self.selection_label = tk.Label(status_frame, text="", 
                                       font=('Segoe UI', 9, 'bold'), bg=self.frame_bg, 
                                       fg=self.primary_color, anchor='e')
        self.selection_label.pack(side=tk.RIGHT)
    
    def load_folder(self, prefix):
        """Load folder contents from S3 using boto3"""
        if not BOTO3_AVAILABLE:
            self.status_label.config(text="❌ boto3 not installed. Run: pip install boto3")
            return
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.status_label.config(text="Loading...")
        self.selection_label.config(text="")
        self.update()
        
        try:
            # Create S3 client with profile if specified
            session_kwargs = {}
            if self.profile and self.profile != "default":
                session_kwargs['profile_name'] = self.profile
            
            session = boto3.Session(**session_kwargs)
            s3_client = session.client('s3')
            
            # List objects with pagination support
            list_kwargs = {
                'Bucket': self.bucket,
                'Prefix': prefix,
                'Delimiter': '/'
            }
            
            response = s3_client.list_objects_v2(**list_kwargs)
            
            folders = []
            files = []
            
            # Process folders (CommonPrefixes)
            for prefix_info in response.get('CommonPrefixes', []):
                folder_path = prefix_info['Prefix']
                # Get just the folder name (last segment before trailing slash)
                folder_name = folder_path.rstrip('/').split('/')[-1]
                if folder_name:  # Skip empty names
                    folders.append(folder_name)
            
            # Process files (Contents)
            for obj in response.get('Contents', []):
                key = obj['Key']
                
                # Skip the prefix itself if it's returned
                if key == prefix or key.endswith('/'):
                    continue
                
                # Get just the filename (last segment)
                filename = key.split('/')[-1]
                if not filename:  # Skip if no filename
                    continue
                    
                size = obj['Size']
                modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                files.append((filename, size, modified))
            
            # Add folders to tree
            for folder in sorted(folders):
                self.tree.insert('', 'end', text=f"📁 {folder}", 
                               values=('Folder', '--', ''), tags=('folder',))
            
            # Add files to tree
            for filename, size, modified in sorted(files):
                # Format size
                try:
                    size_int = int(size)
                    if size_int < 1024:
                        size_str = f"{size_int} B"
                    elif size_int < 1024 * 1024:
                        size_str = f"{size_int / 1024:.1f} KB"
                    elif size_int < 1024 * 1024 * 1024:
                        size_str = f"{size_int / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{size_int / (1024 * 1024 * 1024):.2f} GB"
                except:
                    size_str = str(size)
                
                # Determine file icon
                if filename.endswith('.csv'):
                    icon = '📊'
                elif filename.endswith('.txt'):
                    icon = '📄'
                elif filename.endswith('.json'):
                    icon = '📋'
                else:
                    icon = '📄'
                
                self.tree.insert('', 'end', text=f"{icon} {filename}", 
                               values=('File', size_str, modified), tags=('file',))
            
            # Store all items for filtering
            self.all_items = []
            for item in self.tree.get_children():
                item_text = self.tree.item(item, 'text')
                item_values = self.tree.item(item, 'values')
                item_tags = self.tree.item(item, 'tags')
                self.all_items.append((item_text, item_values, item_tags))
            
            # Update status
            folder_count = len(folders)
            file_count = len(files)
            self.status_label.config(text=f"✓ {folder_count} folder(s), {file_count} file(s)")
            
            # Update path
            self.current_prefix = prefix
            path_display = f"s3://{self.bucket}/{prefix}" if prefix else f"s3://{self.bucket}/"
            self.path_label.config(text=path_display)
            
            # Enable/disable back button
            if prefix and prefix != "clients/":
                self.back_btn.config(state=tk.NORMAL)
            else:
                self.back_btn.config(state=tk.DISABLED)
                
        except NoCredentialsError:
            self.status_label.config(text="❌ AWS credentials not configured")
        except ProfileNotFound:
            self.status_label.config(text=f"❌ Profile '{self.profile}' not found")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                self.status_label.config(text="❌ Bucket not found")
            elif error_code == 'AccessDenied':
                self.status_label.config(text="❌ Access denied - check credentials")
            else:
                self.status_label.config(text=f"❌ Error: {error_code}")
        except Exception as e:
            error_msg = str(e)
            self.status_label.config(text=f"❌ Error: {error_msg[:50]}")
            print(f"S3 Browser Error: {error_msg}")
    
    def on_double_click(self, event):
        """Handle double-click"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        
        if 'folder' in tags:
            # Navigate into folder
            item_text = self.tree.item(item, 'text')
            folder_name = item_text.replace('📁 ', '')
            new_prefix = f"{self.current_prefix}{folder_name}/" if self.current_prefix else f"{folder_name}/"
            self.load_folder(new_prefix)
        elif 'file' in tags and self.on_file_select:
            # Select file
            item_text = self.tree.item(item, 'text')
            # Remove icon
            for icon in ['📊', '📄', '📋']:
                item_text = item_text.replace(f"{icon} ", '')
            
            full_key = f"{self.current_prefix}{item_text}" if self.current_prefix else item_text
            self.on_file_select(full_key)
    
    def on_select(self, event):
        """Handle selection change"""
        selection = self.tree.selection()
        if not selection:
            self.selection_label.config(text="")
            return
        
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        
        if 'file' in tags:
            item_text = self.tree.item(item, 'text')
            # Remove icon
            for icon in ['📊', '📄', '📋']:
                item_text = item_text.replace(f"{icon} ", '')
            self.selection_label.config(text=f"Selected: {item_text}")
        else:
            self.selection_label.config(text="")
    
    def go_up(self):
        """Go to parent folder"""
        if not self.current_prefix or self.current_prefix == "clients/":
            return
        
        # Remove trailing slash
        prefix = self.current_prefix.rstrip('/')
        
        # Go up one level
        if '/' in prefix:
            new_prefix = prefix.rsplit('/', 1)[0] + '/'
        else:
            new_prefix = ""
        
        self.load_folder(new_prefix)
    
    def refresh(self):
        """Refresh current folder"""
        self.load_folder(self.current_prefix)
    
    def get_selected_file(self):
        """Get the currently selected file path"""
        selection = self.tree.selection()
        if not selection:
            return None
        
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        
        if 'file' not in tags:
            return None
        
        item_text = self.tree.item(item, 'text')
        # Remove icons
        for icon in ['📊', '📄', '📋']:
            item_text = item_text.replace(f"{icon} ", '')
        
        full_key = f"{self.current_prefix}{item_text}" if self.current_prefix else item_text
        return full_key
    
    def _on_search_focus_in(self, event):
        """Clear placeholder text on focus"""
        if self.search_entry.get() == "Filter files...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg='black')
    
    def _on_search_focus_out(self, event):
        """Restore placeholder text if empty"""
        if not self.search_entry.get():
            self.search_entry.insert(0, "Filter files...")
            self.search_entry.config(fg='gray')
    
    def filter_current_view(self):
        """Filter the currently displayed files and folders"""
        search_term = self.search_var.get().lower()
        
        # Skip if placeholder text is showing
        if search_term == "filter files...":
            return
        
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not search_term or search_term.strip() == "":
            # Show all items if search is empty
            for text, values, tags in self.all_items:
                self.tree.insert('', 'end', text=text, values=values, tags=tags)
        else:
            # Show only matching items
            matching_count = 0
            for text, values, tags in self.all_items:
                # Search in the filename (remove icon first)
                clean_text = text.replace('📁 ', '').replace('📊 ', '').replace('📄 ', '').replace('📋 ', '')
                if search_term in clean_text.lower():
                    self.tree.insert('', 'end', text=text, values=values, tags=tags)
                    matching_count += 1
            
            # Update status with match count
            if matching_count == 0:
                self.status_label.config(text=f"No matches for '{search_term}'")
            else:
                self.status_label.config(text=f"Showing {matching_count} of {len(self.all_items)} items")
    
    def clear_filter(self):
        """Clear the search filter"""
        self.search_var.set('')
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "Filter files...")
        self.search_entry.config(fg='gray')
        self.filter_current_view()
        
        # Restore original status
        folder_count = sum(1 for _, values, _ in self.all_items if values[0] == 'Folder')
        file_count = len(self.all_items) - folder_count
        self.status_label.config(text=f"✓ {folder_count} folder(s), {file_count} file(s)")
    
    def sort_tree_column(self, col):
        """Sort tree by the specified column"""
        # Get all items with their data
        items = []
        for item_id in self.tree.get_children():
            if col == '#0':
                value = self.tree.item(item_id, 'text')
            else:
                values = self.tree.item(item_id, 'values')
                col_index = ['Type', 'Size', 'Modified'].index(col)
                value = values[col_index]
            items.append((value, item_id))
        
        # Toggle sort direction
        reverse = self.sort_reverse.get(col, False)
        self.sort_reverse[col] = not reverse
        self.current_sort_column = col
        
        # Sort based on column type
        if col == 'Modified':
            # Sort by date
            def date_sort_key(item):
                val = item[0]
                if not val or val == '' or val == '--':
                    return datetime.min if not reverse else datetime.max
                try:
                    # Parse date format: "2024-01-15 10:30:00"
                    return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        # Try without time
                        return datetime.strptime(val, "%Y-%m-%d")
                    except ValueError:
                        return datetime.min if not reverse else datetime.max
            
            items.sort(key=date_sort_key, reverse=reverse)
        
        elif col == 'Size':
            # Sort by size (convert back to bytes for proper sorting)
            def size_sort_key(item):
                val = item[0]
                if val == '--':
                    return -1 if not reverse else float('inf')
                try:
                    # Parse size string like "1.2 MB", "500 KB", "100 B"
                    if ' B' in val:
                        return float(val.replace(' B', ''))
                    elif ' KB' in val:
                        return float(val.replace(' KB', '')) * 1024
                    elif ' MB' in val:
                        return float(val.replace(' MB', '')) * 1024 * 1024
                    elif ' GB' in val:
                        return float(val.replace(' GB', '')) * 1024 * 1024 * 1024
                    else:
                        return 0
                except:
                    return 0
            
            items.sort(key=size_sort_key, reverse=reverse)
        
        elif col == 'Type':
            # Sort folders first, then files
            def type_sort_key(item):
                val = item[0]
                # Folders come first
                if val == 'Folder':
                    return (0, '') if not reverse else (1, '')
                else:
                    return (1, val.lower()) if not reverse else (0, val.lower())
            
            items.sort(key=type_sort_key, reverse=reverse)
        
        else:  # Name column
            # Sort alphabetically, but keep folders together at top
            def name_sort_key(item):
                text = item[0]
                # Remove icons for sorting
                clean_text = text.replace('📁 ', '').replace('📊 ', '').replace('📄 ', '').replace('📋 ', '')
                # Check if folder by looking for icon
                is_folder = '📁' in text
                # Sort folders first, then by name
                return (0 if is_folder else 1, clean_text.lower()) if not reverse else (1 if is_folder else 0, clean_text.lower())
            
            items.sort(key=name_sort_key, reverse=reverse)
        
        # Reorder items in tree
        for index, (value, item_id) in enumerate(items):
            self.tree.move(item_id, '', index)
        
        # Update column headers with sort indicators
        for column in ['#0', 'Type', 'Size', 'Modified']:
            if column == col:
                if column == '#0':
                    base_text = 'Name'
                else:
                    base_text = column
                direction = ' ▼' if reverse else ' ▲'
                self.tree.heading(column, text=f"{base_text}{direction}", 
                                command=lambda c=column: self.sort_tree_column(c))
            else:
                if column == '#0':
                    self.tree.heading(column, text='Name', 
                                    command=lambda c=column: self.sort_tree_column(c))
                else:
                    self.tree.heading(column, text=column, 
                                    command=lambda c=column: self.sort_tree_column(c))


class EligibilitySearchTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Eligibility Search Tool")
        
        # Check if this is running in HelloToolbelt (MockRoot) or standalone
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        # Check CURRENT tier (not just if Tier 3 was ever unlocked)
        # This ensures download button only shows when ACTIVELY using Tier 3
        current_tier = getattr(root, 'current_tier', 'Tier 3')  # Default to Tier 3 for standalone
        self.is_tier3 = (current_tier == 'Tier 3')  # True only if current tier is Tier 3
        
        if not self.is_in_toolbelt:
            # Only configure background if running standalone
            self.root.configure(bg='#ffffff')
        
        # Use system default colors that will adapt to light/dark mode
        self.setup_adaptive_styling()
        
        self.root.minsize(1000, 800)
        
        # Eligibility search variables
        self.eligibility_file_path = ""
        self.eligibility_df = pd.DataFrame()
        
        # S3-related variables (will be initialized in _build_upload_section)
        self.selected_s3_file = None
        
        # Column selection variables
        self.first_name_var = tk.StringVar()
        self.last_name_var = tk.StringVar()
        self.date_of_birth_var = tk.StringVar()
        self.relationship_var = tk.StringVar()
        self.term_date_var = tk.StringVar()
        
        self.search_first_name = tk.StringVar()
        self.search_last_name = tk.StringVar()
        self.filtered_df = pd.DataFrame()
        
        self.date_format_analysis = {}
        
        # Build interface immediately - no delays
        self.build_interface()
        
        # Force immediate render
        self.root.update_idletasks()
        
        # Center window only if standalone (defer to after render)
        if not self.is_in_toolbelt:
            self.root.after_idle(self._center_window)

    def setup_adaptive_styling(self):
        """Setup styling that adapts to system theme (light/dark mode)"""
        # When running in HelloToolbelt, inherit colors from parent
        if self.is_in_toolbelt:
            # Get colors from the parent container (HelloToolbelt)
            try:
                parent_bg = self.root.cget('bg')
                parent_fg = self.root.cget('fg') 
            except:
                # Fallback colors
                parent_bg = '#ffffff'
                parent_fg = '#2c3e50'
        else:
            # Get system default colors when running standalone
            temp_label = tk.Label(self.root)
            parent_bg = temp_label.cget('bg')
            parent_fg = temp_label.cget('fg')
            temp_label.destroy()
        
        # Determine if we're in dark mode by checking background brightness
        try:
            # Convert color to RGB if it's a hex value
            if parent_bg.startswith('#'):
                r, g, b = int(parent_bg[1:3], 16), int(parent_bg[3:5], 16), int(parent_bg[5:7], 16)
            else:
                # Try to get RGB values from color name
                rgb = self.root.winfo_rgb(parent_bg)
                r, g, b = [x // 256 for x in rgb]
            
            # Calculate brightness (0-255)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            self.is_dark_mode = brightness < 128
        except:
            # Fallback to light mode if color parsing fails
            self.is_dark_mode = False
        
        # Fonts and sizes - consistent with HelloToolbelt
        self.title_font = ("Segoe UI", 14, "bold")
        self.subtitle_font = ("Segoe UI", 11, "bold")
        self.label_font = ("Segoe UI", 10)
        self.text_font = ("Segoe UI", 10)
        
        self.button_padx = 8
        self.button_pady = 4
        self.frame_padx = 20
        self.frame_pady = 15
        
        # Adaptive color scheme based on detected theme
        if self.is_dark_mode:
            # Dark mode colors - inherit parent background for transparency
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.primary_color = "#df9621"
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#ffffff'
            self.text_secondary = '#cccccc'
            # Button text colors - black for both modes
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state
        else:
            # Light mode colors - inherit parent background for transparency
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.primary_color = '#df9621'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.text_secondary = '#34495e'
            # Button text colors - black for both modes
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state

    def refresh_styling(self, is_dark_mode):
        """Refresh styling when dark mode is toggled from HelloToolbelt"""
        self.is_dark_mode = is_dark_mode
        
        # IMPORTANT: Update styling BEFORE rebuilding the interface
        # This ensures the new colors are calculated and available
        self.setup_adaptive_styling()
        
        # Clear and recreate the interface
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Reinitialize the interface with the updated colors
        self.build_interface()

    def _center_window(self):
        window_width = 1200
        window_height = 900
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    def _add_button_hover(self, button, normal_color, hover_color, normal_fg=None, hover_fg=None):
        """Add hover effects to buttons with error handling"""
        try:
            # Use adaptive button text colors if not specified
            if normal_fg is None:
                normal_fg = getattr(self, 'button_text_color', '#000000')
            if hover_fg is None:
                hover_fg = getattr(self, 'button_hover_text_color', '#000000')
                
            def on_enter(e):
                try:
                    if button.winfo_exists():
                        button.config(bg=hover_color, fg=hover_fg)
                except tk.TclError:
                    pass
            
            def on_leave(e):
                try:
                    if button.winfo_exists():
                        button.config(bg=normal_color, fg=normal_fg)
                except tk.TclError:
                    pass
            
            button.bind("<Enter>", on_enter)
            button.bind("<Leave>", on_leave)
        except Exception as e:
            print(f"Warning: Could not add button hover: {e}")

    def detect_date_format(self, date_string):
        if pd.isna(date_string) or str(date_string).strip() == '':
            return None
        
        date_str = str(date_string).strip()
        
        #date format patterns
        patterns = {
            r'^\d{1,2}/\d{1,2}/\d{4}$': 'M/D/YYYY',
            r'^\d{1,2}-\d{1,2}-\d{4}$': 'M-D-YYYY',
            r'^\d{4}/\d{1,2}/\d{1,2}$': 'YYYY/M/D',
            r'^\d{4}-\d{1,2}-\d{1,2}$': 'YYYY-M-D',
            r'^\d{1,2}/\d{1,2}/\d{2}$': 'M/D/YY',
            r'^\d{1,2}-\d{1,2}-\d{2}$': 'M-D-YY',
            r'^\d{2}/\d{2}/\d{4}$': 'MM/DD/YYYY',
            r'^\d{2}-\d{2}-\d{4}$': 'MM-DD-YYYY',
            r'^\d{4}/\d{2}/\d{2}$': 'YYYY/MM/DD',
            r'^\d{4}-\d{2}-\d{2}$': 'YYYY-MM-DD',
            r'^\d{2}/\d{2}/\d{2}$': 'MM/DD/YY',
            r'^\d{2}-\d{2}-\d{2}$': 'MM-DD-YY',
            r'^[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}$': 'Month D, YYYY',
            r'^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}$': 'D Month YYYY',
            r'^[A-Za-z]{3,9}\s+\d{1,2}\s+\d{4}$': 'Month D YYYY',
        }
        
        for pattern, format_name in patterns.items():
            if re.match(pattern, date_str):
                return format_name
        
        return 'Unknown Format'

    def analyze_date_formats_in_column(self, column_data):
        if column_data is None or len(column_data) == 0:
            return None
        
        format_counts = Counter()
        total_valid_dates = 0
        
        for date_value in column_data:
            if pd.notna(date_value) and str(date_value).strip() != '':
                detected_format = self.detect_date_format(date_value)
                if detected_format and detected_format != 'Unknown Format':
                    format_counts[detected_format] += 1
                    total_valid_dates += 1
        
        if total_valid_dates == 0:
            return None
        
        # Find most common format, line 122 is currently set to 90%
        most_common = format_counts.most_common(1)
        if not most_common:
            return None
        
        dominant_format, dominant_count = most_common[0]
        dominant_percentage = (dominant_count / total_valid_dates) * 100
        
        return {
            'dominant_format': dominant_format,
            'dominant_count': dominant_count,
            'dominant_percentage': dominant_percentage,
            'total_valid_dates': total_valid_dates,
            'format_breakdown': dict(format_counts),
            'is_consistent': dominant_percentage >= 90.0
        }

    def calculate_age(self, birth_date_str, format_analysis=None):
        if pd.isna(birth_date_str) or str(birth_date_str).strip() == '':
            return None, None, "No date provided", None
        
        format_warning = None
        if format_analysis and format_analysis['is_consistent']:
            detected_format = self.detect_date_format(birth_date_str)
            if detected_format and detected_format != format_analysis['dominant_format']:
                format_warning = f"⚠️ FORMAT ANOMALY: {detected_format} (Expected: {format_analysis['dominant_format']})"
        
        try:
            birth_date = date_parser.parse(str(birth_date_str), fuzzy=True).date()
            today = date.today()
            age = today.year - birth_date.year
            
            if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                age -= 1
            
            # Determine if under 18
            is_under_18 = age < 18
            
            age_text = f"Age: {age} ({'Under 18' if is_under_18 else '18 or older'})"
            
            return age, is_under_18, age_text, format_warning
            
        except Exception as e:
            return None, None, f"Invalid date format: {str(birth_date_str)}", format_warning

    def check_term_date(self, term_date_str, format_analysis=None):
        # Check if term date is blank/empty first
        if pd.isna(term_date_str) or str(term_date_str).strip() == '' or str(term_date_str).lower() == 'nan':
            return None, None, "No term date provided", None
        
        format_warning = None
        if format_analysis and format_analysis['is_consistent']:
            detected_format = self.detect_date_format(term_date_str)
            if detected_format and detected_format != format_analysis['dominant_format']:
                format_warning = f"⚠️ FORMAT ANOMALY: {detected_format} (Expected: {format_analysis['dominant_format']})"
        
        try:
            term_date = date_parser.parse(str(term_date_str), fuzzy=True).date()
            
            today = date.today()
            is_expired = term_date < today
            
            days_diff = (term_date - today).days
            
            if is_expired:
                days_ago = abs(days_diff)
                status_text = f"EXPIRED: {term_date} ({days_ago} days ago)"
            else:
                status_text = f"Active: {term_date} ({days_diff} days remaining)"
            
            return term_date, is_expired, status_text, format_warning
            
        except Exception as e:
            return None, None, f"Invalid term date format: {str(term_date_str)}", format_warning

    def analyze_all_records(self):
        """Analyze all records in the file and show failure percentages"""
        if self.eligibility_df.empty:
            messagebox.showwarning("No Data", "Please load a file first.")
            return
        
        # Get column names
        dob_col = self._get_column_name_from_selection(self.date_of_birth_var.get())
        term_date_col = self._get_column_name_from_selection(self.term_date_var.get())
        relationship_col = self._get_column_name_from_selection(self.relationship_var.get())
        
        if not dob_col and not term_date_col:
            messagebox.showwarning("No Columns Selected", 
                                 "Please select at least a Date of Birth or Term Date column to analyze.")
            return
        
        # Get format analysis for selected columns
        dob_format_analysis = self.date_format_analysis.get(dob_col) if dob_col else None
        term_format_analysis = self.date_format_analysis.get(term_date_col) if term_date_col else None
        
        # Initialize counters
        total_records = len(self.eligibility_df)
        
        # Age analysis variables
        under_18_count = 0
        valid_dob_count = 0
        invalid_dob_count = 0
        dob_format_anomaly_count = 0
        
        # Term date analysis variables
        expired_count = 0
        valid_term_count = 0
        invalid_term_count = 0
        blank_term_count = 0  # NEW: Track blank term dates separately
        term_format_anomaly_count = 0
        
        # Relationship analysis variables
        relationship_counts = {}
        
        # Process all records
        for _, row in self.eligibility_df.iterrows():
            # Analyze date of birth if column is selected
            if dob_col and dob_col in self.eligibility_df.columns:
                age, is_under_18, age_text, format_warning = self.calculate_age(row[dob_col], dob_format_analysis)
                
                if age is not None:
                    valid_dob_count += 1
                    if is_under_18:
                        under_18_count += 1
                else:
                    invalid_dob_count += 1
                
                if format_warning:
                    dob_format_anomaly_count += 1
            
            # Analyze term date if column is selected
            if term_date_col and term_date_col in self.eligibility_df.columns:
                term_date, is_expired, term_text, format_warning = self.check_term_date(row[term_date_col], term_format_analysis)
                
                # Check if term date is blank first
                term_value = row[term_date_col]
                if pd.isna(term_value) or str(term_value).strip() == '' or str(term_value).lower() == 'nan':
                    blank_term_count += 1
                    valid_term_count += 1  # NEW: Count blank dates as "valid"
                elif term_date is not None:
                    if is_expired:
                        expired_count += 1
                        # Expired dates are NOT counted as "valid"
                    else:
                        valid_term_count += 1  # Only count non-expired dates as "valid"
                else:
                    # This is an invalid format (not blank, but couldn't parse)
                    invalid_term_count += 1
                
                if format_warning:
                    term_format_anomaly_count += 1
            
            # Analyze relationship if column is selected
            if relationship_col and relationship_col in self.eligibility_df.columns:
                # PRESERVE EXACT VALUES - don't modify the relationship values at all
                relationship_value = row[relationship_col]
                
                # Handle NaN/None values
                if pd.isna(relationship_value):
                    relationship_counts['Unknown/Blank'] = relationship_counts.get('Unknown/Blank', 0) + 1
                else:
                    # Convert to string but preserve exact formatting (including leading zeros)
                    relationship_str = str(relationship_value).strip()
                    if relationship_str == '' or relationship_str.lower() == 'nan':
                        relationship_counts['Unknown/Blank'] = relationship_counts.get('Unknown/Blank', 0) + 1
                    else:
                        # Keep EXACT value as it appears in the file
                        relationship_counts[relationship_str] = relationship_counts.get(relationship_str, 0) + 1
        
        # Calculate percentages
        report_lines = []
        report_lines.append(f"📊 BULK ANALYSIS REPORT")
        report_lines.append(f"=" * 50)
        report_lines.append(f"Total Records Analyzed: {total_records:,}")
        report_lines.append("")
        
        # Age analysis results
        if dob_col:
            report_lines.append(f"🎂 AGE ANALYSIS (Column: {dob_col})")
            report_lines.append(f"-" * 35)
            
            if valid_dob_count > 0:
                under_18_percentage = (under_18_count / valid_dob_count) * 100
                report_lines.append(f"✅ Valid Birth Dates: {valid_dob_count:,} ({(valid_dob_count/total_records)*100:.1f}%)")
                report_lines.append(f"⚠️  Under 18: {under_18_count:,} ({under_18_percentage:.1f}% of valid dates)")
            
            if invalid_dob_count > 0:
                invalid_dob_percentage = (invalid_dob_count / total_records) * 100
                report_lines.append(f"❌ Invalid Birth Dates: {invalid_dob_count:,} ({invalid_dob_percentage:.1f}%)")
            
            if dob_format_anomaly_count > 0:
                dob_anomaly_percentage = (dob_format_anomaly_count / total_records) * 100
                report_lines.append(f"🔍 Format Anomalies: {dob_format_anomaly_count:,} ({dob_anomaly_percentage:.1f}%)")
            
            report_lines.append("")
        
        # Term date analysis results
        if term_date_col:
            report_lines.append(f"📅 TERM DATE ANALYSIS (Column: {term_date_col})")
            report_lines.append(f"-" * 35)
            
            if valid_term_count > 0:
                expired_percentage = (expired_count / valid_term_count) * 100
                report_lines.append(f"✅ Valid Term Dates: {valid_term_count:,} ({(valid_term_count/total_records)*100:.1f}%)")
                report_lines.append(f"⚠️  Expired: {expired_count:,} ({expired_percentage:.1f}% of valid dates)")
            
            # REMOVED: Blank term dates line completely
            
            if invalid_term_count > 0:
                invalid_term_percentage = (invalid_term_count / total_records) * 100
                report_lines.append(f"❌ Invalid Term Dates: {invalid_term_count:,} ({invalid_term_percentage:.1f}%)")
            
            if term_format_anomaly_count > 0:
                term_anomaly_percentage = (term_format_anomaly_count / total_records) * 100
                report_lines.append(f"🔍 Format Anomalies: {term_format_anomaly_count:,} ({term_anomaly_percentage:.1f}%)")
            
            report_lines.append("")
        
        # Relationship analysis results
        if relationship_col and relationship_counts:
            report_lines.append(f"👥 RELATIONSHIP BREAKDOWN (Column: {relationship_col})")
            report_lines.append(f"-" * 35)
            
            # Sort relationships by count (highest first)
            sorted_relationships = sorted(relationship_counts.items(), key=lambda x: x[1], reverse=True)
            
            for relationship, count in sorted_relationships:
                percentage = (count / total_records) * 100
                report_lines.append(f"• {relationship}: {count:,} ({percentage:.1f}%)")
            
            report_lines.append("")
        
        # Overall summary - count unique problematic rows (not sum of all issues)
        problematic_rows = set()
        
        # Track which rows have any issues
        for idx, row in self.eligibility_df.iterrows():
            has_issue = False
            
            # Check age issues
            if dob_col and dob_col in self.eligibility_df.columns:
                age, is_under_18, age_text, format_warning = self.calculate_age(row[dob_col], dob_format_analysis)
                if is_under_18 or age is None or format_warning:
                    has_issue = True
            
            # Check term date issues (ONLY count actual invalid dates, not blank ones)
            if term_date_col and term_date_col in self.eligibility_df.columns:
                term_value = row[term_date_col]
                # Skip blank term dates (don't count as issues - they are considered clean)
                if not (pd.isna(term_value) or str(term_value).strip() == '' or str(term_value).lower() == 'nan'):
                    term_date, is_expired, term_text, format_warning = self.check_term_date(row[term_date_col], term_format_analysis)
                    # Only count as issue if expired OR invalid format OR format anomaly
                    # Blank dates are automatically considered clean (no issue)
                    if is_expired or term_date is None or format_warning:
                        has_issue = True
            
            if has_issue:
                problematic_rows.add(idx)
        
        total_problematic_rows = len(problematic_rows)
        
        if total_problematic_rows > 0:
            issue_percentage = (total_problematic_rows / total_records) * 100
            report_lines.append("")  # Extra line break
            report_lines.append("")  # Extra line break
            report_lines.append(f"⚠️  OVERALL ISSUES FOUND")
            report_lines.append(f"-" * 35)
            report_lines.append(f"Rows with Issues: {total_problematic_rows:,} ({issue_percentage:.1f}%)")
            report_lines.append(f"Clean Records: {total_records - total_problematic_rows:,} ({100-issue_percentage:.1f}%)")
        else:
            report_lines.append("")  # Extra line break
            report_lines.append("")  # Extra line break
            report_lines.append(f"✅ NO ISSUES FOUND - ALL RECORDS CLEAN!")
        
        # Show results in a popup window
        self._show_analysis_popup("\n".join(report_lines))

    def _show_analysis_popup(self, report_text):
        """Show the analysis results in a popup window"""
        popup = tk.Toplevel(self.root)
        popup.title("Bulk Analysis Results")
        popup.geometry("600x500")
        popup.configure(bg=self.bg_color)
        
        # Center the popup
        popup.transient(self.root)
        popup.grab_set()
        
        # Create main frame
        main_frame = tk.Frame(popup, bg=self.bg_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Bulk Analysis Results", font=self.title_font,
                              bg=self.bg_color, fg=self.text_color)
        title_label.pack(pady=(0, 20))
        
        # Scrollable text area
        text_frame = tk.Frame(main_frame, bg=self.bg_color, relief='solid', bd=1)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Courier", 10),
                                               bg=self.bg_color, fg=self.text_color, relief='flat', bd=0,
                                               padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, report_text)
        text_widget.config(state=tk.DISABLED)
        
        # Buttons frame
        button_frame = tk.Frame(main_frame, bg=self.bg_color)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Copy button
        def copy_report():
            popup.clipboard_clear()
            popup.clipboard_append(report_text)
            popup.update()
            messagebox.showinfo("Copied", "Report copied to clipboard!")
        
        copy_button = tk.Button(button_frame, text="📋 Copy Report", command=copy_report,
                               padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                               bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        close_button = tk.Button(button_frame, text="❌ Close", command=popup.destroy,
                                padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                bg='#95a5a6', fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        close_button.pack(side=tk.RIGHT)
        
        self._add_button_hover(copy_button, self.primary_color, '#2980b9')
        self._add_button_hover(close_button, '#95a5a6', '#7f8c8d')

    def build_interface(self):
        # Main container with padding (non-scrollable)
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header (stays fixed at top)
        header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_content = tk.Frame(header_frame, bg=self.primary_color)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        header_icon = tk.Label(header_content, text="🔍", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_label = tk.Label(header_content, text="Eligibility Search Tool", 
                               font=('Segoe UI', 16, 'bold'), bg=self.primary_color, fg='white')
        header_label.pack(side=tk.LEFT, anchor='w')
        
        # Create scrollable container for content (scrolls independently)
        self.main_scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color, bg=self.bg_color)
        self.main_scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        content_container = self.main_scrollable_container.scrollable_frame
        content_container.configure(bg=self.bg_color)
        
        # Upload section
        self._build_upload_section(content_container)
        
        # File info section
        self.eligibility_file_info_frame = tk.Frame(content_container, bg=self.bg_color)
        self.eligibility_file_info_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Column selection section
        self.column_selection_frame = tk.Frame(content_container, bg=self.bg_color)
        self.column_selection_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Search section
        self.search_frame = tk.Frame(content_container, bg=self.bg_color)
        self.search_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Preview section
        preview_section = tk.Frame(content_container, bg=self.bg_color)
        preview_section.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        
        self.eligibility_preview_label = tk.Label(preview_section, text="File Preview:", 
                                                  font=self.subtitle_font, bg=self.bg_color, fg=self.text_color)
        self.eligibility_preview_label.pack(anchor='w', pady=(0, 10))
        self.eligibility_preview_label.pack_forget()  # Hide initially
        
        self.eligibility_preview_frame = tk.Frame(preview_section, bg=self.bg_color)
        self.eligibility_preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Force immediate scroll update - no delay
        try:
            if hasattr(self, 'main_scrollable_container'):
                self.main_scrollable_container.force_scroll_update()
        except Exception:
            pass

    def _build_upload_section(self, parent):
        upload_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        upload_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Track if S3 section is expanded
        self.s3_section_expanded = tk.BooleanVar(value=False)
        self.s3_loaded = False  # Track if data has been loaded
        
        # Collapsible header
        upload_header = tk.Frame(upload_frame, bg=self.header_bg, cursor="hand2")
        upload_header.pack(fill=tk.X)
        
        upload_header_content = tk.Frame(upload_header, bg=self.header_bg)
        upload_header_content.pack(fill=tk.X, pady=15, padx=20)
        
        # Expand/collapse icon
        self.s3_expand_icon = tk.Label(upload_header_content, text="▶", 
                                       font=('Segoe UI', 12), bg=self.header_bg, fg=self.text_color)
        self.s3_expand_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        upload_label = tk.Label(upload_header_content, text="📁 File Source (S3 or Local)", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        upload_label.pack(side=tk.LEFT, anchor='w')
        
        # Make header clickable
        upload_header.bind('<Button-1>', lambda e: self.toggle_s3_section())
        upload_header_content.bind('<Button-1>', lambda e: self.toggle_s3_section())
        self.s3_expand_icon.bind('<Button-1>', lambda e: self.toggle_s3_section())
        upload_label.bind('<Button-1>', lambda e: self.toggle_s3_section())
        
        # ALWAYS VISIBLE: Upload button frame (outside collapsible content)
        always_visible_frame = tk.Frame(upload_frame, bg=self.frame_bg)
        always_visible_frame.pack(fill=tk.X, padx=15, pady=(10, 15))
        
        # Upload Local File button (ALWAYS VISIBLE)
        upload_button = tk.Button(always_visible_frame, text="📁 Upload Local File", 
                                 command=self.load_eligibility_file,
                                 bg=self.success_color, fg='black',
                                 font=('Segoe UI', 10, 'bold'), padx=20, pady=8, 
                                 relief='flat', bd=0, cursor="hand2")
        upload_button.pack(side=tk.LEFT)
        self._add_button_hover(upload_button, self.success_color, '#229954')
        
        # Info label (ALWAYS VISIBLE)
        self.upload_info_label = tk.Label(always_visible_frame, text="Upload a local file or browse S3 below", 
                                         font=('Segoe UI', 9), bg=self.frame_bg, fg=self.text_secondary)
        self.upload_info_label.pack(side=tk.LEFT, padx=(15, 0))
        
        # Content frame (collapsible - contains S3 browser)
        self.s3_content_frame = tk.Frame(upload_frame, bg=self.frame_bg)
        
        # S3 Browser widget
        self.s3_browser = S3FileBrowserWidget(
            self.s3_content_frame,
            bucket="s3.hello.do.integration",
            initial_prefix="clients/",
            profile="default",
            on_file_select=self.on_s3_file_selected,
            bg_color=self.bg_color,
            auto_load=False  # Don't auto-load until expanded
        )
        self.s3_browser.pack(fill=tk.BOTH, expand=True)
        
        # S3 Action button frame (inside collapsible content)
        s3_button_frame = tk.Frame(self.s3_content_frame, bg=self.frame_bg)
        s3_button_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Download button (save to disk) - ONLY FOR TIER 3
        if self.is_tier3:
            download_button = tk.Button(s3_button_frame, text="💾 Download File", 
                                       command=self.download_selected_s3_file,
                                       bg='#6c757d', fg='black',
                                       font=('Segoe UI', 10, 'bold'), padx=20, pady=8, 
                                       relief='flat', bd=0, cursor="hand2")
            download_button.pack(side=tk.LEFT, padx=(0, 10))
            self._add_button_hover(download_button, '#6c757d', '#5a6268')
        
        # Load Selected S3 File button (only visible when expanded)
        load_button = tk.Button(s3_button_frame, text="📥 Load Selected S3 File", 
                               command=self.load_selected_s3_file,
                               bg=self.primary_color, fg='black',
                               font=('Segoe UI', 10, 'bold'), padx=20, pady=8, 
                               relief='flat', bd=0, cursor="hand2")
        load_button.pack(side=tk.LEFT)
        self._add_button_hover(load_button, self.primary_color, '#c77f1b')
        
        # S3 status label
        self.s3_status_label = tk.Label(s3_button_frame, text="Select a file from S3 above", 
                                       font=('Segoe UI', 9), bg=self.frame_bg, fg=self.text_secondary)
        self.s3_status_label.pack(side=tk.LEFT, padx=(15, 0))
    
    def toggle_s3_section(self):
        """Toggle the S3 browser section visibility"""
        if self.s3_section_expanded.get():
            # Collapse
            self.s3_content_frame.pack_forget()
            self.s3_expand_icon.config(text="▶")
            self.s3_section_expanded.set(False)
        else:
            # Expand
            self.s3_content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
            self.s3_expand_icon.config(text="▼")
            self.s3_section_expanded.set(True)
            
            # Load data on first expand
            if not self.s3_loaded:
                self.s3_browser.load_folder(self.s3_browser.current_prefix)
                self.s3_loaded = True
    
    def on_s3_file_selected(self, s3_key):
        """Callback when a file is selected in the S3 browser"""
        self.selected_s3_file = s3_key
        self.s3_status_label.config(
            text=f"Selected: {s3_key.split('/')[-1]}",
            fg=self.primary_color
        )
    
    def download_selected_s3_file(self):
        """Download the selected S3 file to local disk using boto3"""
        if not BOTO3_AVAILABLE:
            messagebox.showerror("boto3 Not Available", 
                               "boto3 library is required. Install with: pip install boto3")
            return
        
        s3_key = self.s3_browser.get_selected_file()
        
        if not s3_key:
            messagebox.showwarning("No File Selected", 
                                "Please select a file from the S3 browser first.")
            return
        
        # Ask user where to save the file
        filename = s3_key.split('/')[-1]
        save_path = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(filename)[1],
            initialfile=filename,
            filetypes=[
                ("CSV Files", "*.csv"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*")
            ]
        )
        
        if not save_path:
            return  # User cancelled
        
        bucket = "s3.hello.do.integration"
        profile = "default"
        
        # Show progress
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading from S3")
        progress_window.geometry("500x180")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Match app theme colors
        dialog_bg = '#3c3c3c' if self.is_dark_mode else '#f8f9fa'
        dialog_fg = '#ffffff' if self.is_dark_mode else '#2c3e50'
        dialog_secondary = '#cccccc' if self.is_dark_mode else '#6c757d'
        
        progress_window.configure(bg=dialog_bg)
        
        # Center
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - 250
        y = (progress_window.winfo_screenheight() // 2) - 90
        progress_window.geometry(f"500x180+{x}+{y}")
        
        status_label = tk.Label(progress_window, text="Downloading from S3...", 
                            font=('Segoe UI', 11),
                            bg=dialog_bg, fg=dialog_fg)
        status_label.pack(pady=20)
        
        detail_label = tk.Label(progress_window, text=f"s3://{bucket}/{s3_key}", 
                            font=('Segoe UI', 9), 
                            bg=dialog_bg, fg=dialog_secondary)
        detail_label.pack(pady=(0, 10))
        
        progress = ttk.Progressbar(progress_window, mode='indeterminate', length=400)
        progress.pack(pady=10)
        progress.start(10)
        
        progress_window.update()
        
        def do_download():
            """Perform download in background thread"""
            try:
                # Create S3 client with profile
                session_kwargs = {}
                if profile and profile != "default":
                    session_kwargs['profile_name'] = profile
                
                session = boto3.Session(**session_kwargs)
                s3_client = session.client('s3')
                
                # Download file
                s3_client.download_file(bucket, s3_key, save_path)
                
                # Get file size
                file_size = os.path.getsize(save_path)
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                elif file_size < 1024 * 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{file_size / (1024 * 1024 * 1024):.2f} GB"
                
                progress.stop()
                progress_window.destroy()
                
                # Log S3 file download to audit trail
                if hasattr(self.root, 'log_file_access'):
                    self.root.log_file_access(f"s3://{bucket}/{s3_key}", "DOWNLOADED_FROM_S3")
                
                messagebox.showinfo("Download Complete", 
                                  f"File downloaded successfully!\n\n"
                                  f"File: {filename}\n"
                                  f"Size: {size_str}\n"
                                  f"Location: {save_path}")
                
            except NoCredentialsError:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("AWS Error", 
                                   "AWS credentials not configured. Check Settings → AWS Credentials.")
            except ClientError as e:
                progress.stop()
                progress_window.destroy()
                error_code = e.response['Error']['Code']
                messagebox.showerror("Download Error", 
                                   f"Failed to download file:\n{error_code}")
            except Exception as e:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("Error", 
                                   f"Failed to download file:\n{str(e)}")
        
        # Run download in thread to keep UI responsive
        download_thread = threading.Thread(target=do_download, daemon=True)
        download_thread.start()
    
    def load_selected_s3_file(self):
        """Load the currently selected S3 file using boto3"""
        if not BOTO3_AVAILABLE:
            messagebox.showerror("boto3 Not Available", 
                               "boto3 library is required. Install with: pip install boto3")
            return
        
        s3_key = self.s3_browser.get_selected_file()
        
        if not s3_key:
            messagebox.showwarning("No File Selected", 
                                "Please select a file from the S3 browser first.")
            return
        
        bucket = "s3.hello.do.integration"
        profile = "default"
        
        # Show progress
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading from S3")
        progress_window.geometry("500x180")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Match app theme colors
        dialog_bg = '#3c3c3c' if self.is_dark_mode else '#f8f9fa'
        dialog_fg = '#ffffff' if self.is_dark_mode else '#2c3e50'
        dialog_secondary = '#cccccc' if self.is_dark_mode else '#6c757d'
        
        progress_window.configure(bg=dialog_bg)
        
        # Center
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - 250
        y = (progress_window.winfo_screenheight() // 2) - 90
        progress_window.geometry(f"500x180+{x}+{y}")
        
        status_label = tk.Label(progress_window, text="Downloading from S3...", 
                            font=('Segoe UI', 11),
                            bg=dialog_bg, fg=dialog_fg)
        status_label.pack(pady=20)
        
        detail_label = tk.Label(progress_window, text=f"s3://{bucket}/{s3_key}", 
                            font=('Segoe UI', 9), 
                            bg=dialog_bg, fg=dialog_secondary)
        detail_label.pack(pady=(0, 10))
        
        progress = ttk.Progressbar(progress_window, mode='indeterminate', length=400)
        progress.pack(pady=10)
        progress.start(10)
        
        progress_window.update()
        
        def do_load():
            """Perform load in background thread"""
            try:
                # Create S3 client with profile
                session_kwargs = {}
                if profile and profile != "default":
                    session_kwargs['profile_name'] = profile
                
                session = boto3.Session(**session_kwargs)
                s3_client = session.client('s3')
                
                # Create temp file
                temp_dir = tempfile.gettempdir()
                filename = s3_key.split('/')[-1]
                local_path = os.path.join(temp_dir, filename)
                
                # Download file
                s3_client.download_file(bucket, s3_key, local_path)
                
                progress.stop()
                progress_window.destroy()
                
                try:
                    # Process the file using the same logic as manual upload
                    self.eligibility_file_path = local_path
                    
                    # Log S3 file access to audit trail
                    if hasattr(self.root, 'log_file_access'):
                        self.root.log_file_access(f"s3://{bucket}/{s3_key}", "LOADED_FROM_S3")
                    
                    self._process_eligibility_file()
                    
                    # Auto-collapse S3 section after successful load
                    if self.s3_section_expanded.get():
                        self.toggle_s3_section()
                
                finally:
                    # Clean up: Delete temporary file after processing
                    try:
                        if os.path.exists(local_path):
                            os.remove(local_path)
                            print(f"Cleaned up temporary file: {local_path}")
                    except Exception as cleanup_error:
                        print(f"Warning: Could not delete temporary file {local_path}: {cleanup_error}")
                
            except NoCredentialsError:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("AWS Error",
                                   "AWS credentials not configured. Check Settings → AWS Credentials.")
            except ClientError as e:
                progress.stop()
                progress_window.destroy()
                error_code = e.response['Error']['Code']
                messagebox.showerror("Load Error",
                                   f"Failed to load file:\n{error_code}")
            except Exception as e:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("Error",
                                   f"Failed to load file:\n{str(e)}")
        
        # Run load in thread to keep UI responsive
        load_thread = threading.Thread(target=do_load, daemon=True)
        load_thread.start()


    def load_eligibility_file(self):
        """Select and load a file from the local filesystem"""
        self.eligibility_file_path = filedialog.askopenfilename(
            filetypes=[("CSV/TXT Files", "*.csv *.txt"), ("All Files", "*.*")]
        )
        if not self.eligibility_file_path:
            return
        
        # Log file access to audit trail
        if hasattr(self.root, 'log_file_access'):
            self.root.log_file_access(self.eligibility_file_path, "LOADED_FILE")
        
        self._process_eligibility_file()
    
    def _process_eligibility_file(self):
        """Process the eligibility file (works for both manual upload and S3)"""
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Loading File")
        progress_window.geometry("500x280")  # Increased height for OK button
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Match app theme colors
        dialog_bg = '#3c3c3c' if self.is_dark_mode else '#f8f9fa'
        dialog_fg = '#ffffff' if self.is_dark_mode else '#2c3e50'
        dialog_secondary = '#cccccc' if self.is_dark_mode else '#6c757d'
        
        progress_window.configure(bg=dialog_bg)
        
        # Center the window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - 250
        y = (progress_window.winfo_screenheight() // 2) - 140  # Adjusted for new height
        progress_window.geometry(f"500x280+{x}+{y}")
        
        # Progress window content
        title_label = tk.Label(progress_window, text="Processing File", 
                              font=('Segoe UI', 12, 'bold'),
                              bg=dialog_bg, fg=dialog_fg)
        title_label.pack(pady=(20, 10))
        
        status_label = tk.Label(progress_window, text="Detecting file format...", 
                               font=('Segoe UI', 10),
                               bg=dialog_bg, fg=dialog_fg)
        status_label.pack(pady=10)
        
        details_label = tk.Label(progress_window, text="", 
                                font=('Segoe UI', 9), 
                                bg=dialog_bg, fg=dialog_secondary)
        details_label.pack(pady=5)
        
        progress_bar = ttk.Progressbar(progress_window, mode='determinate', length=400)
        progress_bar.pack(pady=15)
        
        progress_text = tk.Label(progress_window, text="0%", 
                                font=('Segoe UI', 9, 'bold'),
                                bg=dialog_bg, fg=dialog_fg)
        progress_text.pack()
        
        progress_window.update()
        
        try:
            # Step 1: Detect delimiter (10%)
            progress_bar['value'] = 10
            progress_text.config(text="10%")
            status_label.config(text="Detecting delimiter...")
            details_label.config(text="Testing comma, tab, and pipe delimiters")
            progress_window.update()
            import time
            time.sleep(0.3)  # Brief pause to show progress
            
            delimiters_to_try = [
                (',', 'Comma'),
                ('\t', 'Tab'), 
                ('|', 'Pipe')
            ]
            
            successful_load = False
            used_delimiter = None
            used_delimiter_name = None
            
            best_result = None
            best_column_count = 0
            best_delimiter_info = None
            
            for delim, delim_name in delimiters_to_try:
                try:
                    # Force string dtype in test read to preserve formatting
                    test_df = pd.read_csv(self.eligibility_file_path, delimiter=delim, nrows=5, dtype=str)
                    column_count = len(test_df.columns)
                    
                    if column_count > best_column_count:
                        best_column_count = column_count
                        best_result = test_df
                        best_delimiter_info = (delim, delim_name)
                        
                except Exception as e:
                    continue
            
            # Step 2: Load file (30%)
            progress_bar['value'] = 30
            progress_text.config(text="30%")
            status_label.config(text="Loading file data...")
            if best_delimiter_info:
                details_label.config(text=f"Using {best_delimiter_info[1]} delimiter")
            progress_window.update()
            time.sleep(0.3)  # Brief pause to show progress
            
            if best_result is not None and best_column_count > 1:
                try:
                    # Force ALL columns to be read as strings to preserve exact formatting (including leading zeros)
                    self.eligibility_df = pd.read_csv(self.eligibility_file_path, delimiter=best_delimiter_info[0], dtype=str)
                    successful_load = True
                    used_delimiter = best_delimiter_info[0]
                    used_delimiter_name = best_delimiter_info[1]
                    
                except Exception as e:
                    successful_load = False
            
            if not successful_load:
                try:
                    # Force ALL columns to be read as strings to preserve exact formatting (including leading zeros)
                    self.eligibility_df = pd.read_csv(self.eligibility_file_path, delimiter=',', dtype=str)
                    used_delimiter = ','
                    used_delimiter_name = 'Comma (fallback)'
                    successful_load = True
                except Exception as e:
                    progress_window.destroy()
                    messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
                    return
            
            if not successful_load:
                progress_window.destroy()
                messagebox.showerror("Error", "Failed to load file with any delimiter.")
                return
            
            # Step 3: Analyze data (60%)
            progress_bar['value'] = 60
            progress_text.config(text="60%")
            status_label.config(text="Analyzing data...")
            details_label.config(text=f"Loaded {len(self.eligibility_df):,} rows, {len(self.eligibility_df.columns)} columns")
            progress_window.update()
            time.sleep(0.3)  # Brief pause to show progress
            
            self._analyze_file_date_formats()
            
            # Step 4: Preparing UI (80%)
            progress_bar['value'] = 80
            progress_text.config(text="80%")
            status_label.config(text="Preparing interface...")
            details_label.config(text="Setting up column selections and preview")
            progress_window.update()
            time.sleep(0.3)  # Brief pause to show progress
            
            self._show_eligibility_file_info(used_delimiter_name)
            self._show_eligibility_column_selection()
            self._show_eligibility_search_section()
            
            # Step 5: Displaying preview (95%)
            progress_bar['value'] = 95
            progress_text.config(text="95%")
            status_label.config(text="Displaying preview...")
            progress_window.update()
            time.sleep(0.3)  # Brief pause to show progress
            
            self._show_eligibility_preview()
            
            # Step 6: Complete! (100%)
            progress_bar['value'] = 100
            progress_text.config(text="100%")
            status_label.config(text="File loaded successfully from S3!")
            
            # Show file details
            filename = os.path.basename(self.eligibility_file_path)
            details_label.config(
                text=f"File: {filename}\nRows: {len(self.eligibility_df):,} | Columns: {len(self.eligibility_df.columns)}",
                fg='#27ae60'
            )
            progress_window.update()
            time.sleep(0.2)  # Brief pause before showing OK button
            
            # Add OK button with black text
            ok_button = tk.Button(progress_window, text="OK", 
                                 command=progress_window.destroy,
                                 padx=30, pady=8, 
                                 font=('Segoe UI', 10, 'bold'),
                                 bg=self.primary_color, fg='#000000',  # Black text
                                 relief='flat', bd=0, cursor="hand2")
            ok_button.pack(pady=(10, 15))
            
            # Force scroll update after content is loaded
            def update_scroll_after_load():
                try:
                    if hasattr(self, 'main_scrollable_container'):
                        self.main_scrollable_container.force_scroll_update()
                except Exception:
                    pass
            
            # Multiple updates to ensure it works
            self.root.after(200, update_scroll_after_load)
            self.root.after(500, update_scroll_after_load)
            
            # Don't auto-close - wait for user to click OK
            
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Error", f"Failed to process file:\n{str(e)}")
            
            # Multiple updates to ensure it works
            self.root.after(200, update_scroll_after_load)
            self.root.after(500, update_scroll_after_load)
            
    def _analyze_file_date_formats(self):
        if self.eligibility_df.empty:
            return
        
        self.date_format_analysis = {}
        
        # Look for columns that might contain dates
        date_keywords = ['date', 'birth', 'dob', 'term', 'expire', 'end', 'start', 'create']
        date_columns = []
        
        for col in self.eligibility_df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in date_keywords):
                date_columns.append(col)
        
        # Analyze each potential date column
        for col in date_columns:
            analysis = self.analyze_date_formats_in_column(self.eligibility_df[col])
            if analysis:
                self.date_format_analysis[col] = analysis

    def _get_date_format_summary(self):
        if not self.date_format_analysis:
            return ""
        
        summary_lines = []
        for col, analysis in self.date_format_analysis.items():
            if analysis['is_consistent']:
                summary_lines.append(f"✅ {col}: {analysis['dominant_format']} ({analysis['dominant_percentage']:.1f}% consistent)")
            else:
                summary_lines.append(f"⚠️ {col}: Mixed formats - {analysis['dominant_format']} ({analysis['dominant_percentage']:.1f}%)")
        
        if summary_lines:
            return "Date Format Analysis:\n" + "\n".join(summary_lines)
        return ""

    def _show_eligibility_column_selection(self):
        for widget in self.column_selection_frame.winfo_children():
            widget.destroy()
        
        if self.eligibility_df.empty:
            return
        
        # Column selection section
        selection_frame = tk.Frame(self.column_selection_frame, bg=self.frame_bg, relief='solid', bd=1)
        selection_frame.pack(fill=tk.X, pady=(0, 0))
        
        # Header
        selection_header = tk.Frame(selection_frame, bg=self.header_bg, height=50)
        selection_header.pack(fill=tk.X)
        
        selection_label = tk.Label(selection_header, text="🔗 Step 2: Select Columns", 
                                  font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        selection_label.pack(pady=15)
        
        # Content
        selection_content = tk.Frame(selection_frame, bg=self.frame_bg)
        selection_content.pack(fill=tk.X, padx=20, pady=20)
        
        column_options = [""] + [f"{i}: {col}" for i, col in enumerate(self.eligibility_df.columns)]
        
        dropdowns_frame = tk.Frame(selection_content, bg=self.frame_bg)
        dropdowns_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Row 1
        row1_frame = tk.Frame(dropdowns_frame, bg=self.frame_bg)
        row1_frame.pack(fill=tk.X, pady=(0, 10))
        
        first_name_frame = tk.Frame(row1_frame, bg=self.frame_bg)
        first_name_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        first_name_label = tk.Label(first_name_frame, text="First Name:", width=12, anchor="w", 
                                   font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        first_name_label.pack(anchor='w')
        
        self.first_name_dropdown = ttk.Combobox(first_name_frame, textvariable=self.first_name_var, 
                                               values=column_options, state="readonly", width=25)
        self.first_name_dropdown.pack(anchor='w', pady=(5, 0))
        
        last_name_frame = tk.Frame(row1_frame, bg=self.frame_bg)
        last_name_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        last_name_label = tk.Label(last_name_frame, text="Last Name:", width=12, anchor="w", 
                                  font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        last_name_label.pack(anchor='w')
        
        self.last_name_dropdown = ttk.Combobox(last_name_frame, textvariable=self.last_name_var, 
                                              values=column_options, state="readonly", width=25)
        self.last_name_dropdown.pack(anchor='w', pady=(5, 0))
        
        # Date of Birth dropdown
        dob_frame = tk.Frame(row1_frame, bg=self.frame_bg)
        dob_frame.pack(side=tk.LEFT)
        
        dob_label = tk.Label(dob_frame, text="Date of Birth:", width=12, anchor="w", 
                            font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        dob_label.pack(anchor='w')
        
        self.dob_dropdown = ttk.Combobox(dob_frame, textvariable=self.date_of_birth_var, 
                                        values=column_options, state="readonly", width=25)
        self.dob_dropdown.pack(anchor='w', pady=(5, 0))
        
        # Row 2
        row2_frame = tk.Frame(dropdowns_frame, bg=self.frame_bg)
        row2_frame.pack(fill=tk.X)
        
        relationship_frame = tk.Frame(row2_frame, bg=self.frame_bg)
        relationship_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        relationship_label = tk.Label(relationship_frame, text="Relationship:", width=12, anchor="w", 
                                     font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        relationship_label.pack(anchor='w')
        
        self.relationship_dropdown = ttk.Combobox(relationship_frame, textvariable=self.relationship_var, 
                                                 values=column_options, state="readonly", width=25)
        self.relationship_dropdown.pack(anchor='w', pady=(5, 0))
        
        term_date_frame = tk.Frame(row2_frame, bg=self.frame_bg)
        term_date_frame.pack(side=tk.LEFT)
        
        term_date_label = tk.Label(term_date_frame, text="Term Date:", width=12, anchor="w", 
                                  font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        term_date_label.pack(anchor='w')
        
        self.term_date_dropdown = ttk.Combobox(term_date_frame, textvariable=self.term_date_var, 
                                              values=column_options, state="readonly", width=25)
        self.term_date_dropdown.pack(anchor='w', pady=(5, 0))
        
        self.first_name_var.set("")
        self.last_name_var.set("")
        self.date_of_birth_var.set("")
        self.relationship_var.set("")
        self.term_date_var.set("")
        
        # Help text
        help_text = ("Select the columns that correspond to each field. The tool will auto-detect common column names.")
        help_label = tk.Label(selection_content, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
        help_label.pack(anchor="w")
        
        self._auto_select_eligibility_columns()

    def _auto_select_eligibility_columns(self):
        if self.eligibility_df.empty:
            return
            
        columns = [col.lower() for col in self.eligibility_df.columns]
        
        # First name patterns
        first_name_patterns = [
            'first_name', 'firstname', 'fname', 'first', 'given_name', 'givenname'
        ]
        
        last_name_patterns = [
            'last_name', 'lastname', 'lname', 'last', 'surname', 'family_name', 'familyname'
        ]
        
        dob_patterns = [
            'date_of_birth', 'dateofbirth', 'dob', 'birth_date', 'birthdate', 
            'date_birth', 'birth', 'born', 'birthday'
        ]
        
        relationship_patterns = [
            'relationship', 'relation', 'member_type', 'membertype', 'rel', 
            'member_relation', 'family_relation', 'dependency', 'dependent_type'
        ]
        
        term_patterns = [
            'term_date', 'termdate', 'end_date', 'enddate', 'termination_date',
            'terminationdate', 'term', 'end', 'expiry', 'expiry_date'
        ]
        
        for pattern in first_name_patterns:
            for i, col in enumerate(columns):
                if pattern in col:
                    actual_column = self.eligibility_df.columns[i]
                    self.first_name_var.set(f"{i}: {actual_column}")
                    break
            if self.first_name_var.get():
                break
        
        for pattern in last_name_patterns:
            for i, col in enumerate(columns):
                if pattern in col:
                    actual_column = self.eligibility_df.columns[i]
                    self.last_name_var.set(f"{i}: {actual_column}")
                    break
            if self.last_name_var.get():
                break
        
        for pattern in dob_patterns:
            for i, col in enumerate(columns):
                if pattern in col:
                    actual_column = self.eligibility_df.columns[i]
                    self.date_of_birth_var.set(f"{i}: {actual_column}")
                    break
            if self.date_of_birth_var.get():
                break
        
        for pattern in relationship_patterns:
            for i, col in enumerate(columns):
                if pattern in col:
                    actual_column = self.eligibility_df.columns[i]
                    self.relationship_var.set(f"{i}: {actual_column}")
                    break
            if self.relationship_var.get():
                break
        
        for pattern in term_patterns:
            for i, col in enumerate(columns):
                if pattern in col:
                    actual_column = self.eligibility_df.columns[i]
                    self.term_date_var.set(f"{i}: {actual_column}")
                    break
            if self.term_date_var.get():
                break

    def _show_eligibility_search_section(self):
        for widget in self.search_frame.winfo_children():
            widget.destroy()
        
        if self.eligibility_df.empty:
            return
        
        # Search section
        search_frame = tk.Frame(self.search_frame, bg=self.frame_bg, relief='solid', bd=1)
        search_frame.pack(fill=tk.X, pady=(0, 0))
        
        # Header
        search_header = tk.Frame(search_frame, bg=self.header_bg, height=50)
        search_header.pack(fill=tk.X)
        
        search_label = tk.Label(search_header, text="🔍 Step 3: Search Records", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        search_label.pack(pady=15)
        
        # Content
        search_content = tk.Frame(search_frame, bg=self.frame_bg)
        search_content.pack(fill=tk.X, padx=20, pady=20)
        
        search_inputs_frame = tk.Frame(search_content, bg=self.frame_bg)
        search_inputs_frame.pack(fill=tk.X, pady=(0, 15))
        
        # First Name search
        first_name_search_frame = tk.Frame(search_inputs_frame, bg=self.frame_bg)
        first_name_search_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        first_name_search_label = tk.Label(first_name_search_frame, text="Search First Name:", 
                                           width=15, anchor="w", font=self.label_font,
                                           bg=self.frame_bg, fg=self.text_secondary)
        first_name_search_label.pack(anchor='w')
        
        first_name_entry_frame = tk.Frame(first_name_search_frame, bg=self.bg_color, relief='solid', bd=1)
        first_name_search_entry = tk.Entry(first_name_entry_frame, textvariable=self.search_first_name, 
                                           width=23, font=self.text_font, bg=self.bg_color, fg=self.text_color,
                                           relief='flat', bd=0)
        first_name_search_entry.pack(padx=5, pady=3)
        first_name_entry_frame.pack(anchor='w', pady=(5, 0))
        
        # Last Name search
        last_name_search_frame = tk.Frame(search_inputs_frame, bg=self.frame_bg)
        last_name_search_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        last_name_search_label = tk.Label(last_name_search_frame, text="Search Last Name:", 
                                          width=15, anchor="w", font=self.label_font,
                                          bg=self.frame_bg, fg=self.text_secondary)
        last_name_search_label.pack(anchor='w')
        
        last_name_entry_frame = tk.Frame(last_name_search_frame, bg=self.bg_color, relief='solid', bd=1)
        last_name_search_entry = tk.Entry(last_name_entry_frame, textvariable=self.search_last_name, 
                                          width=23, font=self.text_font, bg=self.bg_color, fg=self.text_color,
                                          relief='flat', bd=0)
        last_name_search_entry.pack(padx=5, pady=3)
        last_name_entry_frame.pack(anchor='w', pady=(5, 0))
        
        # Search buttons
        search_buttons_frame = tk.Frame(search_inputs_frame, bg=self.frame_bg)
        search_buttons_frame.pack(side=tk.LEFT)
        
        tk.Label(search_buttons_frame, text="Actions:", width=10, anchor="w", 
                font=self.label_font, bg=self.frame_bg, fg=self.text_secondary).pack(anchor='w')
        
        buttons_container = tk.Frame(search_buttons_frame, bg=self.frame_bg)
        buttons_container.pack(anchor='w', pady=(5, 0))
        
        search_button = tk.Button(buttons_container, text="🔍 Search", command=self._perform_eligibility_search,
                                 padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                 bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        search_button.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_button = tk.Button(buttons_container, text="🗑️ Clear", command=self._clear_eligibility_search,
                                padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                bg='#95a5a6', fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        copy_button = tk.Button(buttons_container, text="📋 Copy", command=self._copy_preview_results,
                               padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                               bg=self.warning_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        copy_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # NEW: Add the Bulk Analysis button
        bulk_button = tk.Button(buttons_container, text="📊 Analyze All", command=self.analyze_all_records,
                               padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                               bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        bulk_button.pack(side=tk.LEFT)
        
        # Add hover effects to buttons
        self._add_button_hover(search_button, self.primary_color, '#2980b9')
        self._add_button_hover(clear_button, '#95a5a6', '#7f8c8d')
        self._add_button_hover(copy_button, self.warning_color, '#d35400')
        self._add_button_hover(bulk_button, self.success_color, '#229954')
        
        # Search info display
        search_info_frame = tk.Frame(search_content, bg=self.frame_bg)
        search_info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.search_info_label = tk.Label(search_info_frame, text="", 
                                          font=("Segoe UI", 10), foreground=self.primary_color, bg=self.frame_bg)
        self.search_info_label.pack(anchor='w')
        
        # Help text
        help_text = ("Enter partial or complete names to search. Leave fields empty to search all records. Use 'Analyze All' to get a comprehensive data quality report.")
        help_label = tk.Label(search_content, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
        help_label.pack(anchor="w")

    def _perform_eligibility_search(self):
        if self.eligibility_df.empty:
            return
        
        search_first = self.search_first_name.get().strip()
        search_last = self.search_last_name.get().strip()
        
        if not search_first and not search_last:
            return
        
        first_name_col = self._get_column_name_from_selection(self.first_name_var.get())
        last_name_col = self._get_column_name_from_selection(self.last_name_var.get())
        dob_col = self._get_column_name_from_selection(self.date_of_birth_var.get())
        term_date_col = self._get_column_name_from_selection(self.term_date_var.get())
        
        filtered_data = self.eligibility_df.copy()
        
        if search_first and first_name_col:
            if first_name_col in filtered_data.columns:
                mask = filtered_data[first_name_col].astype(str).str.contains(
                    search_first, case=False, na=False)
                filtered_data = filtered_data[mask]
            else:
                return
        elif search_first and not first_name_col:
            return
        
        if search_last and last_name_col:
            if last_name_col in filtered_data.columns:
                mask = filtered_data[last_name_col].astype(str).str.contains(
                    search_last, case=False, na=False)
                filtered_data = filtered_data[mask]
            else:
                return
        elif search_last and not last_name_col:
            return
        
        dob_format_analysis = self.date_format_analysis.get(dob_col) if dob_col else None
        term_format_analysis = self.date_format_analysis.get(term_date_col) if term_date_col else None
        
        if dob_col and dob_col in filtered_data.columns:
            age_info = []
            format_warnings = []
            under_18_count = 0
            format_anomaly_count = 0
            
            for _, row in filtered_data.iterrows():
                age, is_under_18, age_text, format_warning = self.calculate_age(row[dob_col], dob_format_analysis)
                age_info.append(age_text)
                format_warnings.append(format_warning if format_warning else "")
                
                if is_under_18:
                    under_18_count += 1
                if format_warning:
                    format_anomaly_count += 1
            
            filtered_data = filtered_data.copy()
            filtered_data['Age_Status'] = age_info
            filtered_data['DOB_Format_Check'] = format_warnings
        
        if term_date_col and term_date_col in filtered_data.columns:
            term_info = []
            term_format_warnings = []
            expired_count = 0
            term_format_anomaly_count = 0
            
            for _, row in filtered_data.iterrows():
                term_date, is_expired, term_text, format_warning = self.check_term_date(row[term_date_col], term_format_analysis)
                term_info.append(term_text)
                term_format_warnings.append(format_warning if format_warning else "")
                
                if is_expired:
                    expired_count += 1
                if format_warning:
                    term_format_anomaly_count += 1
            
            if 'Age_Status' not in filtered_data.columns:
                filtered_data = filtered_data.copy()
            filtered_data['Term_Status'] = term_info
            filtered_data['Term_Format_Check'] = term_format_warnings
        
        self.filtered_df = filtered_data
        
        total_records = len(self.eligibility_df)
        filtered_records = len(self.filtered_df)
        
        search_terms = []
        if search_first:
            search_terms.append(f"First Name: '{search_first}'")
        if search_last:
            search_terms.append(f"Last Name: '{search_last}'")
        
        search_summary = " AND ".join(search_terms)
        info_text = f"Found {filtered_records:,} of {total_records:,} records matching {search_summary}"
        
        # Add age and term date information to summary if available
        warning_parts = []
        has_any_anomalies = False
        
        # Initialize counters
        under_18_count = 0
        expired_count = 0
        format_anomaly_count = 0
        term_format_anomaly_count = 0
        
        if dob_col and dob_col in self.eligibility_df.columns and 'Age_Status' in filtered_data.columns:
            under_18_count = sum(1 for status in filtered_data['Age_Status'] if 'Under 18' in str(status))
            if under_18_count > 0:
                warning_parts.append(f"⚠️ {under_18_count} under 18")
                has_any_anomalies = True
            else:
                warning_parts.append("✅ All 18+")
            
            # Check for format anomalies in DOB
            format_anomaly_count = sum(1 for warning in filtered_data['DOB_Format_Check'] if warning)
            if format_anomaly_count > 0:
                warning_parts.append(f"🔍 {format_anomaly_count} DOB format anomalies")
                has_any_anomalies = True
        
        if term_date_col and term_date_col in self.eligibility_df.columns and 'Term_Status' in filtered_data.columns:
            expired_count = sum(1 for status in filtered_data['Term_Status'] if 'EXPIRED' in str(status))
            if expired_count > 0:
                warning_parts.append(f"⚠️ {expired_count} expired")
                has_any_anomalies = True
            else:
                warning_parts.append("✅ All active")
            
            # Check for format anomalies in term dates
            if 'Term_Format_Check' in filtered_data.columns:
                term_format_anomaly_count = sum(1 for warning in filtered_data['Term_Format_Check'] if warning)
                if term_format_anomaly_count > 0:
                    warning_parts.append(f"🔍 {term_format_anomaly_count} term date format anomalies")
                    has_any_anomalies = True
        
        if warning_parts:
            info_text += f" | {' | '.join(warning_parts)}"
        
        # Determine color based on whether records were found AND whether there are any anomalies
        if filtered_records == 0:
            label_color = self.danger_color  # No records found
        elif has_any_anomalies:
            label_color = self.danger_color  # Records found but has anomalies (under 18, expired, or format issues)
        else:
            label_color = self.success_color  # Records found and everything is clean
        
        self.search_info_label.config(text=info_text, foreground=label_color)
        
        # Update preview with filtered results
        self._show_eligibility_preview(use_filtered=True)

    def _copy_preview_results(self):
        if self.eligibility_df.empty:
            return
        
        # Determine which data to copy
        if not self.filtered_df.empty:
            data_to_copy = self.filtered_df
            data_type = "filtered search results"
        else:
            data_to_copy = self.eligibility_df
            data_type = "all data"
        
        try:
            # Get filename
            filename = os.path.basename(self.eligibility_file_path) if self.eligibility_file_path else "Unknown File"
            
            # Convert to tab-separated format for better Excel compatibility
            data_csv = data_to_copy.to_csv(sep='\t', index=False)
            
            # Add filename and metadata header
            header_lines = [
                f"Source File:\t{filename}",
                f"Total Columns:\t{len(data_to_copy.columns)}",
                "",  # Empty line separator
            ]
            
            # Combine header with data
            clipboard_text = "\n".join(header_lines) + data_csv
            
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(clipboard_text)
            self.root.update()  # Required for clipboard to work properly
            
            # Show confirmation
            row_count = len(data_to_copy)
            col_count = len(data_to_copy.columns)
            messagebox.showinfo("Copy Successful", 
                               f"✅ Copied {data_type} to clipboard!\n\n"
                               f"📁 Source File: {filename}\n\n"
                               f"📊 Data copied:\n"
                               f"• Rows: {row_count:,}\n"
                               f"• Columns: {col_count}\n"
                               f"• Format: Tab-separated (Excel compatible)\n\n"
                               f"💡 Tip: Paste into Excel, Google Sheets, or any text editor")
            
        except Exception as e:
            pass

    def _clear_eligibility_search(self):
        self.search_first_name.set("")
        self.search_last_name.set("")
        self.filtered_df = pd.DataFrame()
        self.search_info_label.config(text="")
        
        # Show all data in preview
        self._show_eligibility_preview(use_filtered=False)

    def _get_column_name_from_selection(self, selection):
        if selection and ":" in selection:
            try:
                col_index = int(selection.split(":")[0])
                if 0 <= col_index < len(self.eligibility_df.columns):
                    return self.eligibility_df.columns[col_index]
            except (ValueError, IndexError):
                pass
        return None

    def _show_eligibility_file_info(self, delimiter_name=None):
        for widget in self.eligibility_file_info_frame.winfo_children():
            widget.destroy()
        
        if self.eligibility_df.empty:
            return
        
        # File info section
        info_frame = tk.Frame(self.eligibility_file_info_frame, bg=self.frame_bg, relief='solid', bd=1)
        info_frame.pack(fill=tk.X, pady=(0, 0))
        
        # Header
        info_header = tk.Frame(info_frame, bg=self.header_bg, height=40)
        info_header.pack(fill=tk.X)
        
        info_label = tk.Label(info_header, text="📄 File Information", 
                             font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        info_label.pack(pady=10)
        
        # Content
        info_content = tk.Frame(info_frame, bg=self.frame_bg)
        info_content.pack(fill=tk.X, padx=20, pady=15)
        
        filename = os.path.basename(self.eligibility_file_path)
        rows, cols = self.eligibility_df.shape
        
        if delimiter_name:
            info_text = f"📁 File: {filename} | 📊 Rows: {rows:,} | 📋 Columns: {cols} | 🔗 Delimiter: {delimiter_name}"
        else:
            info_text = f"📁 File: {filename} | 📊 Rows: {rows:,} | 📋 Columns: {cols}"
            
        info_text_label = tk.Label(info_content, text=info_text, font=self.label_font,
                                   bg=self.frame_bg, fg=self.text_color)
        info_text_label.pack(anchor='w')

    def _show_eligibility_preview(self, use_filtered=False):
        for widget in self.eligibility_preview_frame.winfo_children():
            widget.destroy()
        
        if self.eligibility_df.empty:
            self.eligibility_preview_label.pack_forget()
            return
        
        # Determine which data to show
        if use_filtered and not self.filtered_df.empty:
            preview_data = self.filtered_df.head(10)
            total_rows = len(self.filtered_df)
            data_type = "Filtered"
        else:
            preview_data = self.eligibility_df.head(10)
            total_rows = len(self.eligibility_df)
            data_type = "All"
        
        # Preview section
        preview_frame = tk.Frame(self.eligibility_preview_frame, bg=self.frame_bg, relief='solid', bd=1)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        
        # Header
        preview_header = tk.Frame(preview_frame, bg=self.header_bg, height=50)
        preview_header.pack(fill=tk.X)
        
        # Update label to show what type of data is being displayed
        label_text = f"📊 File Preview ({data_type} Data - Showing first 10 of {total_rows:,} rows)"
        preview_label = tk.Label(preview_header, text=label_text, 
                                font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        preview_label.pack(pady=15)
        
        # Content
        preview_content = tk.Frame(preview_frame, bg=self.frame_bg)
        preview_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        cols = list(preview_data.columns)
        
        tree_container = tk.Frame(preview_content, bg=self.bg_color, relief='solid', bd=1)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        style = ttk.Style()
        style.configure("EligibilityPreview.Treeview", font=self.text_font)
        style.configure("EligibilityPreview.Treeview.Heading", font=self.label_font)
        
        tree = ttk.Treeview(tree_container, columns=cols, show="headings", 
                           height=12, style="EligibilityPreview.Treeview")
        
        for i, col in enumerate(cols):
            header_text = f"{i}: {col}"
            tree.heading(col, text=header_text)
            tree.column(col, width=150, minwidth=100, anchor="w")
        
        for idx, (_, row) in enumerate(preview_data.iterrows()):
            display_values = []
            for col_name, val in row.items():
                # PRESERVE EXACT VALUES - especially for relationship column
                if pd.isna(val):
                    str_val = ""  # Show empty for NaN values
                else:
                    # Convert to string but preserve exact formatting (no title case, no stripping for relationship)
                    str_val = str(val)
                
                # Truncate only if too long for display
                if len(str_val) > 30:
                    str_val = str_val[:27] + "..."
                display_values.append(str_val)
            
            # Color code rows with any anomalies as red
            tags = []
            has_age_issue = 'Age_Status' in row and 'Under 18' in str(row['Age_Status'])
            has_term_issue = 'Term_Status' in row and 'EXPIRED' in str(row['Term_Status'])
            has_dob_format_issue = 'DOB_Format_Check' in row and row['DOB_Format_Check']
            has_term_format_issue = 'Term_Format_Check' in row and row['Term_Format_Check']
            
            # If ANY anomaly exists, highlight the entire row in red
            if has_age_issue or has_term_issue or has_dob_format_issue or has_term_format_issue:
                tags = ['anomaly']
            
            tree.insert("", "end", values=display_values, tags=tags)
        
        tree.tag_configure('anomaly', background='#ffcccc', foreground='#990000')  # Red background for any anomaly
        
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=h_scrollbar.set)
        
        tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Show preview label
        self.eligibility_preview_label.pack(anchor='w', pady=(0, 10))

if __name__ == "__main__":
    root = tk.Tk()
    app = EligibilitySearchTool(root)
    root.mainloop()