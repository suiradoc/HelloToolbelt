import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import subprocess
import os
import threading
import sys
import json
import re
from pathlib import Path
from datetime import datetime

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg_color='#ffffff', *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.parent = parent
        
        container = tk.Frame(self, bg=bg_color)
        container.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(container, highlightthickness=0, bg=bg_color)
        self.scrollbar_v = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        
        self.canvas.configure(yscrollcommand=self.scrollbar_v.set)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_v.pack(side="right", fill="y")
        
        self.canvas_has_focus = False
        
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        self._setup_scrolling()
        
    def _setup_scrolling(self):
        self.in_toolbelt = self._detect_hellotoolbelt()
        
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        self.canvas.bind("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind("<Button-5>", self._on_mousewheel_linux)
        
        self._bind_mousewheel_to_children(self.scrollable_frame)
        
    def _detect_hellotoolbelt(self):
        try:
            current_parent = self.parent
            while current_parent:
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
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel_linux)
            widget.bind("<Button-5>", self._on_mousewheel_linux)
            
            for child in widget.winfo_children():
                self._bind_mousewheel_to_children(child)
        except Exception:
            pass
    
    def _on_enter(self, event):
        self.canvas_has_focus = True
        try:
            self.canvas.focus_set()
        except:
            pass
        
    def _on_leave(self, event):
        self.canvas_has_focus = False
        
    def _on_mousewheel(self, event):
        if self.in_toolbelt and not self.canvas_has_focus:
            return "break"
        
        return self._do_scroll(event)
        
    def _on_mousewheel_linux(self, event):
        if self.in_toolbelt and not self.canvas_has_focus:
            return "break"
        
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            return "break"
        
        return self._do_scroll_with_delta(delta)
    
    def _do_scroll(self, event):
        try:
            if hasattr(event, 'delta'):
                delta = int(-1 * (event.delta / 120))
            else:
                return "break"
            
            return self._do_scroll_with_delta(delta)
            
        except Exception:
            return "break"
    
    def _do_scroll_with_delta(self, delta):
        try:
            delta = max(-3, min(3, delta))
            
            current_top, current_bottom = self.canvas.yview()
            
            canvas_height = self.canvas.winfo_height()
            self.canvas.update_idletasks()  # Ensure geometry is up to date
            
            bbox = self.canvas.bbox("all")
            if not bbox:
                return "break"
            
            content_height = bbox[3] - bbox[1]  # bottom - top
            
            if content_height <= canvas_height:
                return "break"
            
            scroll_top = current_top
            scroll_bottom = current_bottom
            
            if delta < 0 and scroll_top <= 0.0:
                return "break"
                
            if delta > 0 and scroll_bottom >= 1.0:
                return "break"
            
            self.canvas.yview_scroll(delta, "units")
            return "break"
            
        except Exception as e:
            print(f"Scroll error: {e}")
            return "break"
        
    def check_scroll_needed(self):
        try:
            self.canvas.update_idletasks()
            bbox = self.canvas.bbox("all")
            if not bbox:
                self.scrollbar_v.pack_forget()
                return False
            
            canvas_height = self.canvas.winfo_height()
            content_height = bbox[3] - bbox[1]
            
            if content_height > canvas_height:
                self.scrollbar_v.pack(side="right", fill="y")
                return True
            else:
                self.scrollbar_v.pack_forget()
                return False
        except Exception:
            return False
    
    def _on_frame_configure(self, event):
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.after_idle(self.check_scroll_needed)
        except Exception:
            pass
        
    def _on_canvas_configure(self, event):
        try:
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
            self.canvas.after_idle(self._update_scroll_region)
            self.canvas.after_idle(self.check_scroll_needed)
        except Exception:
            pass
    
    def _update_scroll_region(self):
        try:
            self.canvas.update_idletasks()
            bbox = self.canvas.bbox("all")
            if bbox:
                self.canvas.configure(scrollregion=(0, bbox[1], 0, bbox[3]))
        except Exception:
            pass
    
    def force_scroll_update(self):
        self.canvas.after_idle(self._update_scroll_region)
        self.canvas.after_idle(lambda: self._bind_mousewheel_to_children(self.scrollable_frame))

class DLQFetcherTool:
    def __init__(self, root):
        self.root = root
        self.root.title("DLQ Fetcher Tool")
        
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        if not self.is_in_toolbelt:
            self.root.configure(bg='#ffffff')
        
        self.setup_adaptive_styling()
        
        self.root.minsize(900, 750)
        
        self.config_dir = self.get_config_directory()
        
        self.config_file = self.config_dir / ".dlq_fetcher_config.json"
        
        self.load_config()
        
        self.queue_options = [
            "dead_letter_integrations_prod",
            "dead_letter_chief_prod"
        ]
        
        self.current_process = None
        self.is_running = False
        
        self.build_gui()
        
        if not self.is_in_toolbelt:
            self._center_window()

    def get_config_directory(self):
        try:
            if getattr(sys, 'frozen', False):
                if sys.platform.startswith('win'):
                    app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
                    config_dir = Path(app_data) / 'HelloToolbelt'
                elif sys.platform.startswith('darwin'):
                    config_dir = Path.home() / 'Library' / 'Application Support' / 'HelloToolbelt'
                else:
                    config_dir = Path.home() / '.config' / 'HelloToolbelt'
            else:
                config_dir = Path(__file__).parent.absolute()
            
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir
            
        except Exception as e:
            fallback_dir = Path.home() / '.hellotoolbelt'
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir

    def get_default_jar_path(self):
        try:
            if getattr(sys, 'frozen', False):
                exe_dir = Path(sys.executable).parent
                jar_path = exe_dir / "DLQ_Fetcher.jar"
                
                if not jar_path.exists():
                    documents_path = Path.home() / 'Documents' / 'DLQ_Fetcher.jar'
                    if documents_path.exists():
                        return documents_path
                
                return jar_path
            else:
                script_dir = Path(__file__).parent.absolute()
                return script_dir / "DLQ_Fetcher.jar"
        except Exception:
            return Path.home() / "DLQ_Fetcher.jar"

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
        
        self.button_padx = 8
        self.button_pady = 4
        self.frame_padx = 20
        self.frame_pady = 15
        
        if self.is_dark_mode:
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.primary_color = "#c70c0c"
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#ffffff'
            self.text_secondary = '#cccccc'
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state
        else:
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.primary_color = '#c70c0c'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.text_secondary = '#34495e'
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state
        
        self.help_text_color = '#7f8c8d'

    def refresh_styling(self, is_dark_mode):
        self.is_dark_mode = is_dark_mode
        
        self.setup_adaptive_styling()
        
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.build_gui()

    def _center_window(self):
        window_width = 900
        window_height = 750
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    def build_gui(self):
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_content = tk.Frame(header_frame, bg=self.primary_color)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        header_icon = tk.Label(header_content, text="📨", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_label = tk.Label(header_content, text="DLQ Fetcher Tool", 
                               font=('Segoe UI', 16, 'bold'), bg=self.primary_color, fg='white')
        header_label.pack(side=tk.LEFT, anchor='w')
        
        self.scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color, bg=self.bg_color)
        self.scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        content_container = self.scrollable_container.scrollable_frame
        content_container.configure(bg=self.bg_color)
        
        self._build_configuration_section(content_container)
        self._build_action_section(content_container)
        self._build_output_section(content_container)
        
        def update_scroll_after_build():
            try:
                if hasattr(self, 'scrollable_container'):
                    self.scrollable_container.force_scroll_update()
                    self.scrollable_container._bind_mousewheel_to_children(self.scrollable_container.scrollable_frame)
            except Exception as e:
                print(f"Error updating scroll: {e}")
        
        self.root.after(100, update_scroll_after_build)
        self.root.after(500, update_scroll_after_build)
        self.root.after(1000, update_scroll_after_build)

    def _build_configuration_section(self, parent):
        config_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        config_header = tk.Frame(config_frame, bg=self.header_bg, height=50, cursor="hand2")
        config_header.pack(fill=tk.X)
        
        config_header.bind("<Button-1>", self._toggle_configuration)
        
        header_content = tk.Frame(config_header, bg=self.header_bg, cursor="hand2")
        header_content.pack(fill=tk.X, pady=15)
        header_content.bind("<Button-1>", self._toggle_configuration)
        
        self.config_arrow = tk.Label(header_content, text="▼", font=("Segoe UI", 12), 
                                    bg=self.header_bg, fg=self.text_color, cursor="hand2")
        self.config_arrow.pack(side=tk.LEFT, padx=(20, 5))
        self.config_arrow.bind("<Button-1>", self._toggle_configuration)
        
        config_label = tk.Label(header_content, text="⚙️ Configuration", font=self.subtitle_font, 
                               bg=self.header_bg, fg=self.text_color, cursor="hand2")
        config_label.pack(side=tk.LEFT)
        config_label.bind("<Button-1>", self._toggle_configuration)
        
        jar_exists = self.jar_path.exists()
        status_text = f"({self.queue_name}) - {'Ready' if jar_exists else 'Needs Setup'}"
        self.config_status_header = tk.Label(header_content, text=status_text, 
                                           font=("Segoe UI", 9), bg=self.header_bg, 
                                           fg=self.help_text_color, cursor="hand2")
        self.config_status_header.pack(side=tk.RIGHT, padx=(0, 20))
        self.config_status_header.bind("<Button-1>", self._toggle_configuration)
        
        self.config_content = tk.Frame(config_frame, bg=self.frame_bg)
        
        jar_exists = self.jar_path.exists()
        queue_is_set = bool(self.queue_name and self.queue_name in self.queue_options)
        self.config_expanded = not (jar_exists and queue_is_set)
        
        jar_frame = tk.Frame(self.config_content, bg=self.frame_bg)
        jar_frame.pack(fill=tk.X, pady=(20, 15), padx=20)
        
        jar_label = tk.Label(jar_frame, text="JAR File Path:", font=self.label_font, 
                            bg=self.frame_bg, fg=self.text_color)
        jar_label.pack(anchor='w', pady=(0, 5))
        
        jar_path_frame = tk.Frame(jar_frame, bg=self.bg_color, relief='solid', bd=1)
        jar_path_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.jar_path_var = tk.StringVar(value=str(self.jar_path))
        jar_entry = tk.Entry(jar_path_frame, textvariable=self.jar_path_var, font=self.text_font,
                            bg=self.bg_color, fg=self.text_color, relief='flat', bd=0)
        jar_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)
        
        browse_btn = tk.Button(jar_path_frame, text="Browse", command=self.browse_jar_file,
                              padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                              bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        browse_btn.pack(side=tk.RIGHT, padx=(5, 10))
        
        separator1 = tk.Frame(self.config_content, bg=self.header_bg, height=1)
        separator1.pack(fill=tk.X, padx=20, pady=(0, 15))

        sheets_header_frame = tk.Frame(self.config_content, bg=self.frame_bg)
        sheets_header_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

        sheets_header_label = tk.Label(sheets_header_frame, text="📊 Google Sheets Configuration", 
                                    font=("Segoe UI", 10, "bold"), bg=self.frame_bg, fg=self.text_color)
        sheets_header_label.pack(anchor='w')

        sheets_desc = tk.Label(sheets_header_frame, 
                            text="Configure Google Sheets export settings (optional)",
                            font=("Segoe UI", 9), fg=self.help_text_color, bg=self.frame_bg)
        sheets_desc.pack(anchor='w', pady=(2, 0))

        sheets_url_frame = tk.Frame(self.config_content, bg=self.frame_bg)
        sheets_url_frame.pack(fill=tk.X, pady=(0, 15), padx=20)

        sheets_url_label = tk.Label(sheets_url_frame, text="Google Sheets URL:", 
                                    font=self.label_font, bg=self.frame_bg, fg=self.text_color)
        sheets_url_label.pack(anchor='w', pady=(0, 5))

        sheets_url_entry_frame = tk.Frame(sheets_url_frame, bg=self.bg_color, relief='solid', bd=1)
        sheets_url_entry_frame.pack(fill=tk.X, pady=(0, 5))

        self.sheets_url_var = tk.StringVar(value=self.config.get('sheets_url', ''))
        sheets_url_entry = tk.Entry(sheets_url_entry_frame, textvariable=self.sheets_url_var,
                                    font=self.text_font, bg=self.bg_color, fg=self.text_color,
                                    relief='flat', bd=0)
        sheets_url_entry.pack(fill=tk.X, padx=10, pady=8)
        sheets_url_entry.bind('<FocusOut>', lambda e: self._save_sheets_config())

        sheets_url_help = tk.Label(sheets_url_frame, 
                                text="Paste the full Google Sheets URL (e.g., https://docs.google.com/spreadsheets/d/YOUR_ID/edit)",
                                font=("Segoe UI", 8), fg=self.help_text_color, bg=self.frame_bg,
                                justify=tk.LEFT, wraplength=800)
        sheets_url_help.pack(anchor='w')

        service_account_frame = tk.Frame(self.config_content, bg=self.frame_bg)
        service_account_frame.pack(fill=tk.X, pady=(0, 15), padx=20)

        service_account_label = tk.Label(service_account_frame, text="Service Account JSON Path:", 
                                        font=self.label_font, bg=self.frame_bg, fg=self.text_color)
        service_account_label.pack(anchor='w', pady=(0, 5))

        service_account_path_frame = tk.Frame(service_account_frame, bg=self.bg_color, relief='solid', bd=1)
        service_account_path_frame.pack(fill=tk.X, pady=(0, 5))

        self.service_account_var = tk.StringVar(value=self.config.get('service_account_path', ''))
        service_account_entry = tk.Entry(service_account_path_frame, textvariable=self.service_account_var,
                                        font=self.text_font, bg=self.bg_color, fg=self.text_color,
                                        relief='flat', bd=0)
        service_account_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)

        browse_sa_btn = tk.Button(service_account_path_frame, text="Browse", command=self.browse_service_account,
                                padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                                bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        browse_sa_btn.pack(side=tk.RIGHT, padx=(5, 10))

        service_account_help = tk.Label(service_account_frame, 
                                    text="Path to your Google Service Account JSON file (for server-to-server authentication)",
                                    font=("Segoe UI", 8), fg=self.help_text_color, bg=self.frame_bg,
                                    justify=tk.LEFT, wraplength=800)
        service_account_help.pack(anchor='w')

        self._add_button_hover(browse_sa_btn, self.primary_color, '#2980b9')

        separator2 = tk.Frame(self.config_content, bg=self.header_bg, height=1)
        separator2.pack(fill=tk.X, padx=20, pady=(0, 15))

        status_frame = tk.Frame(self.config_content, bg=self.frame_bg)
        status_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        status_title = tk.Label(status_frame, text="Status:", font=("Segoe UI", 10, "bold"), 
                               bg=self.frame_bg, fg=self.text_color)
        status_title.pack(anchor="w", pady=(0, 5))
        
        self.status_label = tk.Label(status_frame, text=self._get_initial_status(), 
                                    font=("Segoe UI", 10), bg=self.frame_bg, fg=self.help_text_color)
        self.status_label.pack(anchor="w")
        
        self._add_button_hover(browse_btn, self.primary_color, '#2980b9')
        
        self._update_configuration_display()

    def _toggle_configuration(self, event=None):
        self.config_expanded = not self.config_expanded
        self._update_configuration_display()
    
    def _update_configuration_display(self):
        if self.config_expanded:
            self.config_content.pack(fill=tk.X)
            self.config_arrow.config(text="▼")
        else:
            self.config_content.pack_forget()
            self.config_arrow.config(text="▶")
        
        jar_exists = self.jar_path.exists()
        status_text = f"({self.queue_name}) - {'Ready' if jar_exists else 'Needs Setup'}"
        self.config_status_header.config(text=status_text)

    def _on_queue_changed(self, event=None):
        self.queue_name = self.queue_name_var.get()
        self.save_config()
        self._update_configuration_display()

    def _build_action_section(self, parent):
        action_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        action_header = tk.Frame(action_frame, bg=self.header_bg, height=50)
        action_header.pack(fill=tk.X)
        
        action_label = tk.Label(action_header, text="🚀 Actions", font=self.subtitle_font,
                            bg=self.header_bg, fg=self.text_color)
        action_label.pack(pady=15)
        
        action_content = tk.Frame(action_frame, bg=self.frame_bg)
        action_content.pack(fill=tk.X, padx=20, pady=20)
        
        queue_section_frame = tk.Frame(action_content, bg=self.frame_bg)
        queue_section_frame.pack(fill=tk.X, pady=(0, 15))
        
        queue_section_label = tk.Label(queue_section_frame, text="Select Queue:", 
                                    font=("Segoe UI", 10, "bold"), bg=self.frame_bg, fg=self.text_color)
        queue_section_label.pack(anchor='w', pady=(0, 8))
        
        queue_combo_frame = tk.Frame(queue_section_frame, bg=self.bg_color, relief='solid', bd=1)
        queue_combo_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.queue_name_var = tk.StringVar(value=self.queue_name)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        if self.is_dark_mode:
            style.configure('Action.TCombobox',
                        fieldbackground=self.bg_color,
                        background=self.bg_color,
                        foreground=self.text_color,
                        borderwidth=0,
                        relief='flat')
            style.map('Action.TCombobox',
                    fieldbackground=[('readonly', self.bg_color)],
                    selectbackground=[('readonly', self.primary_color)],
                    selectforeground=[('readonly', 'white')])
        else:
            style.configure('Action.TCombobox',
                        fieldbackground=self.bg_color,
                        background=self.bg_color,
                        foreground=self.text_color,
                        borderwidth=0,
                        relief='flat')
            style.map('Action.TCombobox',
                    fieldbackground=[('readonly', self.bg_color)],
                    selectbackground=[('readonly', self.primary_color)],
                    selectforeground=[('readonly', 'white')])
        
        self.queue_combo = ttk.Combobox(queue_combo_frame, textvariable=self.queue_name_var,
                                    values=self.queue_options, state="readonly",
                                    font=self.text_font, style='Action.TCombobox')
        self.queue_combo.pack(fill=tk.X, padx=10, pady=8)
        self.queue_combo.bind('<<ComboboxSelected>>', self._on_queue_changed)
        
        sheet_tab_section_frame = tk.Frame(action_content, bg=self.frame_bg)
        sheet_tab_section_frame.pack(fill=tk.X, pady=(0, 15))
        
        sheet_tab_section_label = tk.Label(sheet_tab_section_frame, text="Google Sheets Tab Name:", 
                                        font=("Segoe UI", 10, "bold"), bg=self.frame_bg, fg=self.text_color)
        sheet_tab_section_label.pack(anchor='w', pady=(0, 8))
        
        sheet_tab_entry_frame = tk.Frame(sheet_tab_section_frame, bg=self.bg_color, relief='solid', bd=1)
        sheet_tab_entry_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.sheet_tab_var = tk.StringVar(value=self.config.get('sheet_tab_name', 'Sheet1'))
        sheet_tab_entry = tk.Entry(sheet_tab_entry_frame, textvariable=self.sheet_tab_var,
                                font=self.text_font, bg=self.bg_color, fg=self.text_color,
                                relief='flat', bd=0)
        sheet_tab_entry.pack(fill=tk.X, padx=10, pady=8)
        sheet_tab_entry.bind('<FocusOut>', lambda e: self._save_sheets_config())
        
        sheet_tab_help = tk.Label(sheet_tab_section_frame, 
                                text="Tab name to export to (e.g., Sheet1, DLQ_Data). Data will be appended to this tab.",
                                font=("Segoe UI", 8), fg=self.help_text_color, bg=self.frame_bg,
                                justify=tk.LEFT, wraplength=800)
        sheet_tab_help.pack(anchor='w')
        
        separator = tk.Frame(action_content, bg=self.header_bg, height=1)
        separator.pack(fill=tk.X, pady=(0, 15))
        
        buttons_frame = tk.Frame(action_content, bg=self.frame_bg)
        buttons_frame.pack(pady=(0, 15))
        
        self.run_btn = tk.Button(buttons_frame, text="▶️ Run DLQ Fetcher", command=self.run_dlq_fetcher,
                                padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                                bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        self.run_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        self.stop_btn = tk.Button(buttons_frame, text="⏹️ Stop Process", command=self.stop_process,
                                padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                                bg=self.danger_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2",
                                state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        clear_btn = tk.Button(buttons_frame, text="🗑️ Clear Output", command=self.clear_output,
                            padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 10),
                            bg='#95a5a6', fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        clear_btn.pack(side=tk.LEFT)
        
        self._add_button_hover(self.run_btn, self.success_color, '#229954')
        self._add_button_hover(self.stop_btn, self.danger_color, '#c0392b')
        self._add_button_hover(clear_btn, '#95a5a6', '#7f8c8d')
        
        help_frame = tk.Frame(action_content, bg=self.frame_bg)
        help_frame.pack(fill=tk.X)
        
        help_text = ("Click 'Run DLQ Fetcher' to execute the JAR file with the selected queue. "
                    "If it doesn't pull anything the first time, please run again, sometimes it hangs.")
        help_label = tk.Label(help_frame, text=help_text, font=("Segoe UI", 9), 
                            fg=self.help_text_color, bg=self.frame_bg, justify=tk.LEFT, wraplength=800)
        help_label.pack(anchor="w")

    def _add_button_hover(self, button, normal_color, hover_color, normal_fg=None, hover_fg=None):
        try:
            if normal_fg is None:
                normal_fg = getattr(self, 'button_text_color', '#000000')
            if hover_fg is None:
                hover_fg = getattr(self, 'button_hover_text_color', '#000000')
                
            def on_enter(e):
                try:
                    if button['state'] != tk.DISABLED and button.winfo_exists():
                        button.config(bg=hover_color, fg=hover_fg)
                except tk.TclError:
                    pass
            
            def on_leave(e):
                try:
                    if button['state'] != tk.DISABLED and button.winfo_exists():
                        button.config(bg=normal_color, fg=normal_fg)
                except tk.TclError:
                    pass
            
            button.bind("<Enter>", on_enter)
            button.bind("<Leave>", on_leave)
        except Exception as e:
            print(f"Warning: Could not add button hover: {e}")

    def _get_initial_status(self):
        jar_exists = self.jar_path.exists()
        if jar_exists:
            return f"✅ JAR file found at: {self.jar_path}"
        else:
            return f"❌ JAR file not found at: {self.jar_path}"

    def _update_status(self, message, color=None):
        if color is None:
            color = self.help_text_color
        self.status_label.config(text=message, fg=color)

    def browse_jar_file(self):
        file_path = filedialog.askopenfilename(
            title="Select DLQ_Fetcher.jar",
            filetypes=[("JAR files", "*.jar"), ("All files", "*.*")],
            initialdir=str(self.config_dir)
        )
        if file_path:
            self.jar_path = Path(file_path)
            self.jar_path_var.set(str(self.jar_path))
            self._update_status(f"✅ JAR file selected: {self.jar_path}", self.help_text_color)
            self.save_config()
            self._update_configuration_display()

    def run_dlq_fetcher(self):
        if self.is_running:
            self._update_status("⚠️ Process is already running", self.help_text_color)
            return
        
        jar_path = Path(self.jar_path_var.get())
        queue_name = self.queue_name_var.get().strip()
        
        if not jar_path.exists():
            self._update_status("❌ JAR file not found", self.help_text_color)
            messagebox.showerror("Error", f"JAR file not found: {jar_path}")
            return
        
        if not queue_name:
            self._update_status("❌ Queue name cannot be empty", self.help_text_color)
            messagebox.showerror("Error", "Please select a queue name")
            return
        
        self.jar_path = jar_path  # Update the jar_path instance variable
        self.queue_name = queue_name
        self.save_config()
        
        command = ["java", "-jar", str(jar_path), queue_name]
        
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, f"Running command: {' '.join(command)}\n")
        self.output_text.insert(tk.END, "=" * 50 + "\n\n")
        
        self.is_new_run = True
        
        self.is_running = True
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._update_status("🚀 Running DLQ Fetcher...", self.help_text_color)
        
        self.process_thread = threading.Thread(target=self._run_process, args=(command,))
        self.process_thread.daemon = True
        self.process_thread.start()

    def _run_process(self, command):
        try:
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            previous_line = ""
            
            for line in iter(self.current_process.stdout.readline, ''):
                if line:
                    stripped_line = line.strip()
                    
                    formatted_line = self._format_uuid_json_line(stripped_line)
                    
                    if (stripped_line and 
                        previous_line.strip() and 
                        not self.is_new_run and
                        self._is_new_result(stripped_line)):
                        self.root.after(0, self._append_output, "\n" + "-" * 50 + "\n\n")
                    
                    output_line = formatted_line if formatted_line != stripped_line else line
                    self.root.after(0, self._append_output, output_line)
                    
                    previous_line = line
                    self.is_new_run = False
            
            return_code = self.current_process.wait()
            
            if not self.is_new_run:
                self.root.after(0, self._append_output, "\n" + "=" * 50 + "\n")
            
            if return_code == 0:
                self.root.after(0, self._update_status, "✅ Process completed successfully", self.help_text_color)
            else:
                self.root.after(0, self._update_status, f"❌ Process failed with code: {return_code}", self.help_text_color)
                
        except FileNotFoundError:
            self.root.after(0, self._update_status, "❌ Java not found. Please install Java.", self.help_text_color)
            self.root.after(0, self._append_output, "Error: Java not found. Please install Java and ensure it's in your PATH.\n")
        except Exception as e:
            self.root.after(0, self._update_status, f"❌ Error: {str(e)}", self.help_text_color)
            self.root.after(0, self._append_output, f"Error: {str(e)}\n")
        finally:
            self.root.after(0, self._reset_ui_state)

    def _format_uuid_json_line(self, line):
        uuid_chars = '0123456789abcdef-'
        
        if (len(line) > 36 and 
            line[8] == '-' and line[13] == '-' and line[18] == '-' and line[23] == '-' and
            all(c.lower() in uuid_chars for c in line[:36]) and
            line[36:].strip().startswith('{')):
            
            uuid_part = line[:36]
            json_part = line[36:].strip()
            
            return f"{uuid_part}\n{json_part}\n"
        
        return line

    def _is_new_result(self, line):
        if (len(line) > 36 and 
            line[8] == '-' and line[13] == '-' and line[18] == '-' and line[23] == '-'):
            uuid_chars = '0123456789abcdef-'
            if all(c.lower() in uuid_chars for c in line[:36]):
                return True
                
        return (line.startswith('{') or 
                line.startswith('[') or 
                'result' in line.lower() or 
                'message' in line.lower() or 
                line.startswith('Processing') or 
                line.startswith('Found'))

    def _append_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.update()

    def _reset_ui_state(self):
        self.is_running = False
        self.run_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.current_process = None

    def stop_process(self):
        if self.current_process and self.is_running:
            try:
                self.current_process.terminate()
                self._update_status("⏹️ Process stopped", self.help_text_color)
                self._append_output("\n--- Process stopped by user ---\n")
            except Exception as e:
                self._update_status(f"❌ Error stopping process: {str(e)}", self.help_text_color)
        else:
            self._update_status("⚠️ No process is running", self.help_text_color)

    def clear_output(self):
        self.output_text.delete("1.0", tk.END)
        self._update_status("🗑️ Output cleared", self.help_text_color)

    def copy_output(self):
        output = self.output_text.get("1.0", tk.END).strip()
        if output:
            self.root.clipboard_clear()
            self.root.clipboard_append(output)
            self.root.update()
            self._update_status("📋 Output copied to clipboard", self.help_text_color)
            messagebox.showinfo("Copied", "✅ Output copied to clipboard!")
        else:
            self._update_status("❌ No output to copy", self.help_text_color)
    
    def save_output(self):
        output = self.output_text.get("1.0", tk.END).strip()
        if not output:
            self._update_status("❌ No output to save", self.help_text_color)
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Output",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")],
            initialdir=str(self.config_dir)
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(output)
                self._update_status(f"💾 Output saved to: {file_path}", self.help_text_color)
                messagebox.showinfo("Saved", f"✅ Output saved to:\n{file_path}")
            except Exception as e:
                self._update_status(f"❌ Error saving file: {str(e)}", self.help_text_color)
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")

    def _build_output_section(self, parent):
        output_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        output_header = tk.Frame(output_frame, bg=self.header_bg, height=50)
        output_header.pack(fill=tk.X)
        
        output_label = tk.Label(output_header, text="📋 Output", font=self.subtitle_font,
                               bg=self.header_bg, fg=self.text_color)
        output_label.pack(pady=15)
        
        output_content = tk.Frame(output_frame, bg=self.frame_bg)
        output_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        text_frame = tk.Frame(output_content, bg=self.bg_color, relief='solid', bd=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.output_text = scrolledtext.ScrolledText(text_frame, height=12, width=80, font=('Consolas', 10),
                                                    bg=self.bg_color, fg=self.text_color,
                                                    selectbackground=self.primary_color,
                                                    selectforeground='white',
                                                    relief='flat', bd=0,
                                                    padx=10, pady=10, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        output_buttons_frame = tk.Frame(output_content, bg=self.frame_bg)
        output_buttons_frame.pack(fill=tk.X)
        
        copy_output_btn = tk.Button(output_buttons_frame, text="📋 Copy Output", command=self.copy_output,
                                   padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                                   bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        copy_output_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        save_output_btn = tk.Button(output_buttons_frame, text="💾 Save Output", command=self.save_output,
                                   padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                                   bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        save_output_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_sheets_btn = tk.Button(output_buttons_frame, text="📊 Export to Sheets", command=self.export_to_sheets,
                                     padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                                     bg='#34495e', fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        export_sheets_btn.pack(side=tk.LEFT)
        
        self._add_button_hover(copy_output_btn, self.primary_color, '#2980b9')
        self._add_button_hover(save_output_btn, self.success_color, '#229954')
        self._add_button_hover(export_sheets_btn, '#34495e', '#2c3e50')

    def _save_sheets_config(self):
        self.config['sheets_url'] = self.sheets_url_var.get().strip()
        self.config['service_account_path'] = self.service_account_var.get().strip()
        self.config['sheet_tab_name'] = self.sheet_tab_var.get().strip() or 'Sheet1'
        self.save_config()
        self._update_configuration_display()

    def browse_service_account(self):
        file_path = filedialog.askopenfilename(
            title="Select Service Account JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(self.config_dir)
        )
        if file_path:
            self.service_account_var.set(file_path)
            self._save_sheets_config()
            self._update_status(f"✅ Service Account JSON selected: {file_path}", self.help_text_color)

    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                    
                jar_path_str = self.config.get('jar_path', '')
                if jar_path_str and Path(jar_path_str).exists():
                    self.jar_path = Path(jar_path_str)
                else:
                    self.jar_path = self.get_default_jar_path()
                    
                self.queue_name = self.config.get('queue_name', "dead_letter_integrations_prod")
            else:
                self.config = {}
                self.jar_path = self.get_default_jar_path()
                self.queue_name = "dead_letter_integrations_prod"
                self.save_config()
                
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            self.config = {}
            self.jar_path = self.get_default_jar_path()
            self.queue_name = "dead_letter_integrations_prod"

    def save_config(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            config = {
                'jar_path': str(self.jar_path),
                'queue_name': self.queue_name,
                'sheets_url': self.config.get('sheets_url', ''),
                'service_account_path': self.config.get('service_account_path', ''),
                'sheet_tab_name': self.config.get('sheet_tab_name', 'Sheet1')
            }
            
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.bak')
                if backup_file.exists():
                    backup_file.unlink()
                self.config_file.rename(backup_file)
            
            temp_file.rename(self.config_file)
            
            backup_file = self.config_file.with_suffix('.bak')
            if backup_file.exists():
                backup_file.unlink()
                
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def parse_output_data(self):
        output = self.output_text.get("1.0", tk.END).strip()
        if not output:
            return []
        
        data = []
        lines = output.split('\n')
        
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if uuid_pattern.match(line):
                uuid = line
                
                if i + 1 < len(lines):
                    json_line = lines[i + 1].strip()
                    if json_line.startswith('{'):
                        try:
                            json_data = json.loads(json_line)
                            data.append({
                                'uuid': uuid,
                                'json': json_data,
                                'json_str': json_line
                            })
                            i += 2
                            continue
                        except json.JSONDecodeError:
                            pass
            
            i += 1
        
        return data

    def export_to_sheets(self):
        sheets_url = self.config.get('sheets_url', '').strip()
        service_account_path = self.config.get('service_account_path', '').strip()
        
        if not sheets_url:
            messagebox.showerror("Error", "Please configure Google Sheets URL in Configuration section first.")
            return
        
        if not service_account_path or not Path(service_account_path).exists():
            messagebox.showerror("Error", "Please configure a valid Service Account JSON file in Configuration section first.")
            return
        
        sheets_id = self._extract_sheet_id(sheets_url)
        if not sheets_id:
            messagebox.showerror("Error", "Invalid Google Sheets URL. Please use the full URL from your browser.")
            return
        
        data = self.parse_output_data()
        if not data:
            messagebox.showwarning("Warning", "No valid data found to export.\n\nExpected format:\nUUID\n{JSON data}")
            return
        
        self._update_status(f"📊 Exporting {len(data)} records to Google Sheets...", self.help_text_color)
        
        export_thread = threading.Thread(target=self._do_sheets_export, args=(sheets_id, service_account_path, data))
        export_thread.daemon = True
        export_thread.start()

    def _extract_sheet_id(self, url):
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        return None

    def _do_sheets_export(self, sheets_id, service_account_path, data):
        try:
            from google.oauth2 import service_account
            
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            try:
                creds = service_account.Credentials.from_service_account_file(
                    service_account_path, scopes=SCOPES)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", 
                    f"Failed to load service account credentials:\n\n{str(e)}\n\n"
                    f"Please ensure:\n"
                    f"1. The JSON file is valid\n"
                    f"2. It's a service account key (not OAuth client)\n"
                    f"3. The service account has access to the sheet"
                ))
                self.root.after(0, self._update_status, "❌ Failed to load credentials", self.danger_color)
                return
            
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            
            tab_name = self.config.get('sheet_tab_name', 'Sheet1').strip() or 'Sheet1'
            
            try:
                spreadsheet = sheet.get(spreadsheetId=sheets_id).execute()
                sheet_exists = any(s['properties']['title'] == tab_name for s in spreadsheet['sheets'])
                
                if not sheet_exists:
                    request_body = {
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': tab_name
                                }
                            }
                        }]
                    }
                    sheet.batchUpdate(spreadsheetId=sheets_id, body=request_body).execute()
                    self.root.after(0, lambda: print(f"Created new tab: {tab_name}"))
            except Exception as e:
                self.root.after(0, lambda: print(f"Error checking/creating tab: {e}"))
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            headers = ['Timestamp', 'UUID', 'Raw JSON']
            values = [headers]
            
            for record in data:
                values.append([
                    timestamp,
                    record['uuid'],
                    record['json_str']
                ])
            
            body = {'values': values}
            
            result = sheet.values().append(
                spreadsheetId=sheets_id,
                range=f'{tab_name}!A1',  # Use configured tab name
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            updates = result.get('updates', {})
            updated_cells = updates.get('updatedCells', 0)
            updated_rows = updates.get('updatedRows', 0)
            
            sheets_url = self.config.get('sheets_url', '')
            self.root.after(0, lambda: messagebox.showinfo(
                "Success", 
                f"✅ Successfully exported {len(data)} records to '{tab_name}' tab!\n\n"
                f"Updated {updated_rows} rows ({updated_cells} cells)\n\n"
                f"View at: {sheets_url}"
            ))
            self.root.after(0, self._update_status, 
                          f"✅ Exported {len(data)} records to '{tab_name}' tab", 
                          self.success_color)
            
        except HttpError as error:
            error_msg = str(error)
            tab_name = self.config.get('sheet_tab_name', 'Sheet1').strip() or 'Sheet1'
            self.root.after(0, lambda: messagebox.showerror(
                "Google Sheets Error", 
                f"Failed to export to Google Sheets:\n\n{error_msg}\n\n"
                f"Please check:\n"
                f"1. Sheet URL is correct\n"
                f"2. Service account has edit access to the sheet\n"
                f"3. Google Sheets API is enabled in your project\n"
                f"4. Share the sheet with the service account email"
            ))
            self.root.after(0, self._update_status, f"❌ Export failed: {error}", self.danger_color)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(
                "Error", 
                f"An error occurred:\n\n{error_msg}"
            ))
            self.root.after(0, self._update_status, f"❌ Export failed: {error_msg}", self.danger_color)
            
if __name__ == "__main__":
    root = tk.Tk()
    app = DLQFetcherTool(root)
    root.mainloop()