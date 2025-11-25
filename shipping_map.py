import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import os
from collections import Counter
import re

# US State abbreviations to full names
STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'Washington D.C.', 'PR': 'Puerto Rico', 'VI': 'Virgin Islands', 'GU': 'Guam',
    'AS': 'American Samoa', 'MP': 'Northern Mariana Islands'
}

# Zipcode to state mapping (first 3 digits)
ZIPCODE_TO_STATE = {
    range(350, 368): 'AL', range(995, 1000): 'AK', range(850, 866): 'AZ', range(716, 730): 'AR',
    range(900, 962): 'CA', range(800, 817): 'CO', range(60, 70): 'CT', range(197, 200): 'DE',
    range(320, 340): 'FL', range(300, 320): 'GA', range(340, 350): 'FL', range(967, 969): 'HI',
    range(832, 839): 'ID', range(600, 630): 'IL', range(460, 480): 'IN', range(500, 529): 'IA',
    range(660, 680): 'KS', range(400, 428): 'KY', range(700, 715): 'LA', range(39, 50): 'ME',
    range(206, 213): 'MD', range(10, 28): 'MA', range(480, 500): 'MI', range(550, 568): 'MN',
    range(386, 398): 'MS', range(630, 659): 'MO', range(590, 600): 'MT', range(680, 694): 'NE',
    range(889, 899): 'NV', range(30, 39): 'NH', range(70, 90): 'NJ', range(870, 885): 'NM',
    range(100, 150): 'NY', range(270, 290): 'NC', range(580, 589): 'ND', range(430, 459): 'OH',
    range(730, 750): 'OK', range(970, 980): 'OR', range(150, 197): 'PA', range(28, 30): 'RI',
    range(290, 300): 'SC', range(570, 578): 'SD', range(370, 386): 'TN', range(750, 800): 'TX',
    range(840, 848): 'UT', range(50, 60): 'VT', range(220, 247): 'VA', range(980, 995): 'WA',
    range(247, 270): 'WV', range(530, 550): 'WI', range(820, 832): 'WY', range(200, 206): 'DC',
    range(6, 10): 'PR', range(8, 9): 'VI', range(969, 970): 'GU'
}

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg_color='#ffffff', *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Store parent reference
        self.parent = parent
        
        # Create container
        container = tk.Frame(self, bg=bg_color)
        container.pack(fill="both", expand=True)
        
        # Canvas and scrollbars (using ttk.Scrollbar for modern look)
        self.canvas = tk.Canvas(container, highlightthickness=0, bg=bg_color)
        self.scrollbar_v = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        # Scrollable frame
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=self.scrollbar_v.set)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Pack components
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
            
            content_height = bbox[3] - bbox[1]
            canvas_height = self.canvas.winfo_height()
            
            if content_height > canvas_height:
                # Show scrollbar
                if not self.scrollbar_v.winfo_ismapped():
                    self.scrollbar_v.pack(side="right", fill="y")
                return True
            else:
                # Hide scrollbar
                self.scrollbar_v.pack_forget()
                return False
        except Exception as e:
            print(f"Error checking scroll: {e}")
            return False
        
    def _on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Check if scrollbar is needed after content changes
            self.canvas.after_idle(self.check_scroll_needed)
        except Exception:
            pass
        
    def _on_canvas_configure(self, event):
        """Reset the canvas window to match the width of the canvas"""
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
        # Check if scrollbar should be visible
        self.canvas.after_idle(self.check_scroll_needed)

class ZipcodeHeatmapTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Zipcode State Heatmap")
        self.root.geometry("1200x800")
        
        # Data storage
        self.file_data = []
        self.file_headers = []
        self.state_counts = {}
        
        # Check if running in HelloToolbelt
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        # Setup adaptive styling based on parent theme
        self.setup_adaptive_styling()
        
        # Fonts
        self.title_font = ('Segoe UI', 16, 'bold')
        self.subtitle_font = ('Segoe UI', 12, 'bold')
        self.label_font = ('Segoe UI', 10)
        self.text_font = ('Segoe UI', 9)
        self.button_font = ('Segoe UI', 10)
        
        # Setup the UI
        self.setup_ui()
    
    def setup_adaptive_styling(self):
        """Setup styling that adapts to HelloToolbelt theme (light/dark mode)"""
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
        
        # Adaptive color scheme based on detected theme
        if self.is_dark_mode:
            # Dark mode colors - inherit parent background
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.button_bg = "#a34ae2"
            self.button_fg = '#ffffff'
            self.text_color = parent_fg if parent_fg else '#ffffff'
            self.secondary_text_color = '#cccccc'
        else:
            # Light mode colors - inherit parent background
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.button_bg = '#0078d4'
            self.button_fg = '#ffffff'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.secondary_text_color = '#34495e'
    
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
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        if not self.is_in_toolbelt:
            # Only configure background if running standalone
            self.root.configure(bg=self.bg_color)
        
        # Main container with padding (non-scrollable)
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header (stays fixed at top)
        header_frame = tk.Frame(main_container, bg='#a34ae2' if not self.is_dark_mode else '#a34ae2', relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_content = tk.Frame(header_frame, bg='#a34ae2' if not self.is_dark_mode else '#a34ae2')
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        header_icon = tk.Label(header_content, text="🗺️", font=('Segoe UI', 20), 
                              bg='#a34ae2' if not self.is_dark_mode else '#a34ae2', fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_label = tk.Label(header_content, text="Zipcode State Heatmap", 
                               font=('Segoe UI', 16, 'bold'), 
                               bg='#a34ae2' if not self.is_dark_mode else '#a34ae2', fg='white')
        header_label.pack(side=tk.LEFT, anchor='w')
        
        # Create scrollable container for content (scrolls independently)
        self.scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color)
        self.scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        content_container = self.scrollable_container.scrollable_frame
        content_container.configure(bg=self.bg_color)
        
        # Step 1: Upload File
        self._create_upload_section(content_container)
        
        # Hidden sections
        self.heatmap_section = tk.Frame(content_container, bg=self.bg_color)
        self._create_heatmap_section()
        
        # Force scroll update after interface is built
        def update_scroll_after_build():
            try:
                if hasattr(self, 'scrollable_container'):
                    self.scrollable_container.force_scroll_update()
            except Exception:
                pass
        
        self.root.after(100, update_scroll_after_build)
        self.root.after(500, update_scroll_after_build)
    
    def _create_upload_section(self, parent):
        """Create file upload section"""
        upload_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        upload_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Header
        header = tk.Frame(upload_frame, bg=self.header_bg, height=40)
        header.pack(fill=tk.X)
        
        label = tk.Label(header, text="Step 1: Upload CSV or TXT File", 
                        font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        label.pack(pady=10)
        
        # Content
        content = tk.Frame(upload_frame, bg=self.frame_bg)
        content.pack(fill=tk.X, padx=20, pady=15)
        
        # Upload button
        upload_btn = tk.Button(content, text="📁 Select CSV or TXT File", 
                              command=self.load_file,
                              bg=self.button_bg, fg='#000000',
                              font=self.button_font, cursor='hand2',
                              padx=20, pady=10)
        upload_btn.pack(anchor='w')
        
        # File info label
        self.file_info_label = tk.Label(content, text="", font=self.label_font,
                                       bg=self.frame_bg, fg=self.text_color)
        self.file_info_label.pack(anchor='w', pady=(10, 0))
        
        # Column selection frame (hidden initially)
        self.column_selection_frame = tk.Frame(content, bg=self.frame_bg)
        
        # Zipcode column
        col_select_label = tk.Label(self.column_selection_frame, 
                                    text="Zipcode Column:", 
                                    font=self.label_font,
                                    bg=self.frame_bg, fg=self.text_color)
        col_select_label.pack(anchor='w', pady=(15, 5))
        
        self.zipcode_col_var = tk.StringVar()
        self.zipcode_combo = ttk.Combobox(self.column_selection_frame, 
                                         textvariable=self.zipcode_col_var,
                                         font=self.text_font, 
                                         state='readonly', 
                                         width=40)
        self.zipcode_combo.pack(anchor='w')
        self.zipcode_combo.bind('<<ComboboxSelected>>', self._on_column_change)
        
        # Date of Birth column
        dob_label = tk.Label(self.column_selection_frame, 
                            text="Date of Birth Column (Optional):", 
                            font=self.label_font,
                            bg=self.frame_bg, fg=self.text_color)
        dob_label.pack(anchor='w', pady=(10, 5))
        
        self.dob_col_var = tk.StringVar()
        self.dob_combo = ttk.Combobox(self.column_selection_frame, 
                                     textvariable=self.dob_col_var,
                                     font=self.text_font, 
                                     state='readonly', 
                                     width=40)
        self.dob_combo.pack(anchor='w')
        
        # Termination Date column
        term_label = tk.Label(self.column_selection_frame, 
                             text="Termination Date Column (Optional):", 
                             font=self.label_font,
                             bg=self.frame_bg, fg=self.text_color)
        term_label.pack(anchor='w', pady=(10, 5))
        
        self.term_col_var = tk.StringVar()
        self.term_combo = ttk.Combobox(self.column_selection_frame, 
                                      textvariable=self.term_col_var,
                                      font=self.text_font, 
                                      state='readonly', 
                                      width=40)
        self.term_combo.pack(anchor='w')
        
        # Info label for filtering
        filter_info = tk.Label(self.column_selection_frame,
                              text="ℹ️ Users under 18 and with past termination dates will be excluded",
                              font=('Segoe UI', 9, 'italic'),
                              bg=self.frame_bg, fg=self.secondary_text_color)
        filter_info.pack(anchor='w', pady=(10, 0))
        
        # Process button
        self.process_btn = tk.Button(self.column_selection_frame, 
                                     text="🔄 Process Zipcodes",
                                     command=self.process_selected_column,
                                     bg='#27ae60', fg='#000000',
                                     font=self.button_font, cursor='hand2',
                                     padx=15, pady=8)
        self.process_btn.pack(anchor='w', pady=(10, 0))
    
    def _create_heatmap_section(self):
        """Create heatmap visualization section"""
        heatmap_frame = tk.Frame(self.heatmap_section, bg=self.frame_bg, relief='solid', bd=1)
        heatmap_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Header
        header = tk.Frame(heatmap_frame, bg=self.header_bg, height=40)
        header.pack(fill=tk.X)
        
        label = tk.Label(header, text="Step 2: State Distribution Heatmap", 
                        font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        label.pack(pady=10)
        
        # Content - will be populated after file load
        self.heatmap_content = tk.Frame(heatmap_frame, bg=self.frame_bg)
        self.heatmap_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    def load_file(self):
        """Load CSV/TXT file and show column selection"""
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Detect delimiter
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                sample = f.read(8192)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample, delimiters=',\t|;')
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ','
            
            # Load file
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=delimiter)
                self.file_headers = next(reader)
                self.file_data = list(reader)
            
            # Update file info
            filename = os.path.basename(file_path)
            row_count = len(self.file_data)
            col_count = len(self.file_headers)
            
            delimiter_names = {',': 'Comma', '\t': 'Tab', '|': 'Pipe', ';': 'Semicolon'}
            delimiter_name = delimiter_names.get(delimiter, delimiter)
            
            self.file_info_label.config(
                text=f"✅ Loaded: {filename}\n"
                     f"Rows: {row_count:,} | Columns: {col_count} | Delimiter: {delimiter_name}"
            )
            
            # Populate column dropdown with indexed column names
            column_options = [f"{idx}: {header}" for idx, header in enumerate(self.file_headers)]
            self.zipcode_combo['values'] = column_options
            self.dob_combo['values'] = ['(None)'] + column_options
            self.term_combo['values'] = ['(None)'] + column_options
            
            # Auto-detect zipcode column and set as default
            zipcode_col_idx = self._auto_detect_zipcode_column()
            if zipcode_col_idx is not None:
                self.zipcode_col_var.set(column_options[zipcode_col_idx])
            elif column_options:
                self.zipcode_col_var.set(column_options[0])
            
            # Auto-detect DOB column
            dob_col_idx = self._auto_detect_dob_column()
            if dob_col_idx is not None:
                self.dob_col_var.set(column_options[dob_col_idx])
            else:
                self.dob_col_var.set('(None)')
            
            # Auto-detect Term Date column
            term_col_idx = self._auto_detect_term_column()
            if term_col_idx is not None:
                self.term_col_var.set(column_options[term_col_idx])
            else:
                self.term_col_var.set('(None)')
            
            # Show column selection frame
            self.column_selection_frame.pack(fill=tk.X, pady=(10, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
    
    def _on_column_change(self, event=None):
        """Handle column selection change"""
        pass  # Could add preview functionality here
    
    def process_selected_column(self):
        """Process zipcodes using the selected column"""
        if not self.file_data or not self.file_headers:
            messagebox.showerror("Error", "No file loaded!")
            return
        
        selected = self.zipcode_col_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a zipcode column!")
            return
        
        try:
            # Extract column indices from selections
            zipcode_col_idx = int(selected.split(':')[0])
            zipcode_col_name = self.file_headers[zipcode_col_idx]
            
            # Get optional DOB and Term Date columns
            dob_col_idx = None
            dob_col_name = None
            if self.dob_col_var.get() and self.dob_col_var.get() != '(None)':
                dob_col_idx = int(self.dob_col_var.get().split(':')[0])
                dob_col_name = self.file_headers[dob_col_idx]
            
            term_col_idx = None
            term_col_name = None
            if self.term_col_var.get() and self.term_col_var.get() != '(None)':
                term_col_idx = int(self.term_col_var.get().split(':')[0])
                term_col_name = self.file_headers[term_col_idx]
            
            # Process zipcodes with filtering
            self._process_zipcodes_with_filters(zipcode_col_idx, dob_col_idx, term_col_idx)
            
            if not self.state_counts:
                messagebox.showwarning("No Data", 
                                     "No valid users found after applying filters.\n\n"
                                     "All users may have been excluded due to:\n"
                                     "• Being under 18 years old\n"
                                     "• Having past termination dates\n"
                                     "• Invalid zipcodes")
                return
            
            # Update file info to show selected columns
            current_text = self.file_info_label.cget("text")
            info_lines = [current_text, f"Zipcode Column: '{zipcode_col_name}' (Column {zipcode_col_idx})"]
            
            if dob_col_name:
                info_lines.append(f"DOB Column: '{dob_col_name}' (Column {dob_col_idx})")
            if term_col_name:
                info_lines.append(f"Term Date Column: '{term_col_name}' (Column {term_col_idx})")
            
            # Add filtering stats if available
            if hasattr(self, 'filtering_stats'):
                stats = self.filtering_stats
                info_lines.append(f"\n📊 Filtering Results:")
                info_lines.append(f"  • Total Rows: {stats['total']:,}")
                info_lines.append(f"  • Included: {stats['included']:,}")
                if stats['excluded_age'] > 0:
                    info_lines.append(f"  • Excluded (Under 18): {stats['excluded_age']:,}")
                if stats['excluded_term'] > 0:
                    info_lines.append(f"  • Excluded (Past Term Date): {stats['excluded_term']:,}")
                if stats['excluded_invalid'] > 0:
                    info_lines.append(f"  • Excluded (Invalid Zipcode): {stats['excluded_invalid']:,}")
            
            self.file_info_label.config(text="\n".join(info_lines))
            
            # Show hidden sections
            self.heatmap_section.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
            
            # Generate visualizations
            self._generate_heatmap()
            
            messagebox.showinfo("Success", 
                              f"Successfully processed zipcodes!\n\n"
                              f"Found users in {len(self.state_counts)} states.\n"
                              f"Total valid users: {sum(self.state_counts.values()):,}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process zipcodes:\n{str(e)}")
    
    def _auto_detect_zipcode_column(self):
        """Auto-detect zipcode column by header name"""
        zipcode_keywords = ['zip', 'zipcode', 'postal', 'zip code', 'postal code', 'postcode']
        
        for idx, header in enumerate(self.file_headers):
            header_lower = header.lower().strip()
            if any(keyword in header_lower for keyword in zipcode_keywords):
                return idx
        
        return None
    
    def _auto_detect_dob_column(self):
        """Auto-detect date of birth column by header name"""
        dob_keywords = ['dob', 'date of birth', 'birth date', 'birthdate', 'birthday', 'date_of_birth']
        
        for idx, header in enumerate(self.file_headers):
            header_lower = header.lower().strip()
            if any(keyword in header_lower for keyword in dob_keywords):
                return idx
        
        return None
    
    def _auto_detect_term_column(self):
        """Auto-detect termination date column by header name"""
        term_keywords = ['term', 'termination', 'term date', 'termination date', 'end date', 
                        'termination_date', 'term_date', 'end_date']
        
        for idx, header in enumerate(self.file_headers):
            header_lower = header.lower().strip()
            if any(keyword in header_lower for keyword in term_keywords):
                return idx
        
        return None
    
    def _process_zipcodes_with_filters(self, zipcode_col_idx, dob_col_idx=None, term_col_idx=None):
        """Process zipcodes and count by state with age and term date filtering"""
        from datetime import datetime, date
        import dateutil.parser as date_parser
        
        self.state_counts = Counter()
        
        # Track filtering statistics
        total_count = 0
        included_count = 0
        excluded_age_count = 0
        excluded_term_count = 0
        excluded_invalid_count = 0
        
        today = date.today()
        
        for row in self.file_data:
            total_count += 1
            
            if len(row) <= zipcode_col_idx:
                excluded_invalid_count += 1
                continue
            
            # Check DOB filter (exclude under 18)
            if dob_col_idx is not None and len(row) > dob_col_idx:
                dob_str = row[dob_col_idx].strip()
                if dob_str:
                    try:
                        # Try to parse date
                        dob = self._parse_date(dob_str)
                        if dob:
                            # Calculate age
                            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                            if age < 18:
                                excluded_age_count += 1
                                continue
                    except:
                        pass  # If can't parse, don't exclude
            
            # Check Term Date filter (exclude past dates)
            if term_col_idx is not None and len(row) > term_col_idx:
                term_str = row[term_col_idx].strip()
                if term_str:
                    try:
                        # Try to parse date
                        term_date = self._parse_date(term_str)
                        if term_date:
                            # Exclude if termination date is in the past
                            if term_date < today:
                                excluded_term_count += 1
                                continue
                    except:
                        pass  # If can't parse, don't exclude
            
            # Process zipcode
            zipcode = self._clean_zipcode(row[zipcode_col_idx])
            if zipcode:
                state = self._zipcode_to_state(zipcode)
                if state:
                    self.state_counts[state] += 1
                    included_count += 1
                else:
                    excluded_invalid_count += 1
            else:
                excluded_invalid_count += 1
        
        # Store filtering stats
        self.filtering_stats = {
            'total': total_count,
            'included': included_count,
            'excluded_age': excluded_age_count,
            'excluded_term': excluded_term_count,
            'excluded_invalid': excluded_invalid_count
        }
    
    def _parse_date(self, date_str):
        """Parse date string in various formats"""
        if not date_str or not date_str.strip():
            return None
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%Y%m%d',
            '%m/%d/%y',
            '%d-%m-%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        
        # Try using dateutil parser as fallback
        try:
            import dateutil.parser as date_parser
            return date_parser.parse(date_str).date()
        except:
            pass
        
        return None
    
    def _process_zipcodes(self, zipcode_col_idx):
        """Process zipcodes and count by state"""
        self.state_counts = Counter()
        invalid_count = 0
        
        for row in self.file_data:
            if len(row) > zipcode_col_idx:
                zipcode = self._clean_zipcode(row[zipcode_col_idx])
                if zipcode:
                    state = self._zipcode_to_state(zipcode)
                    if state:
                        self.state_counts[state] += 1
                    else:
                        invalid_count += 1
        
        if invalid_count > 0:
            print(f"Note: {invalid_count} invalid or unrecognized zipcodes")
    
    def _clean_zipcode(self, zipcode):
        """Clean and extract 5-digit zipcode"""
        if not zipcode:
            return None
        
        # Remove any non-digit characters
        digits = re.sub(r'\D', '', str(zipcode))
        
        # Take first 5 digits
        if len(digits) >= 5:
            return digits[:5]
        
        return None
    
    def _zipcode_to_state(self, zipcode):
        """Convert 5-digit zipcode to state abbreviation"""
        if not zipcode or len(zipcode) != 5:
            return None
        
        try:
            zip_int = int(zipcode[:3])
            
            for zip_range, state in ZIPCODE_TO_STATE.items():
                if zip_int in zip_range:
                    return state
            
            return None
        except ValueError:
            return None
    
    def _generate_heatmap(self):
        """Generate visual heatmap of state distribution"""
        # Clear previous content
        for widget in self.heatmap_content.winfo_children():
            widget.destroy()
        
        if not self.state_counts:
            tk.Label(self.heatmap_content, text="No state data to display", 
                    font=self.label_font, bg=self.frame_bg).pack()
            return
        
        # Get max count for color scaling
        max_count = max(self.state_counts.values())
        total_count = sum(self.state_counts.values())
        
        # Summary
        summary_frame = tk.Frame(self.heatmap_content, bg=self.frame_bg)
        summary_frame.pack(fill=tk.X, pady=(0, 20))
        
        summary_text = f"Total Users: {total_count:,} | States Represented: {len(self.state_counts)}"
        tk.Label(summary_frame, text=summary_text, font=self.subtitle_font,
                bg=self.frame_bg, fg=self.text_color).pack()
        
        # Color legend
        legend_frame = tk.Frame(self.heatmap_content, bg=self.frame_bg)
        legend_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(legend_frame, text="Color Scale: ", font=self.label_font,
                bg=self.frame_bg, fg=self.text_color).pack(side=tk.LEFT, padx=(0, 10))
        
        legend_colors = [
            ('#f0f0f0', 'No Data'),
            ('#bbdefb', f'1-{int(max_count*0.2)}'),
            ('#64b5f6', f'{int(max_count*0.2)+1}-{int(max_count*0.4)}'),
            ('#2196f3', f'{int(max_count*0.4)+1}-{int(max_count*0.6)}'),
            ('#1976d2', f'{int(max_count*0.6)+1}-{int(max_count*0.8)}'),
            ('#0d47a1', f'{int(max_count*0.8)+1}+')
        ]
        
        for color, label in legend_colors:
            legend_box = tk.Frame(legend_frame, bg=color, width=40, height=20, 
                                relief='solid', bd=1)
            legend_box.pack(side=tk.LEFT, padx=2)
            tk.Label(legend_frame, text=label, font=('Segoe UI', 8),
                    bg=self.frame_bg, fg=self.text_color).pack(side=tk.LEFT, padx=(0, 10))
        
        # Copy button
        copy_btn = tk.Button(self.heatmap_content, text="📋 Copy to Clipboard",
                           command=self.copy_state_data,
                           bg='#27ae60', fg='#000000',
                           font=self.button_font, cursor='hand2',
                           padx=20, pady=10)
        copy_btn.pack(pady=(0, 15))
        
        # Create grid of all states with color coding
        grid_frame = tk.Frame(self.heatmap_content, bg=self.frame_bg)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sort all states alphabetically by state code
        all_states = sorted(STATE_NAMES.keys())
        
        # Create grid layout (8 columns for good display)
        cols = 8
        
        for idx, state in enumerate(all_states):
            row = idx // cols
            col = idx % cols
            
            count = self.state_counts.get(state, 0)
            
            # Determine color
            if count == 0:
                bg_color = '#404040' if self.is_dark_mode else '#f0f0f0'
                text_color = '#999999'
            else:
                bg_color = self._get_heatmap_color(count, max_count)
                text_color = '#ffffff' if count > max_count * 0.4 else '#000000'
            
            # Create cell frame
            cell_frame = tk.Frame(grid_frame, bg=bg_color, relief='solid', bd=1, 
                                 width=130, height=60)
            cell_frame.grid(row=row, column=col, padx=2, pady=2, sticky='nsew')
            cell_frame.grid_propagate(False)
            
            # State code
            state_label = tk.Label(cell_frame, text=state, 
                                  font=('Segoe UI', 11, 'bold'),
                                  bg=bg_color, fg=text_color)
            state_label.pack(pady=(5, 0))
            
            # Count
            count_text = f"{count:,}" if count > 0 else "0"
            count_label = tk.Label(cell_frame, text=count_text,
                                  font=('Segoe UI', 10),
                                  bg=bg_color, fg=text_color)
            count_label.pack()
            
            # Percentage (if count > 0)
            if count > 0:
                percentage = (count / total_count) * 100
                pct_label = tk.Label(cell_frame, text=f"({percentage:.1f}%)",
                                    font=('Segoe UI', 8),
                                    bg=bg_color, fg=text_color)
                pct_label.pack()
        
        # Configure grid to expand
        for i in range(cols):
            grid_frame.grid_columnconfigure(i, weight=1)
    
    def copy_state_data(self):
        """Copy state data to clipboard in a format suitable for Google Sheets"""
        if not self.state_counts:
            messagebox.showerror("Error", "No data to copy")
            return
        
        try:
            # Create tab-separated data for Google Sheets
            lines = []
            
            # Header
            lines.append("State Code\tState Name\tUser Count\tPercentage")
            
            # Data - sorted alphabetically by state code
            total_count = sum(self.state_counts.values())
            all_states = sorted(STATE_NAMES.keys())
            
            for state in all_states:
                count = self.state_counts.get(state, 0)
                state_name = STATE_NAMES[state]
                percentage = (count / total_count) * 100 if count > 0 else 0
                
                lines.append(f"{state}\t{state_name}\t{count}\t{percentage:.2f}%")
            
            # Copy to clipboard
            clipboard_text = "\n".join(lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(clipboard_text)
            self.root.update()
            
            messagebox.showinfo("Copied!", 
                              f"✅ Copied {len(all_states)} states to clipboard!\n\n"
                              "Paste into Google Sheets with Ctrl+V\n"
                              "You can then apply conditional formatting based on the User Count column.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy:\n{str(e)}")
    
    def _create_state_tooltip(self, canvas, item, state, count):
        """Create tooltip for state on hover"""
        def on_enter(event):
            # Get item coordinates
            coords = canvas.coords(item)
            x = (coords[0] + coords[2]) / 2
            y = coords[1] - 10
            
            # Create tooltip text
            state_name = STATE_NAMES.get(state, state)
            if count > 0:
                total = sum(self.state_counts.values())
                percentage = (count / total) * 100
                tooltip_text = f"{state_name}\n{count:,} users ({percentage:.1f}%)"
            else:
                tooltip_text = f"{state_name}\nNo data"
            
            # Create tooltip
            canvas.tooltip = canvas.create_text(x, y, 
                                              text=tooltip_text,
                                              font=('Segoe UI', 9, 'bold'),
                                              fill='#ffffff',
                                              tags='tooltip')
            
            # Get text bounding box
            bbox = canvas.bbox(canvas.tooltip)
            padding = 5
            
            # Create background rectangle
            canvas.tooltip_bg = canvas.create_rectangle(
                bbox[0] - padding, bbox[1] - padding,
                bbox[2] + padding, bbox[3] + padding,
                fill='#2c3e50', outline='#ffffff', width=2,
                tags='tooltip'
            )
            
            # Raise text above background
            canvas.tag_raise(canvas.tooltip)
        
        def on_leave(event):
            # Remove tooltip
            canvas.delete('tooltip')
        
        canvas.tag_bind(item, '<Enter>', on_enter)
        canvas.tag_bind(item, '<Leave>', on_leave)
    
    def _get_heatmap_color(self, count, max_count):
        """Get color based on count (gradient from light to dark blue)"""
        if max_count == 0:
            return '#e3f2fd'
        
        ratio = count / max_count
        
        if ratio >= 0.8:
            return '#0d47a1'  # Dark blue
        elif ratio >= 0.6:
            return '#1976d2'  # Medium-dark blue
        elif ratio >= 0.4:
            return '#2196f3'  # Medium blue
        elif ratio >= 0.2:
            return '#64b5f6'  # Light-medium blue
        else:
            return '#bbdefb'  # Light blue
    
    def export_results(self):
        """Export state statistics to CSV"""
        if not self.state_counts:
            messagebox.showerror("Error", "No data to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="state_distribution.csv"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['State Code', 'State Name', 'User Count', 'Percentage'])
                
                # Write data
                total_count = sum(self.state_counts.values())
                sorted_states = sorted(self.state_counts.items(), key=lambda x: x[1], reverse=True)
                
                for state, count in sorted_states:
                    percentage = (count / total_count) * 100
                    writer.writerow([
                        state,
                        STATE_NAMES.get(state, state),
                        count,
                        f"{percentage:.2f}%"
                    ])
            
            messagebox.showinfo("Export Complete", 
                              f"✅ Exported state statistics to:\n{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ZipcodeHeatmapTool(root)
    root.mainloop()