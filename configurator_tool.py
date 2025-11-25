import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pandas as pd
import json
import os
import re
from datetime import datetime
from pathlib import Path
import threading
import time

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
        
class CollapsibleFrame(tk.Frame):
    def __init__(self, parent, title="", bg_color='#ffffff', header_bg='#e9ecef', text_color='#2c3e50', *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(bg=bg_color)
        
        self.bg_color = bg_color
        self.header_bg = header_bg
        self.text_color = text_color
        self.is_collapsed = False
        
        # Header frame (always visible)
        self.header_frame = tk.Frame(self, bg=header_bg, relief='solid', bd=1, cursor="hand2")
        self.header_frame.pack(fill=tk.X)
        
        # Header content
        header_content = tk.Frame(self.header_frame, bg=header_bg)
        header_content.pack(fill=tk.X, padx=15, pady=10)
        
        # Collapse/expand indicator
        self.indicator = tk.Label(header_content, text="▼", font=('Segoe UI', 12), 
                                 bg=header_bg, fg=text_color, cursor="hand2")
        self.indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        # Title label
        self.title_label = tk.Label(header_content, text=title, font=('Segoe UI', 11, 'bold'), 
                                   bg=header_bg, fg=text_color, cursor="hand2")
        self.title_label.pack(side=tk.LEFT)
        
        # Content frame (collapsible)
        self.content_frame = tk.Frame(self, bg=bg_color, relief='solid', bd=1)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Bind click events
        self.header_frame.bind("<Button-1>", self.toggle_collapse)
        header_content.bind("<Button-1>", self.toggle_collapse)
        self.indicator.bind("<Button-1>", self.toggle_collapse)
        self.title_label.bind("<Button-1>", self.toggle_collapse)
        
    def toggle_collapse(self, event=None):
        try:
            if self.is_collapsed:
                self.content_frame.pack(fill=tk.BOTH, expand=True)
                self.indicator.config(text="▼")
                self.is_collapsed = False
            else:
                self.content_frame.pack_forget()
                self.indicator.config(text="▶")
                self.is_collapsed = True
        except Exception as e:
            print(f"Error toggling collapse: {e}")

class CSVConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Client Configuration")
        
        # Add error handling for root configuration
        try:
            # Check if this is running in HelloToolbelt (MockRoot) or standalone
            self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
            
            if not self.is_in_toolbelt:
                # Only configure background if running standalone
                self.root.configure(bg='#ffffff')
        except Exception as e:
            print(f"Warning: Could not configure root window: {e}")
            self.is_in_toolbelt = False
        
        # Initialize state variables first
        self.file_path = ""
        self.df = pd.DataFrame()
        self.column_vars = {}
        self.optional_vars = {}
        self.relationship_map = {}
        self.date_format_vars = {}
        self.detected_date_formats = {}
        self._updating_interface = False  # Flag to prevent recursive updates
        self._widgets_created = False  # Flag to track widget creation
        
        # Use system default colors that will adapt to light/dark mode
        try:
            self.setup_adaptive_styling()
        except Exception as e:
            print(f"Warning: Could not setup styling: {e}")
            self._setup_fallback_styling()
        
        self.root.minsize(1000, 800)
        
        try:
            self._init_file_type_configs()
            self._init_date_formats()
        except Exception as e:
            print(f"Error initializing configurations: {e}")
            messagebox.showerror("Initialization Error", f"Failed to initialize: {e}")
            return
        
        # Default file type
        self.current_file_type = "Eligibility"
        self._update_current_file_type_attributes()
        
        # Create main interface with error handling
        try:
            self._create_main_interface()
            self._widgets_created = True
        except Exception as e:
            print(f"Error creating interface: {e}")
            messagebox.showerror("Interface Error", f"Failed to create interface: {e}")
            return
        
        # Center window only if standalone
        if not self.is_in_toolbelt:
            try:
                self._center_window()
            except Exception as e:
                print(f"Warning: Could not center window: {e}")

    def _setup_fallback_styling(self):
        """Fallback styling if adaptive styling fails"""
        self.is_dark_mode = False
        self.title_font = ("Arial", 14, "bold")
        self.subtitle_font = ("Arial", 11, "bold")
        self.label_font = ("Arial", 10)
        self.text_font = ("Arial", 10)
        
        self.button_padx = 8
        self.button_pady = 4
        self.frame_padx = 20
        self.frame_pady = 15
        
        # Light mode fallback colors
        self.bg_color = '#ffffff'
        self.frame_bg = '#f8f9fa'
        self.header_bg = '#e9ecef'
        self.primary_color = '#3498db'
        self.success_color = '#27ae60'
        self.danger_color = '#e74c3c'
        self.warning_color = '#f39c12'
        self.text_color = '#2c3e50'
        self.text_secondary = '#34495e'
        self.button_text_color = '#000000'
        self.button_hover_text_color = '#000000'

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
            try:
                temp_label = tk.Label(self.root)
                parent_bg = temp_label.cget('bg')
                parent_fg = temp_label.cget('fg')
                temp_label.destroy()
            except:
                parent_bg = '#ffffff'
                parent_fg = '#2c3e50'
        
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
            self.primary_color = '#4a90e2'
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
            self.primary_color = '#3498db'
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
        if self._updating_interface:
            return  # Prevent recursive updates
            
        self._updating_interface = True
        
        try:
            self.is_dark_mode = is_dark_mode
            
            # Force update the colors based on the new dark mode state
            if self.is_in_toolbelt:
                # Get the updated colors from HelloToolbelt container
                try:
                    parent_bg = self.root.cget('bg')
                    parent_fg = self.root.cget('fg')
                except:
                    # Fallback based on dark mode state
                    if is_dark_mode:
                        parent_bg = '#2b2b2b'
                        parent_fg = '#ffffff'
                    else:
                        parent_bg = '#ffffff'
                        parent_fg = '#2c3e50'
            else:
                # Standalone mode - use appropriate colors
                if is_dark_mode:
                    parent_bg = '#2b2b2b'
                    parent_fg = '#ffffff'
                else:
                    parent_bg = '#ffffff'
                    parent_fg = '#2c3e50'
            
            # Update color scheme based on new dark mode state
            if is_dark_mode:
                # Dark mode colors
                self.bg_color = parent_bg
                self.frame_bg = '#3c3c3c'
                self.header_bg = '#4a4a4a'
                self.primary_color = '#4a90e2'
                self.success_color = '#27ae60'
                self.danger_color = '#e74c3c'
                self.warning_color = '#f39c12'
                self.text_color = parent_fg
                self.text_secondary = '#cccccc'
                # Button text colors - black for both modes
                self.button_text_color = '#000000'  # Black text for good contrast
                self.button_hover_text_color = '#000000'  # Black text for hover state
            else:
                # Light mode colors
                self.bg_color = parent_bg
                self.frame_bg = '#f8f9fa'
                self.header_bg = '#e9ecef'
                self.primary_color = '#3498db'
                self.success_color = '#27ae60'
                self.danger_color = '#e74c3c'
                self.warning_color = '#f39c12'
                self.text_color = parent_fg
                self.text_secondary = '#34495e'
                # Button text colors - black for both modes
                self.button_text_color = '#000000'  # Black text for good contrast
                self.button_hover_text_color = '#000000'  # Black text for hover state
            
            # Clear and recreate the interface with error handling
            try:
                for widget in self.root.winfo_children():
                    widget.destroy()
            except tk.TclError:
                pass  # Widgets may have been destroyed already
            
            # Reinitialize the interface
            self._create_main_interface()
            self._widgets_created = True
            
            # If data was loaded, rebuild the data processing interface
            if not self.df.empty:
                self.build_data_processing()
                self.show_preview()
                self.show_mapping_fields()
                
        except Exception as e:
            print(f"Error refreshing styling: {e}")
        finally:
            self._updating_interface = False

    def _center_window(self):
        try:
            window_width = 1200
            window_height = 900
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            center_x = int(screen_width/2 - window_width/2)
            center_y = int(screen_height/2 - window_height/2)
            
            self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        except Exception as e:
            print(f"Warning: Could not center window: {e}")

    def _add_button_hover(self, button, normal_color, hover_color, normal_fg=None, hover_fg=None):
        """Add hover effects to buttons with error handling"""
        try:
            # Use adaptive button text colors if not specified
            if normal_fg is None:
                normal_fg = getattr(self, 'button_text_color', 'white')
            if hover_fg is None:
                hover_fg = getattr(self, 'button_hover_text_color', 'white')
                
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

    # [Rest of the methods remain the same - _init_file_type_configs, _init_date_formats, etc.]
    # I'll include just the essential ones for brevity, but you should keep all your existing methods

    def _init_file_type_configs(self):
        base_fields = [
            "first_name", "last_name", "date_of_birth", "gender", "relationship", 
            "employee_id", "streetaddress", "city", "state", "zipcode",
            "health_plan_group_id", "health_plan_member_id", "member_id_link",
            "external_member_id", "term_date", "health_plan_provider", 
            "vendor_carrier_id", "member_hash", "client"
        ]
        
        self.file_type_configs = {
            "Eligibility": {
                "fields": base_fields,
                "date_fields": ["date_of_birth", "term_date"],
                "default_non_optional": ["first_name", "last_name", "date_of_birth"],
                "special_fields": ["relationship"]
            },
            "Formatting": {
                "fields": base_fields + ["addr2", "email", "location", "language"],
                "date_fields": ["date_of_birth", "term_date"],
                "default_non_optional": ["first_name", "last_name", "date_of_birth"],
                "special_fields": ["relationship"]
            },
            "Enrichment - UNDER CONSTRUCTION": {
                "fields": base_fields + ["addr2", "email", "email2", "condition1", 
                         "condition2", "condition3", "condition4", "ethnicity", 
                         "language", "location"],
                "date_fields": ["date_of_birth", "term_date"],
                "default_non_optional": ["first_name", "last_name", "date_of_birth"],
                "special_fields": ["relationship"]
            },
            "Medical Claims - UNDER CONSTRUCTION": {
                "fields": ["first_name", "last_name", "date_of_birth", "streetaddress", 
                          "addr2", "city", "state", "zipcode", "gender", "email", 
                          "icd_code", "claim_date", "client"],
                "date_fields": ["date_of_birth", "claim_date"],
                "default_non_optional": ["first_name", "last_name", "date_of_birth"],
                "special_fields": ["relationship"]
            },
            "Pharmacy Claims - UNDER CONSTRUCTION": {
                "fields": base_fields + ["addr2", "email", "ndc_code", "rx_fill_date",
                         "member_match_id", "drug_label_name", "brand_code", "generic_name",
                         "drug_quantity", "drug_strength", "refills_remaining", "day_supply",
                         "last_fill_date"],
                "date_fields": ["date_of_birth", "rx_fill_date", "last_fill_date"],
                "default_non_optional": ["first_name", "last_name", "date_of_birth"],
                "special_fields": ["relationship"]
            }
        }

    def _init_date_formats(self):
        self.date_formats = {
            "yyyyMMdd": {
                "regex": r"^([0-9]{4}|[0-9]{2})([0]?[1-9]|[1][0-2])([0]?[1-9]|[1|2][0-9]|[3][0|1])$",
                "conversion": {"yyyyMMdd": "yyyy-MM-dd"}
            },
            "MM/dd/yyyy": {
                "regex": r"^([0]?[1-9]|[1][0-2])/([0]?[1-9]|[1|2][0-9]|[3][0|1])/([0-9]{4}|[0-9]{2})$",
                "conversion": {"MM/dd/yyyy": "yyyy-MM-dd"}
            },
            "MM/dd/yy": {
                "regex": r"^([0]?[1-9]|[1][0-2])/([0]?[1-9]|[1|2][0-9]|[3][0|1])/([0-9]{4}|[0-9]{2})$",
                "conversion": {"MM/dd/yy": "yyyy-MM-dd"}
            },
            "yyyy-MM-dd": {
                "regex": r"^([0-9]{4}|[0-9]{2})-([0]?[1-9]|[1][0-2])-([0]?[1-9]|[1|2][0-9]|[3][0|1])$",
                "conversion": {}
            }
        }

    def _update_current_file_type_attributes(self):
        try:
            config = self.file_type_configs[self.current_file_type]
            self.fields = config["fields"]
            self.date_fields = config["date_fields"]
            self.default_non_optional = config["default_non_optional"]
            self.special_fields = config["special_fields"]
        except KeyError as e:
            print(f"Warning: File type configuration not found: {e}")
            # Use Eligibility as fallback
            config = self.file_type_configs["Eligibility"]
            self.fields = config["fields"]
            self.date_fields = config["date_fields"]
            self.default_non_optional = config["default_non_optional"]
            self.special_fields = config["special_fields"]

    def _create_main_interface(self):
        try:
            # Main container with padding (non-scrollable)
            main_container = tk.Frame(self.root, bg=self.bg_color)
            main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
            
            # Header (stays fixed at top)
            header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
            header_frame.pack(fill=tk.X, pady=(0, 20))
            
            header_content = tk.Frame(header_frame, bg=self.primary_color)
            header_content.pack(fill=tk.X, padx=20, pady=15)
            
            header_icon = tk.Label(header_content, text="⚙️", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
            header_icon.pack(side=tk.LEFT, padx=(0, 10))
            
            header_label = tk.Label(header_content, text="Client Configuration", 
                                font=('Segoe UI', 16, 'bold'), bg=self.primary_color, fg='white')
            header_label.pack(side=tk.LEFT, anchor='w')
            
            # Create scrollable container for content (scrolls independently)
            self.main_scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color, bg=self.bg_color)
            self.main_scrollable_container.pack(fill=tk.BOTH, expand=True)
            
            # Get the scrollable frame from the container
            content_container = self.main_scrollable_container.scrollable_frame
            content_container.configure(bg=self.bg_color)
            
            # Build sections (reordered)
            self._build_file_upload_section(content_container)  # Now Step 1
            self._build_basic_settings_section(content_container)  # Now Step 2
            
            # Store reference to content container for later use
            self.main_config_container = content_container
            
            # Force scroll update after interface is built
            def update_scroll_after_build():
                try:
                    if hasattr(self, 'main_scrollable_container'):
                        self.main_scrollable_container.force_scroll_update()
                        # Also update mouse wheel bindings for new children
                        self.main_scrollable_container._bind_mousewheel_to_children(self.main_scrollable_container.scrollable_frame)
                except Exception as e:
                    print(f"Error updating scroll in main interface: {e}")
            
            # Multiple attempts to ensure scrolling works
            self.root.after(100, update_scroll_after_build)
            self.root.after(500, update_scroll_after_build)
            self.root.after(1000, update_scroll_after_build)
            
        except Exception as e:
            print(f"Error creating main interface: {e}")
            raise

    def _force_scroll_update(self):
        """Force scroll update at any time - can be called from anywhere"""
        try:
            if hasattr(self, 'main_scrollable_container'):
                self.main_scrollable_container.force_scroll_update()
                # Also update mouse wheel bindings for new children
                self.main_scrollable_container._bind_mousewheel_to_children(self.main_scrollable_container.scrollable_frame)
                print("Scroll update forced successfully")
        except Exception as e:
            print(f"Error forcing scroll update: {e}")

    def build_data_processing(self):
        try:
            self.clear_data_processing()

            # Data processing frame with modern styling
            self.data_processing_frame = tk.Frame(self.main_config_container, bg=self.frame_bg, relief='solid', bd=1)
            self.data_processing_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

            # Data preview section
            preview_header = tk.Frame(self.data_processing_frame, bg=self.header_bg, height=50)
            preview_header.pack(fill=tk.X)
            
            preview_label = tk.Label(preview_header, text="📊 Data Preview", 
                                    font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            preview_label.pack(pady=15)
            
            preview_content = tk.Frame(self.data_processing_frame, bg=self.frame_bg)
            preview_content.pack(fill=tk.X, padx=20, pady=10)
            
            self.preview_frame = tk.Frame(preview_content, bg=self.bg_color, relief='solid', bd=1)
            self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Field mapping section
            mapping_header = tk.Frame(self.data_processing_frame, bg=self.header_bg, height=50)
            mapping_header.pack(fill=tk.X, pady=(20, 0))
            
            mapping_label = tk.Label(mapping_header, text="🔗 Field Mapping Configuration", 
                                    font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            mapping_label.pack(pady=15)
            
            mapping_content = tk.Frame(self.data_processing_frame, bg=self.frame_bg)
            mapping_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            mapping_container = tk.Frame(mapping_content, bg=self.frame_bg)
            mapping_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Create sub-frames for different sections
            self.mapping_frame = tk.Frame(mapping_container, bg=self.bg_color, relief='solid', bd=1)
            self.mapping_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

            # Right side container for all other settings
            right_settings_container = tk.Frame(mapping_container, bg=self.frame_bg)
            right_settings_container.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))

            self.date_format_frame = tk.Frame(right_settings_container, bg=self.bg_color, relief='solid', bd=1)
            self.date_format_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Relationship frame comes BELOW date format frame
            if "relationship" in self.special_fields:
                self.relationship_frame = tk.Frame(right_settings_container, bg=self.bg_color, relief='solid', bd=1)
                self.relationship_frame.pack(fill=tk.X)
            
            # Generate button frame
            self.generate_button_frame = tk.Frame(self.main_config_container, bg=self.bg_color)
            self.generate_button_frame.pack(fill=tk.X, pady=20)
            
            generate_button = tk.Button(self.generate_button_frame, text="🚀 Generate JSON Configuration", 
                                    command=self.generate_json, 
                                    padx=self.button_padx + 2, pady=self.button_pady + 1, 
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
            generate_button.pack(side=tk.LEFT)
            
            self._add_button_hover(generate_button, self.primary_color, '#2980b9')
            
            # Force scroll update after building data processing interface
            def update_scroll_after_build():
                try:
                    self._force_scroll_update()
                    print("Scroll update after data processing build completed")
                except Exception as e:
                    print(f"Error in scroll update after data processing: {e}")
            
            # Multiple attempts with different timings
            self.root.after(100, update_scroll_after_build)
            self.root.after(300, update_scroll_after_build)
            self.root.after(500, update_scroll_after_build)
            
        except Exception as e:
            print(f"Error building data processing: {e}")
            messagebox.showerror("Error", f"Failed to build data processing interface: {e}")

    def show_mapping_fields(self):
        try:
            # Clear existing widgets safely
            for widget in self.mapping_frame.winfo_children():
                try:
                    widget.destroy()
                except tk.TclError:
                    pass

            if hasattr(self, 'relationship_frame') and self.relationship_frame.winfo_exists():
                for widget in self.relationship_frame.winfo_children():
                    try:
                        widget.destroy()
                    except tk.TclError:
                        pass

            columns = list(self.df.columns)
            # Create numbered column options
            numbered_columns = [f"{i}: {col}" for i, col in enumerate(columns)]

            # Header for mapping section
            mapping_header = tk.Label(self.mapping_frame, 
                    text=f"🔗 Field Mapping - {self.current_file_type} ({len(self.fields)} fields)",
                    font=self.subtitle_font, bg=self.bg_color, fg=self.text_color)
            mapping_header.pack(anchor="w", pady=(10, 15), padx=10)

            fields_content = tk.Frame(self.mapping_frame, bg=self.bg_color)
            fields_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

            self.create_field_widgets(fields_content, self.fields, numbered_columns)
            self.setup_special_fields()
            
            # Force scroll update after showing mapping fields
            def update_scroll_after_mapping():
                try:
                    self._force_scroll_update()
                    print("Scroll update after mapping fields completed")
                except Exception as e:
                    print(f"Error in scroll update after mapping: {e}")
            
            self.root.after(200, update_scroll_after_mapping)
            
        except Exception as e:
            print(f"Error showing mapping fields: {e}")

    def update_relationship_mapping(self, field, preserved_mappings=None):
        try:
            if field != "relationship" or "relationship" not in self.special_fields:
                return

            selected_col_numbered = self.column_vars[field].get()
            if selected_col_numbered == "":
                return
            
            # Extract actual column name from numbered format
            if ":" in selected_col_numbered:
                selected_col = selected_col_numbered.split(":", 1)[1].strip()
                if selected_col not in self.df.columns:
                    return
            else:
                return

            # Limit unique values to prevent hanging on large datasets
            unique_vals = sorted(self.df[selected_col].dropna().unique()[:100])  # Limit to 100 unique values
            
            # Only clear if we're not preserving mappings
            if preserved_mappings is None:
                self.relationship_map.clear()

            # Clear existing widgets safely
            for widget in self.relationship_frame.winfo_children():
                try:
                    widget.destroy()
                except tk.TclError:
                    pass

            # Header for relationship section
            rel_header = tk.Label(self.relationship_frame, text="👥 Relationship Mapping", 
                                 font=self.subtitle_font, bg=self.bg_color, fg=self.text_color)
            rel_header.pack(anchor="w", pady=(10, 15), padx=10)
            
            rel_content = tk.Frame(self.relationship_frame, bg=self.bg_color)
            rel_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            for val in unique_vals:
                rel_row = tk.Frame(rel_content, bg=self.bg_color)
                rel_row.pack(fill=tk.X, pady=2)
                
                display_val = str(val)
                if len(display_val) > 15:  
                    display_val = display_val[:12] + "..."
                    
                tk.Label(rel_row, text=display_val, width=15, anchor="w",
                        bg=self.bg_color, fg=self.text_secondary, font=self.label_font).pack(side=tk.LEFT, padx=(0, 5))
                
                # Set default value to blank, but use preserved mapping if available
                if preserved_mappings and val in preserved_mappings:
                    default_val = preserved_mappings[val]
                else:
                    default_val = ""
                
                var = tk.StringVar(value=default_val)
                dropdown = ttk.Combobox(rel_row, textvariable=var, 
                                       values=["", "employee", "spouse", "dependent"], 
                                       state="readonly", width=10)
                dropdown.pack(side=tk.LEFT, padx=5)
                
                self.relationship_map[val] = var
            
            # Force scroll update after relationship mapping
            def update_scroll_after_relationship():
                try:
                    self._force_scroll_update()
                    print("Scroll update after relationship mapping completed")
                except Exception as e:
                    print(f"Error in scroll update after relationship: {e}")
            
            self.root.after(200, update_scroll_after_relationship)
            
        except Exception as e:
            print(f"Error updating relationship mapping: {e}")

    def load_file(self):
        try:
            self.file_path = filedialog.askopenfilename(filetypes=[("CSV/TXT Files", "*.csv *.txt")])
            if not self.file_path:
                return
                
            # Update status to show loading
            self.upload_status_var.set("🔄 Loading file...")
            self.root.update_idletasks()
            
            # Auto-detect delimiter before reading the file
            detected_delimiter = self.detect_delimiter(self.file_path)
            
            # Update the delimiter dropdown with detected value
            # Map internal delimiter to display value
            delimiter_mapping = {",": ",", "|": "|", "\t": "Tab"}
            display_delimiter = delimiter_mapping.get(detected_delimiter, ",")
            self.delim_var.set(display_delimiter)
            
            # Read file with detected delimiter
            delimiter = '\t' if detected_delimiter == 'Tab' else detected_delimiter
            
            # For large files, read only a sample first to check structure
            try:
                # Try to read just the first few rows to validate structure
                sample_df = pd.read_csv(self.file_path, delimiter=delimiter, nrows=10)
                
                # If successful, read the full file but with reasonable limits
                self.df = pd.read_csv(self.file_path, delimiter=delimiter, nrows=10000)  # Limit to 10k rows for stability
                
                if len(self.df) == 10000:
                    print("Warning: File truncated to 10,000 rows for performance")
                    
            except pd.errors.EmptyDataError:
                self.upload_status_var.set("❌ File is empty")
                messagebox.showerror("Error", "The selected file is empty.")
                return
            except pd.errors.ParserError as e:
                # If parsing fails with detected delimiter, try fallback delimiters
                print(f"Failed with detected delimiter '{detected_delimiter}', trying fallbacks...")
                
                fallback_delimiters = [",", "|", "\t"]
                success = False
                
                for fallback_delim in fallback_delimiters:
                    if fallback_delim == detected_delimiter:
                        continue  # Skip the one we already tried
                        
                    try:
                        test_df = pd.read_csv(self.file_path, delimiter=fallback_delim, nrows=10)
                        if len(test_df.columns) > 1:  # Must have multiple columns
                            # Success with fallback
                            self.df = pd.read_csv(self.file_path, delimiter=fallback_delim, nrows=10000)
                            
                            # Update delimiter dropdown
                            fallback_display = delimiter_mapping.get(fallback_delim, ",")
                            self.delim_var.set(fallback_display)
                            
                            print(f"Successfully parsed with fallback delimiter: '{fallback_delim}'")
                            success = True
                            break
                    except:
                        continue
                
                if not success:
                    self.upload_status_var.set("❌ Failed to parse file")
                    messagebox.showerror("Error", f"Failed to parse file with any delimiter. Please check the file format.\n\nOriginal error: {e}")
                    return
            
            # Update status
            filename = os.path.basename(self.file_path)
            self.upload_status_var.set(f"✅ Loaded: {filename} ({len(self.df)} rows, {len(self.df.columns)} columns)")
            
            # Auto-collapse the file upload section after successful load
            if hasattr(self, 'upload_collapsible') and not self.upload_collapsible.is_collapsed:
                self.upload_collapsible.toggle_collapse()
            
            # Use threading for UI updates to prevent hanging
            def build_interface():
                try:
                    self.build_data_processing()
                    self.show_preview()
                    self.show_mapping_fields()
                    
                    # Force scroll region update after all content is loaded with multiple attempts
                    def update_scroll():
                        try:
                            print("Forcing scroll update after file load...")
                            self._force_scroll_update()
                        except Exception as e:
                            print(f"Error updating scroll: {e}")
                    
                    # Multiple attempts to ensure scroll works at different timings
                    self.root.after(100, update_scroll)
                    self.root.after(300, update_scroll)
                    self.root.after(500, update_scroll)
                    self.root.after(1000, update_scroll)
                    self.root.after(1500, update_scroll)
                    
                except Exception as e:
                    print(f"Error building interface: {e}")
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to build interface: {e}"))
            
            # Schedule interface building on main thread
            self.root.after(100, build_interface)
            
        except FileNotFoundError:
            self.upload_status_var.set("❌ File not found")
            messagebox.showerror("Error", "The selected file could not be found.")
        except PermissionError:
            self.upload_status_var.set("❌ Permission denied")
            messagebox.showerror("Error", "Permission denied. The file may be open in another application.")
        except MemoryError:
            self.upload_status_var.set("❌ File too large")
            messagebox.showerror("Error", "The file is too large to process. Please try a smaller file.")
        except Exception as e:
            self.upload_status_var.set("❌ Failed to load file")
            print(f"Error loading file: {e}")
            messagebox.showerror("Error", f"Failed to read file: {e}")

    def on_file_type_changed(self, event):
        if self._updating_interface:
            return  # Prevent recursive updates
            
        try:
            new_file_type = self.filetype_var.get()
            if new_file_type != self.current_file_type:
                # Save current mappings
                current_mappings = {}
                current_optional_settings = {}
                current_date_formats = {}
                current_relationship_mappings = {}
                
                for field, var in self.column_vars.items():
                    if var.get():  # Only save if a column is selected
                        current_mappings[field] = var.get()
                
                for field, var in self.optional_vars.items():
                    current_optional_settings[field] = var.get()
                
                for field, var in self.date_format_vars.items():
                    current_date_formats[field] = var.get()
                
                # Save relationship mappings before clearing
                for key, var in self.relationship_map.items():
                    current_relationship_mappings[key] = var.get()
                
                # Update file type
                self.current_file_type = new_file_type
                self._update_current_file_type_attributes()
                
                # Rebuild interface if file is loaded
                if hasattr(self, 'data_processing_frame') and self.data_processing_frame.winfo_exists():
                    self.clear_data_processing()
                    if not self.df.empty:
                        self.build_data_processing()
                        self.show_preview()
                        self.show_mapping_fields()
                        
                        # Restore mappings where possible
                        for field, column_value in current_mappings.items():
                            if field in self.column_vars:  # Field exists in new file type
                                self.column_vars[field].set(column_value)
                        
                        for field, optional_value in current_optional_settings.items():
                            if field in self.optional_vars:  # Field exists in new file type
                                self.optional_vars[field].set(optional_value)
                        
                        for field, format_value in current_date_formats.items():
                            if field in self.date_format_vars:  # Field exists in new file type
                                self.date_format_vars[field].set(format_value)
                        
                        # Handle relationship mappings restoration
                        if current_relationship_mappings and "relationship" in self.column_vars and self.column_vars["relationship"].get():
                            # Pass the preserved mappings to update_relationship_mapping
                            self.update_relationship_mapping("relationship", current_relationship_mappings)
                            # Set flag to prevent double-calling in setup_special_fields
                            self._relationship_mapping_updated = True
                        
                        self.setup_special_fields()
                        
                        # Force scroll update after file type change
                        def update_scroll_after_type_change():
                            try:
                                self._force_scroll_update()
                                print("Scroll update after file type change completed")
                            except Exception as e:
                                print(f"Error in scroll update after type change: {e}")
                        
                        self.root.after(300, update_scroll_after_type_change)
                        
        except Exception as e:
            print(f"Error changing file type: {e}")
            messagebox.showerror("Error", f"Failed to change file type: {e}")

    def _build_file_upload_section(self, parent):
        try:
            # File upload section - now collapsible
            self.upload_collapsible = CollapsibleFrame(
                parent, 
                title="📁 Step 1: File Upload & Processing",
                bg_color=self.frame_bg,
                header_bg=self.header_bg,
                text_color=self.text_color
            )
            self.upload_collapsible.pack(fill=tk.X, pady=(0, 15))
            
            # Content
            upload_content = tk.Frame(self.upload_collapsible.content_frame, bg=self.frame_bg)
            upload_content.pack(fill=tk.X, padx=20, pady=20)
            
            # Upload button with styling
            button_frame = tk.Frame(upload_content, bg=self.frame_bg)
            button_frame.pack(fill=tk.X, pady=(0, 15))
            
            upload_button = tk.Button(button_frame, text="📁 Upload CSV/TXT File", 
                                     command=self.load_file, 
                                     padx=self.button_padx + 2, pady=self.button_pady + 1, 
                                     font=('Segoe UI', 10, 'bold'),
                                     bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
            upload_button.pack(side=tk.LEFT)
            
            self._add_button_hover(upload_button, self.success_color, '#229954')
            
            # Status label
            self.upload_status_var = tk.StringVar(value="No file selected")
            status_label = tk.Label(button_frame, textvariable=self.upload_status_var, 
                                   font=("Segoe UI", 10), fg="#7f8c8d", bg=self.frame_bg)
            status_label.pack(side=tk.LEFT, padx=(20, 0))
            
            # Help text
            help_text = ("Upload your CSV or TXT file to begin configuration. The tool will analyze the file structure and allow you to map columns to the required fields.")
            help_label = tk.Label(upload_content, text=help_text, font=("Segoe UI", 9), 
                                 fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
            help_label.pack(anchor="w")
        except Exception as e:
            print(f"Error building file upload section: {e}")
            raise

    def _build_basic_settings_section(self, parent):
        try:
            # Basic settings frame - now collapsible and Step 2
            self.settings_collapsible = CollapsibleFrame(
                parent, 
                title="⚙️ Step 2: Basic Configuration",
                bg_color=self.frame_bg,
                header_bg=self.header_bg,
                text_color=self.text_color
            )
            self.settings_collapsible.pack(fill=tk.X, pady=(0, 15))
            
            # Content
            settings_content = tk.Frame(self.settings_collapsible.content_frame, bg=self.frame_bg)
            settings_content.pack(fill=tk.X, padx=20, pady=20)

            # Create grid for organized layout
            fields_grid = tk.Frame(settings_content, bg=self.frame_bg)
            fields_grid.pack(fill=tk.X)

            # Initialize variables with error handling
            try:
                self.client_var = tk.StringVar(value="")
                self.prefix_var = tk.StringVar(value="")
                self.delim_var = tk.StringVar(value=",")
                self.filetype_var = tk.StringVar(value="Eligibility")
                self.headers_var = tk.BooleanVar(value=True)
                self.members_var = tk.BooleanVar(value=True)
                self.restricted_client_var = tk.BooleanVar(value=False)
                self.integration_var = tk.StringVar(value="")
                self.provider_var = tk.StringVar(value="")
            except Exception as e:
                print(f"Error initializing variables: {e}")
                raise

            # Left column fields
            left_fields = [
                ("Client Name", "client_var", ""),
                ("File Prefix", "prefix_var", ""),
                ("Delimiter", "delim_var", ",", "combobox", [",", "|", "Tab"]),
                ("File Type", "filetype_var", "Eligibility", "combobox", list(self.file_type_configs.keys()))
            ]

            # Right column fields  
            right_fields = [
                ("Header Row", "headers_var", True, "checkbutton"),
                ("All Members File", "members_var", True, "checkbutton"),
                ("Restricted Client", "restricted_client_var", False, "checkbutton"),
                ("Integration Name", "integration_var", ""),
                ("health_plan_provider", "provider_var", "")
            ]

            # Create left column
            for idx, field_data in enumerate(left_fields):
                label_text, var_name, default_val = field_data[:3]
                widget_type = field_data[3] if len(field_data) > 3 else "entry"
                values = field_data[4] if len(field_data) > 4 else None
                
                row = idx
                
                label = tk.Label(fields_grid, text=label_text + ":", width=15, anchor="e", 
                               font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
                label.grid(row=row, column=0, sticky='e', padx=(5,2), pady=5)

                if widget_type == "combobox":
                    if var_name == "delim_var":
                        widget = ttk.Combobox(fields_grid, textvariable=self.delim_var, 
                                             values=values, state="readonly", width=25)
                    elif var_name == "filetype_var":
                        widget = ttk.Combobox(fields_grid, textvariable=self.filetype_var,
                                             values=values, state="readonly", width=25)
                        widget.bind("<<ComboboxSelected>>", self.on_file_type_changed)
                else:
                    if var_name == "client_var":
                        entry_frame = tk.Frame(fields_grid, bg=self.bg_color, relief='solid', bd=1)
                        widget = tk.Entry(entry_frame, textvariable=self.client_var, width=28, 
                                        font=self.text_font, bg=self.bg_color, fg=self.text_color, 
                                        relief='flat', bd=0)
                        widget.pack(padx=5, pady=3)
                        widget = entry_frame
                    elif var_name == "prefix_var":
                        entry_frame = tk.Frame(fields_grid, bg=self.bg_color, relief='solid', bd=1)
                        widget = tk.Entry(entry_frame, textvariable=self.prefix_var, width=28, 
                                        font=self.text_font, bg=self.bg_color, fg=self.text_color, 
                                        relief='flat', bd=0)
                        widget.pack(padx=5, pady=3)
                        widget = entry_frame
                
                widget.grid(row=row, column=1, sticky='w', padx=(0,20), pady=5)

            # Create right column
            for idx, field_data in enumerate(right_fields):
                label_text, var_name, default_val = field_data[:3]
                widget_type = field_data[3] if len(field_data) > 3 else "entry"
                
                row = idx
                
                label = tk.Label(fields_grid, text=label_text + ":", width=15, anchor="e", 
                               font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
                label.grid(row=row, column=2, sticky='e', padx=(20,2), pady=5)

                if widget_type == "checkbutton":
                    if var_name == "headers_var":
                        widget = tk.Checkbutton(fields_grid, variable=self.headers_var, 
                                              bg=self.frame_bg, fg=self.text_color)
                    elif var_name == "members_var":
                        widget = tk.Checkbutton(fields_grid, variable=self.members_var, 
                                              bg=self.frame_bg, fg=self.text_color)
                    elif var_name == "restricted_client_var":
                        widget = tk.Checkbutton(fields_grid, variable=self.restricted_client_var, 
                                              bg=self.frame_bg, fg=self.text_color)
                else:
                    if var_name == "integration_var":
                        entry_frame = tk.Frame(fields_grid, bg=self.bg_color, relief='solid', bd=1)
                        widget = tk.Entry(entry_frame, textvariable=self.integration_var, width=28, 
                                        font=self.text_font, bg=self.bg_color, fg=self.text_color, 
                                        relief='flat', bd=0)
                        widget.pack(padx=5, pady=3)
                        widget = entry_frame
                    elif var_name == "provider_var":
                        entry_frame = tk.Frame(fields_grid, bg=self.bg_color, relief='solid', bd=1)
                        widget = tk.Entry(entry_frame, textvariable=self.provider_var, width=28, 
                                        font=self.text_font, bg=self.bg_color, fg=self.text_color, 
                                        relief='flat', bd=0)
                        widget.pack(padx=5, pady=3)
                        widget = entry_frame
                
                widget.grid(row=row, column=3, sticky='w', padx=(0,20), pady=5)

            # Help text
            help_frame = tk.Frame(settings_content, bg=self.frame_bg)
            help_frame.pack(fill=tk.X, pady=(10, 0))
            
            help_text = ("Note: All basic configuration fields (Client Name, File Prefix, Integration Name) are required for JSON generation.")
            help_label = tk.Label(help_frame, text=help_text, font=("Segoe UI", 9), 
                                 fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
            help_label.pack(anchor="w")
        except Exception as e:
            print(f"Error building basic settings: {e}")
            raise

    def on_file_type_changed(self, event):
        if self._updating_interface:
            return  # Prevent recursive updates
            
        try:
            new_file_type = self.filetype_var.get()
            if new_file_type != self.current_file_type:
                # Save current mappings
                current_mappings = {}
                current_optional_settings = {}
                current_date_formats = {}
                current_relationship_mappings = {}
                
                for field, var in self.column_vars.items():
                    if var.get():  # Only save if a column is selected
                        current_mappings[field] = var.get()
                
                for field, var in self.optional_vars.items():
                    current_optional_settings[field] = var.get()
                
                for field, var in self.date_format_vars.items():
                    current_date_formats[field] = var.get()
                
                # Save relationship mappings before clearing
                for key, var in self.relationship_map.items():
                    current_relationship_mappings[key] = var.get()
                
                # Update file type
                self.current_file_type = new_file_type
                self._update_current_file_type_attributes()
                
                # Rebuild interface if file is loaded
                if hasattr(self, 'data_processing_frame') and self.data_processing_frame.winfo_exists():
                    self.clear_data_processing()
                    if not self.df.empty:
                        self.build_data_processing()
                        self.show_preview()
                        self.show_mapping_fields()
                        
                        # Restore mappings where possible
                        for field, column_value in current_mappings.items():
                            if field in self.column_vars:  # Field exists in new file type
                                self.column_vars[field].set(column_value)
                        
                        for field, optional_value in current_optional_settings.items():
                            if field in self.optional_vars:  # Field exists in new file type
                                self.optional_vars[field].set(optional_value)
                        
                        for field, format_value in current_date_formats.items():
                            if field in self.date_format_vars:  # Field exists in new file type
                                self.date_format_vars[field].set(format_value)
                        
                        # Handle relationship mappings restoration
                        if current_relationship_mappings and "relationship" in self.column_vars and self.column_vars["relationship"].get():
                            # Pass the preserved mappings to update_relationship_mapping
                            self.update_relationship_mapping("relationship", current_relationship_mappings)
                            # Set flag to prevent double-calling in setup_special_fields
                            self._relationship_mapping_updated = True
                        
                        self.setup_special_fields()
        except Exception as e:
            print(f"Error changing file type: {e}")
            messagebox.showerror("Error", f"Failed to change file type: {e}")

    def clear_data_processing(self):
        try:
            self.column_vars.clear()
            self.optional_vars.clear()
            self.relationship_map.clear()
            self.date_format_vars.clear()
            self.detected_date_formats.clear()
            
            if hasattr(self, 'data_processing_frame') and self.data_processing_frame.winfo_exists():
                self.data_processing_frame.destroy()
            if hasattr(self, 'generate_button_frame') and self.generate_button_frame.winfo_exists():
                self.generate_button_frame.destroy()
        except Exception as e:
            print(f"Error clearing data processing: {e}")

    def build_data_processing(self):
        try:
            self.clear_data_processing()

            # Data processing frame with modern styling
            self.data_processing_frame = tk.Frame(self.main_config_container, bg=self.frame_bg, relief='solid', bd=1)
            self.data_processing_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

            # Data preview section
            preview_header = tk.Frame(self.data_processing_frame, bg=self.header_bg, height=50)
            preview_header.pack(fill=tk.X)
            
            preview_label = tk.Label(preview_header, text="📊 Data Preview", 
                                    font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            preview_label.pack(pady=15)
            
            preview_content = tk.Frame(self.data_processing_frame, bg=self.frame_bg)
            preview_content.pack(fill=tk.X, padx=20, pady=10)
            
            self.preview_frame = tk.Frame(preview_content, bg=self.bg_color, relief='solid', bd=1)
            self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Field mapping section
            mapping_header = tk.Frame(self.data_processing_frame, bg=self.header_bg, height=50)
            mapping_header.pack(fill=tk.X, pady=(20, 0))
            
            mapping_label = tk.Label(mapping_header, text="🔗 Field Mapping Configuration", 
                                    font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            mapping_label.pack(pady=15)
            
            mapping_content = tk.Frame(self.data_processing_frame, bg=self.frame_bg)
            mapping_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            mapping_container = tk.Frame(mapping_content, bg=self.frame_bg)
            mapping_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Create sub-frames for different sections
            self.mapping_frame = tk.Frame(mapping_container, bg=self.bg_color, relief='solid', bd=1)
            self.mapping_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

            # Right side container for all other settings
            right_settings_container = tk.Frame(mapping_container, bg=self.frame_bg)
            right_settings_container.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))

            self.date_format_frame = tk.Frame(right_settings_container, bg=self.bg_color, relief='solid', bd=1)
            self.date_format_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Relationship frame comes BELOW date format frame
            if "relationship" in self.special_fields:
                self.relationship_frame = tk.Frame(right_settings_container, bg=self.bg_color, relief='solid', bd=1)
                self.relationship_frame.pack(fill=tk.X)
            
            # Generate button frame
            self.generate_button_frame = tk.Frame(self.main_config_container, bg=self.bg_color)
            self.generate_button_frame.pack(fill=tk.X, pady=20)
            
            generate_button = tk.Button(self.generate_button_frame, text="🚀 Generate JSON Configuration", 
                                    command=self.generate_json, 
                                    padx=self.button_padx + 2, pady=self.button_pady + 1, 
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
            generate_button.pack(side=tk.LEFT)
            
            self._add_button_hover(generate_button, self.primary_color, '#2980b9')
            
            # Force scroll update after building data processing interface
            def update_scroll_after_build():
                try:
                    if hasattr(self, 'main_scrollable_container'):
                        self.main_scrollable_container.force_scroll_update()
                except Exception:
                    pass
            
            self.root.after(200, update_scroll_after_build)
            
        except Exception as e:
            print(f"Error building data processing: {e}")
            messagebox.showerror("Error", f"Failed to build data processing interface: {e}")

    def detect_date_format(self, col_data):
        try:
            # Limit sample size to prevent hanging on large datasets
            sample_data = [str(x) for x in col_data.head(100) if str(x) != 'nan' and str(x).strip()]
            
            if not sample_data:
                return "Unknown"
                
            sample = sample_data[:min(50, len(sample_data))]
            format_counts = {}
            
            for date_str in sample:
                for format_name, format_info in self.date_formats.items():
                    try:
                        if re.match(format_info["regex"], date_str):
                            format_counts[format_name] = format_counts.get(format_name, 0) + 1
                    except re.error:
                        continue  # Skip invalid regex
            
            return max(format_counts, key=format_counts.get) if format_counts else "Unknown"
        except Exception as e:
            print(f"Error detecting date format: {e}")
            return "Unknown"

    def detect_delimiter(self, file_path):
        """Detect the delimiter used in a CSV/TXT file"""
        try:
            # Read first few lines to detect delimiter
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                # Read first 5 lines for analysis
                sample_lines = []
                for i, line in enumerate(file):
                    if i >= 5:  # Only read first 5 lines
                        break
                    sample_lines.append(line.strip())
            
            if not sample_lines:
                return ","  # Default fallback
            
            # Test delimiters in order of preference: comma, pipe, tab
            delimiters_to_test = [',', '|', '\t']
            delimiter_scores = {}
            
            for delimiter in delimiters_to_test:
                scores = []
                for line in sample_lines:
                    if line:  # Skip empty lines
                        # Count occurrences of delimiter
                        count = line.count(delimiter)
                        scores.append(count)
                
                if scores:
                    # Calculate consistency score (lower std dev = more consistent)
                    avg_count = sum(scores) / len(scores)
                    if avg_count > 0:  # Must have at least some occurrences
                        # Calculate standard deviation
                        variance = sum((x - avg_count) ** 2 for x in scores) / len(scores)
                        std_dev = variance ** 0.5
                        
                        # Score based on average count and consistency
                        # Higher average count and lower std dev = better score
                        consistency_score = avg_count / (std_dev + 1)  # +1 to avoid division by zero
                        delimiter_scores[delimiter] = (avg_count, consistency_score)
            
            # Find best delimiter
            if delimiter_scores:
                # Sort by consistency score, then by average count
                best_delimiter = max(delimiter_scores.items(), 
                                key=lambda x: (x[1][1], x[1][0]))[0]
                
                # Validate that the best delimiter actually creates reasonable columns
                test_line = sample_lines[0] if sample_lines else ""
                if test_line:
                    columns = test_line.split(best_delimiter)
                    if len(columns) > 1:  # Must create at least 2 columns
                        return best_delimiter
            
            # Fallback detection using csv.Sniffer
            try:
                import csv
                sample_text = '\n'.join(sample_lines)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample_text, delimiters=',|\t')
                detected = dialect.delimiter
                
                # Map detected delimiter to our options
                if detected == ',':
                    return ","
                elif detected == '|':
                    return "|"
                elif detected == '\t':
                    return "Tab"
                else:
                    return ","  # Default fallback
                    
            except Exception:
                pass
            
            return ","  # Final fallback
            
        except Exception as e:
            print(f"Error detecting delimiter: {e}")
            return ","  # Fallback to comma

    def load_file(self):
        try:
            self.file_path = filedialog.askopenfilename(filetypes=[("CSV/TXT Files", "*.csv *.txt")])
            if not self.file_path:
                return
                
            # Update status to show loading
            self.upload_status_var.set("🔄 Loading file...")
            self.root.update_idletasks()
            
            # Auto-detect delimiter before reading the file
            detected_delimiter = self.detect_delimiter(self.file_path)
            
            # Update the delimiter dropdown with detected value
            # Map internal delimiter to display value
            delimiter_mapping = {",": ",", "|": "|", "\t": "Tab"}
            display_delimiter = delimiter_mapping.get(detected_delimiter, ",")
            self.delim_var.set(display_delimiter)
            
            # Read file with detected delimiter
            delimiter = '\t' if detected_delimiter == 'Tab' else detected_delimiter
            
            # For large files, read only a sample first to check structure
            try:
                # Try to read just the first few rows to validate structure
                sample_df = pd.read_csv(self.file_path, delimiter=delimiter, nrows=10)
                
                # If successful, read the full file but with reasonable limits
                self.df = pd.read_csv(self.file_path, delimiter=delimiter, nrows=10000)  # Limit to 10k rows for stability
                
                if len(self.df) == 10000:
                    print("Warning: File truncated to 10,000 rows for performance")
                    
            except pd.errors.EmptyDataError:
                self.upload_status_var.set("❌ File is empty")
                messagebox.showerror("Error", "The selected file is empty.")
                return
            except pd.errors.ParserError as e:
                # If parsing fails with detected delimiter, try fallback delimiters
                print(f"Failed with detected delimiter '{detected_delimiter}', trying fallbacks...")
                
                fallback_delimiters = [",", "|", "\t"]
                success = False
                
                for fallback_delim in fallback_delimiters:
                    if fallback_delim == detected_delimiter:
                        continue  # Skip the one we already tried
                        
                    try:
                        test_df = pd.read_csv(self.file_path, delimiter=fallback_delim, nrows=10)
                        if len(test_df.columns) > 1:  # Must have multiple columns
                            # Success with fallback
                            self.df = pd.read_csv(self.file_path, delimiter=fallback_delim, nrows=10000)
                            
                            # Update delimiter dropdown
                            fallback_display = delimiter_mapping.get(fallback_delim, ",")
                            self.delim_var.set(fallback_display)
                            
                            print(f"Successfully parsed with fallback delimiter: '{fallback_delim}'")
                            success = True
                            break
                    except:
                        continue
                
                if not success:
                    self.upload_status_var.set("❌ Failed to parse file")
                    messagebox.showerror("Error", f"Failed to parse file with any delimiter. Please check the file format.\n\nOriginal error: {e}")
                    return
            
            # Update status
            filename = os.path.basename(self.file_path)
            self.upload_status_var.set(f"✅ Loaded: {filename} ({len(self.df)} rows, {len(self.df.columns)} columns)")
            
            # Auto-collapse the file upload section after successful load
            if hasattr(self, 'upload_collapsible') and not self.upload_collapsible.is_collapsed:
                self.upload_collapsible.toggle_collapse()
            
            # Use threading for UI updates to prevent hanging
            def build_interface():
                try:
                    self.build_data_processing()
                    self.show_preview()
                    self.show_mapping_fields()
                    
                    # Force scroll region update after all content is loaded
                    def update_scroll():
                        try:
                            print("Forcing scroll update after file load...")
                            if hasattr(self, 'main_scrollable_container'):
                                self.main_scrollable_container.force_scroll_update()
                        except Exception as e:
                            print(f"Error updating scroll: {e}")
                    
                    # Multiple attempts to ensure scroll works
                    self.root.after(100, update_scroll)
                    self.root.after(500, update_scroll)
                    self.root.after(1000, update_scroll)
                    
                except Exception as e:
                    print(f"Error building interface: {e}")
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to build interface: {e}"))
            
            # Schedule interface building on main thread
            self.root.after(100, build_interface)
            
        except FileNotFoundError:
            self.upload_status_var.set("❌ File not found")
            messagebox.showerror("Error", "The selected file could not be found.")
        except PermissionError:
            self.upload_status_var.set("❌ Permission denied")
            messagebox.showerror("Error", "Permission denied. The file may be open in another application.")
        except MemoryError:
            self.upload_status_var.set("❌ File too large")
            messagebox.showerror("Error", "The file is too large to process. Please try a smaller file.")
        except Exception as e:
            self.upload_status_var.set("❌ Failed to load file")
            print(f"Error loading file: {e}")
            messagebox.showerror("Error", f"Failed to read file: {e}")

    def refresh_styling(self, is_dark_mode):
        """Refresh styling when dark mode is toggled from HelloToolbelt"""
        if self._updating_interface:
            return  # Prevent recursive updates
            
        self._updating_interface = True
        
        try:
            self.is_dark_mode = is_dark_mode
            
            # Force update the colors based on the new dark mode state
            if self.is_in_toolbelt:
                # Get the updated colors from HelloToolbelt container
                try:
                    parent_bg = self.root.cget('bg')
                    parent_fg = self.root.cget('fg')
                except:
                    # Fallback based on dark mode state
                    if is_dark_mode:
                        parent_bg = '#2b2b2b'
                        parent_fg = '#ffffff'
                    else:
                        parent_bg = '#ffffff'
                        parent_fg = '#2c3e50'
            else:
                # Standalone mode - use appropriate colors
                if is_dark_mode:
                    parent_bg = '#2b2b2b'
                    parent_fg = '#ffffff'
                else:
                    parent_bg = '#ffffff'
                    parent_fg = '#2c3e50'
            
            # Update color scheme based on new dark mode state
            if is_dark_mode:
                # Dark mode colors
                self.bg_color = parent_bg
                self.frame_bg = '#3c3c3c'
                self.header_bg = '#4a4a4a'
                self.primary_color = '#4a90e2'
                self.success_color = '#27ae60'
                self.danger_color = '#e74c3c'
                self.warning_color = '#f39c12'
                self.text_color = parent_fg
                self.text_secondary = '#cccccc'
                # Button text colors - black for both modes
                self.button_text_color = '#000000'  # Black text for good contrast
                self.button_hover_text_color = '#000000'  # Black text for hover state
            else:
                # Light mode colors
                self.bg_color = parent_bg
                self.frame_bg = '#f8f9fa'
                self.header_bg = '#e9ecef'
                self.primary_color = '#3498db'
                self.success_color = '#27ae60'
                self.danger_color = '#e74c3c'
                self.warning_color = '#f39c12'
                self.text_color = parent_fg
                self.text_secondary = '#34495e'
                # Button text colors - black for both modes
                self.button_text_color = '#000000'  # Black text for good contrast
                self.button_hover_text_color = '#000000'  # Black text for hover state
            
            # Clear and recreate the interface with error handling
            try:
                for widget in self.root.winfo_children():
                    widget.destroy()
            except tk.TclError:
                pass  # Widgets may have been destroyed already
            
            # Reinitialize the interface
            self._create_main_interface()
            self._widgets_created = True
            
            # If data was loaded, rebuild the data processing interface
            if not self.df.empty:
                self.build_data_processing()
                self.show_preview()
                self.show_mapping_fields()
                
        except Exception as e:
            print(f"Error refreshing styling: {e}")
        finally:
            self._updating_interface = False
            
    def show_preview(self):
        try:
            # Clear existing widgets safely
            for widget in self.preview_frame.winfo_children():
                try:
                    widget.destroy()
                except tk.TclError:
                    pass

            if self.df.empty:
                return

            preview_scroll_frame = tk.Frame(self.preview_frame, bg=self.bg_color)
            preview_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            tree_frame = tk.Frame(preview_scroll_frame, bg=self.bg_color)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            # Limit preview to first 5 rows for performance
            preview = self.df.head(5)
            cols = list(preview.columns)

            try:
                style = ttk.Style()
                style.configure("Treeview", font=self.text_font)
                style.configure("Treeview.Heading", font=self.label_font)
            except tk.TclError:
                pass  # Style may not be available
            
            tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=5)
            for col in cols:
                try:
                    position = self.df.columns.get_loc(col)
                    header_text = f"{position}: {col}"
                    tree.heading(col, text=header_text)
                    tree.column(col, width=120, minwidth=100, anchor="center")
                except Exception as e:
                    print(f"Warning: Could not configure column {col}: {e}")

            for _, row in preview.iterrows():
                try:
                    tree.insert("", "end", values=list(row))
                except Exception as e:
                    print(f"Warning: Could not insert row: {e}")

            y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=y_scroll.set)
            
            x_scroll = ttk.Scrollbar(preview_scroll_frame, orient="horizontal", command=tree.xview)
            tree.configure(xscrollcommand=x_scroll.set)
            
            tree.pack(side="left", fill="both", expand=True)
            y_scroll.pack(side="right", fill="y")
            x_scroll.pack(side="bottom", fill="x")
        except Exception as e:
            print(f"Error showing preview: {e}")

    def update_date_formats(self):
        try:
            # Clear existing widgets safely
            for widget in self.date_format_frame.winfo_children():
                try:
                    widget.destroy()
                except tk.TclError:
                    pass

            # Header for date format section
            date_header = tk.Label(self.date_format_frame, text="📅 Date Format Settings", 
                                  font=self.subtitle_font, bg=self.bg_color, fg=self.text_color)
            date_header.pack(anchor="w", pady=(10, 15), padx=10)
                
            date_formats_detected = {}
            for field in self.date_fields:
                col_selection = self.column_vars.get(field, tk.StringVar()).get()
                if col_selection and col_selection != "N/A":
                    # Extract actual column name from numbered format
                    if ":" in col_selection:
                        actual_col_name = col_selection.split(":", 1)[1].strip()
                        if actual_col_name in self.df.columns:
                            detected_format = self.detect_date_format(self.df[actual_col_name])
                            self.detected_date_formats[field] = detected_format
                            date_formats_detected[field] = detected_format
            
            # Find most common format
            most_common_format = None
            if len(date_formats_detected) > 1:
                formats = [fmt for fmt in date_formats_detected.values() if fmt != "Unknown"]
                if formats:
                    from collections import Counter
                    most_common_format = Counter(formats).most_common(1)[0][0]
            
            date_content = tk.Frame(self.date_format_frame, bg=self.bg_color)
            date_content.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            for field in self.date_fields:
                col_selection = self.column_vars.get(field, tk.StringVar()).get()
                if col_selection and col_selection != "N/A":
                    # Extract actual column name from numbered format
                    if ":" in col_selection:
                        actual_col_name = col_selection.split(":", 1)[1].strip()
                        if actual_col_name in self.df.columns:
                            field_frame = tk.Frame(date_content, bg=self.bg_color)
                            field_frame.pack(fill=tk.X, pady=2)
                            
                            tk.Label(field_frame, text=f"{field}:", width=12, anchor="w", 
                                    bg=self.bg_color, fg=self.text_secondary, font=self.label_font).pack(side=tk.LEFT, padx=(0, 5))
                            
                            format_to_use = self.detected_date_formats[field]
                            if format_to_use == "Unknown" and most_common_format:
                                format_to_use = most_common_format
                            
                            var = tk.StringVar(value=format_to_use)
                            dropdown = ttk.Combobox(field_frame, textvariable=var, 
                                                 values=list(self.date_formats.keys()) + ["Custom"], 
                                                 width=12, state="readonly")
                            dropdown.pack(side=tk.LEFT, padx=5)
                            self.date_format_vars[field] = var
                            
                            # Status label
                            if self.detected_date_formats[field] != "Unknown":
                                status_text = f"Detected: {self.detected_date_formats[field]}"
                                status_color = self.success_color
                            elif most_common_format and format_to_use == most_common_format:
                                status_text = f"Using: {most_common_format}"
                                status_color = self.warning_color
                            else:
                                status_text = "Not detected"
                                status_color = "#7f8c8d"
                            
                            status_label = tk.Label(field_frame, text=status_text, width=15, anchor="w",
                                                  bg=self.bg_color, fg=status_color, font=("Segoe UI", 9))
                            status_label.pack(side=tk.LEFT, padx=5)
        except Exception as e:
            print(f"Error updating date formats: {e}")

    def show_mapping_fields(self):
        try:
            # Clear existing widgets safely
            for widget in self.mapping_frame.winfo_children():
                try:
                    widget.destroy()
                except tk.TclError:
                    pass

            if hasattr(self, 'relationship_frame') and self.relationship_frame.winfo_exists():
                for widget in self.relationship_frame.winfo_children():
                    try:
                        widget.destroy()
                    except tk.TclError:
                        pass

            columns = list(self.df.columns)
            # Create numbered column options
            numbered_columns = [f"{i}: {col}" for i, col in enumerate(columns)]

            # Header for mapping section
            mapping_header = tk.Label(self.mapping_frame, 
                    text=f"🔗 Field Mapping - {self.current_file_type} ({len(self.fields)} fields)",
                    font=self.subtitle_font, bg=self.bg_color, fg=self.text_color)
            mapping_header.pack(anchor="w", pady=(10, 15), padx=10)

            fields_content = tk.Frame(self.mapping_frame, bg=self.bg_color)
            fields_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

            self.create_field_widgets(fields_content, self.fields, numbered_columns)
            self.setup_special_fields()
        except Exception as e:
            print(f"Error showing mapping fields: {e}")

    def create_field_widgets(self, parent_frame, fields_list, columns):
        try:
            for i, field in enumerate(fields_list):
                field_frame = tk.Frame(parent_frame, bg=self.bg_color)
                field_frame.pack(fill=tk.X, pady=2)
                
                index_label = tk.Label(field_frame, text=f"{i+1}.", width=3, anchor="e",
                                      bg=self.bg_color, fg=self.text_secondary, font=self.label_font)
                index_label.pack(side=tk.LEFT, padx=(0, 2))
                
                tk.Label(field_frame, text=field + ":", width=17, anchor="w",
                        bg=self.bg_color, fg=self.text_secondary, font=self.label_font).pack(side=tk.LEFT, padx=(0, 5))
                
                var = tk.StringVar(value="")
                dropdown = ttk.Combobox(field_frame, textvariable=var, values=[""] + columns, 
                                       state="readonly", width=20)
                dropdown.pack(side=tk.LEFT, padx=5)
                
                if field in self.date_fields or (field == "relationship" and "relationship" in self.special_fields):
                    dropdown.bind("<<ComboboxSelected>>", lambda e, f=field: self.handle_field_selection(f))
                
                self.column_vars[field] = var

                is_optional = field not in self.default_non_optional
                optional_var = tk.BooleanVar(value=is_optional)
                chk = tk.Checkbutton(field_frame, text="Optional", variable=optional_var,
                                   bg=self.bg_color, fg=self.text_secondary, font=self.label_font)
                chk.pack(side=tk.LEFT, padx=5)
                self.optional_vars[field] = optional_var
        except Exception as e:
            print(f"Error creating field widgets: {e}")

    def setup_special_fields(self):
        try:
            if "relationship" in self.column_vars and self.column_vars["relationship"].get():
                # Only call update_relationship_mapping if it hasn't been called yet during file type change
                if not hasattr(self, '_relationship_mapping_updated'):
                    self.update_relationship_mapping("relationship")
            
            # Reset the flag
            if hasattr(self, '_relationship_mapping_updated'):
                delattr(self, '_relationship_mapping_updated')
                
            has_date_field_mapping = any(
                field in self.column_vars and self.column_vars[field].get() != "" 
                for field in self.date_fields
            )
            if has_date_field_mapping:
                self.update_date_formats()
        except Exception as e:
            print(f"Error setting up special fields: {e}")

    def handle_field_selection(self, field):
        try:
            if field == "relationship" and "relationship" in self.special_fields:
                self.update_relationship_mapping(field)
            
            if field in self.date_fields:
                self.update_date_formats()
        except Exception as e:
            print(f"Error handling field selection: {e}")

    def update_relationship_mapping(self, field, preserved_mappings=None):
        try:
            if field != "relationship" or "relationship" not in self.special_fields:
                return

            selected_col_numbered = self.column_vars[field].get()
            if selected_col_numbered == "":
                return
            
            # Extract actual column name from numbered format
            if ":" in selected_col_numbered:
                selected_col = selected_col_numbered.split(":", 1)[1].strip()
                if selected_col not in self.df.columns:
                    return
            else:
                return

            # Limit unique values to prevent hanging on large datasets
            unique_vals = sorted(self.df[selected_col].dropna().unique()[:100])  # Limit to 100 unique values
            
            # Only clear if we're not preserving mappings
            if preserved_mappings is None:
                self.relationship_map.clear()

            # Clear existing widgets safely
            for widget in self.relationship_frame.winfo_children():
                try:
                    widget.destroy()
                except tk.TclError:
                    pass

            # Header for relationship section
            rel_header = tk.Label(self.relationship_frame, text="👥 Relationship Mapping", 
                                 font=self.subtitle_font, bg=self.bg_color, fg=self.text_color)
            rel_header.pack(anchor="w", pady=(10, 15), padx=10)
            
            rel_content = tk.Frame(self.relationship_frame, bg=self.bg_color)
            rel_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            for val in unique_vals:
                rel_row = tk.Frame(rel_content, bg=self.bg_color)
                rel_row.pack(fill=tk.X, pady=2)
                
                display_val = str(val)
                if len(display_val) > 15:  
                    display_val = display_val[:12] + "..."
                    
                tk.Label(rel_row, text=display_val, width=15, anchor="w",
                        bg=self.bg_color, fg=self.text_secondary, font=self.label_font).pack(side=tk.LEFT, padx=(0, 5))
                
                # Set default value to blank, but use preserved mapping if available
                if preserved_mappings and val in preserved_mappings:
                    default_val = preserved_mappings[val]
                else:
                    default_val = ""
                
                var = tk.StringVar(value=default_val)
                dropdown = ttk.Combobox(rel_row, textvariable=var, 
                                       values=["", "employee", "spouse", "dependent"], 
                                       state="readonly", width=10)
                dropdown.pack(side=tk.LEFT, padx=5)
                
                self.relationship_map[val] = var
        except Exception as e:
            print(f"Error updating relationship mapping: {e}")

    def validate_inputs(self):
        """Validate required fields before generating JSON"""
        try:
            client_name = self.client_var.get().strip()
            file_prefix = self.prefix_var.get().strip()
            integration_name = self.integration_var.get().strip()
            
            missing_fields = []
            if not client_name:
                missing_fields.append("Client Name")
            if not file_prefix:
                missing_fields.append("File Prefix")
            if not integration_name:
                missing_fields.append("Integration Name")
            
            if missing_fields:
                messagebox.showerror("Validation Error", 
                                   f"Please fill in the following required fields:\n\n" + 
                                   "\n".join(f"• {field}" for field in missing_fields))
                return False
                
            return True
        except Exception as e:
            print(f"Error validating inputs: {e}")
            messagebox.showerror("Validation Error", f"Error validating inputs: {e}")
            return False

    def generate_json(self):
        try:
            if self.df.empty:
                messagebox.showwarning("Warning", "Please upload and map a file first.")
                return

            if not self.validate_inputs():
                return

            # Get values
            client_name = self.client_var.get().strip()
            file_prefix = self.prefix_var.get().strip()
            integration_name = self.integration_var.get().strip()
            file_type = self.current_file_type

            # Determine file type based on uploaded file extension
            file_extension = os.path.splitext(self.file_path)[1].lower()
            if file_extension == '.csv':
                source_file_type = "csv"
            elif file_extension in ['.txt', '.tsv']:
                source_file_type = "txt"
            else:
                # Default fallback - could also show a warning
                source_file_type = "txt"

            # Create numbered columns list for reference
            numbered_columns = [f"{i}: {col}" for i, col in enumerate(self.df.columns)]

            fields_config = []
            for field, col_var in self.column_vars.items():
                selected_col = col_var.get()
                if selected_col and selected_col != "":
                    # Extract the actual column name from the numbered format "0: column_name"
                    if ":" in selected_col:
                        actual_col = selected_col.split(":", 1)[1].strip()
                        if actual_col in self.df.columns:
                            field_entry = {
                                "index": self.df.columns.get_loc(actual_col),
                                "type": "text",
                                "name": field
                            }
                            
                            # Handle date fields
                            if field in self.date_fields and field in self.date_format_vars:
                                selected_format = self.date_format_vars[field].get()
                                
                                if selected_format in self.date_formats:
                                    pattern = self.date_formats[selected_format]["regex"]
                                    conversion = self.date_formats[selected_format]["conversion"]
                                else:
                                    pattern = self.date_formats["yyyyMMdd"]["regex"]
                                    conversion = self.date_formats["yyyyMMdd"]["conversion"]
                                
                                # Add optional pattern for term_date if marked as optional
                                if self.optional_vars[field].get() and field == "term_date":
                                    if not pattern.endswith("|^$"):
                                        pattern += "|^$"
                                
                                field_entry["pattern"] = pattern
                                if conversion and bool(conversion):
                                    field_entry["conversion"] = conversion
                            
                            # Handle relationship mapping
                            elif field == "relationship" and "relationship" in self.special_fields and self.relationship_map:
                                valid_keys = [k for k in self.relationship_map.keys() 
                                            if self.relationship_map[k].get() != ""]
                                
                                if valid_keys:
                                    pattern = "(?i)^(" + "|".join(str(k).replace("-", "\\-") for k in valid_keys) + ")$"
                                    
                                    conversion = {str(k).lower(): self.relationship_map[k].get() 
                                                for k in valid_keys}
                                        
                                    field_entry["pattern"] = pattern
                                    field_entry["conversion"] = conversion
                                else:
                                    continue
                            
                            # Mark as optional if needed
                            if self.optional_vars[field].get():
                                field_entry["optional"] = True
                            
                            fields_config.append(field_entry)

            # Sort by column index
            fields_config.sort(key=lambda x: x["index"])

            # Build configuration
            task = file_type.lower().replace(" ", "_").replace("/", "_")
            delimiter = "\t" if self.delim_var.get() == "Tab" else self.delim_var.get()
            
            base_path = f"clients_restricted/{client_name}/eligibility" if self.restricted_client_var.get() else f"clients/{client_name}/eligibility"
            
            # Fields to add
            fields_to_add = {}
            if self.provider_var.get().strip():
                fields_to_add["health_plan_provider"] = self.provider_var.get()

            # Build configuration with conditional structure based on file type
            if file_type == "Formatting":
                config = {
                    "task": task,
                    "client": client_name,
                    "source": [
                        {
                            "file_category": "eligibility",
                            "restricted_client": self.restricted_client_var.get(),
                            "integration": integration_name,
                            "file_prefix": file_prefix,
                            "type": source_file_type,  # Use detected file type instead of hardcoded "txt"
                            "headers_line": self.headers_var.get(),
                            "delimiter": delimiter,
                            "storage": {
                                "type": "s3",
                                "key": "${AWS_S3_ACCESS_KEY}",
                                "secret": "${AWS_S3_SECRET_KEY}",
                                "region": "${AWS_S3_INTEGRATIONS_BUCKET_REGION}",
                                "bucket": "${AWS_S3_INTEGRATIONS_BUCKET}",
                                "path": base_path
                            },
                            "fields": fields_config
                        }
                    ],
                    "working_dir": "/tmp"
                }
            else:
                config = {
                    "task": task,
                    "client": client_name,
                    "source": [
                        {
                            "is_all_members_file": self.members_var.get(),
                            "integration": integration_name,
                            "file_prefix": file_prefix,
                            "type": source_file_type,  # Use detected file type instead of hardcoded "txt"
                            "headers_line": self.headers_var.get(),
                            "delimiter": delimiter,
                            "storage": {
                                "type": "s3",
                                "key": "${AWS_S3_ACCESS_KEY}",
                                "secret": "${AWS_S3_SECRET_KEY}",
                                "region": "${AWS_S3_INTEGRATIONS_BUCKET_REGION}",
                                "bucket": "${AWS_S3_INTEGRATIONS_BUCKET}",
                                "path": base_path
                            },
                            "fields": fields_config
                        }
                    ],
                    "working_dir": "/tmp"
                }

            source_config = config["source"][0]
            
            # Add fields_to_add right after storage and before fields
            if fields_to_add:
                # Insert fields_to_add before fields
                fields = source_config.pop("fields")
                source_config["fields_to_add"] = fields_to_add
                source_config["fields"] = fields

            # Save the configuration
            default_filename = f"{client_name}_{task}_config.json"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".json", 
                filetypes=[("JSON files", "*.json")],
                initialfile=default_filename,
                title="Save JSON Configuration"
            )
            
            if save_path:
                try:
                    with open(save_path, "w") as f:
                        json.dump(config, f, indent=2)
                    
                    # Show success message with summary (updated to show correct file type)
                    summary_msg = f"✅ JSON Configuration generated successfully!\n\n"
                    summary_msg += f"📁 File saved to: {save_path}\n\n"
                    summary_msg += f"📋 Configuration Summary:\n"
                    summary_msg += f"• Client: {client_name}\n"
                    summary_msg += f"• Integration: {integration_name}\n"
                    summary_msg += f"• File Type: {file_type}\n"
                    summary_msg += f"• Source File Type: {source_file_type}\n"  # Show the detected file type
                    summary_msg += f"• Task: {task}\n"
                    summary_msg += f"• Fields Mapped: {len(fields_config)}\n"
                    summary_msg += f"• Delimiter: {delimiter}\n"
                    summary_msg += f"• Headers: {'Yes' if self.headers_var.get() else 'No'}\n"
                    summary_msg += f"• Restricted Client: {'Yes' if self.restricted_client_var.get() else 'No'}\n\n"
                    summary_msg += f"🚀 Ready for processing!"
                    
                    messagebox.showinfo("Success", summary_msg)
                    
                except PermissionError:
                    messagebox.showerror("Error", f"Permission denied. Cannot write to:\n{save_path}\n\nPlease choose a different location or check file permissions.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")
        except Exception as e:
            print(f"Error generating JSON: {e}")
            messagebox.showerror("Error", f"Failed to generate configuration: {e}")


# This should be OUTSIDE the class, at module level
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = CSVConfigApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Critical error starting application: {e}")
        try:
            messagebox.showerror("Critical Error", f"Failed to start application:\n{e}")
        except Exception:
            print("Could not show error dialog")