import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import csv
import os
import sys
from datetime import datetime
import re
from dateutil import parser as date_parser
import json
from pathlib import Path



# --- Added from Cron_tool.py: ScrollableFrame for modern scrolling layout ---
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
        
    def _on_frame_configure(self, event=None):
        """Update scroll region when frame size changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.check_scroll_needed()
        
    def _on_canvas_configure(self, event):
        """Update the width of the window frame when canvas is resized"""
        # Update the width of the scrollable_frame to match canvas width
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
# --- End of ScrollableFrame code ---

class FileUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HEDIS Report Builder")
        self.root.geometry("900x800")
        
        # Check if this is running in HelloToolbelt (MockRoot) or standalone
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        # Use adaptive styling to match Base64_Tool.py
        self.setup_adaptive_styling()
        
        self.root.configure(bg=self.bg_color)
        
        # File state
        self.current_file_path = None
        self.current_file_type = None
        self.current_encoding = 'utf-8'  # Default encoding
        self.current_delimiter = ','  # Default delimiter
        self.column_headers = []
        self.current_headers = []
        
        # Setup user data directory for saving files
        self.user_data_dir = self.get_user_data_dir()
        
        # Presets management - save to user data directory
        self.presets_file = os.path.join(self.user_data_dir, "hedis_presets.json")
        self.settings_file = os.path.join(self.user_data_dir, "hedis_settings.json")
        self.presets = self.load_presets()
        
        # Create the main UI
        self.create_widgets()
        
        # Load saved settings
        self.load_settings()
    
    def get_user_data_dir(self):
        """Get the user data directory for saving config files"""
        # Determine the appropriate directory based on OS
        if sys.platform == 'win32':
            # Windows: Use AppData\Local
            base_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'HEDIS')
        elif sys.platform == 'darwin':
            # macOS: Use ~/Library/Application Support
            base_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'HEDIS')
        else:
            # Linux: Use ~/.config
            base_dir = os.path.join(os.path.expanduser('~'), '.config', 'hedis')
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create user data directory: {e}")
            # Fallback to current directory
            base_dir = os.path.expanduser('~')
        
        return base_dir
    
    def setup_adaptive_styling(self):
        """Setup styling that adapts to system theme (light/dark mode) - matching Base64_Tool"""
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
            if parent_bg.startswith('#'):
                r = int(parent_bg[1:3], 16)
                g = int(parent_bg[3:5], 16)
                b = int(parent_bg[5:7], 16)
            else:
                # Handle system color names by getting their RGB values
                rgb = self.root.winfo_rgb(parent_bg)
                r = rgb[0] // 256
                g = rgb[1] // 256
                b = rgb[2] // 256
            
            # Calculate brightness (perceived luminance)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            self.is_dark_mode = brightness < 128
        except:
            # Fallback to light mode if color parsing fails
            self.is_dark_mode = False
        
        # Fonts and sizes - consistent with Base64_Tool
        self.title_font = ("Segoe UI", 14, "bold")
        self.subtitle_font = ("Segoe UI", 11, "bold")
        self.heading_font = ("Segoe UI", 11, "bold")
        self.body_font = ("Segoe UI", 10)
        self.label_font = ("Segoe UI", 10)
        self.text_font = ("Segoe UI", 10)
        self.small_font = ("Segoe UI", 9)
        
        self.button_padx = 8
        self.button_pady = 4
        self.frame_padx = 20
        self.frame_pady = 15
        
        # Adaptive color scheme based on detected theme - matching Base64_Tool
        if self.is_dark_mode:
            # Dark mode colors - inherit parent background for transparency
            self.bg_color = parent_bg  # Use parent's background directly
            self.card_color = '#3c3c3c'
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.primary_color = '#df9621'
            self.primary_hover = '#357ab8'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.text_color = parent_fg if parent_fg else '#ffffff'
            self.secondary_color = '#cccccc'
            self.text_secondary = '#cccccc'
            self.border_color = '#555555'
            # Button text colors - black for both modes
            self.button_text_color = '#000000'
            self.button_hover_text_color = '#000000'
        else:
            # Light mode colors - inherit parent background for transparency  
            self.bg_color = parent_bg  # Use parent's background directly
            self.card_color = '#f8f9fa'
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.primary_color = '#df9621'
            self.primary_hover = '#2980b9'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.secondary_color = '#7f8c8d'
            self.text_secondary = '#7f8c8d'
            self.border_color = '#e2e8f0'
            # Button text colors - black for both modes
            self.button_text_color = '#000000'
            self.button_hover_text_color = '#000000'

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
        self.create_widgets()
    
    def create_widgets(self):
        """Create the main UI components with improved styling"""
        
        # Main container with padding
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header with primary color background (matching multi-file search tool)
        header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_content = tk.Frame(header_frame, bg=self.primary_color)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        header_icon = tk.Label(header_content, text="📄", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_label = tk.Label(header_content, text="HEDIS Report Builder", 
                               font=('Segoe UI', 16, 'bold'), bg=self.primary_color, fg='white')
        header_label.pack(side=tk.LEFT, anchor='w')
        
        # Create scrollable frame for all content
        scroll_frame = ScrollableFrame(main_container, bg_color=self.bg_color)
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        content_frame = scroll_frame.scrollable_frame
        
        # Presets Section
        self.create_card_section(content_frame, "Configuration Presets", self.create_presets_section)
        
        # File Upload Section (Card style)
        self.create_card_section(content_frame, "File Upload", self.create_upload_section)
        
        # Output Options Section
        self.create_card_section(content_frame, "Output Options", self.create_output_section)
        
        # Date Conversion Section
        self.create_card_section(content_frame, "Date Conversion", self.create_date_section)
        
        # Preview Section
        self.create_card_section(content_frame, "File Preview", self.create_preview_section)
        
        # Action Buttons
        self.create_action_buttons(content_frame)
    
    def create_card_section(self, parent, title, content_creator):
        """Create a card-style section with title and content"""
        # Card container
        card = tk.Frame(parent, bg=self.card_color, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.X, pady=(0, 16))
        
        # Add subtle shadow effect with border
        card.configure(highlightbackground=self.border_color, highlightthickness=1)
        
        # Card content with padding
        card_content = tk.Frame(card, bg=self.card_color)
        card_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        
        # Section title
        title_label = tk.Label(
            card_content,
            text=title,
            font=self.heading_font,
            bg=self.card_color,
            fg=self.text_color
        )
        title_label.pack(anchor='w', pady=(0, 12))
        
        # Create content
        content_creator(card_content)
    
    def create_presets_section(self, parent):
        """Create the presets management section"""
        
        # Preset selection row
        preset_row = tk.Frame(parent, bg=self.card_color)
        preset_row.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(
            preset_row,
            text="Select Preset:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 12))
        
        self.preset_var = tk.StringVar(value="Slot 1: Empty")
        self.preset_dropdown = ttk.Combobox(
            preset_row,
            textvariable=self.preset_var,
            values=self.get_preset_dropdown_values(),
            state="readonly",
            width=30,
            font=self.body_font
        )
        self.preset_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.preset_dropdown.bind('<<ComboboxSelected>>', self.on_preset_selected)
        
        # Buttons row
        buttons_row = tk.Frame(parent, bg=self.card_color)
        buttons_row.pack(fill=tk.X)
        
        # Load button
        load_btn = tk.Button(
            buttons_row,
            text="Load",
            command=self.load_selected_preset,
            font=self.body_font,
            bg='#f97316',
            fg=self.button_text_color,
            activebackground='#ea580c',
            activeforeground=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=16,
            pady=8
        )
        load_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Save button
        save_btn = tk.Button(
            buttons_row,
            text="Save",
            command=self.save_selected_preset,
            font=self.body_font,
            bg=self.primary_color,
            fg=self.button_text_color,
            activebackground=self.primary_hover,
            activeforeground=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=16,
            pady=8
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Rename button
        rename_btn = tk.Button(
            buttons_row,
            text="Rename",
            command=self.rename_selected_preset,
            font=self.body_font,
            bg='#8b5cf6',
            fg=self.button_text_color,
            activebackground='#7c3aed',
            activeforeground=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=16,
            pady=8
        )
        rename_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Clear button
        clear_btn = tk.Button(
            buttons_row,
            text="Clear",
            command=self.clear_selected_preset,
            font=self.body_font,
            bg='#dc2626',
            fg=self.button_text_color,
            activebackground='#b91c1c',
            activeforeground=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=16,
            pady=8
        )
        clear_btn.pack(side=tk.LEFT)
    
    def create_upload_section(self, parent):
        """Create the file upload section"""
        self.upload_button = tk.Button(
            parent,
            text="Choose File",
            command=self.upload_file,
            font=self.body_font,
            bg=self.primary_color,
            fg=self.button_text_color,
            activebackground=self.primary_hover,
            activeforeground=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        self.upload_button.pack(anchor='w', pady=(0, 8))
        
        # File info display
        self.file_label = tk.Label(
            parent,
            text="No file selected",
            font=self.small_font,
            bg=self.card_color,
            fg=self.secondary_color,
            anchor='w'
        )
        self.file_label.pack(fill=tk.X)
    
    def create_output_section(self, parent):
        """Create the output options section"""
        
        # Output Type
        type_frame = tk.Frame(parent, bg=self.card_color)
        type_frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(
            type_frame,
            text="Output Format:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 12))
        
        self.output_type_var = tk.StringVar(value=".csv")
        
        radio_frame = tk.Frame(type_frame, bg=self.card_color)
        radio_frame.pack(side=tk.LEFT)
        
        for text, value in [("CSV", ".csv"), ("TXT", ".txt")]:
            tk.Radiobutton(
                radio_frame,
                text=text,
                variable=self.output_type_var,
                value=value,
                font=self.body_font,
                bg=self.card_color,
                fg=self.text_color,
                selectcolor=self.card_color,
                activebackground=self.card_color,
                cursor='hand2'
            ).pack(side=tk.LEFT, padx=(0, 16))
        
        # Filename
        filename_frame = tk.Frame(parent, bg=self.card_color)
        filename_frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(
            filename_frame,
            text="Output Filename:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(anchor='w', pady=(0, 4))
        
        self.filename_var = tk.StringVar()
        filename_entry = tk.Entry(
            filename_frame,
            textvariable=self.filename_var,
            font=self.body_font,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightbackground=self.border_color,
            highlightcolor=self.primary_color
        )
        filename_entry.pack(fill=tk.X, ipady=6)
        
        # Delimiter
        delimiter_frame = tk.Frame(parent, bg=self.card_color)
        delimiter_frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(
            delimiter_frame,
            text="Delimiter:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 12))
        
        self.delimiter_var = tk.StringVar(value="Comma")
        
        delim_options = tk.Frame(delimiter_frame, bg=self.card_color)
        delim_options.pack(side=tk.LEFT)
        
        for text in ["Comma", "Tab", "Pipe"]:
            tk.Radiobutton(
                delim_options,
                text=text,
                variable=self.delimiter_var,
                value=text,
                font=self.body_font,
                bg=self.card_color,
                fg=self.text_color,
                selectcolor=self.card_color,
                activebackground=self.card_color,
                cursor='hand2'
            ).pack(side=tk.LEFT, padx=(0, 16))
        
        # Quote Style
        quote_frame = tk.Frame(parent, bg=self.card_color)
        quote_frame.pack(fill=tk.X)
        
        tk.Label(
            quote_frame,
            text="Quote Style:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 12))
        
        self.quote_var = tk.StringVar(value="No Quotes")
        
        quote_options = tk.Frame(quote_frame, bg=self.card_color)
        quote_options.pack(side=tk.LEFT)
        
        for text in ["No Quotes", "Add Quotes"]:
            tk.Radiobutton(
                quote_options,
                text=text,
                variable=self.quote_var,
                value=text,
                font=self.body_font,
                bg=self.card_color,
                fg=self.text_color,
                selectcolor=self.card_color,
                activebackground=self.card_color,
                cursor='hand2'
            ).pack(side=tk.LEFT, padx=(0, 16))
    
    def create_date_section(self, parent):
        """Create the date conversion section"""
        
        # DOB Column selector
        dob_row = tk.Frame(parent, bg=self.card_color)
        dob_row.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            dob_row,
            text="DOB Column:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 12))
        
        self.dob_var = tk.StringVar(value="Not detected")
        self.dob_dropdown = ttk.Combobox(
            dob_row,
            textvariable=self.dob_var,
            values=["Not detected"],
            state="readonly",
            font=self.body_font,
            width=30
        )
        self.dob_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # DOB status label
        self.dob_status_label = tk.Label(
            dob_row,
            text="",
            font=self.small_font,
            bg=self.card_color,
            fg=self.success_color
        )
        self.dob_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Convert dates checkbox and format options
        convert_row = tk.Frame(parent, bg=self.card_color)
        convert_row.pack(fill=tk.X, pady=(0, 12))
        
        self.convert_date_var = tk.BooleanVar(value=True)  # Enabled by default
        convert_check = tk.Checkbutton(
            convert_row,
            text="Enable conversion",
            variable=self.convert_date_var,
            command=self.toggle_date_format_options,
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color,
            selectcolor=self.card_color,
            activebackground=self.card_color,
            cursor='hand2'
        )
        convert_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Date format conversion options
        self.date_format_frame = tk.Frame(convert_row, bg=self.card_color)
        self.date_format_frame.pack(side=tk.LEFT)
        
        tk.Label(
            self.date_format_frame,
            text="From:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.from_format_var = tk.StringVar(value="MM/DD/YYYY")
        self.from_format_dropdown = ttk.Combobox(
            self.date_format_frame,
            textvariable=self.from_format_var,
            values=["MM/DD/YYYY", "MM/DD/YY", "DD/MM/YYYY", "DD/MM/YY", "YYYY-MM-DD", "YY-MM-DD", "ISO 8601 (with time)", "Auto-detect"],
            state="disabled",
            width=18,
            font=self.body_font
        )
        self.from_format_dropdown.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            self.date_format_frame,
            text="To:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        self.to_format_var = tk.StringVar(value="MM/DD/YYYY")
        self.to_format_dropdown = ttk.Combobox(
            self.date_format_frame,
            textvariable=self.to_format_var,
            values=["MM/DD/YYYY", "MM/DD/YY", "DD/MM/YYYY", "DD/MM/YY", "YYYY-MM-DD", "YY-MM-DD", "YYYYMMDD", "YYMMDD"],
            state="disabled",
            width=13,
            font=self.body_font
        )
        self.to_format_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Second date column (optional)
        date2_row = tk.Frame(parent, bg=self.card_color)
        date2_row.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            date2_row,
            text="Date Column 2:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 12))
        
        self.date2_var = tk.StringVar(value="None")
        self.date2_dropdown = ttk.Combobox(
            date2_row,
            textvariable=self.date2_var,
            values=["None"],
            state="readonly",
            font=self.body_font,
            width=30
        )
        self.date2_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.date2_dropdown.bind('<<ComboboxSelected>>', self.on_date2_selected)
        
        # Convert dates checkbox for date column 2
        convert2_row = tk.Frame(parent, bg=self.card_color)
        convert2_row.pack(fill=tk.X, pady=(0, 12))
        
        self.convert_date2_var = tk.BooleanVar(value=True)  # Enabled by default
        convert2_check = tk.Checkbutton(
            convert2_row,
            text="Enable conversion",
            variable=self.convert_date2_var,
            command=self.toggle_date2_format_options,
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color,
            selectcolor=self.card_color,
            activebackground=self.card_color,
            cursor='hand2'
        )
        convert2_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Date2 format options
        date2_format_row = tk.Frame(parent, bg=self.card_color)
        date2_format_row.pack(fill=tk.X)
        
        # Spacer to align with checkbox above
        spacer = tk.Label(date2_format_row, text="", width=17, bg=self.card_color)
        spacer.pack(side=tk.LEFT)
        
        self.date2_format_frame = tk.Frame(date2_format_row, bg=self.card_color)
        self.date2_format_frame.pack(side=tk.LEFT)
        
        tk.Label(
            self.date2_format_frame,
            text="From:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.from_format2_var = tk.StringVar(value="MM/DD/YYYY")
        self.from_format2_dropdown = ttk.Combobox(
            self.date2_format_frame,
            textvariable=self.from_format2_var,
            values=["MM/DD/YYYY", "MM/DD/YY", "DD/MM/YYYY", "DD/MM/YY", "YYYY-MM-DD", "YY-MM-DD", "ISO 8601 (with time)", "Auto-detect"],
            state="disabled",
            width=18,
            font=self.body_font
        )
        self.from_format2_dropdown.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            self.date2_format_frame,
            text="To:",
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        self.to_format2_var = tk.StringVar(value="MM/DD/YYYY")
        self.to_format2_dropdown = ttk.Combobox(
            self.date2_format_frame,
            textvariable=self.to_format2_var,
            values=["MM/DD/YYYY", "MM/DD/YY", "DD/MM/YYYY", "DD/MM/YY", "YYYY-MM-DD", "YY-MM-DD", "YYYYMMDD", "YYMMDD"],
            state="disabled",
            width=13,
            font=self.body_font
        )
        self.to_format2_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Initially disable format options
        self.toggle_date_format_options()
        self.toggle_date2_format_options()
    
    def create_preview_section(self, parent):
        """Create the file preview section"""
        
        # Preview text widget with custom styling
        preview_container = tk.Frame(parent, bg=self.card_color)
        preview_container.pack(fill=tk.BOTH, expand=True)
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_container,
            wrap=tk.NONE,
            font=('Consolas', 9),
            bg='#fafbfc',
            fg=self.text_color,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=0,
            padx=8,
            pady=8
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.preview_text.insert(tk.END, "Upload a file to see preview...")
        self.preview_text.config(state=tk.DISABLED)
    
    def create_action_buttons(self, parent):
        """Create the action buttons section"""
        
        button_container = tk.Frame(parent, bg=self.bg_color)
        button_container.pack(fill=tk.X, pady=(16, 0))
        
        # Convert button
        self.convert_button = tk.Button(
            button_container,
            text="Convert File",
            command=self.convert_file,
            font=self.heading_font,
            bg=self.success_color,
            fg=self.button_text_color,
            activebackground='#059669',
            activeforeground=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=32,
            pady=12
        )
        self.convert_button.pack(side=tk.LEFT, padx=(0, 12))
        
        # Reset button
        reset_button = tk.Button(
            button_container,
            text="Reset",
            command=self.reset_app,
            font=self.body_font,
            bg=self.card_color,
            fg=self.text_color,
            activebackground=self.border_color,
            activeforeground=self.text_color,
            cursor='hand2',
            relief=tk.SOLID,
            bd=1,
            padx=24,
            pady=10
        )
        reset_button.pack(side=tk.LEFT)
    
    def upload_file(self):
        """Handle file upload with improved feedback"""
        file_path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.current_file_path = file_path
            _, file_extension = os.path.splitext(file_path)
            self.current_file_type = file_extension.lower()
            
            # Detect encoding
            self.current_encoding = self.detect_file_encoding(file_path)
            
            # Detect delimiter
            self.current_delimiter = self.detect_delimiter(file_path, self.current_encoding)
            
            # Map delimiter to display name
            delimiter_display = {
                ',': 'Comma',
                '\t': 'Tab',
                '|': 'Pipe',
                ';': 'Semicolon'
            }.get(self.current_delimiter, 'Unknown')
            
            # Update file label with better formatting
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            size_str = self.format_file_size(file_size)
            
            self.file_label.config(
                text=f"{filename} ({size_str}) [{self.current_encoding}, {delimiter_display}]",
                fg=self.success_color
            )
            
            # Load and preview file
            self.load_file_preview()
            self.populate_column_dropdowns()
    
    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def detect_file_encoding(self, file_path):
        """Detect the encoding of a file"""
        try:
            # Try common encodings first for speed
            encodings_to_try = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
            
            for encoding in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1024)  # Try to read first 1KB
                    return encoding
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            # If common encodings fail, use chardet if available
            try:
                import chardet
                with open(file_path, 'rb') as f:
                    raw_data = f.read(10000)  # Read first 10KB for detection
                result = chardet.detect(raw_data)
                detected_encoding = result['encoding']
                if detected_encoding:
                    return detected_encoding
            except ImportError:
                pass  # chardet not available
            
            # Fallback to utf-8 with error handling
            return 'utf-8'
            
        except Exception as e:
            print(f"Error detecting encoding: {e}")
            return 'utf-8'
    
    def detect_delimiter(self, file_path, encoding='utf-8'):
        """Detect the delimiter used in a CSV/TXT file"""
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                # Read first few lines for better detection
                sample = ''.join([f.readline() for _ in range(min(5, 10))])
                
            # Try to use csv.Sniffer
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters='\t,|;')
                return dialect.delimiter
            except:
                pass
            
            # Fallback: count occurrences of each delimiter in the sample
            delimiters = ['\t', ',', '|', ';']
            delimiter_counts = {delim: sample.count(delim) for delim in delimiters}
            
            # Get delimiter with highest count (must appear at least once)
            max_delim = max(delimiter_counts.items(), key=lambda x: x[1])
            if max_delim[1] > 0:
                return max_delim[0]
            
            # Default to comma if nothing found
            return ','
            
        except Exception as e:
            print(f"Error detecting delimiter: {e}")
            return ','
    
    def load_file_preview(self):
        """Load and display file preview with better formatting"""
        if not self.current_file_path:
            return
        
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        
        try:
            encoding = getattr(self, 'current_encoding', 'utf-8')
            with open(self.current_file_path, 'r', encoding=encoding, errors='replace') as file:
                # Read first 50 lines for preview
                lines = [next(file) for _ in range(50)]
                preview_content = ''.join(lines)
                
                self.preview_text.insert(tk.END, preview_content)
                
                # Check if there are more lines
                try:
                    next(file)
                    self.preview_text.insert(tk.END, "\n\n[Preview limited to first 50 lines...]")
                except StopIteration:
                    pass
        except Exception as e:
            self.preview_text.insert(tk.END, f"Error loading preview:\n{str(e)}")
        
        self.preview_text.config(state=tk.DISABLED)
    
    def populate_column_dropdowns(self):
        """Populate dropdown menus with column headers"""
        if not self.current_file_path:
            return
        
        try:
            encoding = getattr(self, 'current_encoding', 'utf-8')
            detected_delimiter = getattr(self, 'current_delimiter', ',')
            
            if self.current_file_type == '.csv':
                with open(self.current_file_path, 'r', encoding=encoding, newline='', errors='replace') as file:
                    reader = csv.reader(file, delimiter=detected_delimiter)
                    self.column_headers = next(reader, [])
            elif self.current_file_type == '.txt':
                with open(self.current_file_path, 'r', encoding=encoding, errors='replace') as file:
                    first_line = file.readline().strip()
                    # Use detected delimiter or try to detect
                    if detected_delimiter in first_line:
                        self.column_headers = [col.strip() for col in first_line.split(detected_delimiter)]
                    else:
                        # Try to detect delimiter
                        for delimiter in ['\t', ',', '|', ';']:
                            if delimiter in first_line:
                                self.column_headers = [col.strip() for col in first_line.split(delimiter)]
                                break
                        else:
                            self.column_headers = ["[No columns detected]"]
            
            # Store headers for preset config validation
            self.current_headers = self.column_headers
            
            # Update dropdowns
            if self.column_headers:
                self.dob_dropdown['values'] = ["Not detected"] + self.column_headers
                self.date2_dropdown['values'] = ["None"] + self.column_headers
                
                # Auto-select DOB column if it exists
                dob_detected = False
                for col in self.column_headers:
                    if 'dob' in col.lower() or 'birth' in col.lower() or 'date of birth' in col.lower():
                        self.dob_var.set(col)
                        self.dob_status_label.config(text="Auto-detected", fg=self.success_color)
                        dob_detected = True
                        break
                
                if not dob_detected:
                    self.dob_var.set("Not detected")
                    self.dob_status_label.config(text="", fg=self.secondary_color)
        
        except Exception as e:
            print(f"Error populating columns: {e}")
    
    def toggle_date_format_options(self):
        """Enable or disable date conversion format options"""
        if self.convert_date_var.get():
            self.from_format_dropdown.config(state='readonly')
            self.to_format_dropdown.config(state='readonly')
        else:
            self.from_format_dropdown.config(state='disabled')
            self.to_format_dropdown.config(state='disabled')
    
    def toggle_date2_format_options(self):
        """Enable or disable date2 conversion format options"""
        if self.convert_date2_var.get():
            self.from_format2_dropdown.config(state='readonly')
            self.to_format2_dropdown.config(state='readonly')
        else:
            self.from_format2_dropdown.config(state='disabled')
            self.to_format2_dropdown.config(state='disabled')
    
    def on_date2_selected(self, event=None):
        """Handle second date column selection"""
        if self.date2_var.get() != "None" and self.date2_var.get() and self.convert_date2_var.get():
            self.from_format2_dropdown.config(state='readonly')
            self.to_format2_dropdown.config(state='readonly')
        else:
            self.from_format2_dropdown.config(state='disabled')
            self.to_format2_dropdown.config(state='disabled')
    
    def get_delimiter(self):
        """Get the selected delimiter character"""
        delimiter_map = {
            "Comma": ",",
            "Tab": "\t",
            "Pipe": "|"
        }
        return delimiter_map.get(self.delimiter_var.get(), ",")
    
    def get_selected_dob_column(self):
        """Get the selected DOB column name"""
        dob = self.dob_var.get()
        return dob if dob and dob != "Not detected" else None
    
    def get_selected_date2_column(self):
        """Get the selected additional date column name"""
        date2 = self.date2_var.get()
        return date2 if date2 and date2 != "None" else None
    
    def convert_dates_in_row(self, row, headers, dob_column, date2_column=None):
        """Convert date formats in a row of data"""
        if not headers:
            return row
        
        # Return early only if NEITHER column is set OR neither checkbox is enabled
        if (not dob_column or not self.convert_date_var.get()) and (not date2_column or not self.convert_date2_var.get()):
            return row
        
        try:
            # Find the index of the DOB column
            dob_index = headers.index(dob_column) if dob_column and dob_column in headers else -1
            date2_index = headers.index(date2_column) if date2_column and date2_column in headers else -1
            
            # Convert DOB if found AND checkbox enabled (with age validation)
            if dob_index != -1 and dob_index < len(row) and self.convert_date_var.get():
                from_format = self.from_format_var.get()
                to_format = self.to_format_var.get()
                original_value = row[dob_index]
                row[dob_index] = self.convert_date_format(row[dob_index], from_format, to_format, is_dob=True)
                # Debug output
                if original_value != row[dob_index]:
                    print(f"DOB converted: '{original_value}' -> '{row[dob_index]}'")
            
            # Convert additional date column if found AND checkbox enabled (without age validation)
            if date2_index != -1 and date2_index < len(row) and self.convert_date2_var.get():
                from_format2 = self.from_format2_var.get()
                to_format2 = self.to_format2_var.get()
                original_value = row[date2_index]
                row[date2_index] = self.convert_date_format(row[date2_index], from_format2, to_format2, is_dob=False)
                # Debug output
                if original_value != row[date2_index]:
                    print(f"Date2 converted: '{original_value}' -> '{row[date2_index]}'")
        
        except Exception as e:
            print(f"Error converting dates in row: {e}")
        
        return row
    
    def convert_date_format(self, date_str, from_format, to_format, is_dob=False):
        """Convert date string from one format to another"""
        if not date_str or not date_str.strip():
            return date_str
        
        date_str = date_str.strip()
        
        try:
            # Parse the date based on from_format
            if from_format == "Auto-detect" or from_format == "ISO 8601 (with time)":
                # Use dateutil for flexible parsing
                parsed_date = date_parser.parse(date_str, fuzzy=True)
            else:
                # Map format strings to strptime format codes
                format_map = {
                    "MM/DD/YYYY": "%m/%d/%Y",
                    "MM/DD/YY": "%m/%d/%y",
                    "DD/MM/YYYY": "%d/%m/%Y",
                    "DD/MM/YY": "%d/%m/%y",
                    "YYYY-MM-DD": "%Y-%m-%d",
                    "YY-MM-DD": "%y-%m-%d",
                    "YYYYMMDD": "%Y%m%d",
                    "YYMMDD": "%y%m%d"
                }
                
                strptime_format = format_map.get(from_format)
                if strptime_format:
                    try:
                        parsed_date = datetime.strptime(date_str, strptime_format)
                    except ValueError:
                        # If strict parsing fails, try auto-detect
                        parsed_date = date_parser.parse(date_str, fuzzy=True)
                else:
                    # Fallback to auto-detect
                    parsed_date = date_parser.parse(date_str, fuzzy=True)
            
            # If this is a DOB column, check if the date results in someone under 18
            if is_dob:
                today = datetime.now()
                age_years = (today - parsed_date).days / 365.25
                
                # If the person would be under 18, assume century was wrong
                # This handles cases like "50" being parsed as "2050" instead of "1950"
                if age_years < 18:
                    # Subtract 100 years
                    parsed_date = parsed_date.replace(year=parsed_date.year - 100)
                    
                    # Double-check: if still in the future or under 18, try subtracting another 100
                    age_years = (today - parsed_date).days / 365.25
                    if age_years < 18:
                        parsed_date = parsed_date.replace(year=parsed_date.year - 100)
            
            # Format the date based on to_format
            output_format_map = {
                "MM/DD/YYYY": "%m/%d/%Y",
                "MM/DD/YY": "%m/%d/%y",
                "DD/MM/YYYY": "%d/%m/%Y",
                "DD/MM/YY": "%d/%m/%y",
                "YYYY-MM-DD": "%Y-%m-%d",
                "YY-MM-DD": "%y-%m-%d",
                "YYYYMMDD": "%Y%m%d",
                "YYMMDD": "%y%m%d"
            }
            
            strftime_format = output_format_map.get(to_format, "%Y%m%d")
            converted = parsed_date.strftime(strftime_format)
            
            return converted
            
        except Exception as e:
            # If parsing fails, return original
            print(f"Error converting date '{date_str}' from '{from_format}' to '{to_format}': {e}")
            return date_str
    
    # ============ PRESET MANAGEMENT METHODS ============
    
    def load_presets(self):
        """Load presets from file"""
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_presets(self):
        """Save presets to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.presets, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save presets:\n{e}")
    
    def get_preset_dropdown_values(self):
        """Get list of preset names for dropdown"""
        values = []
        for i in range(1, 21):
            slot_name = f"slot_{i}"
            if slot_name in self.presets:
                preset_name = self.presets[slot_name].get("name", f"Slot {i}")
                values.append(f"Slot {i}: {preset_name}")
            else:
                values.append(f"Slot {i}: Empty")
        return values
    
    def update_preset_dropdown(self):
        """Update the preset dropdown values"""
        self.preset_dropdown['values'] = self.get_preset_dropdown_values()
    
    def get_selected_slot_number(self):
        """Extract slot number from the selected dropdown value"""
        selected = self.preset_var.get()
        # Extract number from "Slot X: ..." format
        if selected.startswith("Slot "):
            return int(selected.split(":")[0].replace("Slot ", ""))
        return 1
    
    def on_preset_selected(self, event=None):
        """Handle preset selection from dropdown"""
        # Visual feedback only, actual loading happens on Load button click
        pass
    
    def get_current_config(self):
        """Get current configuration as dictionary"""
        return {
            "quote": self.quote_var.get(),
            "delimiter": self.delimiter_var.get(),
            "output_type": self.output_type_var.get(),
            "filename": self.filename_var.get(),
            "dob_column": self.dob_var.get(),
            "convert_date": self.convert_date_var.get(),
            "from_format": self.from_format_var.get(),
            "to_format": self.to_format_var.get(),
            "date2_column": self.date2_var.get(),
            "convert_date2": self.convert_date2_var.get(),
            "from_format2": self.from_format2_var.get(),
            "to_format2": self.to_format2_var.get()
        }
    
    def apply_config(self, config):
        """Apply configuration to current settings"""
        self.quote_var.set(config.get("quote", "No Quotes"))
        self.delimiter_var.set(config.get("delimiter", "Comma"))
        self.output_type_var.set(config.get("output_type", ".csv"))
        self.filename_var.set(config.get("filename", "converted_file"))
        
        # Only set DOB column if it exists in current headers
        dob_col = config.get("dob_column", "Not detected")
        if dob_col in self.current_headers or dob_col == "Not detected":
            self.dob_var.set(dob_col)
        
        self.convert_date_var.set(config.get("convert_date", False))
        self.from_format_var.set(config.get("from_format", "MM/DD/YYYY"))
        self.to_format_var.set(config.get("to_format", "MM/DD/YYYY"))
        
        # Date2 settings
        date2_col = config.get("date2_column", "None")
        if date2_col in self.current_headers or date2_col == "None":
            self.date2_var.set(date2_col)
        self.convert_date2_var.set(config.get("convert_date2", True))
        self.from_format2_var.set(config.get("from_format2", "MM/DD/YYYY"))
        self.to_format2_var.set(config.get("to_format2", "MM/DD/YYYY"))
        
        # Update format dropdown states
        self.toggle_date_format_options()
        self.toggle_date2_format_options()
        self.on_date2_selected()
    
    def save_selected_preset(self):
        """Save current configuration to selected preset slot"""
        slot_number = self.get_selected_slot_number()
        slot_name = f"slot_{slot_number}"
        
        # Ask for preset name
        current_name = self.presets.get(slot_name, {}).get("name", f"Preset {slot_number}")
        
        # Create dialog for preset name
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Preset")
        dialog.geometry("450x150")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.bg_color)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(
            dialog,
            text=f"Enter name for Slot {slot_number}:",
            font=self.body_font,
            bg=self.bg_color,
            fg=self.text_color
        ).pack(pady=(15, 10))
        
        name_var = tk.StringVar(value=current_name)
        name_entry = tk.Entry(dialog, textvariable=name_var, font=self.body_font, width=40)
        name_entry.pack(pady=10, padx=20)
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        
        def save_and_close():
            preset_name = name_var.get().strip()
            if not preset_name:
                messagebox.showwarning("No Name", "Please enter a name for this preset!")
                return
            
            self.presets[slot_name] = {
                "name": preset_name,
                "config": self.get_current_config()
            }
            
            self.save_presets()
            self.update_preset_dropdown()
            self.preset_var.set(f"Slot {slot_number}: {preset_name}")
            dialog.destroy()
            messagebox.showinfo("Success", f"Preset '{preset_name}' saved to Slot {slot_number}!")
        
        button_frame = tk.Frame(dialog, bg=self.bg_color)
        button_frame.pack(pady=15)
        
        tk.Button(
            button_frame,
            text="Save",
            command=save_and_close,
            font=self.body_font,
            bg=self.success_color,
            fg=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            font=self.body_font,
            bg=self.secondary_color,
            fg=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        name_entry.bind('<Return>', lambda e: save_and_close())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def load_selected_preset(self):
        """Load configuration from selected preset slot"""
        slot_number = self.get_selected_slot_number()
        slot_name = f"slot_{slot_number}"
        
        if slot_name not in self.presets:
            messagebox.showinfo("Empty Slot", f"Slot {slot_number} is empty! Use 'Save' to create a preset.")
            return
        
        preset = self.presets[slot_name]
        preset_name = preset.get("name", f"Preset {slot_number}")
        
        self.apply_config(preset["config"])
        messagebox.showinfo("Success", f"Preset '{preset_name}' loaded from Slot {slot_number}!")
    
    def rename_selected_preset(self):
        """Rename the selected preset slot"""
        slot_number = self.get_selected_slot_number()
        slot_name = f"slot_{slot_number}"
        
        if slot_name not in self.presets:
            messagebox.showinfo("Empty Slot", f"Slot {slot_number} is empty! Nothing to rename.")
            return
        
        current_name = self.presets[slot_name].get("name", f"Preset {slot_number}")
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Preset")
        dialog.geometry("450x150")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.bg_color)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(
            dialog,
            text=f"Enter new name for Slot {slot_number}:",
            font=self.body_font,
            bg=self.bg_color,
            fg=self.text_color
        ).pack(pady=(15, 10))
        
        name_var = tk.StringVar(value=current_name)
        name_entry = tk.Entry(dialog, textvariable=name_var, font=self.body_font, width=40)
        name_entry.pack(pady=10, padx=20)
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        
        def rename_and_close():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("No Name", "Please enter a name for this preset!")
                return
            
            self.presets[slot_name]["name"] = new_name
            self.save_presets()
            self.update_preset_dropdown()
            self.preset_var.set(f"Slot {slot_number}: {new_name}")
            dialog.destroy()
            messagebox.showinfo("Success", f"Preset renamed to '{new_name}'!")
        
        button_frame = tk.Frame(dialog, bg=self.bg_color)
        button_frame.pack(pady=15)
        
        tk.Button(
            button_frame,
            text="Rename",
            command=rename_and_close,
            font=self.body_font,
            bg=self.success_color,
            fg=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            font=self.body_font,
            bg=self.secondary_color,
            fg=self.button_text_color,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        name_entry.bind('<Return>', lambda e: rename_and_close())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def clear_selected_preset(self):
        """Clear the selected preset slot"""
        slot_number = self.get_selected_slot_number()
        slot_name = f"slot_{slot_number}"
        
        if slot_name not in self.presets:
            messagebox.showinfo("Empty Slot", f"Slot {slot_number} is already empty!")
            return
        
        preset_name = self.presets[slot_name].get("name", f"Preset {slot_number}")
        
        if messagebox.askyesno("Confirm", f"Clear preset '{preset_name}' from Slot {slot_number}?"):
            del self.presets[slot_name]
            self.save_presets()
            self.update_preset_dropdown()
            self.preset_var.set(f"Slot {slot_number}: Empty")
            messagebox.showinfo("Success", f"Preset '{preset_name}' cleared from Slot {slot_number}!")
    
    # ============ END PRESET MANAGEMENT METHODS ============
    
    def save_settings(self):
        """Save current settings to a JSON file"""
        settings = {
            "output_type": self.output_type_var.get(),
            "filename": self.filename_var.get(),
            "delimiter": self.delimiter_var.get(),
            "quote_style": self.quote_var.get(),
            "convert_dates": self.convert_date_var.get(),
            "dob_column": self.dob_var.get(),
            "date2_column": self.date2_var.get(),
            "from_format": self.from_format_var.get(),
            "to_format": self.to_format_var.get(),
            "from_format2": self.from_format2_var.get(),
            "to_format2": self.to_format2_var.get()
        }
        
        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def load_settings(self):
        """Load settings from JSON file if it exists"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                
                self.output_type_var.set(settings.get("output_type", ".csv"))
                self.filename_var.set(settings.get("filename", ""))
                self.delimiter_var.set(settings.get("delimiter", "Comma"))
                self.quote_var.set(settings.get("quote_style", "No Quotes"))
                self.convert_date_var.set(settings.get("convert_dates", False))
                self.dob_var.set(settings.get("dob_column", "Not detected"))
                self.date2_var.set(settings.get("date2_column", "None"))
                self.from_format_var.set(settings.get("from_format", "MM/DD/YYYY"))
                self.to_format_var.set(settings.get("to_format", "MM/DD/YYYY"))
                self.from_format2_var.set(settings.get("from_format2", "MM/DD/YYYY"))
                self.to_format2_var.set(settings.get("to_format2", "MM/DD/YYYY"))
                
                self.toggle_date_format_options()
                self.on_date2_selected()
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def reset_app(self):
        """Reset the application to initial state"""
        self.current_file_path = None
        self.current_file_type = None
        self.column_headers = []
        self.current_headers = []
        
        self.file_label.config(text="No file selected", fg=self.secondary_color)
        self.filename_var.set("")
        self.dob_var.set("Not detected")
        self.date2_var.set("None")
        self.dob_status_label.config(text="")
        self.convert_date_var.set(True)  # Keep enabled by default
        self.toggle_date_format_options()
        self.on_date2_selected()
        
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, "Upload a file to see preview...")
        self.preview_text.config(state=tk.DISABLED)
        
        self.dob_dropdown['values'] = ["Not detected"]
        self.date2_dropdown['values'] = ["None"]
    
    def convert_file(self):
        """Convert the current file based on selected output type"""
        if not self.current_file_path:
            messagebox.showwarning("No File", "Please upload a file first!")
            return
        
        # Get output settings
        output_type = self.output_type_var.get()
        filename = self.filename_var.get().strip()
        
        if not filename:
            messagebox.showwarning("No Filename", "Please enter an output filename!")
            return
        
        # Save settings before conversion
        self.save_settings()
        
        # Generate timestamp in YYYYMMDD_HHMMSS format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Remove extension if user added it
        if filename.endswith(output_type):
            filename = filename[:-len(output_type)]
        
        # Add timestamp and extension
        filename_with_timestamp = f"{filename}_{timestamp}{output_type}"
        
        try:
            # Get save location
            save_path = filedialog.asksaveasfilename(
                title=f"Save {output_type.upper()} file",
                initialfile=filename_with_timestamp,
                defaultextension=output_type,
                filetypes=[
                    (f"{output_type.upper()[1:]} files", f"*{output_type}"),
                    ("All files", "*.*")
                ]
            )
            
            if not save_path:
                return
            
            # Perform conversion based on output type
            if output_type == ".csv":
                self.convert_to_csv(save_path)
            else:  # .txt
                self.convert_to_txt(save_path)
            
            # Show success message with DOB column info if selected
            dob_column = self.get_selected_dob_column()
            success_msg = f"File converted and saved to:\n{save_path}"
            if dob_column:
                success_msg += f"\n\nDate of Birth column: {dob_column}"
            
            messagebox.showinfo("Success", success_msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert file:\n{str(e)}")
    
    def convert_to_csv(self, save_path):
        """Convert the current file to CSV format"""
        # Determine quoting style
        use_quotes = self.quote_var.get() == "Add Quotes"
        
        # Get selected delimiter for OUTPUT
        selected_delimiter = self.get_delimiter()
        
        # Get date columns for date conversion
        dob_column = self.get_selected_dob_column()
        date2_column = self.get_selected_date2_column()
        # Convert dates if either checkbox is enabled AND its respective column is set
        should_convert_dates = (self.convert_date_var.get() and dob_column) or (self.convert_date2_var.get() and date2_column)
        
        # Get input encoding and delimiter
        input_encoding = getattr(self, 'current_encoding', 'utf-8')
        input_delimiter = getattr(self, 'current_delimiter', ',')
        
        if self.current_file_type == '.csv':
            # CSV to CSV (potentially with different quoting or delimiter)
            with open(self.current_file_path, 'r', encoding=input_encoding, newline='', errors='replace') as infile:
                reader = csv.reader(infile, delimiter=input_delimiter)
                rows = list(reader)
            
            # Apply date conversion if enabled
            if should_convert_dates and rows:
                headers = rows[0]
                for i in range(1, len(rows)):
                    rows[i] = self.convert_dates_in_row(rows[i], headers, dob_column, date2_column)
            
            with open(save_path, 'w', encoding='utf-8', newline='') as outfile:
                if use_quotes:
                    writer = csv.writer(outfile, delimiter=selected_delimiter, quoting=csv.QUOTE_ALL, quotechar='"')
                else:
                    writer = csv.writer(outfile, delimiter=selected_delimiter, quoting=csv.QUOTE_MINIMAL)
                writer.writerows(rows)
        
        elif self.current_file_type == '.txt':
            # TXT to CSV - assume lines are rows, split by detected delimiter
            with open(self.current_file_path, 'r', encoding=input_encoding, errors='replace') as infile:
                lines = infile.readlines()
            
            # Use detected delimiter or try to detect
            delimiter = input_delimiter
            if not delimiter or delimiter not in (lines[0] if lines else ""):
                # Try to detect delimiter (tab, comma, pipe, semicolon)
                sample = lines[0] if lines else ""
                for delim in ['\t', ',', '|', ';']:
                    if delim in sample:
                        delimiter = delim
                        break
            
            rows = []
            headers = None
            
            if delimiter:
                # Split by detected delimiter
                for idx, line in enumerate(lines):
                    row = [cell.strip() for cell in line.strip().split(delimiter)]
                    if idx == 0:
                        headers = row
                    elif should_convert_dates and headers:
                        row = self.convert_dates_in_row(row, headers, dob_column, date2_column)
                    rows.append(row)
            else:
                # Each line becomes a single cell
                for line in lines:
                    rows.append([line.strip()])
            
            with open(save_path, 'w', encoding='utf-8', newline='') as outfile:
                if use_quotes:
                    writer = csv.writer(outfile, delimiter=selected_delimiter, quoting=csv.QUOTE_ALL, quotechar='"')
                else:
                    writer = csv.writer(outfile, delimiter=selected_delimiter, quoting=csv.QUOTE_MINIMAL)
                writer.writerows(rows)
    
    def convert_to_txt(self, save_path):
        """Convert the current file to TXT format"""
        # Get selected delimiter for OUTPUT
        selected_delimiter = self.get_delimiter()
        
        # Determine if quotes should be added
        use_quotes = self.quote_var.get() == "Add Quotes"
        
        # Get date columns for date conversion
        dob_column = self.get_selected_dob_column()
        date2_column = self.get_selected_date2_column()
        # Convert dates if either checkbox is enabled AND its respective column is set
        should_convert_dates = (self.convert_date_var.get() and dob_column) or (self.convert_date2_var.get() and date2_column)
        
        # Get input encoding and delimiter
        input_encoding = getattr(self, 'current_encoding', 'utf-8')
        input_delimiter = getattr(self, 'current_delimiter', ',')
        
        if self.current_file_type == '.txt':
            # TXT to TXT - potentially add quotes or change delimiter
            with open(self.current_file_path, 'r', encoding=input_encoding, errors='replace') as infile:
                lines = infile.readlines()
            
            # Use detected delimiter or try to detect current delimiter
            current_delimiter = input_delimiter
            if not current_delimiter or current_delimiter not in (lines[0] if lines else ""):
                sample = lines[0] if lines else ""
                for delim in ['\t', ',', '|', ';']:
                    if delim in sample:
                        current_delimiter = delim
                        break
            
            headers = None
            
            with open(save_path, 'w', encoding='utf-8') as outfile:
                if current_delimiter:
                    # Split by detected delimiter and rejoin with selected delimiter
                    for idx, line in enumerate(lines):
                        cells = [cell.strip() for cell in line.strip().split(current_delimiter)]
                        
                        if idx == 0:
                            headers = cells
                        elif should_convert_dates and headers:
                            cells = self.convert_dates_in_row(cells, headers, dob_column, date2_column)
                        
                        if use_quotes:
                            cells = [f'"{cell}"' for cell in cells]
                        outfile.write(selected_delimiter.join(cells) + '\n')
                else:
                    # No delimiter detected, just copy or add quotes to whole line
                    for line in lines:
                        if use_quotes:
                            outfile.write(f'"{line.strip()}"\n')
                        else:
                            outfile.write(line)
        
        elif self.current_file_type == '.csv':
            # CSV to TXT - convert using selected delimiter
            with open(self.current_file_path, 'r', encoding=input_encoding, newline='', errors='replace') as infile:
                reader = csv.reader(infile, delimiter=input_delimiter)
                rows = list(reader)
                
                # Apply date conversion if enabled
                if should_convert_dates and rows:
                    headers = rows[0]
                    for i in range(1, len(rows)):
                        rows[i] = self.convert_dates_in_row(rows[i], headers, dob_column, date2_column)
                
                with open(save_path, 'w', encoding='utf-8') as outfile:
                    for row in rows:
                        if use_quotes:
                            # Add quotes around each cell
                            row = [f'"{cell}"' for cell in row]
                        # Use selected delimiter for TXT output
                        outfile.write(selected_delimiter.join(row) + '\n')


def main():
    root = tk.Tk()
    app = FileUploaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()