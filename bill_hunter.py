import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext, simpledialog
import csv
import os
import json
from datetime import datetime
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

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
        """Detect if we're running inside HelloToolbelt"""
        try:
            current_parent = self.parent
            while current_parent:
                # Look for HelloToolbelt MockRoot characteristics
                if (hasattr(current_parent, '_title') and 
                    hasattr(current_parent, 'pack') and 
                    hasattr(current_parent, '_current_bg')):
                    return True
                try:
                    current_parent = current_parent.master
                except:
                    break
            return False
        except:
            return False
        
    def _bind_mousewheel_to_children(self, widget):
        """Recursively bind mousewheel to all child widgets"""
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel_linux)
            widget.bind("<Button-5>", self._on_mousewheel_linux)
            
            for child in widget.winfo_children():
                self._bind_mousewheel_to_children(child)
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
                folder_name = folder_path.rstrip('/').split('/')[-1]
                if folder_name:
                    folders.append(folder_name)
            
            # Process files (Contents)
            for obj in response.get('Contents', []):
                key = obj['Key']
                
                if key == prefix or key.endswith('/'):
                    continue
                
                filename = key.split('/')[-1]
                if not filename:
                    continue
                    
                size = obj['Size']
                modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                files.append((filename, size, modified))
            
            # Add folders
            for folder in sorted(folders):
                self.tree.insert('', 'end', text=f"📁 {folder}", 
                               values=('Folder', '--', ''), tags=('folder',))
            
            # Add files
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

class S3BrowserDialog:
    """Dialog for browsing S3 folders and selecting files"""
    def __init__(self, parent, bucket, initial_prefix="", profile="default"):
        self.result = None
        self.bucket = bucket
        self.profile = profile
        self.current_prefix = initial_prefix
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Browse S3: {bucket}")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 350
        y = (self.dialog.winfo_screenheight() // 2) - 250
        self.dialog.geometry(f"700x500+{x}+{y}")
        
        self._build_ui()
        
        # Load initial folder
        self.load_folder(self.current_prefix)
        
    def _build_ui(self):
        """Build the UI for S3 browser"""
        # Header frame
        header_frame = tk.Frame(self.dialog, bg='#0a9640', relief='flat', bd=0)
        header_frame.pack(fill=tk.X)
        
        header_content = tk.Frame(header_frame, bg='#0a9640')
        header_content.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(header_content, text="☁️ S3 Browser", 
                font=('Segoe UI', 14, 'bold'), bg='#0a9640', fg='white').pack(side=tk.LEFT)
        
        # Path display frame
        path_frame = tk.Frame(self.dialog, bg='#f8f9fa')
        path_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(path_frame, text="Current path:", 
                font=('Segoe UI', 9), bg='#f8f9fa').pack(side=tk.LEFT, padx=(0, 5))
        
        self.path_label = tk.Label(path_frame, text=f"s3://{self.bucket}/", 
                                   font=('Segoe UI', 9, 'bold'), bg='#f8f9fa', fg='#0a9640')
        self.path_label.pack(side=tk.LEFT)
        
        # Back button
        button_frame = tk.Frame(self.dialog, bg='white')
        button_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.back_btn = tk.Button(button_frame, text="⬆️ Up", command=self.go_up,
                                  bg='#e9ecef', font=('Segoe UI', 9), padx=10, pady=5,
                                  relief='flat', bd=0, cursor="hand2")
        self.back_btn.pack(side=tk.LEFT)
        
        # Treeview for folders and files
        tree_frame = tk.Frame(self.dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.tree = ttk.Treeview(tree_frame, 
                                columns=('Type', 'Size'),
                                yscrollcommand=vsb.set,
                                xscrollcommand=hsb.set)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure columns
        self.tree.heading('#0', text='Name')
        self.tree.heading('Type', text='Type')
        self.tree.heading('Size', text='Size')
        
        self.tree.column('#0', width=400)
        self.tree.column('Type', width=100)
        self.tree.column('Size', width=100)
        
        # Pack scrollbars and tree
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click and selection
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Status label
        self.status_label = tk.Label(self.dialog, text="Loading...", 
                                     font=('Segoe UI', 9), fg='gray')
        self.status_label.pack(pady=(0, 10))
        
        # Button frame
        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        self.select_btn = tk.Button(btn_frame, text="Select File", command=self.select_file,
                                    bg='#0a9640', fg='black', font=('Segoe UI', 10, 'bold'),
                                    padx=20, pady=8, relief='flat', bd=0, cursor="hand2",
                                    state=tk.DISABLED)
        self.select_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self.cancel,
                               bg='#e74c3c', fg='black', font=('Segoe UI', 10),
                               padx=20, pady=8, relief='flat', bd=0, cursor="hand2")
        cancel_btn.pack(side=tk.RIGHT)
    
    def load_folder(self, prefix):
        """Load folder contents from S3 using boto3"""
        if not BOTO3_AVAILABLE:
            self.status_label.config(text="Error: boto3 not installed. Run: pip install boto3")
            return
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.status_label.config(text="Loading folder contents...")
        self.dialog.update()
        
        try:
            # Create S3 client with profile if specified
            session_kwargs = {}
            if self.profile and self.profile != "default":
                session_kwargs['profile_name'] = self.profile
            
            session = boto3.Session(**session_kwargs)
            s3_client = session.client('s3')
            
            # List objects
            list_kwargs = {
                'Bucket': self.bucket,
                'Prefix': prefix,
                'Delimiter': '/'
            }
            
            response = s3_client.list_objects_v2(**list_kwargs)
            
            folders = []
            files = []
            
            # Process folders
            for prefix_info in response.get('CommonPrefixes', []):
                folder_path = prefix_info['Prefix']
                folder_name = folder_path.rstrip('/').split('/')[-1]
                if folder_name:
                    folders.append(folder_name)
            
            # Process files
            for obj in response.get('Contents', []):
                key = obj['Key']
                
                if key == prefix or key.endswith('/'):
                    continue
                
                filename = key.split('/')[-1]
                if not filename:
                    continue
                    
                size = obj['Size']
                files.append((filename, size))
            
            # Add folders first
            for folder in sorted(folders):
                self.tree.insert('', 'end', text=f"📁 {folder}", 
                               values=('Folder', ''), tags=('folder',))
            
            # Add files
            for filename, size in sorted(files):
                # Format size
                try:
                    size_int = int(size)
                    if size_int < 1024:
                        size_str = f"{size_int} B"
                    elif size_int < 1024 * 1024:
                        size_str = f"{size_int / 1024:.1f} KB"
                    else:
                        size_str = f"{size_int / (1024 * 1024):.1f} MB"
                except:
                    size_str = str(size)
                
                self.tree.insert('', 'end', text=f"📄 {filename}", 
                               values=('File', size_str), tags=('file',))
            
            # Update status
            folder_count = len(folders)
            file_count = len(files)
            status_text = f"{folder_count} folder(s), {file_count} file(s)"
            self.status_label.config(text=status_text)
            
            # Update current prefix
            self.current_prefix = prefix
            path_display = f"s3://{self.bucket}/{prefix}" if prefix else f"s3://{self.bucket}/"
            self.path_label.config(text=path_display)
            
            # Enable/disable back button
            if prefix:
                self.back_btn.config(state=tk.NORMAL)
            else:
                self.back_btn.config(state=tk.DISABLED)
                
        except NoCredentialsError:
            self.status_label.config(text="Error: AWS credentials not configured")
        except ProfileNotFound:
            self.status_label.config(text=f"Error: Profile '{self.profile}' not found")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            self.status_label.config(text=f"Error: {error_code}")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
    
    def on_double_click(self, event):
        """Handle double-click on item"""
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
        elif 'file' in tags:
            # Select file
            self.select_file()
    
    def on_select(self, event):
        """Handle selection change"""
        selection = self.tree.selection()
        if not selection:
            self.select_btn.config(state=tk.DISABLED)
            return
        
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        
        # Only enable select button for files
        if 'file' in tags:
            self.select_btn.config(state=tk.NORMAL)
        else:
            self.select_btn.config(state=tk.DISABLED)
    
    def go_up(self):
        """Go up one directory level"""
        if not self.current_prefix:
            return
        
        # Remove trailing slash
        prefix = self.current_prefix.rstrip('/')
        
        # Go up one level
        if '/' in prefix:
            new_prefix = prefix.rsplit('/', 1)[0] + '/'
        else:
            new_prefix = ""
        
        self.load_folder(new_prefix)
    
    def select_file(self):
        """Select the current file and close dialog"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        
        if 'file' not in tags:
            messagebox.showwarning("Invalid Selection", "Please select a file, not a folder.")
            return
        
        # Get filename
        item_text = self.tree.item(item, 'text')
        filename = item_text.replace('📄 ', '')
        
        # Build full S3 key
        self.result = f"{self.current_prefix}{filename}" if self.current_prefix else filename
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel and close dialog"""
        self.result = None
        self.dialog.destroy()

class FileParserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bill Hunter")
        
        # Detect if running inside HelloToolbelt and get shared credentials
        self.in_hellotoolbelt = self._detect_hellotoolbelt_mode()
        
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        if not self.is_in_toolbelt:
            self.root.configure(bg='#ffffff')
        
        self.setup_adaptive_styling()
        
        self.root.minsize(1000, 800)

        self.client = tk.StringVar()
        self.billable_status = tk.StringVar(value="Should be billable")  # ADD THIS LINE
        self.postgres_data = []
        
        # Credential initialization - Conditional based on mode
        if self.in_hellotoolbelt:
            # Running inside HelloToolbelt - use shared credentials
            print("Bill Hunter: Running in HelloToolbelt mode - using shared credentials")
            
            # Point to HelloToolbelt's shared credential variables
            self.db_host = self.hellotoolbelt_instance.db_host
            self.db_port = self.hellotoolbelt_instance.db_port
            self.db_name = self.hellotoolbelt_instance.db_name
            self.db_user = self.hellotoolbelt_instance.db_user
            self.db_password = self.hellotoolbelt_instance.db_password
            
            # Use HelloToolbelt's keyring availability
            self.keyring_available = self.hellotoolbelt_instance.keyring_available
            
            # Check for boto3
            try:
                import boto3
                self.boto3_available = True
            except ImportError:
                self.boto3_available = False
            
            # No need to load config - already loaded by HelloToolbelt
            self.config_file = None  # Not used in HelloToolbelt mode
            
        else:
            # Running standalone - use local credentials
            print("Bill Hunter: Running in standalone mode - using local credentials")
            
            # Database configuration
            self.db_host = tk.StringVar(value="localhost")
            self.db_port = tk.StringVar(value="5432")
            self.db_name = tk.StringVar(value="")
            self.db_user = tk.StringVar(value="")
            self.db_password = tk.StringVar(value="")
            
            # Check for boto3 and keyring availability
            try:
                import boto3
                self.boto3_available = True
            except ImportError:
                self.boto3_available = False
            
            try:
                import keyring
                self.keyring_available = True
            except ImportError:
                self.keyring_available = False
            
            # Config file for database settings
            self.config_file = os.path.join(os.path.expanduser("~"), ".bill_hunter_config.json")
            self.load_db_config()

        self.data = []
        self.headers = []
        self.detected_delimiter = None
        self.first_name_col = tk.StringVar()
        self.last_name_col = tk.StringVar()
        self.termination_date_col = tk.StringVar()
        self.date_of_birth_col = tk.StringVar()
        self.postgres_headers = ['client', 'user_id', 'email', 'first_name', 'last_name', 'date_of_birth',
                         'total_bps', 'first_login_date', 'last_login_date', 'last_bp_date', 
                         'termed_in_cheif', 'termination_date']
        self.matched_results = []
        self.sort_reverse = {}
        self.query_cancelled = False
        self.db_connection = None
        self.db_cursor = None
        self.selected_s3_file = None
        self.polling_active = False  # Track if any polling/background operations are active
        
        # Check for boto3 and keyring availability (only if standalone)
        if not self.in_hellotoolbelt:
            try:
                import boto3
                self.boto3_available = True
            except ImportError:
                self.boto3_available = False
            
            try:
                import keyring
                self.keyring_available = True
            except ImportError:
                self.keyring_available = False
            
            # Config file for database settings
            self.config_file = os.path.join(os.path.expanduser("~"), ".bill_hunter_config.json")
            self.load_db_config()
        
        self._init_date_formats() 

        self.clients_list = [
            "adminstation", "advance_auto_parts", "advance_local", "agco", "akf_group",
            "alamo_cement_and_concrete", "alliancebernstein", "american_showa", "american_trim",
            "amgen", "amneal_pharmaceuticals_llc", "amtrust_financial_services", "apple",
            "applied_medical", "asurion", "avery_dennison", "bank_of_the_west", "banner_health",
            "barclays", "barnes_and_noble_education", "baylor_college_of_medicine",
            "beacon_mobility_corp", "beigene", "bendix_commercial_vehicle_systems_llc",
            "blanchard_valley_health_system", "bloomberg_industry_group",
            "bluecross_blueshield_of_south_carolina_ma",
            "bluecross_blueshield_of_south_carolina_ma_phase_3",
            "bluecross_blueshield_of_south_carolina_ma_phase_4", "brevard_public_schools",
            "bridgestone_americas_inc", "bswift",
            "buckeye_ohio_risk_management_association_inc", "builders_firstsource",
            "bureau_veritas_north_america_inc", "canon_usa", "carlisle_llc", "castlight",
            "celanese_corporation", "chemtrade", "cherokee_nation_businesses_llc",
            "cigna_medicare_advantage", "circle_k", "city_fort_worth", "city_of_atlanta",
            "city_of_minneapolis", "city_of_san_angelo", "cleveland_bakers_and_teamsters",
            "cognizant", "community_health_systems", "conduent_business_services_llc",
            "connecticare", "county_of_el_paso", "cvs_health", "daifuku", "delta_air_lines",
            "department_of_defense_naf", "devon_energy", "dicks_sporting_goods",
            "docusign_inc", "douglas_county_government", "duracell",
            "eastern_atlantic_states_carpenters_health_fund",
            "eighth_district_electrical_benefit_fund",
            "electrical_workers_benefit_trust_local_481",
            "electrical_workers_insurance_fund_local_58", "electrical_workers_trust_fund",
            "emblemhealth_ma_services_company", "emblemhealth_phase_2", "emblemhealth_phase_3",
            "employee_retirement_system_of_texas_ers", "endress_and_hauser",
            "extended_stay_america", "extreme_networks",
            "factory_mutual_insurance_company_aka_fm_global", "fike", "firstgroup_america",
            "firstservice_residential_inc", "flatiron_construction_corporation",
            "florida_sheriffs_employee_benefits_trust",
            "forsyth_county_board_of_commissioners", "fort_zumwalt_school_district",
            "fox_corporation", "fox_valley_laborers_health_and_welfare_fund",
            "fresh_market_inc", "gc_services_limited", "general_dynamics",
            "general_electric_appliances_gea", "general_mills", "geon_performance_solutions_llc",
            "grant_thornton_advisors_llc", "gray_media", "guggenheim_partners", "gxo_logistics",
            "harman_international_industries_incorporated", "hello_heart", "herc_rentals",
            "here_technologies", "hga", "hiland_dairy_foods", "home_depot",
            "huntington_ingalls_incorporated", "huntsman_international_llc",
            "iaff_local_22_philadelphia_health_plan", "incyte_corporation",
            "indiana_department_of_natural_resources", "indiana_laborers_welfare_fund",
            "indiana_pipe_trades_health_and_welfare_fund", "indiana_state_council_of_roofers",
            "indicor", "insulators_and_allied_workers_local_1", "intrepid_usa", "iron_mountain",
            "iron_workers_st_louis_district_council", "jbs_usa", "jcc", "jiffinity",
            "johnson_and_johnson", "joint_industry_board_of_the_electrical_industry", "kbr",
            "kenan_advantage_group", "kentucky_laborers_health_and_welfare_fund",
            "kings_daughters_medical_center", "knauf_insulation", "larimer_county",
            "lawrence_livermore_national_security_llc", "lenovo", "liberty_oilfield_services",
            "lifetouch", "loandepot", "local_813_insurance_fund",
            "local_945_of_ib_of_t_welfare_fund", "lord_corp",
            "lynden_incorporated_and_participating_employers", "macys", "magna_international",
            "maine_bankers_association", "manitowoc_company", "manna_development_group",
            "mannhummel_filtration_technology_us_llc", "maricopa_county_az", "marsh_mclennan",
            "marylandnational_capital_park_and_planning", "maximus", "mccain_foods",
            "mcdonalds", "mcgrath_rentcorp", "md_wise", "medtronic", "metrohealth", "mhbp",
            "mohawk_industries", "mohegan_tribal_gaming_authority",
            "montana_association_of_counties_health_trust", "montgomery_college",
            "mrieux_nutrisciences", "mutual_of_america", "nalc_health_benefit_plan",
            "national_oilwell_varco_lp", "necaibew_welfare_trust_fund", "nixon_peabody",
            "north_carolina_bankers_association", "north_carolina_state_health_plan",
            "northern_michigan_university", "northwestern_mutual", "nustar", "oei_inc",
            "ohio_conference_of_plasterers_and_cement_masons",
            "ohio_conference_of_teamsters_health_fund", "outrigger_hotels",
            "ovation_corporate_travel", "panera", "paychex", "peba_south_carolina",
            "penn_entertainment", "penske", "perdue", "performance_services", "petsmart",
            "philips", "phillips_66", "phs", "piedmont", "pioneer",
            "plumbers_and_steamfitters_local_440", "polar_semiconductor",
            "prairie_farms_dairy_inc", "pratt_industries", "precisely",
            "precision_castparts_corp", "presbyterian_health_plan", "pvh_corp", "qiagen",
            "queen_annes_county_md", "raymour_and_flanigan", "rct_2025", "redners_market",
            "regeneron_pharmaceuticals", "repsol_services_company", "royal_caribbean_cruises",
            "rpm_international", "sacred_heart_university",
            "salt_river_pima_maricopaindian_community",
            "san_diego_electrical_health_and_welfare_trust", "sandia_national_laboratories",
            "sartorius_north_america", "schwan_food_company", "seaworld_parks_and_entertainment",
            "sheet_metal_workers_local_25", "sheet_metal_workers_local_27", "sherwinwilliams",
            "solera", "solventum", "southwestern_ohio_epc", "stallion_oilfield_services_llc",
            "state_of_florida_div_of_state_group_insurance", "state_of_georgia",
            "tailored_shared_services_llc", "teachers_health_trust", "teamsters_local_641",
            "teamsters_local_union_no_727", "tech_mahindra", "technipfmc", "tetra_tech",
            "texas_a_and_m_university_systems", "the_3m", "the_mosaic_company",
            "the_navigators", "the_vancouver_clinic", "thryv_holdings_inc", "ti_automotive",
            "tkc_holdings", "tpc_group", "transwestern_commercial_services",
            "travis_county_central_health", "trilogy_health_services", "ttec1", "ttx_company",
            "ubs_ag_stamford_branch_ubs", "unilever", "union_construction_workers_health_plan",
            "united_federal_credit_union", "valmont_industries", "vertex_aerospace",
            "virgin_pulse", "virginia_bankers_association", "virginia_hospital_center",
            "vna_health_group", "voestalpine_railway_systems_nortrak_llc", "wakefern_food_corp",
            "westerville_city_school_district", "wildlife_conservation_society", "wilsonart",
            "wmc_health", "wolters_kluwer", "wpp_group_usa_inc", "wright_state_university",
            "wycliffe_bible_translators", "ykk_corporation_of_america", "younger_brothers",
            "zimmer_biomet"
        ]
        
        self.build_gui()
        
        if not self.is_in_toolbelt:
            self._center_window()

    def setup_adaptive_styling(self):
        if self.is_in_toolbelt:
            try:
                parent_bg = self.root.cget('bg')
                parent_fg = self.root.cget('fg') 
            except:
                parent_bg = '#ffffff'
                parent_fg = '#2c3e50'
        else:
            temp_label = tk.Label(self.root)
            parent_bg = temp_label.cget('bg')
            parent_fg = temp_label.cget('fg')
            temp_label.destroy()
        
        try:
            if parent_bg.startswith('#'):
                r, g, b = int(parent_bg[1:3], 16), int(parent_bg[3:5], 16), int(parent_bg[5:7], 16)
            else:
                rgb = self.root.winfo_rgb(parent_bg)
                r, g, b = [x // 256 for x in rgb]
            
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            self.is_dark_mode = brightness < 128
        except:
            self.is_dark_mode = False
        
        self.title_font = ("Segoe UI", 14, "bold")
        self.subtitle_font = ("Segoe UI", 11, "bold")
        self.label_font = ("Segoe UI", 10)
        self.text_font = ("Segoe UI", 10)
        
        if self.is_dark_mode:
            self.bg_color = parent_bg
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.primary_color = "#0a9640"
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#ffffff'
            self.text_secondary = '#cccccc'
            self.button_text_color = '#000000'
        else:
            self.bg_color = parent_bg
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.primary_color = '#0a9640'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.text_secondary = '#34495e'
            self.button_text_color = '#000000'
        
        # Configure ttk styles
        style = ttk.Style()
        
        # Get colors for styling
        colors = {
            'bg': self.bg_color,
            'fg': self.text_color,
            'secondary_bg': self.frame_bg,
            'primary': self.primary_color
        }
        
        # Configure frame styles
        style.configure('Tool.TFrame',
                       background=colors['bg'],
                       relief='flat',
                       borderwidth=0)

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
        self.build_gui()

    def _center_window(self):
        window_width = 1000
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    def _detect_hellotoolbelt_mode(self):
        """Detect if we're running inside HelloToolbelt and get shared credentials"""
        try:
            print(f"Bill Hunter: Detecting HelloToolbelt mode...")
            print(f"Bill Hunter: self.root type = {type(self.root)}")
            print(f"Bill Hunter: self.root has db_host = {hasattr(self.root, 'db_host')}")
            print(f"Bill Hunter: self.root has db_password = {hasattr(self.root, 'db_password')}")
            print(f"Bill Hunter: self.root has aws_access_key = {hasattr(self.root, 'aws_access_key')}")
            
            # Walk up the widget hierarchy looking for HelloToolbelt instance
            current = self.root
            depth = 0
            while current:
                print(f"Bill Hunter: Checking depth {depth}, type = {type(current)}")
                
                # Check if this parent has the shared credential attributes
                if (hasattr(current, 'db_host') and 
                    hasattr(current, 'db_password') and
                    hasattr(current, 'aws_access_key') and
                    isinstance(getattr(current, 'db_host', None), tk.Variable)):
                    # Found HelloToolbelt! Store reference
                    print(f"Bill Hunter: Found HelloToolbelt at depth {depth}!")
                    self.hellotoolbelt_instance = current
                    return True
                
                try:
                    current = current.master
                    depth += 1
                except:
                    break
            
            print(f"Bill Hunter: HelloToolbelt not found after checking {depth} levels")
            return False
        except Exception as e:
            print(f"Error detecting HelloToolbelt mode: {e}")
            import traceback
            traceback.print_exc()
            return False

    def build_gui(self):
        # Create BillHunter content directly in root (no notebook wrapper)
        self.billhunter_tab = ttk.Frame(self.root, style='Tool.TFrame')
        self.billhunter_tab.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Build the interface
        self._build_billhunter_tab()
    
    def _build_billhunter_tab(self):
        """Build the main BillHunter functionality tab"""
        # Main container with padding (non-scrollable)
        main_container = ttk.Frame(self.billhunter_tab, style='Tool.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Header (stays fixed at top)
        header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_content = tk.Frame(header_frame, bg=self.primary_color)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        header_icon = tk.Label(header_content, text="🎯", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_label = tk.Label(header_content, text="Bill Hunter", 
                            font=('Segoe UI', 16, 'bold'), bg=self.primary_color, fg='white')
        header_label.pack(side=tk.LEFT, anchor='w')
        
        # Create scrollable container for content (scrolls independently)
        self.scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color, bg=self.bg_color)
        self.scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        content_container = self.scrollable_container.scrollable_frame
        content_container.configure(bg=self.bg_color)
        
        # NEW: S3 File Browser Section (FIRST - at the top)
        self._build_s3_browser_section(content_container)
        
        # Configuration Section (Find Users That, Client, Columns)
        self._build_configuration_section(content_container)
        
        # Actions Section
        self._build_actions_section(content_container)
        
        # Results Section
        self._build_results_section(content_container)
        
        def update_scroll_after_build():
            try:
                if hasattr(self, 'scrollable_container'):
                    self.scrollable_container.force_scroll_update()
            except Exception:
                pass
        
        self.root.after(100, update_scroll_after_build)
        self.root.after(500, update_scroll_after_build)
    
    def _build_s3_browser_section(self, parent):
        """Build the S3 file browser section"""
        s3_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        s3_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Track if S3 section is expanded
        self.s3_section_expanded = tk.BooleanVar(value=False)
        self.s3_loaded = False  # Track if data has been loaded
        
        # Collapsible header
        s3_header = tk.Frame(s3_frame, bg=self.header_bg, cursor="hand2")
        s3_header.pack(fill=tk.X)
        
        s3_header_content = tk.Frame(s3_header, bg=self.header_bg)
        s3_header_content.pack(fill=tk.X, pady=15, padx=20)
        
        # Expand/collapse icon
        self.s3_expand_icon = tk.Label(s3_header_content, text="▶", 
                                       font=('Segoe UI', 12), bg=self.header_bg, fg=self.text_color)
        self.s3_expand_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        s3_label = tk.Label(s3_header_content, text="📁 File Source (S3 or Local)", 
                           font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        s3_label.pack(side=tk.LEFT, anchor='w')
        
        # Make header clickable
        s3_header.bind('<Button-1>', lambda e: self.toggle_s3_section())
        s3_header_content.bind('<Button-1>', lambda e: self.toggle_s3_section())
        self.s3_expand_icon.bind('<Button-1>', lambda e: self.toggle_s3_section())
        s3_label.bind('<Button-1>', lambda e: self.toggle_s3_section())
        
        # ALWAYS VISIBLE: Upload button frame (outside collapsible content)
        always_visible_frame = tk.Frame(s3_frame, bg=self.frame_bg)
        always_visible_frame.pack(fill=tk.X, padx=15, pady=(10, 15))
        
        # Upload Local File button (ALWAYS VISIBLE)
        upload_btn = tk.Button(always_visible_frame, text="📁 Upload Local File", 
                            command=self.upload_file,
                            bg=self.success_color, fg='black',
                            font=('Segoe UI', 10, 'bold'), padx=20, pady=8, 
                            relief='flat', bd=0, cursor="hand2")
        upload_btn.pack(side=tk.LEFT)
        self._add_button_hover(upload_btn, self.success_color, '#229954', 
                            normal_fg='black', hover_fg='black')
        
        # Info label (ALWAYS VISIBLE)
        self.s3_info_label = tk.Label(always_visible_frame, text="Upload a local file or browse S3 below", 
                                    font=('Segoe UI', 9), bg=self.frame_bg, fg=self.text_secondary)
        self.s3_info_label.pack(side=tk.LEFT, padx=(15, 0))
        
        # Content frame (collapsible - contains S3 browser)
        self.s3_content_frame = tk.Frame(s3_frame, bg=self.frame_bg)
        
        # Create the S3 browser widget
        self.s3_browser = S3FileBrowserWidget(
            self.s3_content_frame,
            bucket="s3.hello.do.integration",
            initial_prefix="clients/",
            profile="default",
            on_file_select=self.on_s3_file_selected,
            bg_color=self.bg_color,
            auto_load=False  # Don't load on init
        )
        self.s3_browser.pack(fill=tk.BOTH, expand=True)
        
        # S3 Action button frame (inside collapsible content)
        s3_button_frame = tk.Frame(self.s3_content_frame, bg=self.frame_bg)
        s3_button_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Load Selected S3 File button (only visible when expanded)
        load_btn = tk.Button(s3_button_frame, text="📥 Load Selected S3 File", 
                            command=self.load_selected_s3_file,
                            bg=self.primary_color, fg='black',
                            font=('Segoe UI', 10, 'bold'), padx=20, pady=8, 
                            relief='flat', bd=0, cursor="hand2")
        load_btn.pack(side=tk.LEFT)
        self._add_button_hover(load_btn, self.primary_color, '#2980b9', 
                            normal_fg='black', hover_fg='black')
        
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
            
            # Pause any background polling/operations when collapsed
            self.polling_active = False
            
            # If there's a database connection, you could optionally close it here
            # to save resources (uncomment if needed):
            # if self.db_connection:
            #     try:
            #         if self.db_cursor:
            #             self.db_cursor.close()
            #         self.db_connection.close()
            #         print("Database connection closed while S3 section minimized")
            #     except Exception as e:
            #         print(f"Error closing connection: {e}")
            #     self.db_connection = None
            #     self.db_cursor = None
        else:
            # Expand
            self.s3_content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
            self.s3_expand_icon.config(text="▼")
            self.s3_section_expanded.set(True)
            
            # Resume background operations when expanded
            self.polling_active = True
            
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
        
        # Center
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - 250
        y = (progress_window.winfo_screenheight() // 2) - 90
        progress_window.geometry(f"500x180+{x}+{y}")
        
        status_label = tk.Label(progress_window, text="Downloading from S3...", 
                            font=('Segoe UI', 11))
        status_label.pack(pady=20)
        
        detail_label = tk.Label(progress_window, text=f"s3://{bucket}/{s3_key}", 
                            font=('Segoe UI', 9), fg='gray')
        detail_label.pack(pady=(0, 10))
        
        progress = ttk.Progressbar(progress_window, mode='indeterminate', length=400)
        progress.pack(pady=10)
        progress.start(10)
        
        progress_window.update()
        
        def do_load():
            """Perform load in background thread"""
            try:
                import tempfile
                
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
                    # Process the file
                    self.detected_delimiter = self.detect_delimiter(local_path)
                    
                    with open(local_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f, delimiter=self.detected_delimiter)
                        rows = list(reader)
                    
                    if not rows:
                        messagebox.showwarning("Empty File", "The downloaded file is empty!")
                        return
                    
                    self.headers = rows[0]
                    self.data = rows[1:]
                    
                    # Log S3 file access to audit trail
                    if hasattr(self.root, 'log_file_access'):
                        self.root.log_file_access(f"s3://{bucket}/{s3_key}", "LOADED_FROM_S3")
                    
                    # Update column options
                    column_options = [f"{idx}: {header}" for idx, header in enumerate(self.headers)]
                    
                    self.first_name_combo['values'] = column_options
                    self.last_name_combo['values'] = column_options
                    self.termination_date_combo['values'] = column_options
                    self.date_of_birth_combo['values'] = column_options
                    
                    # Auto-detect columns
                    detected_first, detected_last, detected_term, detected_dob = self.auto_detect_name_columns()
                    
                    if detected_first:
                        self.first_name_col.set(detected_first)
                    elif self.headers:
                        self.first_name_col.set(column_options[0])
                    
                    if detected_last:
                        self.last_name_col.set(detected_last)
                    elif len(self.headers) > 1:
                        self.last_name_col.set(column_options[1])
                    
                    if detected_term:
                        self.termination_date_col.set(detected_term)
                    
                    if detected_dob:
                        self.date_of_birth_col.set(detected_dob)
                    
                    # Update info label
                    delimiter_name = {'|': 'Pipe (|)', ',': 'Comma (,)', '\t': 'Tab (\\t)'}
                    self.s3_info_label.config(
                        text=f"✓ Loaded: {filename} | Rows: {len(self.data)} | Columns: {len(self.headers)}",
                        fg=self.success_color
                    )
                    
                    # Display data
                    self.display_data()
                    
                    messagebox.showinfo("Success", 
                                    f"File loaded successfully!\n\n"
                                    f"File: {filename}\n"
                                    f"Rows: {len(self.data)}\n"
                                    f"Columns: {len(self.headers)}")
                
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
        import threading
        load_thread = threading.Thread(target=do_load, daemon=True)
        load_thread.start()


    def _build_file_upload_section(self, parent):
        upload_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        upload_frame.pack(fill=tk.X, pady=(0, 15))
        
        upload_header = tk.Frame(upload_frame, bg=self.header_bg)
        upload_header.pack(fill=tk.X)
        
        upload_label = tk.Label(upload_header, text="File Source", font=self.subtitle_font, 
                              bg=self.header_bg, fg=self.text_color)
        upload_label.pack(pady=15)
        
        upload_content = tk.Frame(upload_frame, bg=self.frame_bg)
        upload_content.pack(fill=tk.X, padx=20, pady=20)
        

        # AWS Credentials section
        cred_frame = tk.LabelFrame(upload_content, text="AWS Credentials (for S3 Access)", 
                                  font=('Segoe UI', 9, 'bold'), bg=self.frame_bg, 
                                  fg=self.text_color, padx=10, pady=10)
        cred_frame.pack(fill=tk.X, pady=(10, 5))
        
        # Access Key ID
        access_key_frame = tk.Frame(cred_frame, bg=self.frame_bg)
        access_key_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(access_key_frame, text="Access Key ID:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color, width=15, anchor='w').pack(side=tk.LEFT)
        self.aws_access_key_entry = tk.Entry(access_key_frame, font=self.text_font, width=35, show="*")
        self.aws_access_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Secret Access Key
        secret_key_frame = tk.Frame(cred_frame, bg=self.frame_bg)
        secret_key_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(secret_key_frame, text="Secret Access Key:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color, width=15, anchor='w').pack(side=tk.LEFT)
        self.aws_secret_key_entry = tk.Entry(secret_key_frame, font=self.text_font, width=35, show="*")
        self.aws_secret_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Region
        region_frame = tk.Frame(cred_frame, bg=self.frame_bg)
        region_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(region_frame, text="Region:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color, width=15, anchor='w').pack(side=tk.LEFT)
        self.aws_region_entry = tk.Entry(region_frame, font=self.text_font, width=35)
        self.aws_region_entry.insert(0, "us-east-1")
        self.aws_region_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Buttons frame
        cred_buttons_frame = tk.Frame(cred_frame, bg=self.frame_bg)
        cred_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Save credentials button
        save_creds_btn = tk.Button(cred_buttons_frame, text="💾 Save Credentials", 
                                   command=self.save_aws_credentials,
                                   bg='#3498db', fg='black',
                                   font=('Segoe UI', 9), padx=12, pady=5, relief='flat', bd=0, cursor="hand2")
        save_creds_btn.pack(side=tk.LEFT, padx=(0, 5))
        self._add_button_hover(save_creds_btn, '#3498db', '#2980b9', normal_fg='black', hover_fg='black')
        
        # Test connection button
        test_creds_btn = tk.Button(cred_buttons_frame, text="🔌 Test Connection", 
                                   command=self.test_aws_connection,
                                   bg='#27ae60', fg='black',
                                   font=('Segoe UI', 9), padx=12, pady=5, relief='flat', bd=0, cursor="hand2")
        test_creds_btn.pack(side=tk.LEFT, padx=(0, 5))
        self._add_button_hover(test_creds_btn, '#27ae60', '#229954', normal_fg='black', hover_fg='black')
        
        # Clear credentials button
        clear_creds_btn = tk.Button(cred_buttons_frame, text="🗑️ Clear", 
                                    command=self.clear_aws_credentials,
                                    bg='#e74c3c', fg='black',
                                    font=('Segoe UI', 9), padx=12, pady=5, relief='flat', bd=0, cursor="hand2")
        clear_creds_btn.pack(side=tk.LEFT)
        self._add_button_hover(clear_creds_btn, '#e74c3c', '#c0392b', normal_fg='black', hover_fg='black')
        
        # Status label
        self.cred_status_label = tk.Label(cred_frame, text="💡 Credentials stored securely in system keychain", 
                                         font=('Segoe UI', 8), bg=self.frame_bg, fg=self.text_secondary,
                                         wraplength=500, justify=tk.LEFT)
        self.cred_status_label.pack(fill=tk.X, pady=(10, 0))
        

        # File status label
        self.info_label = tk.Label(upload_content, text="No file loaded", 
                                   font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        self.info_label.pack(pady=(10, 0))

    def _build_database_section(self, parent, always_expanded=False):
        db_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        db_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Create a variable to track if section is expanded
        if not hasattr(self, 'db_section_expanded'):
            self.db_section_expanded = tk.BooleanVar(value=always_expanded)
        
        if not always_expanded:
            # Collapsible header
            db_header = tk.Frame(db_frame, bg=self.header_bg, cursor="hand2")
            db_header.pack(fill=tk.X)
            
            # Make header clickable
            db_header_content = tk.Frame(db_header, bg=self.header_bg)
            db_header_content.pack(fill=tk.X, pady=15, padx=20)
            
            self.db_expand_icon = tk.Label(db_header_content, text="▶", 
                                           font=('Segoe UI', 12), bg=self.header_bg, fg=self.text_color)
            self.db_expand_icon.pack(side=tk.LEFT, padx=(0, 10))
            
            db_label = tk.Label(db_header_content, text="Database Configuration (Optional - Auto-run Query)", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            db_label.pack(side=tk.LEFT, anchor='w')
        else:
            # Fixed header for Configuration tab
            db_header = tk.Frame(db_frame, bg=self.header_bg)
            db_header.pack(fill=tk.X)
            
            db_header_content = tk.Frame(db_header, bg=self.header_bg)
            db_header_content.pack(fill=tk.X, pady=15, padx=20)
            
            db_label = tk.Label(db_header_content, text="PostgreSQL Database Settings", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            db_label.pack(side=tk.LEFT, anchor='w')
        
        # Content frame that will be shown/hidden (or always shown in config tab)
        self.db_content = tk.Frame(db_frame, bg=self.frame_bg)
        
        if not PSYCOPG2_AVAILABLE:
            warning_label = tk.Label(self.db_content, 
                                    text="⚠️ psycopg2 not installed. Install with: pip install psycopg2-binary",
                                    font=self.label_font, bg=self.frame_bg, fg='#e74c3c', wraplength=600)
            warning_label.pack(pady=10, padx=20)
        
        info_label = tk.Label(self.db_content, 
                             text="Enter the database name (e.g., 'adminstationdb'). Selected clients are used as schemas.",
                             font=self.label_font, bg=self.frame_bg, fg=self.text_secondary, wraplength=600)
        info_label.pack(pady=(10, 10), padx=20)
        
        # Grid layout for database fields
        db_grid = tk.Frame(self.db_content, bg=self.frame_bg)
        db_grid.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Row 0: Host and Port
        tk.Label(db_grid, text="Host:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).grid(row=0, column=0, sticky="w", pady=(0, 5))
        host_entry = tk.Entry(db_grid, textvariable=self.db_host, font=self.text_font, width=40)
        host_entry.grid(row=0, column=1, sticky="ew", padx=(5, 10), pady=(0, 5))
        
        tk.Label(db_grid, text="Port:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).grid(row=0, column=2, sticky="w", pady=(0, 5))
        port_entry = tk.Entry(db_grid, textvariable=self.db_port, font=self.text_font, width=10)
        port_entry.grid(row=0, column=3, sticky="ew", padx=(5, 0), pady=(0, 5))
        
        # Row 1: Database Name
        tk.Label(db_grid, text="Database:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).grid(row=1, column=0, sticky="w", pady=(0, 5))
        db_entry = tk.Entry(db_grid, textvariable=self.db_name, font=self.text_font, width=40)
        db_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(5, 0), pady=(0, 5))
        
        # Row 2: Username and Password
        tk.Label(db_grid, text="Username:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).grid(row=2, column=0, sticky="w", pady=(0, 5))
        user_entry = tk.Entry(db_grid, textvariable=self.db_user, font=self.text_font, width=40)
        user_entry.grid(row=2, column=1, sticky="ew", padx=(5, 10), pady=(0, 5))
        
        tk.Label(db_grid, text="Password:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).grid(row=2, column=2, sticky="w", pady=(0, 5))
        password_entry = tk.Entry(db_grid, textvariable=self.db_password, font=self.text_font, 
                                 width=25, show="*")
        password_entry.grid(row=2, column=3, sticky="ew", padx=(5, 0), pady=(0, 5))
        
        db_grid.columnconfigure(1, weight=2)
        db_grid.columnconfigure(3, weight=1)
        
        # Button frame for Save and Test buttons
        button_frame = tk.Frame(self.db_content, bg=self.frame_bg)
        button_frame.pack(pady=(5, 15))
        
        # Save button
        save_btn = tk.Button(button_frame, text="💾 Save Configuration", 
                            command=self.save_db_config, bg=self.success_color, fg=self.button_text_color,
                            font=('Segoe UI', 9), padx=15, pady=5, relief='flat', bd=0, cursor="hand2")
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._add_button_hover(save_btn, self.success_color, '#229954')
        
        # Test Connection button
        test_btn = tk.Button(button_frame, text="🔌 Test Connection", 
                            command=self.test_db_connection, bg='#2196F3', fg=self.button_text_color,
                            font=('Segoe UI', 9), padx=15, pady=5, relief='flat', bd=0, cursor="hand2")
        test_btn.pack(side=tk.LEFT)
        self._add_button_hover(test_btn, '#2196F3', '#1976D2')
        
        # Bind click events to header for expand/collapse (only if not always_expanded)
        if not always_expanded:
            db_header.bind("<Button-1>", lambda e: self.toggle_db_section())
            db_header_content.bind("<Button-1>", lambda e: self.toggle_db_section())
            self.db_expand_icon.bind("<Button-1>", lambda e: self.toggle_db_section())
            db_label.bind("<Button-1>", lambda e: self.toggle_db_section())
        else:
            # Always show content in Configuration tab
            self.db_content.pack(fill=tk.X, padx=20, pady=20)
            self.db_section_expanded.set(True)
    
    def toggle_db_section(self):
        """Toggle the database configuration section"""
        if self.db_section_expanded.get():
            # Collapse
            self.db_content.pack_forget()
            self.db_expand_icon.config(text="▶")
            self.db_section_expanded.set(False)
        else:
            # Expand
            self.db_content.pack(fill=tk.X, padx=20, pady=20)
            self.db_expand_icon.config(text="▼")
            self.db_section_expanded.set(True)

    def _build_configuration_section(self, parent):
        config_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        config_header = tk.Frame(config_frame, bg=self.header_bg)
        config_header.pack(fill=tk.X)
        
        config_label = tk.Label(config_header, text="Configuration", font=self.subtitle_font,
                               bg=self.header_bg, fg=self.text_color)
        config_label.pack(pady=15)
        
        config_content = tk.Frame(config_frame, bg=self.frame_bg)
        config_content.pack(fill=tk.X, padx=20, pady=20)
        
        # Billable Status dropdown (first)
        billable_frame = tk.Frame(config_content, bg=self.frame_bg)
        billable_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(billable_frame, text="Find Users That:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).pack(anchor=tk.W, pady=(0, 5))
        self.billable_combo = ttk.Combobox(billable_frame, textvariable=self.billable_status,
                                        values=["Should be billable", "Should not be billable"], 
                                        state="readonly", width=40, font=self.text_font)
        self.billable_combo.pack(fill=tk.X)

        # Client selection
        client_frame = tk.Frame(config_content, bg=self.frame_bg)
        client_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(client_frame, text="Client:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).pack(anchor=tk.W, pady=(0, 5))
        self.client_combo = ttk.Combobox(client_frame, textvariable=self.client,
                                        values=self.clients_list, width=40, font=self.text_font)
        self.client_combo.pack(fill=tk.X)
        
        # Add search functionality to client combobox
        self.client_combo.bind('<KeyRelease>', self._on_client_keyrelease)
        
        # Column dropdowns in grid
        dropdowns_frame = tk.Frame(config_content, bg=self.frame_bg)
        dropdowns_frame.pack(fill=tk.X, pady=(0, 15))
        
        # First Name
        first_name_frame = tk.Frame(dropdowns_frame, bg=self.frame_bg)
        first_name_frame.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")
        
        tk.Label(first_name_frame, text="First Name Column:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).pack(anchor=tk.W, pady=(0, 5))
        self.first_name_combo = ttk.Combobox(first_name_frame, textvariable=self.first_name_col,
                                            state="readonly", width=25, font=self.text_font)
        self.first_name_combo.pack(fill=tk.X)
        
        # Last Name
        last_name_frame = tk.Frame(dropdowns_frame, bg=self.frame_bg)
        last_name_frame.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        tk.Label(last_name_frame, text="Last Name Column:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).pack(anchor=tk.W, pady=(0, 5))
        self.last_name_combo = ttk.Combobox(last_name_frame, textvariable=self.last_name_col,
                                           state="readonly", width=25, font=self.text_font)
        self.last_name_combo.pack(fill=tk.X)
        
        # Termination Date
        term_date_frame = tk.Frame(dropdowns_frame, bg=self.frame_bg)
        term_date_frame.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="ew")
        
        tk.Label(term_date_frame, text="Termination Date Column:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).pack(anchor=tk.W, pady=(0, 5))
        self.termination_date_combo = ttk.Combobox(term_date_frame, textvariable=self.termination_date_col,
                                                   state="readonly", width=25, font=self.text_font)
        self.termination_date_combo.pack(fill=tk.X)
        
        # Date of Birth
        dob_frame = tk.Frame(dropdowns_frame, bg=self.frame_bg)
        dob_frame.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        tk.Label(dob_frame, text="Date of Birth Column:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).pack(anchor=tk.W, pady=(0, 5))
        self.date_of_birth_combo = ttk.Combobox(dob_frame, textvariable=self.date_of_birth_col,
                                               state="readonly", width=25, font=self.text_font)
        self.date_of_birth_combo.pack(fill=tk.X)
        
        dropdowns_frame.columnconfigure(0, weight=1)
        dropdowns_frame.columnconfigure(1, weight=1)
        
        apply_btn = tk.Button(config_content, text="Apply Selection", 
                            command=self.apply_selection, bg=self.primary_color, fg=self.button_text_color,
                            font=('Segoe UI', 10), padx=15, pady=6, relief='flat', bd=0, cursor="hand2")
        apply_btn.pack()
        
        self._add_button_hover(apply_btn, self.primary_color, '#2980b9')

    def _build_actions_section(self, parent):
        actions_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        actions_frame.pack(fill=tk.X, pady=(0, 15))
        
        actions_header = tk.Frame(actions_frame, bg=self.header_bg)
        actions_header.pack(fill=tk.X)
        
        actions_label = tk.Label(actions_header, text="Actions", font=self.subtitle_font,
                               bg=self.header_bg, fg=self.text_color)
        actions_label.pack(pady=15)
        
        actions_content = tk.Frame(actions_frame, bg=self.frame_bg)
        actions_content.pack(fill=tk.X, padx=20, pady=20)
        
        buttons_frame = tk.Frame(actions_content, bg=self.frame_bg)
        buttons_frame.pack()
        
        query_btn = tk.Button(buttons_frame, text="Generate Query", 
                            command=self.generate_query, bg=self.warning_color, fg='black',
                            font=('Segoe UI', 10), padx=15, pady=6, relief='flat', bd=0, cursor="hand2")
        query_btn.pack(side=tk.LEFT, padx=5)
        
        paste_btn = tk.Button(buttons_frame, text="Paste PG Results", 
                            command=self.paste_postgres_results, bg='#9C27B0', fg='black',
                            font=('Segoe UI', 10), padx=15, pady=6, relief='flat', bd=0, cursor="hand2")
        paste_btn.pack(side=tk.LEFT, padx=5)
        
        # Add a separator between Paste PG Results and Run Query
        separator = tk.Frame(buttons_frame, width=2, bg='#d0d0d0', relief='sunken', bd=1)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)
        
        # Create a container frame for run/stop buttons to maintain position
        run_stop_frame = tk.Frame(buttons_frame, bg=self.frame_bg)
        run_stop_frame.pack(side=tk.LEFT, padx=5)
        
        self.run_query_btn = tk.Button(run_stop_frame, text="Run Query in DB", 
                            command=self.run_query_in_db, bg=self.danger_color, fg='black',
                            font=('Segoe UI', 10), padx=15, pady=6, relief='flat', bd=0, cursor="hand2")
        self.run_query_btn.pack()
        
        # Stop button (initially hidden, in same container)
        self.stop_query_btn = tk.Button(run_stop_frame, text="⏹ Stop Query", 
                            command=self.stop_query, bg='#c0392b', fg='black',
                            font=('Segoe UI', 10), padx=15, pady=6, relief='flat', bd=0, cursor="hand2")
        # Don't pack it initially - it will be shown during query execution
        
        match_btn = tk.Button(buttons_frame, text="Match Results", 
                            command=self.match_results, bg='#16a085', fg='black',
                            font=('Segoe UI', 10), padx=15, pady=6, relief='flat', bd=0, cursor="hand2")
        match_btn.pack(side=tk.LEFT, padx=5)
        
        self._add_button_hover(query_btn, self.warning_color, '#e67e22', normal_fg='black', hover_fg='black')
        self._add_button_hover(paste_btn, '#9C27B0', '#7B1FA2', normal_fg='black', hover_fg='black')
        self._add_button_hover(self.run_query_btn, self.danger_color, '#c0392b', normal_fg='black', hover_fg='black')
        self._add_button_hover(self.stop_query_btn, '#c0392b', '#a93226', normal_fg='black', hover_fg='black')
        self._add_button_hover(match_btn, '#16a085', '#138d75', normal_fg='black', hover_fg='black')

    def _build_results_section(self, parent):
        results_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        results_header = tk.Frame(results_frame, bg=self.header_bg)
        results_header.pack(fill=tk.X)
        
        header_content = tk.Frame(results_header, bg=self.header_bg)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        results_label = tk.Label(header_content, text="Results", font=self.subtitle_font,
                            bg=self.header_bg, fg=self.text_color)
        results_label.pack(side=tk.LEFT)
        
        # Search frame
        search_frame = tk.Frame(header_content, bg=self.header_bg)
        search_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(search_frame, text="🔍", bg=self.header_bg, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_results())
        
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, 
                                     font=('Segoe UI', 9), width=25,
                                     relief='solid', bd=1)
        self.search_entry.pack(side=tk.LEFT)
        
        clear_search_btn = tk.Button(search_frame, text="✕", command=self.clear_search,
                                     bg=self.header_bg, font=('Segoe UI', 9),
                                     padx=5, pady=0, relief='flat', bd=0, cursor="hand2")
        clear_search_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        self.copy_results_btn = tk.Button(header_content, text="Copy All Results", 
                            command=self.copy_all_results, bg=self.success_color, fg=self.button_text_color,
                            font=('Segoe UI', 9), padx=12, pady=5, relief='flat', bd=0, cursor="hand2")
        self.copy_results_btn.pack(side=tk.RIGHT)
        self._add_button_hover(self.copy_results_btn, self.success_color, '#229954')
        
        results_content = tk.Frame(results_frame, bg=self.frame_bg)
        results_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        table_frame = tk.Frame(results_content, bg=self.bg_color, relief='solid', bd=1)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        self.tree = ttk.Treeview(table_frame, 
                                yscrollcommand=v_scrollbar.set,
                                xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Track sort state for each column
        self.sort_reverse = {}  # Dictionary to track sort direction for each column
        self.current_sort_column = None
        
        self.tree.bind('<Button-1>', self.on_tree_click)
        self.tree.bind('<Control-c>', self.copy_selected_rows)
        self.tree.bind('<Command-c>', self.copy_selected_rows)

    def _add_button_hover(self, button, normal_color, hover_color, normal_fg=None, hover_fg=None):
        try:
            if normal_fg is None:
                normal_fg = getattr(self, 'button_text_color', '#000000')
            if hover_fg is None:
                hover_fg = normal_fg
                
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
        except Exception:
            pass
    
    def _on_client_keyrelease(self, event):
        """Filter client dropdown based on typed text"""
        try:
            # Get the current text in the combobox
            typed_text = self.client_combo.get().lower()
            
            # If backspace or delete was pressed, or text is empty, show all clients
            if event.keysym in ('BackSpace', 'Delete') or not typed_text:
                self.client_combo['values'] = self.clients_list
                return
            
            # Filter clients that contain the typed text
            filtered_clients = [client for client in self.clients_list 
                              if typed_text in client.lower()]
            
            # Update the combobox values
            self.client_combo['values'] = filtered_clients
            
            # If there are matches, open the dropdown
            if filtered_clients:
                self.client_combo.event_generate('<Down>')
        except Exception:
            pass

    def on_tree_click(self, event):
        pass
    
    def copy_selected_rows(self, event=None):
        selected_items = self.tree.selection()
        
        if not selected_items:
            return
        
        columns = list(self.tree['columns'])
        copied_text = '\t'.join(columns) + '\n'
        
        for item in selected_items:
            values = self.tree.item(item)['values']
            row_text = '\t'.join(str(v) for v in values)
            copied_text += row_text + '\n'
        
        self.root.clipboard_clear()
        self.root.clipboard_append(copied_text.strip())
        
        return 'break'
    
    def detect_delimiter(self, file_path):
        delimiters = ['|', ',', '\t']
        
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            delimiter_counts = {d: first_line.count(d) for d in delimiters}
            max_delimiter = max(delimiter_counts, key=delimiter_counts.get)
            if delimiter_counts[max_delimiter] > 0:
                return max_delimiter
            
        return ','
    
    def auto_detect_name_columns(self):
        first_name_keywords = ['first', 'fname', 'firstname', 'first_name', 'given', 'givenname']
        last_name_keywords = ['last', 'lname', 'lastname', 'last_name', 'surname', 'family', 'familyname']
        termination_date_keywords = ['termination', 'term_date', 'termdate', 'termination_date', 'end_date', 'enddate']
        date_of_birth_keywords = ['dob', 'birth', 'birthdate', 'birth_date', 'date_of_birth', 'dateofbirth']
        
        first_name_col = None
        last_name_col = None
        termination_date_col = None
        date_of_birth_col = None
        
        for idx, header in enumerate(self.headers):
            header_lower = header.lower().strip()
            
            if not first_name_col and any(keyword in header_lower for keyword in first_name_keywords):
                first_name_col = f"{idx}: {header}"
            
            if not last_name_col and any(keyword in header_lower for keyword in last_name_keywords):
                last_name_col = f"{idx}: {header}"
            
            if not termination_date_col and any(keyword in header_lower for keyword in termination_date_keywords):
                termination_date_col = f"{idx}: {header}"
            
            if not date_of_birth_col and any(keyword in header_lower for keyword in date_of_birth_keywords):
                date_of_birth_col = f"{idx}: {header}"
        
        return first_name_col, last_name_col, termination_date_col, date_of_birth_col
    
    def upload_file(self):
        file_path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=(("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*"))
        )
        
        if not file_path:
            return
        
        try:
            self.detected_delimiter = self.detect_delimiter(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=self.detected_delimiter)
                rows = list(reader)
            
            if not rows:
                messagebox.showwarning("Empty File", "The file is empty!")
                return
            
            self.headers = rows[0]
            self.data = rows[1:]
            
            # Log file access to audit trail
            if hasattr(self.root, 'log_file_access'):
                self.root.log_file_access(file_path, "LOADED_FILE")
            
            column_options = [f"{idx}: {header}" for idx, header in enumerate(self.headers)]
            
            self.first_name_combo['values'] = column_options
            self.last_name_combo['values'] = column_options
            self.termination_date_combo['values'] = column_options
            self.date_of_birth_combo['values'] = column_options
            
            detected_first, detected_last, detected_term, detected_dob = self.auto_detect_name_columns()
            
            if detected_first:
                self.first_name_col.set(detected_first)
            elif self.headers:
                self.first_name_col.set(column_options[0])
            
            if detected_last:
                self.last_name_col.set(detected_last)
            elif len(self.headers) > 1:
                self.last_name_col.set(column_options[1])
            
            if detected_term:
                self.termination_date_col.set(detected_term)
            
            if detected_dob:
                self.date_of_birth_col.set(detected_dob)
            
            delimiter_name = {'|': 'Pipe (|)', ',': 'Comma (,)', '\t': 'Tab (\\t)'}
            self.s3_info_label.config(
                text=f"File: {os.path.basename(file_path)} | "
                     f"Delimiter: {delimiter_name.get(self.detected_delimiter, self.detected_delimiter)} | "
                     f"Rows: {len(self.data)} | Columns: {len(self.headers)}"
            )
            
            self.display_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file:\n{str(e)}")
    
    def download_from_s3(self):
        """Download a file from AWS S3 using boto3"""
        if not BOTO3_AVAILABLE:
            messagebox.showerror("boto3 Not Available", 
                               "boto3 library is required. Install with: pip install boto3")
            return
        
        bucket = self.s3_bucket_entry.get().strip()
        key = self.s3_key_entry.get().strip()
        profile = self.aws_profile_entry.get().strip()
        
        if not bucket:
            messagebox.showwarning("Missing Information", "Please enter an S3 bucket name.")
            return
        
        if not key:
            messagebox.showwarning("Missing Information", "Please enter an S3 key/path.")
            return
        
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading from S3")
        progress_window.geometry("500x180")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Center the window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (180 // 2)
        progress_window.geometry(f"500x180+{x}+{y}")
        
        status_label = tk.Label(progress_window, text="Downloading from AWS S3...", 
                               font=('Segoe UI', 11), bg=self.bg_color, fg=self.text_color)
        status_label.pack(pady=20)
        
        detail_label = tk.Label(progress_window, text=f"s3://{bucket}/{key}", 
                               font=('Segoe UI', 9), bg=self.bg_color, fg=self.text_secondary)
        detail_label.pack(pady=(0, 10))
        
        progress = ttk.Progressbar(progress_window, mode='indeterminate', length=400)
        progress.pack(pady=10)
        progress.start(10)
        
        progress_window.update()
        
        def do_download():
            """Perform download in background thread"""
            try:
                import tempfile
                
                # Create S3 client with profile
                session_kwargs = {}
                if profile and profile != "default":
                    session_kwargs['profile_name'] = profile
                
                session = boto3.Session(**session_kwargs)
                s3_client = session.client('s3')
                
                # Create temporary file
                temp_dir = tempfile.gettempdir()
                filename = os.path.basename(key) if '/' in key else key
                local_path = os.path.join(temp_dir, filename)
                
                # Download file
                s3_client.download_file(bucket, key, local_path)
                
                progress.stop()
                progress_window.destroy()
                
                # Process the downloaded file
                try:
                    self.detected_delimiter = self.detect_delimiter(local_path)
                    
                    with open(local_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f, delimiter=self.detected_delimiter)
                        rows = list(reader)
                    
                    if not rows:
                        messagebox.showwarning("Empty File", "The downloaded file is empty!")
                        return
                    
                    self.headers = rows[0]
                    self.data = rows[1:]
                    
                    # Log S3 file access to audit trail
                    if hasattr(self.root, 'log_file_access'):
                        self.root.log_file_access(f"s3://{bucket}/{key}", "DOWNLOADED_FROM_S3")
                    
                    column_options = [f"{idx}: {header}" for idx, header in enumerate(self.headers)]
                    
                    self.first_name_combo['values'] = column_options
                    self.last_name_combo['values'] = column_options
                    self.termination_date_combo['values'] = column_options
                    self.date_of_birth_combo['values'] = column_options
                    
                    detected_first, detected_last, detected_term, detected_dob = self.auto_detect_name_columns()
                    
                    if detected_first:
                        self.first_name_col.set(detected_first)
                    elif self.headers:
                        self.first_name_col.set(column_options[0])
                    
                    if detected_last:
                        self.last_name_col.set(detected_last)
                    elif len(self.headers) > 1:
                        self.last_name_col.set(column_options[1])
                    
                    if detected_term:
                        self.termination_date_col.set(detected_term)
                    
                    if detected_dob:
                        self.date_of_birth_col.set(detected_dob)
                    
                    delimiter_name = {'|': 'Pipe (|)', ',': 'Comma (,)', '\t': 'Tab (\\t)'}
                    self.s3_info_label.config(
                        text=f"S3 File: {filename} | "
                             f"Delimiter: {delimiter_name.get(self.detected_delimiter, self.detected_delimiter)} | "
                             f"Rows: {len(self.data)} | Columns: {len(self.headers)}"
                    )
                    
                    self.display_data()
                    
                    messagebox.showinfo("Success", 
                                      f"Successfully downloaded from S3!\n\n"
                                      f"File: {filename}\n"
                                      f"Rows: {len(self.data)}\n"
                                      f"Columns: {len(self.headers)}")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to process downloaded file:\n{str(e)}")
                
            except NoCredentialsError:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("AWS Credentials Error", 
                                   "AWS credentials not configured\n\n"
                                   "Please check:\n"
                                   "• Configure in HelloToolbelt Settings → AWS Credentials\n"
                                   "• Or run: aws configure")
            except ProfileNotFound:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("AWS Profile Error", 
                                   f"Profile '{profile}' not found\n\n"
                                   f"Please check:\n"
                                   f"• Profile name is correct\n"
                                   f"• Profile exists in ~/.aws/credentials")
            except ClientError as e:
                progress.stop()
                progress_window.destroy()
                error_code = e.response['Error']['Code']
                
                if error_code == 'NoSuchBucket':
                    messagebox.showerror("S3 Error", 
                                       f"Bucket does not exist: {bucket}\n\n"
                                       f"Please check:\n"
                                       f"• Bucket name is correct\n"
                                       f"• You have access to this bucket")
                elif error_code == 'NoSuchKey':
                    messagebox.showerror("S3 Error", 
                                       f"File not found in S3: {key}\n\n"
                                       f"Please check:\n"
                                       f"• Key/path is correct\n"
                                       f"• File exists in the bucket")
                elif error_code == 'AccessDenied':
                    messagebox.showerror("S3 Error", 
                                       f"Access denied\n\n"
                                       f"Please check:\n"
                                       f"• AWS credentials are configured\n"
                                       f"• You have read permissions\n"
                                       f"• Profile '{profile}' is correct")
                else:
                    messagebox.showerror("S3 Error", 
                                       f"Failed to download from S3\n\n"
                                       f"Error: {error_code}")
            except Exception as e:
                progress.stop()
                progress_window.destroy()
                messagebox.showerror("Error", f"Unexpected error:\n{str(e)}")
        
        # Run download in thread to keep UI responsive
        import threading
        download_thread = threading.Thread(target=do_download, daemon=True)
        download_thread.start()

    def save_aws_credentials(self):
        """Save AWS credentials to system keychain"""
        # Delegate to HelloToolbelt if in integrated mode
        if self.in_hellotoolbelt:
            self.hellotoolbelt_instance.save_aws_credentials()
            return
        
        # Original standalone save logic
        access_key = self.aws_access_key_entry.get().strip()
        secret_key = self.aws_secret_key_entry.get().strip()
        region = self.aws_region_entry.get().strip() or "us-east-1"
        
        if not access_key or not secret_key:
            messagebox.showwarning("Missing Credentials", 
                                 "Please enter both Access Key ID and Secret Access Key!")
            return
        
        if self.keyring_available:
            try:
                import keyring
                keyring.set_password("BillHunter", "aws_access_key_id", access_key)
                keyring.set_password("BillHunter", "aws_secret_access_key", secret_key)
                keyring.set_password("BillHunter", "aws_region", region)
                
                self.cred_status_label.config(
                    text="✅ Credentials saved securely in system keychain",
                    fg=self.success_color
                )
                messagebox.showinfo("Success", "AWS credentials saved securely!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save credentials:\n{str(e)}")
        else:
            messagebox.showwarning("Keyring Not Available", 
                                 "Keyring package not installed. Credentials will only be available during this session.\n\n"
                                 "To enable secure storage, install: pip install keyring")
            self.cred_status_label.config(
                text="⚠️ Credentials in memory only (keyring not installed)",
                fg=self.warning_color
            )
    
    def load_aws_credentials(self):
        """Load AWS credentials from system keychain"""
        # Skip if in HelloToolbelt mode - credentials already loaded
        if self.in_hellotoolbelt:
            return
        
        # Original standalone load logic
        if not self.keyring_available:
            return
        
        try:
            import keyring
            access_key = keyring.get_password("BillHunter", "aws_access_key_id")
            secret_key = keyring.get_password("BillHunter", "aws_secret_access_key")
            region = keyring.get_password("BillHunter", "aws_region")
            
            if access_key:
                self.aws_access_key_entry.delete(0, tk.END)
                self.aws_access_key_entry.insert(0, access_key)
            
            if secret_key:
                self.aws_secret_key_entry.delete(0, tk.END)
                self.aws_secret_key_entry.insert(0, secret_key)
            
            if region:
                self.aws_region_entry.delete(0, tk.END)
                self.aws_region_entry.insert(0, region)
            
            if access_key and secret_key:
                self.cred_status_label.config(
                    text="✅ Credentials loaded from system keychain",
                    fg=self.success_color
                )
        except Exception as e:
            pass  # Silently fail if no credentials
    
    def clear_aws_credentials(self):
        """Clear AWS credentials from both UI and keychain"""
        # Delegate to HelloToolbelt if in integrated mode
        if self.in_hellotoolbelt:
            self.hellotoolbelt_instance.clear_aws_credentials()
            return
        
        # Original standalone clear logic
        response = messagebox.askyesno("Clear Credentials", 
                                      "Are you sure you want to clear all AWS credentials?")
        if not response:
            return
        
        # Clear UI fields
        self.aws_access_key_entry.delete(0, tk.END)
        self.aws_secret_key_entry.delete(0, tk.END)
        self.aws_region_entry.delete(0, tk.END)
        self.aws_region_entry.insert(0, "us-east-1")
        
        # Clear from keychain
        if self.keyring_available:
            try:
                import keyring
                keyring.delete_password("BillHunter", "aws_access_key_id")
                keyring.delete_password("BillHunter", "aws_secret_access_key")
                keyring.delete_password("BillHunter", "aws_region")
            except:
                pass  # Ignore errors if credentials don't exist
        
        self.cred_status_label.config(
            text="🗑️ Credentials cleared",
            fg=self.text_secondary
        )
        messagebox.showinfo("Cleared", "AWS credentials have been cleared!")
    
    def test_aws_connection(self):
        """Test AWS connection with entered credentials"""
        # Get credentials from appropriate source
        if self.in_hellotoolbelt:
            access_key = self.hellotoolbelt_instance.aws_access_key.get().strip()
            secret_key = self.hellotoolbelt_instance.aws_secret_key.get().strip()
            region = self.hellotoolbelt_instance.aws_region.get().strip() or "us-east-1"
        else:
            access_key = self.aws_access_key_entry.get().strip()
            secret_key = self.aws_secret_key_entry.get().strip()
            region = self.aws_region_entry.get().strip() or "us-east-1"
        
        if not access_key or not secret_key:
            messagebox.showwarning("Missing Credentials", 
                                 "Please enter AWS credentials first!")
            return
        
        if not self.boto3_available:
            messagebox.showerror("boto3 Not Available", 
                               "boto3 is not installed. Please install it first:\n\n"
                               "pip install boto3")
            return
        
        # Create progress window
        test_window = tk.Toplevel(self.root)
        test_window.title("Testing AWS Connection")
        test_window.geometry("400x150")
        test_window.transient(self.root)
        test_window.grab_set()
        
        tk.Label(test_window, text="Testing AWS Connection...", 
                font=('Segoe UI', 11, 'bold')).pack(pady=20)
        
        progress = ttk.Progressbar(test_window, mode='indeterminate', length=300)
        progress.pack(pady=10)
        progress.start()
        
        status_label = tk.Label(test_window, text="Connecting to AWS...", font=('Segoe UI', 9))
        status_label.pack(pady=10)
        
        def test_connection():
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError
                
                # Create S3 client with credentials
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
                
                # Try to list buckets
                status_label.config(text="Listing S3 buckets...")
                test_window.update()
                
                response = s3_client.list_buckets()
                bucket_count = len(response['Buckets'])
                
                progress.stop()
                test_window.destroy()
                
                # Success!
                self.cred_status_label.config(
                    text=f"✅ Connection successful! Found {bucket_count} bucket(s)",
                    fg=self.success_color
                )
                
                messagebox.showinfo("Success! ✅", 
                                  f"AWS Connection Successful!\n\n"
                                  f"✅ Credentials are valid\n"
                                  f"✅ Found {bucket_count} S3 bucket(s)\n"
                                  f"✅ Region: {region}\n\n"
                                  f"You can now use S3 features!")
                
            except NoCredentialsError:
                progress.stop()
                test_window.destroy()
                self.cred_status_label.config(
                    text="❌ Invalid credentials",
                    fg=self.danger_color
                )
                messagebox.showerror("Invalid Credentials", 
                                   "The provided AWS credentials are invalid.\n\n"
                                   "Please check:\n"
                                   "• Access Key ID is correct\n"
                                   "• Secret Access Key is correct")
            
            except ClientError as e:
                progress.stop()
                test_window.destroy()
                error_code = e.response['Error']['Code']
                
                if error_code == 'InvalidAccessKeyId':
                    self.cred_status_label.config(
                        text="❌ Invalid Access Key ID",
                        fg=self.danger_color
                    )
                    messagebox.showerror("Invalid Access Key", 
                                       "The Access Key ID is invalid.\n\n"
                                       "Please check your Access Key ID.")
                elif error_code == 'SignatureDoesNotMatch':
                    self.cred_status_label.config(
                        text="❌ Invalid Secret Access Key",
                        fg=self.danger_color
                    )
                    messagebox.showerror("Invalid Secret Key", 
                                       "The Secret Access Key is invalid.\n\n"
                                       "Please check your Secret Access Key.")
                else:
                    self.cred_status_label.config(
                        text=f"❌ Error: {error_code}",
                        fg=self.danger_color
                    )
                    messagebox.showerror("AWS Error", 
                                       f"AWS Error: {error_code}\n\n{str(e)}")
            
            except Exception as e:
                progress.stop()
                test_window.destroy()
                self.cred_status_label.config(
                    text="❌ Connection failed",
                    fg=self.danger_color
                )
                messagebox.showerror("Connection Error", 
                                   f"Failed to connect to AWS:\n\n{str(e)}")
        
        # Run test in thread
        import threading
        test_thread = threading.Thread(target=test_connection, daemon=True)
        test_thread.start()

    def extract_column_name(self, selection):
        if ':' in selection:
            return selection.split(': ', 1)[1]
        return selection
    
    def _init_date_formats(self):
        """Initialize date format patterns for DOB normalization"""
        self.date_formats = {
            "yyyyMMdd": {
                "regex": r"^([0-9]{4})(0[1-9]|1[0-2])(0[1-9]|[1-2][0-9]|3[0-1])$",
                "format": "%Y%m%d"
            },
            "MM/dd/yyyy": {
                "regex": r"^([0]?[1-9]|[1][0-2])/([0]?[1-9]|[1|2][0-9]|[3][0|1])/([0-9]{4})$",
                "format": "%m/%d/%Y"
            },
            "MM/dd/yy": {
                "regex": r"^([0]?[1-9]|[1][0-2])/([0]?[1-9]|[1|2][0-9]|[3][0|1])/([0-9]{2})$",
                "format": "%m/%d/%y"
            },
            "yyyy-MM-dd": {
                "regex": r"^([0-9]{4})-([0]?[1-9]|[1][0-2])-([0]?[1-9]|[1|2][0-9]|[3][0|1])$",
                "format": "%Y-%m-%d"
            },
            "MM-dd-yyyy": {
                "regex": r"^([0]?[1-9]|[1][0-2])-([0]?[1-9]|[1|2][0-9]|[3][0|1])-([0-9]{4})$",
                "format": "%m-%d-%Y"
            }
        }
    
    def load_db_config(self):
        """Load database configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.db_host.set(config.get('host', 'localhost'))
                    self.db_port.set(config.get('port', '5432'))
                    self.db_name.set(config.get('database', ''))
                    self.db_user.set(config.get('username', ''))
                    # Note: Password is not saved for security reasons
        except Exception:
            pass  # If config file is corrupted or doesn't exist, use defaults
    
    def save_db_config(self):
        """Save database configuration to file"""
        # Delegate to HelloToolbelt if in integrated mode
        if self.in_hellotoolbelt:
            self.hellotoolbelt_instance.save_db_config()
            return
        
        # Original standalone save logic
        try:
            config = {
                'host': self.db_host.get(),
                'port': self.db_port.get(),
                'database': self.db_name.get(),
                'username': self.db_user.get()
                # Note: Password is not saved for security reasons
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Saved", "Database configuration saved!\n\n(Password is not saved for security)")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save config:\n{str(e)}")
    
    def test_db_connection(self):
        """Test the PostgreSQL database connection"""
        # Delegate to HelloToolbelt if in integrated mode
        if self.in_hellotoolbelt:
            self.hellotoolbelt_instance.test_db_connection()
            return
        
        # Original test logic continues...
        if not PSYCOPG2_AVAILABLE:
            messagebox.showerror("Error", 
                               "psycopg2 is not installed.\n\n"
                               "To install, run:\n"
                               "pip install psycopg2-binary")
            return
        
        # Get current values
        host = self.db_host.get().strip()
        port = self.db_port.get().strip()
        database = self.db_name.get().strip()
        user = self.db_user.get().strip()
        password = self.db_password.get().strip()
        
        # Validate required fields
        if not all([host, database, user]):
            messagebox.showwarning("Missing Information", 
                                 "Please fill in at least:\n"
                                 "• Host\n"
                                 "• Database\n"
                                 "• Username")
            return
        
        # Use default port if not specified
        if not port:
            port = "5432"
        
        # Show progress dialog
        test_window = tk.Toplevel(self.root)
        test_window.title("Testing Connection")
        test_window.geometry("400x150")
        test_window.transient(self.root)
        test_window.grab_set()
        
        # Center the window
        test_window.update_idletasks()
        x = (test_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (test_window.winfo_screenheight() // 2) - (150 // 2)
        test_window.geometry(f"400x150+{x}+{y}")
        
        status_label = tk.Label(test_window, text="Testing database connection...", 
                               font=('Segoe UI', 11), bg=self.bg_color, fg=self.text_color)
        status_label.pack(pady=30)
        
        progress = ttk.Progressbar(test_window, mode='indeterminate', length=300)
        progress.pack(pady=10)
        progress.start(10)
        
        test_window.update()
        
        # Try to connect
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=10
            )
            
            # Test a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            progress.stop()
            test_window.destroy()
            
            # Show success message with PostgreSQL version
            version_short = version.split('\n')[0][:80]  # First line, max 80 chars
            messagebox.showinfo("Connection Successful! ✅", 
                              f"Successfully connected to PostgreSQL database!\n\n"
                              f"Host: {host}\n"
                              f"Database: {database}\n"
                              f"Port: {port}\n\n"
                              f"Server: {version_short}")
            
        except psycopg2.OperationalError as e:
            progress.stop()
            test_window.destroy()
            
            error_msg = str(e)
            
            # Provide helpful error messages
            if "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
                messagebox.showerror("Connection Failed ❌", 
                                   f"Could not connect to the database server.\n\n"
                                   f"Possible issues:\n"
                                   f"• PostgreSQL server is not running\n"
                                   f"• Host or port is incorrect\n"
                                   f"• Firewall is blocking the connection\n\n"
                                   f"Details: {error_msg}")
            elif "authentication failed" in error_msg.lower() or "password" in error_msg.lower():
                messagebox.showerror("Authentication Failed ❌", 
                                   f"Database credentials are incorrect.\n\n"
                                   f"Please check:\n"
                                   f"• Username is correct\n"
                                   f"• Password is correct\n"
                                   f"• User has access to this database\n\n"
                                   f"Details: {error_msg}")
            elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                messagebox.showerror("Database Not Found ❌", 
                                   f"The database '{database}' does not exist.\n\n"
                                   f"Please check:\n"
                                   f"• Database name is spelled correctly\n"
                                   f"• Database exists on the server\n\n"
                                   f"Details: {error_msg}")
            else:
                messagebox.showerror("Connection Error ❌", 
                                   f"Failed to connect to database.\n\n"
                                   f"Error: {error_msg}")
                
        except Exception as e:
            progress.stop()
            test_window.destroy()
            messagebox.showerror("Error ❌", 
                               f"An unexpected error occurred:\n\n{str(e)}")

    def normalize_term_date(self, term_date_value):
        """Convert uploaded termination date into yyyy-MM-dd format."""
        if not term_date_value or str(term_date_value).strip() == '':
            return term_date_value
        
        term_date_str = str(term_date_value).strip()
        
        import re
        for format_name, format_info in self.date_formats.items():
            if re.match(format_info["regex"], term_date_str):
                try:
                    parsed_date = datetime.strptime(term_date_str, format_info["format"])
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        return term_date_value

    def normalize_dob(self, dob_value):
        """Convert uploaded DOB into yyyy-MM-dd format."""
        if not dob_value or str(dob_value).strip() == '':
            return dob_value
        
        dob_str = str(dob_value).strip()
        
        import re
        for format_name, format_info in self.date_formats.items():
            if re.match(format_info["regex"], dob_str):
                try:
                    parsed_date = datetime.strptime(dob_str, format_info["format"])
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        return dob_value
    
    def apply_selection(self):
        if not self.headers:
            messagebox.showwarning("No File", "Please upload a file first!")
            return
        
        client = self.client.get()
        first_col = self.extract_column_name(self.first_name_col.get())
        last_col = self.extract_column_name(self.last_name_col.get())
        term_col = self.extract_column_name(self.termination_date_col.get()) if self.termination_date_col.get() else "Not selected"
        dob_col = self.extract_column_name(self.date_of_birth_col.get()) if self.date_of_birth_col.get() else "Not selected"
        
        if not client:
            messagebox.showwarning("Client Required", 
                                "Please select a client!")
            return
        
        if not first_col or not last_col:
            messagebox.showwarning("Selection Required", 
                                "Please select both first name and last name columns!")
            return
        
        dob_normalized_count = 0
        term_normalized_count = 0
        
        billable_status = self.billable_status.get()  # ADD THIS LINE
        client = self.client.get()
        first_col = self.extract_column_name(self.first_name_col.get())
        
        # ADD THIS VALIDATION:
        if not billable_status:
            messagebox.showwarning("Billable Status Required", 
                                "Please select a billable status!")
            return
    
        # Normalize DOB column if selected
        if dob_col != "Not selected" and dob_col in self.headers:
            try:
                dob_idx = self.headers.index(dob_col)
                
                for row in self.data:
                    if len(row) > dob_idx:
                        original_value = row[dob_idx]
                        normalized_value = self.normalize_dob(original_value)
                        if original_value != normalized_value:
                            row[dob_idx] = normalized_value
                            dob_normalized_count += 1
                            
            except ValueError as e:
                messagebox.showerror("Error", f"DOB column error:\n{str(e)}")
                return
        
        # Normalize termination date column if selected
        if term_col != "Not selected" and term_col in self.headers:
            try:
                term_idx = self.headers.index(term_col)
                
                for row in self.data:
                    if len(row) > term_idx:
                        original_value = row[term_idx]
                        normalized_value = self.normalize_term_date(original_value)
                        if original_value != normalized_value:
                            row[term_idx] = normalized_value
                            term_normalized_count += 1
                            
            except ValueError as e:
                messagebox.showerror("Error", f"Termination date column error:\n{str(e)}")
                return
        
        # Refresh the display to show normalized dates
        self.display_data()
        
        msg = (f"Client: {client}\n"
            f"First Name Column: {first_col}\n"
            f"Last Name Column: {last_col}\n"
            f"Termination Date Column: {term_col}\n"
            f"Date of Birth Column: {dob_col}\n\n")
        
        if dob_normalized_count > 0:
            msg += f"{dob_normalized_count} DOB values normalized to yyyy-MM-dd format.\n"
        
        if term_normalized_count > 0:
            msg += f"{term_normalized_count} termination date values normalized to yyyy-MM-dd format.\n"
        
        if dob_normalized_count > 0 or term_normalized_count > 0:
            msg += "\n"
        
        msg += "You can now process the data with these selections."
        
        messagebox.showinfo("Selection Applied", msg)
    
    def generate_query(self):
        client = self.client.get()
        billable_status = self.billable_status.get()
        
        if not billable_status:
            messagebox.showwarning("Billable Status Required", 
                                "Please select a billable status first!")
            return
        
        if not client:
            messagebox.showwarning("Client Required", 
                                "Please select a client first!")
            return
        
        # The WHERE clause changes based on billable status
        if billable_status == "Should be billable":
            where_clause = "WHERE unbillable IS TRUE"
        else:  # Should not be billable
            where_clause = "WHERE unbillable IS FALSE OR unbillable IS NULL"
        
        query_lines = [
            "SELECT",
            "    user_id,",
            "    email,",
            "    first_name,",
            "    last_name,",
            "    date_of_birth,",
            "    total_bps,",
            "    CASE",
            "        WHEN first_login_date IS NULL",
            "             OR NULLIF(first_login_date::text, '') IS NULL THEN NULL",
            "        WHEN first_login_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((first_login_date::bigint) / 1000.0)::date",
            "        ELSE first_login_date::date",
            "    END AS first_login_date,",
            "    CASE",
            "        WHEN last_login_date IS NULL",
            "             OR NULLIF(last_login_date::text, '') IS NULL THEN NULL",
            "        WHEN last_login_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((last_login_date::bigint) / 1000.0)::date",
            "        ELSE last_login_date::date",
            "    END AS last_login_date,",
            "    CASE",
            "        WHEN last_bp_date IS NULL",
            "             OR NULLIF(last_bp_date::text, '') IS NULL THEN NULL",
            "        WHEN last_bp_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((last_bp_date::bigint) / 1000.0)::date",
            "        ELSE last_bp_date::date",
            "    END AS last_bp_date,",
            "    CASE",
            "        WHEN termination_date IS NULL",
            "             OR NULLIF(termination_date::text, '') IS NULL THEN NULL",
            "        WHEN termination_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((termination_date::bigint) / 1000.0)::date",
            "        ELSE termination_date::date",
            "    END AS termed_in_cheif",
            f"FROM {client}.users",
            where_clause,
            "ORDER BY last_login_date DESC NULLS LAST;"
        ]
        
        query = "\n".join(query_lines)
        
        # Automatically copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(query)
        
        # Show simple confirmation popup
        messagebox.showinfo("Copied", f"Copied Query for: {client}")
    
    def stop_query(self):
        """Stop the running database query"""
        self.query_cancelled = True
        
        # Try to cancel the query and close connection
        try:
            if self.db_cursor:
                self.db_cursor.close()
            if self.db_connection:
                self.db_connection.cancel()
                self.db_connection.close()
        except:
            pass
        
        # Reset UI - swap buttons back
        self.root.config(cursor="")
        self.stop_query_btn.pack_forget()
        self.run_query_btn.pack()
        
        messagebox.showinfo("Query Cancelled", "Database query has been stopped.")
    
    def run_query_in_db(self):
        """Run the query directly in PostgreSQL database and load results"""
        if not PSYCOPG2_AVAILABLE:
            messagebox.showerror("Error", 
                               "psycopg2 is not installed!\n\n"
                               "Install it using:\npip install psycopg2-binary")
            return
        
        client = self.client.get()
        billable_status = self.billable_status.get()
        
        if not billable_status:
            messagebox.showwarning("Billable Status Required", 
                                "Please select a billable status first!")
            return
        
        if not client:
            messagebox.showwarning("Client Required", 
                                "Please select a client first!")
            return
        
        # Validate database configuration
        db_host = self.db_host.get().strip()
        db_port = self.db_port.get().strip()
        db_name = self.db_name.get().strip()
        db_user = self.db_user.get().strip()
        db_password = self.db_password.get()
        
        # Debug logging for troubleshooting
        print(f"Bill Hunter Debug - Database credentials:")
        print(f"  - in_hellotoolbelt: {self.in_hellotoolbelt}")
        print(f"  - db_host: {db_host}")
        print(f"  - db_port: {db_port}")
        print(f"  - db_name: {db_name}")
        print(f"  - db_user: {db_user}")
        print(f"  - db_password length: {len(db_password) if db_password else 0}")
        print(f"  - db_password empty: {not db_password or not db_password.strip()}")
        
        if self.in_hellotoolbelt:
            print(f"  - HelloToolbelt db_password value: {self.hellotoolbelt_instance.db_password.get()}")
            print(f"  - Same object: {self.db_password is self.hellotoolbelt_instance.db_password}")
        
        if not all([db_host, db_port, db_name, db_user]):
            messagebox.showwarning("Database Configuration Required",
                                 "Please fill in all database connection fields:\n"
                                 "Host, Port, Database, and Username")
            return
        
        # Check if password is missing and warn user
        if not db_password or not db_password.strip():
            result = messagebox.askyesno("Password Missing", 
                                        "Database password is empty.\n\n"
                                        "Connection will likely fail if password is required.\n\n"
                                        "Continue anyway?")
            if not result:
                return
        
        # Generate the query
        if billable_status == "Should be billable":
            where_clause = "WHERE unbillable IS TRUE"
        else:
            where_clause = "WHERE unbillable IS FALSE OR unbillable IS NULL"
        
        query_lines = [
            "SELECT",
            "    user_id,",
            "    email,",
            "    first_name,",
            "    last_name,",
            "    date_of_birth,",
            "    total_bps,",
            "    CASE",
            "        WHEN first_login_date IS NULL",
            "             OR NULLIF(first_login_date::text, '') IS NULL THEN NULL",
            "        WHEN first_login_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((first_login_date::bigint) / 1000.0)::date",
            "        ELSE first_login_date::date",
            "    END AS first_login_date,",
            "    CASE",
            "        WHEN last_login_date IS NULL",
            "             OR NULLIF(last_login_date::text, '') IS NULL THEN NULL",
            "        WHEN last_login_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((last_login_date::bigint) / 1000.0)::date",
            "        ELSE last_login_date::date",
            "    END AS last_login_date,",
            "    CASE",
            "        WHEN last_bp_date IS NULL",
            "             OR NULLIF(last_bp_date::text, '') IS NULL THEN NULL",
            "        WHEN last_bp_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((last_bp_date::bigint) / 1000.0)::date",
            "        ELSE last_bp_date::date",
            "    END AS last_bp_date,",
            "    CASE",
            "        WHEN termination_date IS NULL",
            "             OR NULLIF(termination_date::text, '') IS NULL THEN NULL",
            "        WHEN termination_date::text ~ '^[0-9]+$'",
            "             THEN to_timestamp((termination_date::bigint) / 1000.0)::date",
            "        ELSE termination_date::date",
            "    END AS termed_in_cheif",
            f"FROM {client}.users",
            where_clause,
            "ORDER BY last_login_date DESC NULLS LAST;"
        ]
        
        query = "\n".join(query_lines)
        
        # Reset cancellation flag
        self.query_cancelled = False
        
        # Show stop button and hide run button (swap in same container)
        self.run_query_btn.pack_forget()
        self.stop_query_btn.pack()
        
        # Change cursor to show loading
        self.root.config(cursor="watch")
        self.root.update()
        
        # Try to connect and execute query
        try:
            # Check if cancelled before connecting
            if self.query_cancelled:
                raise Exception("Query cancelled by user")
            
            # Connect to database
            self.db_connection = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=10
            )
            
            # Check if cancelled after connecting
            if self.query_cancelled:
                self.db_connection.close()
                raise Exception("Query cancelled by user")
            
            self.db_cursor = self.db_connection.cursor()
            
            # Execute query
            self.db_cursor.execute(query)
            
            # Check if cancelled during execution
            if self.query_cancelled:
                self.db_cursor.close()
                self.db_connection.close()
                raise Exception("Query cancelled by user")
            
            # Fetch all results
            results = self.db_cursor.fetchall()
            
            # Get column names
            column_names = [desc[0] for desc in self.db_cursor.description]
            
            # Close connection
            self.db_cursor.close()
            self.db_connection.close()
            self.db_cursor = None
            self.db_connection = None
            
            # Store results
            self.postgres_data = results
            
            # Reset cursor
            self.root.config(cursor="")
            
            # Hide stop button and show run button (swap back)
            self.stop_query_btn.pack_forget()
            self.run_query_btn.pack()
            
            # Display success message
            messagebox.showinfo("Success", 
                              f"Query executed successfully!\n\n"
                              f"Retrieved {len(results)} rows from {client}.users\n\n"
                              f"Results are now ready for matching.")
            
        except psycopg2.OperationalError as e:
            self.root.config(cursor="")  # Reset cursor
            self.stop_query_btn.pack_forget()
            self.run_query_btn.pack()
            
            error_msg = str(e)
            if "does not exist" in error_msg:
                messagebox.showerror("Database Error", 
                                   f"Database '{db_name}' not found.\n\n"
                                   f"Please verify:\n"
                                   f"1. Database name is correct\n"
                                   f"2. Your user has access to this database\n\n"
                                   f"Full error: {error_msg}")
            elif "authentication failed" in error_msg or "password authentication failed" in error_msg:
                messagebox.showerror("Authentication Error", 
                                   f"Could not authenticate with provided credentials.\n\n"
                                   f"Please check your username and password.\n\n"
                                   f"Full error: {error_msg}")
            elif "Connection refused" in error_msg or "could not connect" in error_msg:
                messagebox.showerror("Connection Error", 
                                   f"Could not connect to server.\n\n"
                                   f"Host: {db_host}\n"
                                   f"Port: {db_port}\n\n"
                                   f"Please check host and port.\n\n"
                                   f"Full error: {error_msg}")
            else:
                messagebox.showerror("Connection Error", 
                                   f"Could not connect to database:\n\n{error_msg}")
        except psycopg2.ProgrammingError as e:
            self.root.config(cursor="")  # Reset cursor
            self.stop_query_btn.pack_forget()
            self.run_query_btn.pack()
            messagebox.showerror("Query Error", 
                               f"Error in SQL query:\n\n{str(e)}\n\n"
                               f"Schema '{client}' may not exist or table 'users' not found.")
        except psycopg2.Error as e:
            self.root.config(cursor="")  # Reset cursor
            self.stop_query_btn.pack_forget()
            self.run_query_btn.pack()
            messagebox.showerror("Database Error", 
                               f"Database error:\n\n{str(e)}")
        except Exception as e:
            self.root.config(cursor="")  # Reset cursor
            self.stop_query_btn.pack_forget()
            self.run_query_btn.pack()
            
            # Check if it was a user cancellation
            if self.query_cancelled or "cancelled by user" in str(e).lower():
                return  # Don't show error for user cancellation
            
            messagebox.showerror("Error", 
                               f"Unexpected error:\n\n{str(e)}")
    
    def clean_postgres_value(self, value):
        if value is None:
            return ''
        value_str = str(value).strip()
        if value_str.startswith('"') and value_str.endswith('"'):
            value_str = value_str[1:-1]
        return value_str
    
    def display_data(self):
        self.tree.delete(*self.tree.get_children())
        
        self.tree['columns'] = self.headers
        self.tree['show'] = 'headings'
        
        # Reset sort state
        self.sort_reverse = {}
        
        for col in self.headers:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=150, anchor=tk.W)
        
        # Store all results for filtering
        self.all_results = list(self.data)
        
        for row in self.data:
            self.tree.insert('', tk.END, values=row)
    
    def sort_treeview(self, col):
        columns = list(self.tree['columns'])
        col_index = columns.index(col)
        
        data_list = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        # Toggle sort direction
        reverse = self.sort_reverse.get(col, False)
        self.sort_reverse[col] = not reverse
        
        # Store current sort column for reference
        self.current_sort_column = col
        
        # Check if column contains dates based on column name or content
        is_date_column = any(keyword in col.lower() for keyword in ['date', 'modified', 'created', 'updated', 'term'])
        
        if is_date_column:
            # Try to sort as dates
            def date_key(item):
                val = item[0]
                if not val or val == '':
                    return datetime.min if not reverse else datetime.max
                
                # Try multiple date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%Y/%m/%d', 
                           '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S']:
                    try:
                        return datetime.strptime(str(val).strip(), fmt)
                    except (ValueError, AttributeError):
                        continue
                
                # If parsing fails, return original for string sort
                return datetime.min if not reverse else datetime.max
            
            try:
                data_list.sort(key=date_key, reverse=reverse)
            except Exception:
                # Fall back to string sort if date parsing fails
                data_list.sort(key=lambda t: t[0].lower() if t[0] else '', reverse=reverse)
        else:
            # Try numeric sort first, fall back to string sort
            try:
                data_list.sort(key=lambda t: float(t[0]) if t[0] else 0, reverse=reverse)
            except (ValueError, TypeError):
                data_list.sort(key=lambda t: str(t[0]).lower() if t[0] else '', reverse=reverse)
        
        # Reorder items in tree
        for index, (val, item) in enumerate(data_list):
            self.tree.move(item, '', index)
        
        # Update column headers with sort indicators
        for column in columns:
            if column == col:
                direction = ' ▼' if reverse else ' ▲'
                self.tree.heading(column, text=f"{column}{direction}", 
                                command=lambda c=column: self.sort_treeview(c))
            else:
                self.tree.heading(column, text=column, 
                                command=lambda c=column: self.sort_treeview(c))
                
    def copy_all_results(self):
        """Copy all results from the treeview to clipboard"""
        items = self.tree.get_children()
        
        if not items:
            messagebox.showinfo("No Data", "No results to copy!")
            return
        
        columns = list(self.tree['columns'])
        copied_text = '\t'.join(columns) + '\n'
        
        for item in items:
            values = self.tree.item(item)['values']
            row_text = '\t'.join(str(v) for v in values)
            copied_text += row_text + '\n'
        
        self.root.clipboard_clear()
        self.root.clipboard_append(copied_text.strip())
        
        messagebox.showinfo("Copied", f"Copied {len(items)} rows to clipboard!")
    
    def filter_results(self):
        """Filter displayed results based on search term"""
        if not hasattr(self, 'all_results'):
            # Store all results on first filter call
            self.all_results = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                self.all_results.append(values)
        
        search_term = self.search_var.get().lower()
        
        # Clear current display
        self.tree.delete(*self.tree.get_children())
        
        if not search_term:
            # Show all results if search is empty
            for row in self.all_results:
                self.tree.insert('', tk.END, values=row)
        else:
            # Show only matching results
            for row in self.all_results:
                # Search across all columns
                if any(search_term in str(value).lower() for value in row):
                    self.tree.insert('', tk.END, values=row)
    
    def clear_search(self):
        """Clear the search box"""
        self.search_var.set('')
        self.search_entry.focus()
    
    def copy_all_results_OLD(self):
        """Copy all results from the treeview to clipboard"""
        items = self.tree.get_children()
        
        if not items:
            messagebox.showinfo("No Data", "No results to copy!")
            return
        
        columns = list(self.tree['columns'])
        copied_text = '\t'.join(columns) + '\n'
        
        for item in items:
            values = self.tree.item(item)['values']
            row_text = '\t'.join(str(v) for v in values)
            copied_text += row_text + '\n'
        
        self.root.clipboard_clear()
        self.root.clipboard_append(copied_text.strip())
        
        messagebox.showinfo("Copied", f"Copied {len(items)} rows to clipboard!")

    def paste_postgres_results(self):
        try:
            clipboard_content = self.root.clipboard_get()
            
            if not clipboard_content.strip():
                messagebox.showwarning("Empty Clipboard", "Clipboard is empty!")
                return
            
            lines = clipboard_content.strip().split('\n')
            
            if not lines:
                messagebox.showwarning("No Data", "No data found in clipboard!")
                return
            
            self.postgres_data = []
            for line in lines:
                if line.strip():
                    raw_row = line.split('\t')
                    cleaned_row = [self.clean_postgres_value(val) for val in raw_row]
                    self.postgres_data.append(cleaned_row)
            
            messagebox.showinfo("Success", 
                              f"PostgreSQL results loaded!\n"
                              f"Rows: {len(self.postgres_data)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse PostgreSQL results:\n{str(e)}")
    
    def match_results(self):
        if not self.data or not self.headers:
            messagebox.showwarning("No File", "Please upload a file first!")
            return
        
        if not self.postgres_data:
            messagebox.showwarning("No PostgreSQL Data", "Please paste PostgreSQL results first!")
            return
        
        # Get the selected client and billable status
        selected_client = self.client.get()
        billable_status = self.billable_status.get()
        
        if not selected_client:
            messagebox.showwarning("Client Required", "Please select a client in the configuration!")
            return
        
        if not billable_status:
            messagebox.showwarning("Billable Status Required", "Please select a billable status in the configuration!")
            return
        
        first_col = self.extract_column_name(self.first_name_col.get())
        last_col = self.extract_column_name(self.last_name_col.get())
        term_col = self.extract_column_name(self.termination_date_col.get()) if self.termination_date_col.get() else None
        dob_col = self.extract_column_name(self.date_of_birth_col.get()) if self.date_of_birth_col.get() else None
        
        if not first_col or not last_col:
            messagebox.showwarning("Column Selection Required", 
                                "Please select first name and last name columns!")
            return
        
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Matching Results")
        progress_window.geometry("450x180")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Center the progress window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (225)
        y = (progress_window.winfo_screenheight() // 2) - (90)
        progress_window.geometry(f"450x180+{x}+{y}")
        
        # Title
        title_label = tk.Label(progress_window, text=f"Matching Results for: {selected_client}", 
                              font=('Segoe UI', 12, 'bold'), pady=15)
        title_label.pack()
        
        # Status label
        status_label = tk.Label(progress_window, text="Initializing...", 
                               font=('Segoe UI', 10))
        status_label.pack(pady=5)
        
        # Progress bar (determinate mode)
        progress_bar = ttk.Progressbar(progress_window, mode='determinate', length=350)
        progress_bar.pack(pady=10)
        
        # Progress text
        progress_text = tk.Label(progress_window, text="0%", 
                                font=('Segoe UI', 9), fg='gray')
        progress_text.pack()
        
        # Details label
        details_label = tk.Label(progress_window, text="", 
                                font=('Segoe UI', 8), fg='gray')
        details_label.pack(pady=5)
        
        progress_window.update()
        
        try:
            status_label.config(text="Reading file columns...")
            progress_window.update()
            
            first_idx = self.headers.index(first_col)
            last_idx = self.headers.index(last_col)
            term_idx = self.headers.index(term_col) if term_col else None
            dob_idx = self.headers.index(dob_col) if dob_col else None
            
            pg_first_idx = 2
            pg_last_idx = 3
            pg_dob_idx = 4
            pg_term_idx = 9  # termed_in_cheif index in PostgreSQL results
            
            today = datetime.now().date()
            
            if billable_status == "Should be billable":
                # ORIGINAL LOGIC: Match PG users with eligibility file (exclude past term dates)
                file_names_to_include = {}
                excluded_count = 0
                
                status_label.config(text="Processing eligibility file...")
                progress_bar['maximum'] = len(self.data)
                progress_window.update()
                
                for idx, row in enumerate(self.data):
                    if idx % 50 == 0:  # Update every 50 rows
                        progress = int((idx / len(self.data)) * 30)  # 0-30% for file processing
                        progress_bar['value'] = progress
                        progress_text.config(text=f"{progress}%")
                        details_label.config(text=f"Processing row {idx + 1} of {len(self.data)}")
                        progress_window.update()
                    
                    if len(row) > max(first_idx, last_idx):
                        first = row[first_idx].strip().lower()
                        last = row[last_idx].strip().lower()
                        
                        # Get DOB if available
                        dob = ''
                        if dob_idx is not None and len(row) > dob_idx:
                            dob = row[dob_idx].strip()
                        
                        # Get termination date from file
                        file_term_date = ''
                        if term_idx is not None and len(row) > term_idx:
                            file_term_date = row[term_idx].strip()
                        
                        should_include = True
                        
                        # Check termination date - EXCLUDE if date is in the past
                        if file_term_date and file_term_date != '':
                            try:
                                term_date = None
                                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%Y/%m/%d', '%Y%m%d']:
                                    try:
                                        term_date = datetime.strptime(file_term_date, fmt).date()
                                        break
                                    except ValueError:
                                        continue
                                
                                # EXCLUDE if termination date is in the past (before today)
                                if term_date and term_date < today:
                                    should_include = False
                                    excluded_count += 1
                            except Exception:
                                pass
                        
                        if should_include:
                            # Store the termination date from the file along with the key
                            if dob:
                                file_names_to_include[(first, last, dob)] = file_term_date
                            else:
                                file_names_to_include[(first, last, '')] = file_term_date
                
                self.matched_results = []
                match_with_dob_count = 0
                match_without_dob_count = 0
                
                status_label.config(text="Matching with PostgreSQL data...")
                progress_bar['maximum'] = 100
                progress_window.update()
                
                for idx, pg_row in enumerate(self.postgres_data):
                    if idx % 50 == 0:  # Update every 50 rows
                        progress = 30 + int((idx / len(self.postgres_data)) * 70)  # 30-100% for matching
                        progress_bar['value'] = progress
                        progress_text.config(text=f"{progress}%")
                        details_label.config(text=f"Matching row {idx + 1} of {len(self.postgres_data)}")
                        progress_window.update()
                    
                    if len(pg_row) > max(pg_first_idx, pg_last_idx):
                        first = self.clean_postgres_value(pg_row[pg_first_idx]).lower()
                        last = self.clean_postgres_value(pg_row[pg_last_idx]).lower()
                        
                        # Get DOB from PostgreSQL results
                        pg_dob = ''
                        if len(pg_row) > pg_dob_idx:
                            pg_dob = self.clean_postgres_value(pg_row[pg_dob_idx]).strip()
                        
                        # Try matching with DOB first
                        matched_term_date = None
                        if pg_dob and (first, last, pg_dob) in file_names_to_include:
                            matched_term_date = file_names_to_include[(first, last, pg_dob)]
                            match_with_dob_count += 1
                        # Fall back to matching without DOB if DOB match fails
                        elif (first, last, '') in file_names_to_include:
                            matched_term_date = file_names_to_include[(first, last, '')]
                            match_without_dob_count += 1
                        
                        # If we found a match, add the client and termination date
                        if matched_term_date is not None:
                            modified_row = [selected_client]  # Start with client in first position
                            # Add the rest of the PostgreSQL row data
                            modified_row.extend(pg_row)
                            # Append the file termination date as termination_date column
                            modified_row.append(matched_term_date)
                            self.matched_results.append(modified_row)
                
                msg = f"Found {len(self.matched_results)} matching records from PostgreSQL results.\n"
                msg += f"Billable Status: {billable_status}\n"
                msg += f"Client '{selected_client}' added to all matched records.\n"
                if match_with_dob_count > 0:
                    msg += f"{match_with_dob_count} matched with DOB verification.\n"
                if match_without_dob_count > 0:
                    msg += f"{match_without_dob_count} matched by name only (no DOB in file).\n"
                if excluded_count > 0:
                    msg += f"{excluded_count} users with past termination dates were excluded from the file."
            
            else:  # Should not be billable
                # NEW LOGIC: Show PG users who are NOT in file OR have past termination dates
                # Build a dictionary of all names in the eligibility file with their term dates
                file_names_with_dob = {}  # Changed from set to dict to store term dates
                file_names_without_dob = {}  # Changed from set to dict to store term dates
                
                status_label.config(text="Building file index...")
                progress_bar['maximum'] = 100
                progress_window.update()
                
                for idx, row in enumerate(self.data):
                    if idx % 50 == 0:  # Update every 50 rows
                        progress = int((idx / len(self.data)) * 30)  # 0-30% for file indexing
                        progress_bar['value'] = progress
                        progress_text.config(text=f"{progress}%")
                        details_label.config(text=f"Indexing row {idx + 1} of {len(self.data)}")
                        progress_window.update()
                    
                    if len(row) > max(first_idx, last_idx):
                        first = row[first_idx].strip().lower()
                        last = row[last_idx].strip().lower()
                        
                        if not first or not last:  # Skip empty names
                            continue
                        
                        # Get DOB if available
                        dob = ''
                        if dob_idx is not None and len(row) > dob_idx:
                            dob = row[dob_idx].strip()
                        
                        # Get termination date from file
                        file_term_date = ''
                        if term_idx is not None and len(row) > term_idx:
                            file_term_date = row[term_idx].strip()
                        
                        # Store names with their termination dates
                        if dob:
                            file_names_with_dob[(first, last, dob)] = file_term_date
                        else:
                            file_names_without_dob[(first, last)] = file_term_date
                
                self.matched_results = []
                not_in_file_count = 0
                past_term_in_file_count = 0
                excluded_auto_term_count = 0
                
                status_label.config(text="Finding non-billable users...")
                progress_window.update()
                
                # Find PG users who are NOT in the eligibility file OR have past termination dates
                for idx, pg_row in enumerate(self.postgres_data):
                    if idx % 50 == 0:  # Update every 50 rows
                        progress = 30 + int((idx / len(self.postgres_data)) * 70)  # 30-100% for matching
                        progress_bar['value'] = progress
                        progress_text.config(text=f"{progress}%")
                        details_label.config(text=f"Checking row {idx + 1} of {len(self.postgres_data)}")
                        progress_window.update()
                    
                    if len(pg_row) > max(pg_first_idx, pg_last_idx):
                        first = self.clean_postgres_value(pg_row[pg_first_idx]).lower()
                        last = self.clean_postgres_value(pg_row[pg_last_idx]).lower()
                        
                        if not first or not last:  # Skip empty names
                            continue
                        
                        # Get DOB from PostgreSQL results
                        pg_dob = ''
                        if len(pg_row) > pg_dob_idx:
                            pg_dob = self.clean_postgres_value(pg_row[pg_dob_idx]).strip()
                        
                        # Check if this person is in the eligibility file and get their term date
                        found_in_file = False
                        file_term_date_for_match = None
                        
                        # First try to match with DOB if PG has DOB
                        if pg_dob:
                            if (first, last, pg_dob) in file_names_with_dob:
                                found_in_file = True
                                file_term_date_for_match = file_names_with_dob[(first, last, pg_dob)]
                        
                        # If not found with DOB, check name-only match
                        if not found_in_file:
                            if (first, last) in file_names_without_dob:
                                found_in_file = True
                                file_term_date_for_match = file_names_without_dob[(first, last)]
                            else:
                                # Also check if name exists in file with any DOB
                                for (file_first, file_last, file_dob), term_date in file_names_with_dob.items():
                                    if first == file_first and last == file_last:
                                        found_in_file = True
                                        file_term_date_for_match = term_date
                                        break
                        
                        # Get termination date from PG results (column 9 - termed_in_cheif)
                        pg_term_date = ''
                        if len(pg_row) > pg_term_idx:
                            pg_term_date = self.clean_postgres_value(pg_row[pg_term_idx])
                        
                        # Check if FILE termination date is in the past (if user is in file)
                        has_past_file_term_date = False
                        if found_in_file and file_term_date_for_match and file_term_date_for_match.strip():
                            try:
                                file_term_date_obj = None
                                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%Y/%m/%d', '%Y%m%d']:
                                    try:
                                        file_term_date_obj = datetime.strptime(file_term_date_for_match, fmt).date()
                                        break
                                    except ValueError:
                                        continue
                                
                                # Check if file termination date is in the past (before today)
                                if file_term_date_obj and file_term_date_obj < today:
                                    has_past_file_term_date = True
                            except Exception:
                                pass
                        
                        # Check if termed_in_cheif date is in the future
                        has_future_termed_in_cheif = False
                        if pg_term_date and pg_term_date.strip():
                            try:
                                cheif_term_date = None
                                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%Y/%m/%d', '%Y%m%d']:
                                    try:
                                        cheif_term_date = datetime.strptime(pg_term_date, fmt).date()
                                        break
                                    except ValueError:
                                        continue
                                
                                # Check if termed_in_cheif date is in the future (today or later)
                                if cheif_term_date and cheif_term_date >= today:
                                    has_future_termed_in_cheif = True
                            except Exception:
                                pass
                        
                        # Include if NOT in file OR has past termination date (either condition)
                        # BUT exclude if has past FILE term date AND future termed_in_cheif (auto-term scheduled)
                        should_include = False
                        if has_past_file_term_date and has_future_termed_in_cheif:
                            # Exclude: has past term date in file but will auto-term in the future
                            should_include = False
                            excluded_auto_term_count += 1
                        elif not found_in_file:
                            # Not in file at all - should not be billable
                            should_include = True
                            not_in_file_count += 1
                        elif has_past_file_term_date:
                            # In file but has past term date - should not be billable
                            should_include = True
                            past_term_in_file_count += 1
                        
                        if should_include:
                            modified_row = [selected_client]  # Start with client in first position
                            # Add the rest of the PostgreSQL row data
                            modified_row.extend(pg_row)
                            # Use the file termination date if in file, otherwise PG date
                            final_term_date = file_term_date_for_match if found_in_file else ''
                            modified_row.append(final_term_date)
                            self.matched_results.append(modified_row)
                
                msg = f"Found {len(self.matched_results)} users who should not be billable.\n"
                msg += f"Billable Status: {billable_status}\n"
                msg += f"Client '{selected_client}' added to all records.\n\n"
                msg += f"Breakdown:\n"
                if not_in_file_count > 0:
                    msg += f"  • {not_in_file_count} not in file\n"
                if past_term_in_file_count > 0:
                    msg += f"  • {past_term_in_file_count} in file but have past term dates\n"
                if excluded_auto_term_count > 0:
                    msg += f"\nExcluded:\n"
                    msg += f"  • {excluded_auto_term_count} users with past term dates but future termed_in_cheif (auto-term scheduled)\n"
                msg += f"\n(File contained {len(file_names_with_dob) + len(file_names_without_dob)} unique names)"
            
            # Display results in tree
            status_label.config(text="Displaying results...")
            progress_bar['value'] = 100
            progress_text.config(text="100%")
            progress_window.update()
            
            self.tree.delete(*self.tree.get_children())
            
            self.tree['columns'] = self.postgres_headers
            self.tree['show'] = 'headings'
            
            # Reset sort state
            self.sort_reverse = {}
            
            for col in self.postgres_headers:
                self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
                self.tree.column(col, width=150, anchor=tk.W)
            
            # Store all results for filtering
            self.all_results = list(self.matched_results)
            
            for row in self.matched_results:
                self.tree.insert('', tk.END, values=row)
            
            # Close progress window
            progress_window.destroy()
            
            messagebox.showinfo("Match Complete", msg)
            
        except ValueError as e:
            progress_window.destroy()
            messagebox.showerror("Error", f"Column not found:\n{str(e)}")
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Error", f"Failed to match results:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileParserGUI(root)
    root.mainloop()