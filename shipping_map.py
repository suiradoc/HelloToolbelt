import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import os
from collections import Counter
import re

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
            
            content_height = bbox[3] - bbox[1]
            canvas_height = self.canvas.winfo_height()
            
            if content_height > canvas_height:
                if not self.scrollbar_v.winfo_ismapped():
                    self.scrollbar_v.pack(side="right", fill="y")
                return True
            else:
                self.scrollbar_v.pack_forget()
                return False
        except Exception as e:
            print(f"Error checking scroll: {e}")
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
        self.canvas.after_idle(self.check_scroll_needed)

class ZipcodeHeatmapTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Zipcode State Heatmap")
        self.root.geometry("1200x800")
        
        self.file_data = []
        self.file_headers = []
        self.state_counts = {}
        
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        self.setup_adaptive_styling()
        
        self.title_font = ('Segoe UI', 16, 'bold')
        self.subtitle_font = ('Segoe UI', 12, 'bold')
        self.label_font = ('Segoe UI', 10)
        self.text_font = ('Segoe UI', 9)
        self.button_font = ('Segoe UI', 10)
        
        self.setup_ui()
    
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
        
        if self.is_dark_mode:
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.button_bg = "#a34ae2"
            self.button_fg = '#ffffff'
            self.text_color = parent_fg if parent_fg else '#ffffff'
            self.secondary_text_color = '#cccccc'
        else:
            self.bg_color = parent_bg  # Use parent's background directly
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.button_bg = '#0078d4'
            self.button_fg = '#ffffff'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.secondary_text_color = '#34495e'
    
    def refresh_styling(self, is_dark_mode):
        self.is_dark_mode = is_dark_mode
        
        self.setup_adaptive_styling()
        
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.setup_ui()
    
    def setup_ui(self):
        if not self.is_in_toolbelt:
            self.root.configure(bg=self.bg_color)
        
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
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
        
        self.scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color)
        self.scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        content_container = self.scrollable_container.scrollable_frame
        content_container.configure(bg=self.bg_color)
        
        self._create_upload_section(content_container)
        
        self.heatmap_section = tk.Frame(content_container, bg=self.bg_color)
        self._create_heatmap_section()
        
        def update_scroll_after_build():
            try:
                if hasattr(self, 'scrollable_container'):
                    self.scrollable_container.force_scroll_update()
            except Exception:
                pass
        
        self.root.after(100, update_scroll_after_build)
        self.root.after(500, update_scroll_after_build)
    
    def _create_upload_section(self, parent):
        upload_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        upload_frame.pack(fill=tk.X, pady=(0, 15))
        
        header = tk.Frame(upload_frame, bg=self.header_bg, height=40)
        header.pack(fill=tk.X)
        
        label = tk.Label(header, text="Step 1: Upload CSV or TXT File", 
                        font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        label.pack(pady=10)
        
        content = tk.Frame(upload_frame, bg=self.frame_bg)
        content.pack(fill=tk.X, padx=20, pady=15)
        
        upload_btn = tk.Button(content, text="📁 Select CSV or TXT File", 
                              command=self.load_file,
                              bg=self.button_bg, fg='#000000',
                              font=self.button_font, cursor='hand2',
                              padx=20, pady=10)
        upload_btn.pack(anchor='w')
        
        self.file_info_label = tk.Label(content, text="", font=self.label_font,
                                       bg=self.frame_bg, fg=self.text_color)
        self.file_info_label.pack(anchor='w', pady=(10, 0))
        
        self.column_selection_frame = tk.Frame(content, bg=self.frame_bg)
        
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
        
        filter_info = tk.Label(self.column_selection_frame,
                              text="ℹ️ Users under 18 and with past termination dates will be excluded",
                              font=('Segoe UI', 9, 'italic'),
                              bg=self.frame_bg, fg=self.secondary_text_color)
        filter_info.pack(anchor='w', pady=(10, 0))
        
        self.process_btn = tk.Button(self.column_selection_frame, 
                                     text="🔄 Process Zipcodes",
                                     command=self.process_selected_column,
                                     bg='#27ae60', fg='#000000',
                                     font=self.button_font, cursor='hand2',
                                     padx=15, pady=8)
        self.process_btn.pack(anchor='w', pady=(10, 0))
    
    def _create_heatmap_section(self):
        heatmap_frame = tk.Frame(self.heatmap_section, bg=self.frame_bg, relief='solid', bd=1)
        heatmap_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        header = tk.Frame(heatmap_frame, bg=self.header_bg, height=40)
        header.pack(fill=tk.X)
        
        label = tk.Label(header, text="Step 2: State Distribution Heatmap", 
                        font=self.subtitle_font, bg=self.header_bg, fg=self.text_color)
        label.pack(pady=10)
        
        self.heatmap_content = tk.Frame(heatmap_frame, bg=self.frame_bg)
        self.heatmap_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                sample = f.read(8192)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample, delimiters=',\t|;')
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ','
            
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=delimiter)
                self.file_headers = next(reader)
                self.file_data = list(reader)
            
            filename = os.path.basename(file_path)
            row_count = len(self.file_data)
            col_count = len(self.file_headers)
            
            delimiter_names = {',': 'Comma', '\t': 'Tab', '|': 'Pipe', ';': 'Semicolon'}
            delimiter_name = delimiter_names.get(delimiter, delimiter)
            
            self.file_info_label.config(
                text=f"✅ Loaded: {filename}\n"
                     f"Rows: {row_count:,} | Columns: {col_count} | Delimiter: {delimiter_name}"
            )
            
            column_options = [f"{idx}: {header}" for idx, header in enumerate(self.file_headers)]
            self.zipcode_combo['values'] = column_options
            self.dob_combo['values'] = ['(None)'] + column_options
            self.term_combo['values'] = ['(None)'] + column_options
            
            zipcode_col_idx = self._auto_detect_zipcode_column()
            if zipcode_col_idx is not None:
                self.zipcode_col_var.set(column_options[zipcode_col_idx])
            elif column_options:
                self.zipcode_col_var.set(column_options[0])
            
            dob_col_idx = self._auto_detect_dob_column()
            if dob_col_idx is not None:
                self.dob_col_var.set(column_options[dob_col_idx])
            else:
                self.dob_col_var.set('(None)')
            
            term_col_idx = self._auto_detect_term_column()
            if term_col_idx is not None:
                self.term_col_var.set(column_options[term_col_idx])
            else:
                self.term_col_var.set('(None)')
            
            self.column_selection_frame.pack(fill=tk.X, pady=(10, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
    
    def _on_column_change(self, event=None):
        pass  # Could add preview functionality here
    
    def process_selected_column(self):
        if not self.file_data or not self.file_headers:
            messagebox.showerror("Error", "No file loaded!")
            return
        
        selected = self.zipcode_col_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a zipcode column!")
            return
        
        try:
            zipcode_col_idx = int(selected.split(':')[0])
            zipcode_col_name = self.file_headers[zipcode_col_idx]
            
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
            
            self._process_zipcodes_with_filters(zipcode_col_idx, dob_col_idx, term_col_idx)
            
            if not self.state_counts:
                messagebox.showwarning("No Data", 
                                     "No valid users found after applying filters.\n\n"
                                     "All users may have been excluded due to:\n"
                                     "• Being under 18 years old\n"
                                     "• Having past termination dates\n"
                                     "• Invalid zipcodes")
                return
            
            current_text = self.file_info_label.cget("text")
            info_lines = [current_text, f"Zipcode Column: '{zipcode_col_name}' (Column {zipcode_col_idx})"]
            
            if dob_col_name:
                info_lines.append(f"DOB Column: '{dob_col_name}' (Column {dob_col_idx})")
            if term_col_name:
                info_lines.append(f"Term Date Column: '{term_col_name}' (Column {term_col_idx})")
            
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
            
            self.heatmap_section.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
            
            self._generate_heatmap()
            
            messagebox.showinfo("Success", 
                              f"Successfully processed zipcodes!\n\n"
                              f"Found users in {len(self.state_counts)} states.\n"
                              f"Total valid users: {sum(self.state_counts.values()):,}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process zipcodes:\n{str(e)}")
    
    def _auto_detect_zipcode_column(self):
        zipcode_keywords = ['zip', 'zipcode', 'postal', 'zip code', 'postal code', 'postcode']
        
        for idx, header in enumerate(self.file_headers):
            header_lower = header.lower().strip()
            if any(keyword in header_lower for keyword in zipcode_keywords):
                return idx
        
        return None
    
    def _auto_detect_dob_column(self):
        dob_keywords = ['dob', 'date of birth', 'birth date', 'birthdate', 'birthday', 'date_of_birth']
        
        for idx, header in enumerate(self.file_headers):
            header_lower = header.lower().strip()
            if any(keyword in header_lower for keyword in dob_keywords):
                return idx
        
        return None
    
    def _auto_detect_term_column(self):
        term_keywords = ['term', 'termination', 'term date', 'termination date', 'end date', 
                        'termination_date', 'term_date', 'end_date']
        
        for idx, header in enumerate(self.file_headers):
            header_lower = header.lower().strip()
            if any(keyword in header_lower for keyword in term_keywords):
                return idx
        
        return None
    
    def _process_zipcodes_with_filters(self, zipcode_col_idx, dob_col_idx=None, term_col_idx=None):
        from datetime import datetime, date
        import dateutil.parser as date_parser
        
        self.state_counts = Counter()
        
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
            
            if dob_col_idx is not None and len(row) > dob_col_idx:
                dob_str = row[dob_col_idx].strip()
                if dob_str:
                    try:
                        dob = self._parse_date(dob_str)
                        if dob:
                            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                            if age < 18:
                                excluded_age_count += 1
                                continue
                    except:
                        pass  # If can't parse, don't exclude
            
            if term_col_idx is not None and len(row) > term_col_idx:
                term_str = row[term_col_idx].strip()
                if term_str:
                    try:
                        term_date = self._parse_date(term_str)
                        if term_date:
                            if term_date < today:
                                excluded_term_count += 1
                                continue
                    except:
                        pass  # If can't parse, don't exclude
            
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
        
        self.filtering_stats = {
            'total': total_count,
            'included': included_count,
            'excluded_age': excluded_age_count,
            'excluded_term': excluded_term_count,
            'excluded_invalid': excluded_invalid_count
        }
    
    def _parse_date(self, date_str):
        if not date_str or not date_str.strip():
            return None
        
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
        
        try:
            import dateutil.parser as date_parser
            return date_parser.parse(date_str).date()
        except:
            pass
        
        return None
    
    def _process_zipcodes(self, zipcode_col_idx):
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
        if not zipcode:
            return None
        
        digits = re.sub(r'\D', '', str(zipcode))
        
        if len(digits) >= 5:
            return digits[:5]
        
        return None
    
    def _zipcode_to_state(self, zipcode):
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
        for widget in self.heatmap_content.winfo_children():
            widget.destroy()
        
        if not self.state_counts:
            tk.Label(self.heatmap_content, text="No state data to display", 
                    font=self.label_font, bg=self.frame_bg).pack()
            return
        
        max_count = max(self.state_counts.values())
        total_count = sum(self.state_counts.values())
        
        summary_frame = tk.Frame(self.heatmap_content, bg=self.frame_bg)
        summary_frame.pack(fill=tk.X, pady=(0, 20))
        
        summary_text = f"Total Users: {total_count:,} | States Represented: {len(self.state_counts)}"
        tk.Label(summary_frame, text=summary_text, font=self.subtitle_font,
                bg=self.frame_bg, fg=self.text_color).pack()
        
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
        
        copy_btn = tk.Button(self.heatmap_content, text="📋 Copy to Clipboard",
                           command=self.copy_state_data,
                           bg='#27ae60', fg='#000000',
                           font=self.button_font, cursor='hand2',
                           padx=20, pady=10)
        copy_btn.pack(pady=(0, 15))
        
        grid_frame = tk.Frame(self.heatmap_content, bg=self.frame_bg)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        all_states = sorted(STATE_NAMES.keys())
        
        cols = 8
        
        for idx, state in enumerate(all_states):
            row = idx // cols
            col = idx % cols
            
            count = self.state_counts.get(state, 0)
            
            if count == 0:
                bg_color = '#404040' if self.is_dark_mode else '#f0f0f0'
                text_color = '#999999'
            else:
                bg_color = self._get_heatmap_color(count, max_count)
                text_color = '#ffffff' if count > max_count * 0.4 else '#000000'
            
            cell_frame = tk.Frame(grid_frame, bg=bg_color, relief='solid', bd=1, 
                                 width=130, height=60)
            cell_frame.grid(row=row, column=col, padx=2, pady=2, sticky='nsew')
            cell_frame.grid_propagate(False)
            
            state_label = tk.Label(cell_frame, text=state, 
                                  font=('Segoe UI', 11, 'bold'),
                                  bg=bg_color, fg=text_color)
            state_label.pack(pady=(5, 0))
            
            count_text = f"{count:,}" if count > 0 else "0"
            count_label = tk.Label(cell_frame, text=count_text,
                                  font=('Segoe UI', 10),
                                  bg=bg_color, fg=text_color)
            count_label.pack()
            
            if count > 0:
                percentage = (count / total_count) * 100
                pct_label = tk.Label(cell_frame, text=f"({percentage:.1f}%)",
                                    font=('Segoe UI', 8),
                                    bg=bg_color, fg=text_color)
                pct_label.pack()
        
        for i in range(cols):
            grid_frame.grid_columnconfigure(i, weight=1)
    
    def copy_state_data(self):
        if not self.state_counts:
            messagebox.showerror("Error", "No data to copy")
            return
        
        try:
            lines = []
            
            lines.append("State Code\tState Name\tUser Count\tPercentage")
            
            total_count = sum(self.state_counts.values())
            all_states = sorted(STATE_NAMES.keys())
            
            for state in all_states:
                count = self.state_counts.get(state, 0)
                state_name = STATE_NAMES[state]
                percentage = (count / total_count) * 100 if count > 0 else 0
                
                lines.append(f"{state}\t{state_name}\t{count}\t{percentage:.2f}%")
            
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
        def on_enter(event):
            coords = canvas.coords(item)
            x = (coords[0] + coords[2]) / 2
            y = coords[1] - 10
            
            state_name = STATE_NAMES.get(state, state)
            if count > 0:
                total = sum(self.state_counts.values())
                percentage = (count / total) * 100
                tooltip_text = f"{state_name}\n{count:,} users ({percentage:.1f}%)"
            else:
                tooltip_text = f"{state_name}\nNo data"
            
            canvas.tooltip = canvas.create_text(x, y, 
                                              text=tooltip_text,
                                              font=('Segoe UI', 9, 'bold'),
                                              fill='#ffffff',
                                              tags='tooltip')
            
            bbox = canvas.bbox(canvas.tooltip)
            padding = 5
            
            canvas.tooltip_bg = canvas.create_rectangle(
                bbox[0] - padding, bbox[1] - padding,
                bbox[2] + padding, bbox[3] + padding,
                fill='#2c3e50', outline='#ffffff', width=2,
                tags='tooltip'
            )
            
            canvas.tag_raise(canvas.tooltip)
        
        def on_leave(event):
            canvas.delete('tooltip')
        
        canvas.tag_bind(item, '<Enter>', on_enter)
        canvas.tag_bind(item, '<Leave>', on_leave)
    
    def _get_heatmap_color(self, count, max_count):
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
                
                writer.writerow(['State Code', 'State Name', 'User Count', 'Percentage'])
                
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