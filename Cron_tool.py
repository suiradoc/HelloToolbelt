import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import threading
import time

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
            
        except Exception:
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

class CronJobGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("CronJob Configuration Tool")
        
        try:
            self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
            
            if not self.is_in_toolbelt:
                self.root.configure(bg='#ffffff')
        except Exception as e:
            print(f"Warning: Could not configure root window: {e}")
            self.is_in_toolbelt = False
        
        self.cron_fields = {}
        self.cron_vars = {}
        self._updating_interface = False  # Flag to prevent recursive updates
        self._widgets_created = False  # Flag to track widget creation
        
        try:
            self.setup_adaptive_styling()
        except Exception as e:
            print(f"Warning: Could not setup styling: {e}")
            self._setup_fallback_styling()
        
        self.root.minsize(800, 700)
        
        try:
            self.task_type_var = tk.StringVar(value="eligibility_and_format_file")
            self.secret_var = tk.StringVar(value="integrations")
            self.encryption_var = tk.StringVar(value="False")
            self.restricted_client_var = tk.StringVar(value="No")
            self.cron_preview_var = tk.StringVar()
        except Exception as e:
            print(f"Error initializing variables: {e}")
            messagebox.showerror("Initialization Error", f"Failed to initialize variables: {e}")
            return
        
        try:
            self._create_main_interface()
            self._widgets_created = True
        except Exception as e:
            print(f"Error creating interface: {e}")
            messagebox.showerror("Interface Error", f"Failed to create interface: {e}")
            return
        
        if not self.is_in_toolbelt:
            try:
                self._center_window()
            except Exception as e:
                print(f"Warning: Could not center window: {e}")

    def _setup_fallback_styling(self):
        self.is_dark_mode = False
        self.title_font = ("Arial", 14, "bold")
        self.subtitle_font = ("Arial", 11, "bold")
        self.label_font = ("Arial", 10)
        self.text_font = ("Arial", 10)
        
        self.button_padx = 8
        self.button_pady = 4
        self.frame_padx = 20
        self.frame_pady = 15
        
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
        if self.is_in_toolbelt:
            try:
                parent_bg = self.root.cget('bg')
                parent_fg = self.root.cget('fg') 
            except:
                parent_bg = '#ffffff'
                parent_fg = '#2c3e50'
        else:
            try:
                temp_label = tk.Label(self.root)
                parent_bg = temp_label.cget('bg')
                parent_fg = temp_label.cget('fg')
                temp_label.destroy()
            except:
                parent_bg = '#ffffff'
                parent_fg = '#2c3e50'
        
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
            self.primary_color = '#4a90e2'
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
            self.primary_color = '#3498db'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.warning_color = '#f39c12'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.text_secondary = '#34495e'
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state

    def refresh_styling(self, is_dark_mode):
        if self._updating_interface:
            return  # Prevent recursive updates
            
        self._updating_interface = True
        
        try:
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
                self.primary_color = '#4a90e2'
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
                self.primary_color = '#3498db'
                self.success_color = '#27ae60'
                self.danger_color = '#e74c3c'
                self.warning_color = '#f39c12'
                self.text_color = parent_fg
                self.text_secondary = '#34495e'
                self.button_text_color = '#000000'  # Black text for good contrast
                self.button_hover_text_color = '#000000'  # Black text for hover state
            
            try:
                for widget in self.root.winfo_children():
                    widget.destroy()
            except tk.TclError:
                pass  # Widgets may have been destroyed already
            
            self._create_main_interface()
            self._widgets_created = True
                
        except Exception as e:
            print(f"Error refreshing styling: {e}")
        finally:
            self._updating_interface = False

    def _center_window(self):
        try:
            window_width = 1000
            window_height = 900
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            center_x = int(screen_width/2 - window_width/2)
            center_y = int(screen_height/2 - window_height/2)
            
            self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        except Exception as e:
            print(f"Warning: Could not center window: {e}")

    def _add_button_hover(self, button, normal_color, hover_color, normal_fg=None, hover_fg=None):
        try:
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

    def _create_main_interface(self):
        try:
            main_container = tk.Frame(self.root, bg=self.bg_color)
            main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
            
            header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
            header_frame.pack(fill=tk.X, pady=(0, 20))
            
            header_content = tk.Frame(header_frame, bg=self.primary_color)
            header_content.pack(fill=tk.X, padx=20, pady=15)
            
            header_icon = tk.Label(header_content, text="⏰", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
            header_icon.pack(side=tk.LEFT, padx=(0, 10))
            
            header_label = tk.Label(header_content, text="CronJob Configuration Tool", 
                                   font=('Segoe UI', 16, 'bold'), bg=self.primary_color, fg='white')
            header_label.pack(side=tk.LEFT, anchor='w')
            
            self.main_scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color, bg=self.bg_color)
            self.main_scrollable_container.pack(fill=tk.BOTH, expand=True)
            
            cron_container = self.main_scrollable_container.scrollable_frame
            cron_container.configure(bg=self.bg_color)

            self._build_cron_schedule_section(cron_container)
            self._build_cron_config_section(cron_container)
            self._build_cron_additional_settings(cron_container)
            
            button_frame = tk.Frame(cron_container, bg=self.bg_color)
            button_frame.pack(pady=20)
            
            yml_button = tk.Button(button_frame, text="🚀 Create YAML", 
                                  command=self.generate_yml, 
                                  padx=self.button_padx + 2, pady=self.button_pady + 1, 
                                  font=('Segoe UI', 10, 'bold'),
                                  bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
            yml_button.pack()
            
            self._add_button_hover(yml_button, self.success_color, '#229954')
            
            def update_scroll_after_creation():
                try:
                    if hasattr(self, 'main_scrollable_container'):
                        self.main_scrollable_container.force_scroll_update()
                except Exception:
                    pass
            
            self.root.after(100, update_scroll_after_creation)
            
        except Exception as e:
            print(f"Error creating main interface: {e}")
            raise

    def _build_cron_schedule_section(self, parent):
        try:
            cron_schedule_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
            cron_schedule_frame.pack(fill=tk.X, pady=(0, 15))
            
            schedule_header = tk.Frame(cron_schedule_frame, bg=self.header_bg, height=50)
            schedule_header.pack(fill=tk.X)
            
            schedule_label = tk.Label(schedule_header, text="⏱️ Step 1: Schedule Settings", 
                                     font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            schedule_label.pack(pady=15)
            
            schedule_content = tk.Frame(cron_schedule_frame, bg=self.frame_bg)
            schedule_content.pack(fill=tk.X, padx=20, pady=20)

            cron_fields_frame = tk.Frame(schedule_content, bg=self.frame_bg)
            cron_fields_frame.pack(fill=tk.X, pady=(0, 15))

            cron_defaults = {"Minute": "0", "Hour": "1", "Day of Month": "*", "Month": "*", "Day of Week": "5"}
            cron_options = {
                "Minute": ['*'] + [str(i) for i in range(0, 60, 5)],
                "Hour": ['*'] + [str(i) for i in range(0, 24)],
                "Day of Month": ['*'] + [str(i) for i in range(1, 32)],
                "Month": ['*'] + [str(i) for i in range(1, 13)],
                "Day of Week": ['*'] + [str(i) for i in range(0, 7)]
            }

            cron_fields = [
                ("Minute", 0, 0), ("Hour", 0, 2),
                ("Day of Month", 1, 0), ("Month", 1, 2),
                ("Day of Week", 2, 0)
            ]

            for label, row, col in cron_fields:
                try:
                    tk.Label(cron_fields_frame, text=label + ":", width=12, anchor="e", 
                            font=self.label_font, bg=self.frame_bg, fg=self.text_secondary).grid(
                        row=row, column=col, sticky='e', padx=(5,2), pady=5)
                    var = tk.StringVar(value=cron_defaults[label])
                    cron_dropdown = ttk.Combobox(cron_fields_frame, textvariable=var, 
                                                values=cron_options[label], state="readonly", width=15)
                    cron_dropdown.grid(row=row, column=col+1, sticky='w', padx=(0,20), pady=5)
                    self.cron_vars[label.lower().replace(" ", "_")] = var
                    cron_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_cron_preview())
                except Exception as e:
                    print(f"Error creating cron field {label}: {e}")

            help_frame = tk.Frame(schedule_content, bg=self.frame_bg)
            help_frame.pack(fill=tk.X, pady=(10, 15))
            
            help_text = ("Day of Week: 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday\n"
                        "Use '*' for 'any value' in any field")
            help_label = tk.Label(help_frame, text=help_text, font=("Segoe UI", 9), 
                                 fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
            help_label.pack(anchor="w")

            preview_frame = tk.Frame(schedule_content, bg=self.bg_color, relief='solid', bd=1)
            preview_frame.pack(fill=tk.X, pady=(0, 0))
            
            preview_label = tk.Label(preview_frame, text="📅 Schedule Preview:", 
                                   font=self.subtitle_font, bg=self.bg_color, fg=self.text_color)
            preview_label.pack(pady=(10, 5), padx=15, anchor="w")
            
            cron_preview_label = tk.Label(preview_frame, textvariable=self.cron_preview_var, 
                                         font=("Segoe UI", 11), fg=self.primary_color, bg=self.bg_color)
            cron_preview_label.pack(pady=(0, 10), padx=15, anchor="w")
            
            self.update_cron_preview()
        except Exception as e:
            print(f"Error building cron schedule section: {e}")
            raise

    def _build_cron_config_section(self, parent):
        try:
            config_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
            config_frame.pack(fill=tk.X, pady=(0, 15))
            
            config_header = tk.Frame(config_frame, bg=self.header_bg, height=50)
            config_header.pack(fill=tk.X)
            
            config_label = tk.Label(config_header, text="⚙️ Step 2: Job Configuration", 
                                   font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            config_label.pack(pady=15)
            
            config_content = tk.Frame(config_frame, bg=self.frame_bg)
            config_content.pack(fill=tk.X, padx=20, pady=20)
            
            fields_grid = tk.Frame(config_content, bg=self.frame_bg)
            fields_grid.pack(fill=tk.X, pady=(0, 15))

            config_fields = [
                ("Client", "client_name"),
                ("Shortname", "short_identifier"),
                ("Integration", "integration_name"),
                ("Task Type", "task_type"),
                ("Host", "sftp_host"),
                ("Port", "sftp_port"),
                ("Username", "sftp_username"),
                ("Password", "sftp_password"),
                ("KexAlgo", "kex_algorithm"),
                ("Path", "remote_path"),
                ("File Prefixes", "file_prefixes"),
                ("To File", "destination_filename")
            ]

            for idx, (label_text, field_key) in enumerate(config_fields):
                try:
                    row = idx // 2
                    col = (idx % 2) * 2

                    label = tk.Label(fields_grid, text=label_text + ":", width=15, anchor="e", 
                                   font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
                    label.grid(row=row, column=col, sticky='e', padx=(5,2), pady=5)

                    if label_text == "Task Type":
                        options = [
                            "eligibility_and_format_file", "formatting", "fetch_files_only",
                            "eligibility", "process_claims_report"
                        ]
                        dropdown = ttk.Combobox(fields_grid, textvariable=self.task_type_var, 
                                               values=options, state="readonly", width=25)
                        dropdown.grid(row=row, column=col+1, sticky='w', padx=(0,20), pady=5)
                    else:
                        entry_frame = tk.Frame(fields_grid, bg=self.bg_color, relief='solid', bd=1)
                        entry = tk.Entry(entry_frame, width=28, font=self.text_font, 
                                       bg=self.bg_color, fg=self.text_color, relief='flat', bd=0)
                        entry.pack(padx=5, pady=3)
                        entry_frame.grid(row=row, column=col+1, sticky='w', padx=(0,20), pady=5)
                        
                        if label_text == "Port":
                            entry.insert(0, "22")
                        self.cron_fields[field_key] = entry
                except Exception as e:
                    print(f"Error creating config field {label_text}: {e}")

            desc_frame = tk.Frame(config_content, bg=self.frame_bg)
            desc_frame.pack(fill=tk.X, pady=(10, 0))
            
            desc_text = ("Shortname is for process naming, please keep it short, no spaces, if there is a space use a - .\n"
                        "Username and Password should be the base64 encoded secret key names.\n"
                        "File Prefixes: Comma-separated list of prefixes to match files.")
            desc_label = tk.Label(desc_frame, text=desc_text, font=("Segoe UI", 9), 
                                 fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
            desc_label.pack(anchor="w")
        except Exception as e:
            print(f"Error building cron config section: {e}")
            raise

    def _build_cron_additional_settings(self, parent):
        try:
            additional_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
            additional_frame.pack(fill=tk.X, pady=(0, 15))
            
            additional_header = tk.Frame(additional_frame, bg=self.header_bg, height=50)
            additional_header.pack(fill=tk.X)
            
            additional_label = tk.Label(additional_header, text="🔧 Step 3: Additional Settings", 
                                       font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
            additional_label.pack(pady=15)
            
            additional_content = tk.Frame(additional_frame, bg=self.frame_bg)
            additional_content.pack(fill=tk.X, padx=20, pady=20)
            
            settings_frame = tk.Frame(additional_content, bg=self.frame_bg)
            settings_frame.pack(fill=tk.X, pady=(0, 15))

            secret_frame = tk.Frame(settings_frame, bg=self.frame_bg)
            secret_frame.pack(fill=tk.X, pady=5)
            
            secret_label = tk.Label(secret_frame, text="Secret Location:", width=15, anchor="e", 
                                   font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
            secret_label.pack(side=tk.LEFT, padx=(5,2))

            secret_options = ["integrations-restricted-clients", "integrations"]
            secret_dropdown = ttk.Combobox(secret_frame, textvariable=self.secret_var, 
                                          values=secret_options, state="readonly", width=30)
            secret_dropdown.pack(side=tk.LEFT, padx=5)

            encryption_frame = tk.Frame(settings_frame, bg=self.frame_bg)
            encryption_frame.pack(fill=tk.X, pady=5)
            
            encryption_label = tk.Label(encryption_frame, text="Encryption:", width=15, anchor="e", 
                                       font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
            encryption_label.pack(side=tk.LEFT, padx=(5,2))

            encryption_dropdown = ttk.Combobox(encryption_frame, textvariable=self.encryption_var, 
                                              values=["True", "False"], state="readonly", width=30)
            encryption_dropdown.pack(side=tk.LEFT, padx=5)

            restricted_frame = tk.Frame(settings_frame, bg=self.frame_bg)
            restricted_frame.pack(fill=tk.X, pady=5)
            
            restricted_label = tk.Label(restricted_frame, text="Restricted Client:", width=15, anchor="e", 
                                       font=self.label_font, bg=self.frame_bg, fg=self.text_secondary)
            restricted_label.pack(side=tk.LEFT, padx=(5,2))

            restricted_dropdown = ttk.Combobox(restricted_frame, textvariable=self.restricted_client_var, 
                                              values=["Yes", "No"], state="readonly", width=30)
            restricted_dropdown.pack(side=tk.LEFT, padx=5)

            desc_frame = tk.Frame(additional_content, bg=self.frame_bg)
            desc_frame.pack(fill=tk.X, pady=(10, 0))
            
            desc_text = ("Secret Location: Choose 'integrations-restricted-clients' for restricted clients,\n"
                        "otherwise use 'integrations'. Encryption: Enable GPG encryption for file transfers.\n"
                        "Restricted Client: If 'Yes', files will be stored in 'clients_restricted' S3 path.")
            desc_label = tk.Label(desc_frame, text=desc_text, font=("Segoe UI", 9), 
                                 fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT, wraplength=900)
            desc_label.pack(anchor="w")
        except Exception as e:
            print(f"Error building additional settings section: {e}")
            raise

    def update_cron_preview(self):
        try:
            minute = self.cron_vars.get('minute', tk.StringVar()).get() or "0"
            hour = self.cron_vars.get('hour', tk.StringVar()).get() or "1"
            day_of_month = self.cron_vars.get('day_of_month', tk.StringVar()).get() or "*"
            month = self.cron_vars.get('month', tk.StringVar()).get() or "*"
            day_of_week = self.cron_vars.get('day_of_week', tk.StringVar()).get() or "5"
            
            cron_syntax = f"{minute} {hour} {day_of_month} {month} {day_of_week}"
            cron_text = self.cron_comment(minute, hour, day_of_month, month, day_of_week)
            
            self.cron_preview_var.set(f"{cron_syntax}   ({cron_text})")
        except Exception as e:
            print(f"Error updating cron preview: {e}")
            self.cron_preview_var.set("Error generating preview")

    def cron_comment(self, minute, hour, day_of_month, month, day_of_week):
        try:
            parts = []
            if minute.isdigit() and hour.isdigit():
                parts.append(f"At {hour.zfill(2)}:{minute.zfill(2)}")
            if day_of_week.isdigit():
                days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                day_index = int(day_of_week)
                if 0 <= day_index <= 6:
                    parts.append(f"every {days[day_index]}")
            elif day_of_month != '*':
                parts.append(f"on day {day_of_month} of the month")
            if month != '*' and month.isdigit():
                months = ["", "January", "February", "March", "April", "May", "June", 
                         "July", "August", "September", "October", "November", "December"]
                month_index = int(month)
                if 1 <= month_index <= 12:
                    parts.append(f"in {months[month_index]}")
            return ' '.join(parts) if parts else "Custom cron schedule"
        except Exception as e:
            print(f"Error generating cron comment: {e}")
            return "Custom cron schedule"

    def validate_inputs(self):
        try:
            required_fields = [
                ('client_name', 'Client'), 
                ('short_identifier', 'Shortname'),
                ('integration_name', 'Integration'),
                ('sftp_host', 'Host'),
                ('sftp_username', 'Username'),
                ('sftp_password', 'Password'),
                ('file_prefixes', 'File Prefixes')
            ]
            
            missing_fields = []
            for field_key, field_name in required_fields:
                if field_key in self.cron_fields:
                    try:
                        value = self.cron_fields[field_key].get().strip()
                        if not value:
                            missing_fields.append(field_name)
                    except Exception as e:
                        print(f"Error getting value for field {field_key}: {e}")
                        missing_fields.append(field_name)
            
            if missing_fields:
                messagebox.showerror("Validation Error", 
                                   f"Please fill in the following required fields:\n\n" + 
                                   "\n".join(f"• {field}" for field in missing_fields))
                return False
            
            try:
                port_value = self.cron_fields.get('sftp_port', tk.Entry()).get().strip()
                if port_value:
                    int(port_value)
            except ValueError:
                messagebox.showerror("Validation Error", "Port must be a valid number")
                return False
            except Exception as e:
                print(f"Error validating port: {e}")
                messagebox.showerror("Validation Error", "Error validating port field")
                return False
                
            return True
        except Exception as e:
            print(f"Error validating inputs: {e}")
            messagebox.showerror("Validation Error", f"Error validating inputs: {e}")
            return False

    def generate_yml(self):
        try:
            if not self.validate_inputs():
                return
                
            data = {}
            for key, entry in self.cron_fields.items():
                try:
                    data[key] = entry.get().strip()
                except Exception as e:
                    print(f"Error getting value for field {key}: {e}")
                    data[key] = ""

            cron_values = {}
            for key, var in self.cron_vars.items():
                try:
                    cron_values[key] = var.get()
                except Exception as e:
                    print(f"Error getting cron value for {key}: {e}")
                    cron_values[key] = "*"
                    
            schedule = f"{cron_values.get('minute', '0')} {cron_values.get('hour', '1')} {cron_values.get('day_of_month', '*')} {cron_values.get('month', '*')} {cron_values.get('day_of_week', '5')}"
            cron_comment_text = self.cron_comment(**cron_values)

            client = data.get('client_name', '')
            shortname = data.get('short_identifier', '')
            integration = data.get('integration_name', '')
            task_type = self.task_type_var.get()
            host = data.get('sftp_host', '')
            port = int(data.get('sftp_port') or 22)
            username = data.get('sftp_username', '')
            password = data.get('sftp_password', '')
            kexalgo = data.get('kex_algorithm', '')
            path = data.get('remote_path', '')
            file_prefixes_str = data.get('file_prefixes', '')
            file_prefixes = [prefix.strip() for prefix in file_prefixes_str.split(',') if prefix.strip()]
            encryption = self.encryption_var.get() == "True"
            restricted_client = self.restricted_client_var.get() == "Yes"
            to_file = data.get('destination_filename', '')
            secret_location = self.secret_var.get()

            env_vars = [
                {"name": "AWS_S3_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "aws_s3_access_key"}}},
                {"name": "AWS_S3_SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "aws_s3_secret_key"}}},
                {"name": "AWS_SQS_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "aws_sqs_access_key"}}},
                {"name": "AWS_SQS_SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "aws_sqs_secret_key"}}},
                {"name": "PLAY_SECRET", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "play_secret"}}},
                {"name": "PROMETHEUS_USERNAME", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "prometheus_username"}}},
                {"name": "PROMETHEUS_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "prometheus_password"}}},
                {"name": "PUSH_GATEWAY_USERNAME", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "push_gateway_username"}}},
                {"name": "PUSH_GATEWAY_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "integrations", "key": "push_gateway_password"}}}
            ]

            if username:
                env_vars.append({"name": f"{username.upper()}", "valueFrom": {"secretKeyRef": {"name": secret_location, "key": f"{username.lower()}"}}})
            if password:
                env_vars.append({"name": f"{password.upper()}", "valueFrom": {"secretKeyRef": {"name": secret_location, "key": f"{password.lower()}"}}})

            if encryption:
                env_vars.extend([
                    {"name": "PASSPHRASE", "valueFrom": {"secretKeyRef": {"name": "gpg-passphrase", "key": "passphrase"}}},
                    {"name": "PGP_PRIVATE_KEY", "valueFrom": {"secretKeyRef": {"name": "gpg-private-key", "key": "private-key"}}}
                ])

            application_conf = f'''include "application.conf"

worker = {{
  mode = "direct"
  context = "integration"
  task_name = "get_client_files"
  client_name = "{client}"
}}

redis = {{
  host = "redis-production-master"
  port = 6379
}}

metrics = {{
  username = ${{PROMETHEUS_USERNAME}}
  password = ${{PROMETHEUS_PASSWORD}}
}}

sqs = {{
  secret_key = ${{AWS_SQS_SECRET_KEY}},
  access_key = ${{AWS_SQS_ACCESS_KEY}},
  region = "us-east-1",
  queue_name = "integrations_prod",
  encryption = {{
    key = "alias/sqs-production-latest",
    cache = {{
      capacity = 1000,
      max_age_minutes = 10080
    }}
  }}
}}

play.http.secret.key = ${{PLAY_SECRET}}'''

            client_json = {
                "task": "get_client_files",
                "client": client,
                "integration": integration,
                "task_type": task_type,
                "source": {
                    "storage": {
                        "type": "sftp",
                        "host": host,
                        "port": str(port),
                        "username": f"${{{username.upper()}}}" if username else "",
                        "password": f"${{{password.upper()}}}" if password else "",
                        "kexAlgo": kexalgo,
                        "path": path
                    },
                    "file_prefixes": file_prefixes,
                    "encryption": encryption
                },
                "destination": {
                    "storage": {
                        "type": "s3",
                        "key": "${AWS_S3_ACCESS_KEY}",
                        "secret": "${AWS_S3_SECRET_KEY}",
                        "region": "us-east-1",
                        "bucket": "s3.hello.do.integration",
                        "path": f"clients_restricted/{client}/eligibility" if restricted_client else f"clients/{client}/eligibility"
                    },
                    "to_file": to_file
                },
                "working_dir": "/tmp"
            }

            cronjob_yaml = f"""apiVersion: batch/v1
kind: CronJob
metadata:
  name: integration-get-files-{shortname.lower()}
  namespace: integrations-prod
spec:
  schedule: "{schedule}" # {cron_comment_text}
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: integration-job-runner
            image: 046525326440.dkr.ecr.us-east-1.amazonaws.com/queuers:deployed-integrations-prod
            imagePullPolicy: Always
            ports:
              - containerPort: 9000
            env:
{self.dict_to_yaml(env_vars, indent=14)}
            volumeMounts:
            - mountPath: /usr/src/queuers/conf/application.prod.conf
              name: integration-get-files-{shortname.lower()}-conf
              subPath: application.prod.conf
            - name: tasks
              mountPath: /usr/src/queuers/conf/tasks
            - name: get-client-files-tasks
              mountPath: /usr/src/queuers/conf/tasks_raw/get_client_files
          volumes:
          - name: integration-get-files-{shortname.lower()}-conf
            configMap:
               name: integration-get-files-{shortname.lower()}-conf
               items:
                - key: application.prod.conf
                  path:  application.prod.conf
          - name: tasks
            emptyDir: {{}}
          - name: get-client-files-tasks
            configMap:
              name: integration-get-client-files-{shortname.lower()}-task
          imagePullSecrets:
          - name: myregistrykey
          nodeSelector:
            role: services
            env: prod
          restartPolicy: Never
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: integration-get-files-{shortname.lower()}-conf
  namespace: integrations-prod
data:
  application.prod.conf: |-
{self.indent_multiline(application_conf, 4)}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: integration-get-client-files-{shortname.lower()}-task
  namespace: integrations-prod
data:
  {client.lower()}.json: |-
{self.indent_multiline(json.dumps(client_json, indent=2), 4)}
"""

            default_filename = f"cronjob-{shortname.lower()}-{client.lower()}.yml"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".yml", 
                filetypes=[("YAML files", "*.yml"), ("All files", "*.*")],
                initialfile=default_filename,
                title="Save Kubernetes CronJob YAML"
            )
            
            if save_path:
                try:
                    with open(save_path, 'w') as file:
                        file.write(cronjob_yaml)
                    
                    summary_msg = f"✅ Kubernetes CronJob YAML generated successfully!\n\n"
                    summary_msg += f"📁 File saved to: {save_path}\n\n"
                    summary_msg += f"📋 Configuration Summary:\n"
                    summary_msg += f"• Client: {client}\n"
                    summary_msg += f"• Integration: {integration}\n"
                    summary_msg += f"• Schedule: {schedule} ({cron_comment_text})\n"
                    summary_msg += f"• Task Type: {task_type}\n"
                    summary_msg += f"• SFTP Host: {host}:{port}\n"
                    summary_msg += f"• File Prefixes: {', '.join(file_prefixes)}\n"
                    summary_msg += f"• Encryption: {'Enabled' if encryption else 'Disabled'}\n"
                    summary_msg += f"• Secret Location: {secret_location}\n"
                    summary_msg += f"• Restricted Client: {'Yes' if restricted_client else 'No'}\n\n"
                    summary_msg += f"🚀 Ready to deploy to Kubernetes!"
                    
                    messagebox.showinfo("Success", summary_msg)
                    
                except PermissionError:
                    messagebox.showerror("Error", f"Permission denied. Cannot write to:\n{save_path}\n\nPlease choose a different location or check file permissions.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
        except Exception as e:
            print(f"Error generating YAML: {e}")
            messagebox.showerror("Error", f"Failed to generate YAML configuration: {e}")

    def dict_to_yaml(self, data, indent=2):
        try:
            lines = []
            for item in data:
                lines.append(' ' * indent + f"- name: {item['name']}")
                lines.append(' ' * (indent + 2) + "valueFrom:")
                lines.append(' ' * (indent + 4) + "secretKeyRef:")
                lines.append(' ' * (indent + 6) + f"name: {item['valueFrom']['secretKeyRef']['name']}")
                lines.append(' ' * (indent + 6) + f"key: {item['valueFrom']['secretKeyRef']['key']}")
            return '\n'.join(lines)
        except Exception as e:
            print(f"Error converting dict to YAML: {e}")
            return f"# Error generating environment variables: {e}"

    def indent_multiline(self, text, indent=2):
        try:
            return '\n'.join((' ' * indent) + line for line in text.splitlines())
        except Exception as e:
            print(f"Error indenting multiline text: {e}")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = CronJobGenerator(root)
        root.mainloop()
    except Exception as e:
        print(f"Critical error starting application: {e}")
        try:
            messagebox.showerror("Critical Error", f"Failed to start application:\n{e}")
        except:
            print("Could not show error dialog")