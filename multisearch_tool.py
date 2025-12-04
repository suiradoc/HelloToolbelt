import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pandas as pd
import os
import glob
import threading
from pathlib import Path

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

class MultiFileColumnSearchTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-File Column Search Tool")
        
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        if not self.is_in_toolbelt:
            self.root.configure(bg='#ffffff')
        
        self.setup_adaptive_styling()
        
        self.root.minsize(1000, 800)
        
        self.search_folder_path = tk.StringVar()
        self.search_column_name = tk.StringVar()
        self.search_delimiter = tk.StringVar(value="auto")
        
        self.csv_enabled = tk.BooleanVar(value=True)
        self.xlsx_enabled = tk.BooleanVar(value=True)
        self.xls_enabled = tk.BooleanVar(value=True)
        self.tsv_enabled = tk.BooleanVar(value=True)
        self.txt_enabled = tk.BooleanVar(value=True)
        
        self.search_results = {}
        
        self.build_interface()
        
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
        
        self.button_padx = 8
        self.button_pady = 4
        self.frame_padx = 20
        self.frame_pady = 15
        
        if self.is_dark_mode:
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.primary_color = '#df9621'
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
            self.primary_color = '#df9621'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.text_secondary = '#34495e'
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state

    def refresh_styling(self, is_dark_mode):
        self.is_dark_mode = is_dark_mode
        
        if self.is_in_toolbelt:
            try:
                parent_bg = self.root.cget('bg')
                parent_fg = self.root.cget('fg')
            except:
                if is_dark_mode:
                    parent_bg = '#2b2b2b'
                    parent_fg = '#ffffff'
                else:
                    parent_bg = '#ffffff'
                    parent_fg = '#2c3e50'
        else:
            if is_dark_mode:
                parent_bg = '#2b2b2b'
                parent_fg = '#ffffff'
            else:
                parent_bg = '#ffffff'
                parent_fg = '#2c3e50'
        
        if is_dark_mode:
            self.bg_color = parent_bg
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.primary_color = '#df9621'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg
            self.text_secondary = '#cccccc'
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state
        else:
            self.bg_color = parent_bg
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.primary_color = '#df9621'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg
            self.text_secondary = '#34495e'
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state
        
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.build_interface()

    def _center_window(self):
        window_width = 1200
        window_height = 1000
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    def build_interface(self):
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_content = tk.Frame(header_frame, bg=self.primary_color)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        header_icon = tk.Label(header_content, text="📂", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_label = tk.Label(header_content, text="Multi-File Column Search Tool", 
                               font=('Segoe UI', 16, 'bold'), bg=self.primary_color, fg='white')
        header_label.pack(side=tk.LEFT, anchor='w')
        
        self.scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color, bg=self.bg_color)
        self.scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        content_container = self.scrollable_container.scrollable_frame
        content_container.configure(bg=self.bg_color)
        
        self._build_folder_selection_section(content_container)
        self._build_column_search_section(content_container)
        self._build_search_values_section(content_container)
        self._build_file_settings_section(content_container)
        self._build_action_section(content_container)
        self._build_progress_section(content_container)
        self._build_results_section(content_container)
        
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

    def _add_button_hover(self, button, normal_color, hover_color, normal_fg=None, hover_fg=None):
        if normal_fg is None:
            normal_fg = getattr(self, 'button_text_color', '#000000')
        if hover_fg is None:
            hover_fg = getattr(self, 'button_hover_text_color', '#000000')
            
        def on_enter(e):
            button.config(bg=hover_color, fg=hover_fg)
        
        def on_leave(e):
            button.config(bg=normal_color, fg=normal_fg)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _build_folder_selection_section(self, parent):
        folder_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        folder_header = tk.Frame(folder_frame, bg=self.header_bg, height=50)
        folder_header.pack(fill=tk.X)
        
        folder_label = tk.Label(folder_header, text="📁 Step 1: Select Search Location", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        folder_label.pack(pady=15)
        
        folder_content = tk.Frame(folder_frame, bg=self.frame_bg)
        folder_content.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(folder_content, text="Folder to search:", font=self.label_font, 
                bg=self.frame_bg, fg=self.text_secondary).pack(anchor="w", pady=(0, 10))
        
        path_frame = tk.Frame(folder_content, bg=self.frame_bg)
        path_frame.pack(fill=tk.X, pady=(0, 15))
        
        path_entry_frame = tk.Frame(path_frame, bg=self.bg_color, relief='solid', bd=1)
        path_entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        path_entry = tk.Entry(path_entry_frame, textvariable=self.search_folder_path, font=self.text_font,
                             bg=self.bg_color, fg=self.text_color, relief='flat', bd=0)
        path_entry.pack(fill=tk.X, padx=10, pady=8)
        
        browse_button = tk.Button(path_frame, text="📁 Browse", command=self.browse_search_folder,
                                 padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                 bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        browse_button.pack(side=tk.RIGHT)
        
        self._add_button_hover(browse_button, self.success_color, '#229954')
        
        help_text = ("Select the folder containing your data files. All supported file types will be searched recursively.\n"
                    "The tool will scan through all subdirectories for matching files.")
        help_label = tk.Label(folder_content, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
        help_label.pack(anchor="w")

    def _build_column_search_section(self, parent):
        column_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        column_frame.pack(fill=tk.X, pady=(0, 15))
        
        column_header = tk.Frame(column_frame, bg=self.header_bg, height=50)
        column_header.pack(fill=tk.X)
        
        column_label = tk.Label(column_header, text="🔍 Step 2: Specify Column to Search", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        column_label.pack(pady=15)
        
        column_content = tk.Frame(column_frame, bg=self.frame_bg)
        column_content.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(column_content, text="Column name:", font=self.label_font, 
                bg=self.frame_bg, fg=self.text_secondary).pack(anchor="w", pady=(0, 10))
        
        column_entry_frame = tk.Frame(column_content, bg=self.bg_color, relief='solid', bd=1)
        column_entry_frame.pack(anchor="w", pady=(0, 15))
        
        column_entry = tk.Entry(column_entry_frame, textvariable=self.search_column_name, 
                               font=self.text_font, bg=self.bg_color, fg=self.text_color, 
                               relief='flat', bd=0, width=30)
        column_entry.pack(padx=10, pady=8)
        
        help_text = ("Enter the exact column header name (case-sensitive). If the column doesn't exist in a file, it will be skipped.\n"
                    "Examples: 'Name', 'Email', 'Customer_ID', 'Product Code'")
        help_label = tk.Label(column_content, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
        help_label.pack(anchor="w")

    def _build_search_values_section(self, parent):
        values_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        values_frame.pack(fill=tk.X, pady=(0, 15))
        
        values_header = tk.Frame(values_frame, bg=self.header_bg, height=50)
        values_header.pack(fill=tk.X)
        
        values_label = tk.Label(values_header, text="📝 Step 3: Enter Search Values", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        values_label.pack(pady=15)
        
        values_content = tk.Frame(values_frame, bg=self.frame_bg)
        values_content.pack(fill=tk.X, padx=20, pady=20)
        
        instructions_label = tk.Label(values_content, text="Enter multiple search values (one per line):", 
                                     font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        instructions_label.pack(anchor="w", pady=(0, 10))
        
        search_values_frame = tk.Frame(values_content, bg=self.bg_color, relief='solid', bd=1)
        search_values_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.search_values_text = tk.Text(search_values_frame, height=4, width=50, wrap=tk.WORD, 
                                         font=self.text_font, bg=self.bg_color, fg=self.text_color,
                                         selectbackground=self.primary_color, selectforeground='white',
                                         relief='flat', bd=0, padx=10, pady=10)
        self.search_values_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        values_scrollbar = ttk.Scrollbar(search_values_frame, orient="vertical", command=self.search_values_text.yview)
        self.search_values_text.configure(yscrollcommand=values_scrollbar.set)
        values_scrollbar.pack(side=tk.RIGHT, fill="y")
        
        values_buttons_frame = tk.Frame(values_content, bg=self.frame_bg)
        values_buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        load_button = tk.Button(values_buttons_frame, text="📁 Load from File", 
                               command=self.load_search_values_from_file,
                               padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                               bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        load_button.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_button = tk.Button(values_buttons_frame, text="🗑️ Clear All", 
                                command=self.clear_search_values,
                                padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                bg='#95a5a6', fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        clear_button.pack(side=tk.LEFT)
        
        self._add_button_hover(load_button, self.primary_color, '#2980b9')
        self._add_button_hover(clear_button, '#95a5a6', '#7f8c8d')
        
        options_frame = tk.Frame(values_content, bg=self.frame_bg)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.search_mode_var = tk.StringVar(value="any")
        tk.Label(options_frame, text="Search mode:", font=self.label_font, 
                bg=self.frame_bg, fg=self.text_secondary).pack(side=tk.LEFT)
        tk.Radiobutton(options_frame, text="Find ANY match", variable=self.search_mode_var, 
                      value="any", font=self.label_font, bg=self.frame_bg, fg=self.text_color).pack(side=tk.LEFT, padx=(10, 0))
        tk.Radiobutton(options_frame, text="Find ALL matches", variable=self.search_mode_var, 
                      value="all", font=self.label_font, bg=self.frame_bg, fg=self.text_color).pack(side=tk.LEFT, padx=(10, 0))
        
        help_text = ("Tips:\n"
                    "• Type each search term on a separate line\n"
                    "• Use 'Load from File' to import terms from a .txt or .csv file\n"
                    "• Search is case-insensitive and finds partial matches\n"
                    "• 'ANY match': Returns rows containing at least one search term\n"
                    "• 'ALL matches': Returns only rows containing every search term")
        help_label = tk.Label(values_content, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
        help_label.pack(anchor="w")

    def _build_file_settings_section(self, parent):
        settings_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        
        settings_header = tk.Frame(settings_frame, bg=self.header_bg, height=50)
        settings_header.pack(fill=tk.X)
        
        settings_label = tk.Label(settings_header, text="⚙️ Step 4: Configure File Settings", 
                                 font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        settings_label.pack(pady=15)
        
        settings_content = tk.Frame(settings_frame, bg=self.frame_bg)
        settings_content.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(settings_content, text="Text file delimiter:", font=self.label_font,
                bg=self.frame_bg, fg=self.text_secondary).pack(anchor="w", pady=(0, 10))
        
        delimiter_frame = tk.Frame(settings_content, bg=self.frame_bg)
        delimiter_frame.pack(anchor="w", pady=(0, 15))
        
        delimiter_combo = ttk.Combobox(delimiter_frame, textvariable=self.search_delimiter, width=20, state="readonly")
        delimiter_combo['values'] = ("auto", "tab (\\t)", "pipe (|)", "comma (,)", "semicolon (;)", "space ( )")
        delimiter_combo.set("auto")
        delimiter_combo.pack(side=tk.LEFT)
        
        tk.Label(delimiter_frame, text=" (for .txt and .tsv files)", font=('Segoe UI', 9), 
                foreground='#7f8c8d', bg=self.frame_bg).pack(side=tk.LEFT, padx=(5, 0))
        
        help_text = ("'Auto' will try common delimiters automatically. Choose a specific delimiter if auto-detection fails.\n"
                    "Excel files (.xlsx/.xls) don't require delimiter settings.")
        help_label = tk.Label(settings_content, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
        help_label.pack(anchor="w")

    def _build_action_section(self, parent):
        action_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        action_header = tk.Frame(action_frame, bg=self.header_bg, height=50)
        action_header.pack(fill=tk.X)
        
        action_label = tk.Label(action_header, text="🚀 Step 5: Execute Search & Export", 
                               font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        action_label.pack(pady=15)
        
        action_content = tk.Frame(action_frame, bg=self.frame_bg)
        action_content.pack(fill=tk.X, padx=20, pady=20)
        
        buttons_frame = tk.Frame(action_content, bg=self.frame_bg)
        buttons_frame.pack(pady=(0, 15))
        
        self.search_button = tk.Button(buttons_frame, text="🔍 Search Files", command=self.start_column_search,
                                      padx=self.button_padx + 2, pady=self.button_pady + 1, 
                                      font=('Segoe UI', 10, 'bold'),
                                      bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        self.search_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.export_csv_button = tk.Button(buttons_frame, text="📊 Export Results to CSV", 
                                          command=self.export_search_results_csv, state='disabled',
                                          padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                          bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        self.export_csv_button.pack(side=tk.LEFT)
        
        self._add_button_hover(self.search_button, self.success_color, '#229954')
        self._add_button_hover(self.export_csv_button, self.primary_color, '#2980b9')
        
        status_frame = tk.Frame(action_content, bg=self.bg_color, relief='solid', bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_title_label = tk.Label(status_frame, text="Export Status:", font=("Segoe UI", 10, "bold"), 
                                     bg=self.bg_color, fg=self.text_color)
        status_title_label.pack(pady=(10, 0), padx=15, anchor="w")
        
        self.export_status_label = tk.Label(status_frame, text="Run a search to enable export option", 
                                           font=("Segoe UI", 10), foreground="#7f8c8d", bg=self.bg_color)
        self.export_status_label.pack(pady=(0, 10), padx=15, anchor="w")
        
        help_text = ("The search will process all files in the selected folder recursively. "
                    "Results include source file information and can be exported to CSV for further analysis.")
        help_label = tk.Label(action_content, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
        help_label.pack(anchor="w")

    def _build_progress_section(self, parent):
        progress_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        progress_header = tk.Frame(progress_frame, bg=self.header_bg, height=50)
        progress_header.pack(fill=tk.X)
        
        progress_label = tk.Label(progress_header, text="⏳ Search Progress", 
                                 font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        progress_label.pack(pady=15)
        
        progress_content = tk.Frame(progress_frame, bg=self.frame_bg)
        progress_content.pack(fill=tk.X, padx=20, pady=20)
        
        self.search_progress = ttk.Progressbar(progress_content, mode='determinate')
        self.search_progress.pack(fill=tk.X, pady=(0, 10))
        
        self.search_progress_label = tk.Label(progress_content, text="Ready to search...", 
                                             font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
        self.search_progress_label.pack(anchor="w")

    def _build_results_section(self, parent):
        results_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        results_header = tk.Frame(results_frame, bg=self.header_bg, height=50)
        results_header.pack(fill=tk.X)
        
        results_label = tk.Label(results_header, text="📄 Search Results", 
                                font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        results_label.pack(pady=15)
        
        results_content = tk.Frame(results_frame, bg=self.frame_bg)
        results_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        text_frame = tk.Frame(results_content, bg=self.bg_color, relief='solid', bd=1)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.search_results_text = scrolledtext.ScrolledText(text_frame, height=20, width=80, 
                                                            wrap=tk.WORD, font=self.text_font,
                                                            bg=self.bg_color, fg=self.text_color,
                                                            selectbackground=self.primary_color,
                                                            selectforeground='white',
                                                            relief='flat', bd=0,
                                                            padx=10, pady=10)
        self.search_results_text.pack(fill=tk.BOTH, expand=True)

    def load_search_values_from_file(self):
        file_path = filedialog.askopenfilename(
            title="Load search values from file",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if file_path.lower().endswith('.csv'):
                try:
                    df = pd.read_csv(file_path)
                    if len(df.columns) > 0:
                        values = df.iloc[:, 0].dropna().astype(str).tolist()
                        content = '\n'.join(values)
                except:
                    pass  # Fall back to treating as text file
            
            self.search_values_text.delete(1.0, tk.END)
            self.search_values_text.insert(1.0, content)
            
            values = self.get_search_values_from_text()
            messagebox.showinfo("Success", f"Loaded {len(values)} search values from file.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def clear_search_values(self):
        self.search_values_text.delete(1.0, tk.END)

    def get_search_values_from_text(self):
        content = self.search_values_text.get(1.0, tk.END).strip()
        if not content:
            return []
        
        values = [line.strip() for line in content.split('\n') if line.strip()]
        return values

    def browse_search_folder(self):
        folder = filedialog.askdirectory(title="Select folder to search")
        if folder:
            self.search_folder_path.set(folder)

    def get_selected_search_delimiter(self):
        delimiter_map = {
            "auto": None,  # Auto-detect
            "tab (\\t)": "\t",
            "pipe (|)": "|",
            "comma (,)": ",",
            "semicolon (;)": ";",
            "space ( )": " "
        }
        return delimiter_map.get(self.search_delimiter.get(), None)

    def get_enabled_search_extensions(self):
        return ['csv', 'xlsx', 'xls', 'tsv', 'txt']

    def validate_search_inputs(self):
        if not self.search_folder_path.get():
            messagebox.showerror("Validation Error", "Please select a folder to search.")
            return False
        
        if not os.path.exists(self.search_folder_path.get()):
            messagebox.showerror("Validation Error", "Selected folder does not exist.")
            return False
        
        if not self.search_column_name.get().strip():
            messagebox.showerror("Validation Error", "Please enter a column name.")
            return False
        
        search_values = self.get_search_values_from_text()
        if not search_values:
            messagebox.showerror("Validation Error", "Please enter at least one search value.")
            return False
        
        return True

    def start_column_search(self):
        if not self.validate_search_inputs():
            return
        
        self.search_button.config(state='disabled')
        self.export_csv_button.config(state='disabled')
        self.search_progress['value'] = 0
        self.search_progress_label.config(text="Initializing search...")
        self.search_results_text.delete(1.0, tk.END)
        self.search_results_text.insert(tk.END, "Searching files...\n")
        
        search_thread = threading.Thread(target=self.perform_column_search)
        search_thread.daemon = True
        search_thread.start()

    def perform_column_search(self):
        try:
            folder_path = self.search_folder_path.get()
            column_name = self.search_column_name.get().strip()
            search_values = self.get_search_values_from_text()
            search_mode = self.search_mode_var.get()
            file_extensions = self.get_enabled_search_extensions()
            
            results = self.search_files_for_multiple_entries(
                folder_path, column_name, search_values, search_mode, file_extensions
            )
            
            self.search_results = results
            
            self.root.after(0, self.display_column_search_results)
            
        except Exception as e:
            self.root.after(0, lambda: self.display_column_search_error(str(e)))

    def search_files_for_multiple_entries(self, folder_path, column_name, search_values, search_mode, file_extensions):
        results = {}
        
        all_files = []
        for ext in file_extensions:
            pattern = os.path.join(folder_path, f"*.{ext}")
            all_files.extend(glob.glob(pattern))
        
        if not all_files:
            self.root.after(0, lambda: self.update_search_results_text(
                f"No files found with extensions {file_extensions} in {folder_path}\n"))
            self.root.after(0, lambda: self.update_search_progress(0, 0, "No files found"))
            return results
        
        total_files = len(all_files)
        search_summary = f"Searching {total_files} files for {len(search_values)} values in column '{column_name}' (Mode: {search_mode.upper()})"
        self.root.after(0, lambda: self.update_search_results_text(f"{search_summary}\n"))
        self.root.after(0, lambda: self.update_search_results_text(f"Search values: {', '.join(search_values[:5])}" + 
                                                                    (f"... and {len(search_values)-5} more" if len(search_values) > 5 else "") + "\n"))
        self.root.after(0, lambda: self.update_search_results_text("-" * 80 + "\n"))
        
        for i, file_path in enumerate(all_files):
            current_file = i + 1
            progress_percent = (current_file / total_files) * 100
            
            self.root.after(0, lambda p=progress_percent, c=current_file, t=total_files, f=os.path.basename(file_path): 
                        self.update_search_progress(p, c, f"Processing {c}/{t}: {f}"))
            
            try:
                progress_msg = f"[{current_file}/{total_files}] Processing: {os.path.basename(file_path)}\n"
                self.root.after(0, lambda msg=progress_msg: self.update_search_results_text(msg))
                
                file_ext = Path(file_path).suffix.lower()
                df = None
                
                if file_ext == '.csv':
                    df = pd.read_csv(file_path)
                elif file_ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(file_path)
                elif file_ext == '.tsv':
                    selected_delimiter = self.get_selected_search_delimiter()
                    if selected_delimiter:
                        df = pd.read_csv(file_path, sep=selected_delimiter)
                    else:
                        df = pd.read_csv(file_path, sep='\t') 
                elif file_ext == '.txt':
                    df = self.handle_search_txt_file_multiple(file_path, column_name, search_values)
                    if df is None:
                        continue
                else:
                    continue
                
                if df is None:
                    continue
                
                if file_ext == '.txt' and isinstance(df, dict):
                    matches = df
                    if matches['found']:
                        text_results = matches['content'].copy()
                        text_results.insert(0, 'Source_File_Name', os.path.basename(file_path))
                        text_results.insert(1, 'Source_File_Path', file_path)
                        text_results.insert(2, 'Matched_Search_Terms', matches['matched_terms'])
                        text_results.insert(3, 'Match_Type', 'Text_Search')
                        
                        results[file_path] = text_results
                        msg = f"✅ Found {matches['total_matches']} line(s) matching search terms in {os.path.basename(file_path)}\n"
                        msg += f"   Matched terms: {', '.join(matches['matched_terms'])}\n"
                        
                        for j, line in enumerate(matches['lines'][:3]):
                            msg += f"   Line {line['number']}: {line['text'][:100]}...\n"
                        
                        if len(matches['lines']) > 3:
                            msg += f"   ... and {len(matches['lines']) - 3} more matches\n"
                        
                        self.root.after(0, lambda m=msg: self.update_search_results_text(m))
                    else:
                        msg = f"❌ No matches found in {os.path.basename(file_path)}\n"
                        self.root.after(0, lambda m=msg: self.update_search_results_text(m))
                    continue
                
                if column_name not in df.columns:
                    msg = f"⚠️  Column '{column_name}' not found in {os.path.basename(file_path)}\n"
                    msg += f"   Available columns: {list(df.columns)}\n"
                    self.root.after(0, lambda m=msg: self.update_search_results_text(m))
                    continue
                
                matching_rows, matched_terms = self.find_multiple_matches(df, column_name, search_values, search_mode)
                
                if not matching_rows.empty:
                    matching_rows_with_source = matching_rows.copy()
                    matching_rows_with_source.insert(0, 'Source_File_Name', os.path.basename(file_path))
                    matching_rows_with_source.insert(1, 'Source_File_Path', file_path)
                    matching_rows_with_source.insert(2, 'Matched_Column', column_name)
                    matching_rows_with_source.insert(3, 'Matched_Value', matching_rows_with_source[column_name])
                    matching_rows_with_source.insert(4, 'Search_Terms_Used', ', '.join(search_values))
                    matching_rows_with_source.insert(5, 'Matched_Terms', ', '.join(matched_terms))
                    
                    results[file_path] = matching_rows_with_source
                    msg = f"✅ Found {len(matching_rows)} match(es) in {os.path.basename(file_path)}\n"
                    msg += f"   Matched search terms: {', '.join(matched_terms)}\n"
                    
                    term_summary = {}
                    for term in matched_terms:
                        term_matches = df[df[column_name].astype(str).str.contains(str(term), case=False, na=False)]
                        term_summary[term] = len(term_matches)
                    
                    for term, count in term_summary.items():
                        msg += f"     '{term}': {count} match(es)\n"
                    
                    for idx, row in matching_rows.head(3).iterrows():
                        context_info = f"{row[column_name]}"
                        other_cols = [col for col in df.columns if col != column_name][:2]
                        for col in other_cols:
                            context_info += f" | {col}: {str(row[col])[:30]}"
                        msg += f"   Row {idx}: {context_info}\n"
                    
                    if len(matching_rows) > 3:
                        msg += f"   ... and {len(matching_rows) - 3} more matches\n"
                    
                    self.root.after(0, lambda m=msg: self.update_search_results_text(m))
                else:
                    msg = f"❌ No matches found in {os.path.basename(file_path)}\n"
                    self.root.after(0, lambda m=msg: self.update_search_results_text(m))
                    
            except Exception as e:
                msg = f"❌ Error reading {os.path.basename(file_path)}: {str(e)}\n"
                self.root.after(0, lambda m=msg: self.update_search_results_text(m))
        
        self.root.after(0, lambda: self.update_search_progress(100, total_files, f"Completed searching {total_files} files"))
        
        return results

    def find_multiple_matches(self, df, column_name, search_values, search_mode):
        all_matches = pd.DataFrame()
        matched_terms = set()
        
        for search_value in search_values:
            mask = df[column_name].astype(str).str.contains(str(search_value), case=False, na=False)
            value_matches = df[mask]
            
            if not value_matches.empty:
                matched_terms.add(search_value)
                if search_mode == "any":
                    all_matches = pd.concat([all_matches, value_matches]).drop_duplicates()
                elif search_mode == "all":
                    if all_matches.empty:
                        all_matches = value_matches
                    else:
                        all_matches = all_matches[all_matches.index.isin(value_matches.index)]
        
        return all_matches, list(matched_terms)

    def handle_search_txt_file_multiple(self, file_path, column_name, search_values):
        try:
            selected_delimiter = self.get_selected_search_delimiter()
            
            if selected_delimiter is None:
                delimiters = ['\t', '|', ',', ';', ' ']
            else:
                delimiters = [selected_delimiter]
            
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(file_path, sep=delimiter, encoding='utf-8')
                    if len(df.columns) > 1 and not all(col.startswith('Unnamed') for col in df.columns):
                        return df
                except:
                    continue
            
            return self.search_plain_text_file_multiple(file_path, search_values)
            
        except Exception as e:
            try:
                return self.search_plain_text_file_multiple(file_path, search_values, encoding='latin-1')
            except:
                return None

    def search_plain_text_file_multiple(self, file_path, search_values, encoding='utf-8'):
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                lines = file.readlines()
            
            matching_lines = []
            matched_terms = set()
            case_sensitive = False
            exact_match = False
            
            for line_num, line in enumerate(lines, 1):
                line_content = line.strip()
                search_line = line_content if case_sensitive else line_content.lower()
                
                line_matches = []
                for search_value in search_values:
                    search_val = search_value if case_sensitive else search_value.lower()
                    
                    found = False
                    if exact_match:
                        found = search_val == search_line
                    else:
                        found = search_val in search_line
                    
                    if found:
                        line_matches.append(search_value)
                        matched_terms.add(search_value)
                
                if line_matches:
                    matching_lines.append({
                        'number': line_num,
                        'text': line_content,
                        'matched_terms': line_matches
                    })
            
            if matching_lines:
                df_data = []
                for match in matching_lines:
                    df_data.append({
                        'Line_Number': match['number'],
                        'Content': match['text'],
                        'Matched_Terms': ', '.join(match['matched_terms'])
                    })
                df = pd.DataFrame(df_data)
                
                return {
                    'found': True,
                    'total_matches': len(matching_lines),
                    'matched_terms': list(matched_terms),
                    'lines': matching_lines,
                    'content': df
                }
            else:
                return {
                    'found': False,
                    'total_matches': 0,
                    'matched_terms': [],
                    'lines': [],
                    'content': pd.DataFrame()
                }
                
        except Exception as e:
            return None

    def update_search_results_text(self, text):
        self.search_results_text.insert(tk.END, text)
        self.search_results_text.see(tk.END)
        self.root.update_idletasks()

    def update_search_progress(self, percentage, current_file, status_text):
        self.search_progress['value'] = percentage
        self.search_progress_label.config(text=status_text)
        self.root.update_idletasks()

    def display_column_search_results(self):
        self.search_progress['value'] = 100
        self.search_progress_label.config(text="Search completed!")
        self.search_button.config(state='normal')
        
        self.update_search_results_text("\n" + "=" * 80 + "\n")
        self.update_search_results_text("SEARCH SUMMARY\n")
        self.update_search_results_text("=" * 80 + "\n")
        
        if self.search_results:
            total_matches = sum(len(df) if isinstance(df, pd.DataFrame) else 0 for df in self.search_results.values())
            search_values = self.get_search_values_from_text()
            
            self.update_search_results_text(f"Search terms used: {len(search_values)}\n")
            self.update_search_results_text(f"Total matches found: {total_matches}\n")
            self.update_search_results_text(f"Files with matches: {len(self.search_results)}\n")
            
            all_matched_terms = set()
            for result in self.search_results.values():
                if isinstance(result, pd.DataFrame) and 'Matched_Terms' in result.columns:
                    for matched_terms_str in result['Matched_Terms'].dropna():
                        if matched_terms_str:
                            terms = [term.strip() for term in str(matched_terms_str).split(',')]
                            all_matched_terms.update(terms)
            
            if all_matched_terms:
                self.update_search_results_text(f"Unique terms with matches: {len(all_matched_terms)}\n")
                self.update_search_results_text(f"Terms found: {', '.join(sorted(all_matched_terms))}\n")
            
            self.export_csv_button.config(state='normal')
            self.export_status_label.config(text=f"✓ Ready to export {total_matches:,} results to CSV", foreground=self.success_color)
            
            self.update_search_results_text("\n📋 Export Information:\n")
            self.update_search_results_text("Each exported row will include:\n")
            self.update_search_results_text("• Source_File_Name: Original filename\n")
            self.update_search_results_text("• Source_File_Path: Complete file path\n")
            self.update_search_results_text("• Matched_Column: Column where match was found\n")
            self.update_search_results_text("• Matched_Value: The actual matching value\n")
            self.update_search_results_text("• Search_Terms_Used: All search terms you provided\n")
            self.update_search_results_text("• Matched_Terms: Which specific terms matched this row\n")
            self.update_search_results_text("• All original columns from the source file\n")
            self.update_search_results_text("\n💡 Click 'Export Results to CSV' to save all results\n")
        else:
            search_values = self.get_search_values_from_text()
            self.update_search_results_text(f"No matches found for any of the {len(search_values)} search terms.\n")
            self.export_status_label.config(text="✗ No results to export", foreground=self.danger_color)

    def export_search_results_csv(self):
        if not self.search_results:
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save CSV results as...",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            all_results = []
            
            for source_file, df in self.search_results.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    all_results.append(df)
            
            if all_results:
                combined_df = pd.concat(all_results, ignore_index=True)
                combined_df.to_csv(file_path, index=False)
                
                search_values = self.get_search_values_from_text()
                messagebox.showinfo("Export Successful", 
                                   f"✅ Exported {len(combined_df):,} results to CSV!\n\n"
                                   f"📊 Export Summary:\n"
                                   f"• Total rows exported: {len(combined_df):,}\n"
                                   f"• Files processed: {len(self.search_results)}\n"
                                   f"• Search terms used: {len(search_values)}\n"
                                   f"• Saved to: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")

    def display_column_search_error(self, error_msg):
        self.search_progress['value'] = 0
        self.search_progress_label.config(text="Search failed!")
        self.search_button.config(state='normal')
        messagebox.showerror("Search Error", f"Search failed: {error_msg}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiFileColumnSearchTool(root)
    root.mainloop()