import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import base64

class ScrollableFrame(tk.Frame):    
    def __init__(self, parent, bg=None, bg_color=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # BG COLOR
        if bg is None:
            if bg_color is not None:
                bg = bg_color
            else:
                try:
                    bg = parent.cget("bg")
                except Exception:
                    bg = "#ffffff"

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.v_scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self.scrollable_frame = self.inner  # Backwards-compatible alias

        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._bind_mousewheel_to_children(self.inner)

    def _on_frame_configure(self, event):
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _on_canvas_configure(self, event):
        try:
            self.canvas.itemconfig(self.window_id, width=event.width)
        except Exception:
            pass

    def _on_mousewheel(self, event):
        try:
            delta = int(-1 * (event.delta / 120))
            self.canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def _bind_mousewheel(self, *_):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, *_):
        self.canvas.unbind_all("<MouseWheel>")

    def _bind_mousewheel_to_children(self, widget):
        try:
            widget.bind("<Enter>", self._bind_mousewheel)
            widget.bind("<Leave>", self._unbind_mousewheel)
            for child in widget.winfo_children():
                self._bind_mousewheel_to_children(child)
        except Exception:
            pass

    def _update_scroll_region(self):
        try:
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def force_scroll_update(self):
        try:
            self.canvas.after_idle(self._update_scroll_region)
            self.canvas.after_idle(lambda: self._bind_mousewheel_to_children(self.scrollable_frame))
        except Exception:
            pass


class Base64Tool:
    def __init__(self, root):
        self.root = root
        self.root.title("Base64 Encoder/Decoder")
        
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        if not self.is_in_toolbelt:
            self.root.configure(bg='#ffffff')
        
        self._apply_color_scheme()
        self._setup_fonts_and_sizing()
        
        self.root.minsize(800, 700)
        
        if not self.is_in_toolbelt:
            self._center_window()
        
        self.build_gui()

    def _get_parent_colors(self):
        """Get background and foreground colors from parent or system."""
        if self.is_in_toolbelt:
            try:
                return self.root.cget('bg'), self.root.cget('fg')
            except:
                return '#ffffff', '#2c3e50'
        else:
            temp_label = tk.Label(self.root)
            bg = temp_label.cget('bg')
            fg = temp_label.cget('fg')
            temp_label.destroy()
            return bg, fg

    def _detect_dark_mode(self, bg_color):
        """Detect if we're in dark mode based on background brightness."""
        try:
            if bg_color.startswith('#'):
                r = int(bg_color[1:3], 16)
                g = int(bg_color[3:5], 16)
                b = int(bg_color[5:7], 16)
            else:
                rgb = self.root.winfo_rgb(bg_color)
                r, g, b = rgb[0] // 256, rgb[1] // 256, rgb[2] // 256
            
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness < 128
        except:
            return False

    def _apply_color_scheme(self, is_dark_mode=None):
        parent_bg, parent_fg = self._get_parent_colors()
        
        if is_dark_mode is None:
            self.is_dark_mode = self._detect_dark_mode(parent_bg)
        else:
            self.is_dark_mode = is_dark_mode
            if is_dark_mode:
                parent_bg = '#2b2b2b' if not self.is_in_toolbelt else parent_bg
                parent_fg = '#ffffff' if not self.is_in_toolbelt else parent_fg
            else:
                parent_bg = '#ffffff' if not self.is_in_toolbelt else parent_bg
                parent_fg = '#2c3e50' if not self.is_in_toolbelt else parent_fg
        
        if self.is_dark_mode:
            self.bg_color = parent_bg
            self.frame_bg = '#3c3c3c'
            self.header_bg = '#4a4a4a'
            self.primary_color = '#4a90e2'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.text_color = parent_fg if parent_fg else '#ffffff'
            self.text_secondary = '#cccccc'
        else:
            self.bg_color = parent_bg
            self.frame_bg = '#f8f9fa'
            self.header_bg = '#e9ecef'
            self.primary_color = '#3498db'
            self.success_color = '#27ae60'
            self.danger_color = '#e74c3c'
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.text_secondary = '#34495e'
        
        self.button_text_color = '#000000'
        self.button_hover_text_color = '#000000'

    def _setup_fonts_and_sizing(self):
        self.title_font = ("Segoe UI", 14, "bold")
        self.subtitle_font = ("Segoe UI", 11, "bold")
        self.label_font = ("Segoe UI", 10)
        self.text_font = ("Segoe UI", 10)
        
        self.button_padx = 8
        self.button_pady = 4
        self.frame_padx = 20
        self.frame_pady = 15

    def refresh_styling(self, is_dark_mode):
        self._apply_color_scheme(is_dark_mode)
        
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
        
        # Header
        header_frame = tk.Frame(main_container, bg=self.primary_color, relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        header_content = tk.Frame(header_frame, bg=self.primary_color)
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        header_icon = tk.Label(header_content, text="🔐", font=('Segoe UI', 20), bg=self.primary_color, fg='white')
        header_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        header_text_frame = tk.Frame(header_content, bg=self.primary_color)
        header_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        header_title = tk.Label(header_text_frame, text="Base64 Encoder & Decoder", font=self.title_font, 
                               bg=self.primary_color, fg='white')
        header_title.pack(anchor="w")
        
        # Scrollable content area
        self.scrollable_container = ScrollableFrame(main_container, bg_color=self.bg_color, bg=self.bg_color)
        self.scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        content_container = self.scrollable_container.scrollable_frame
        content_container.configure(bg=self.bg_color)
        
        # Status bar
        status_frame = tk.Frame(content_container, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=(0, 15), padx=5)
        
        self.status_label = tk.Label(status_frame, text="Ready", font=("Segoe UI", 9),
                                    bg=self.bg_color, fg=self.text_secondary, anchor="w")
        self.status_label.pack(fill=tk.X)
        
        # Main content sections
        content_frame = tk.Frame(content_container, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        self._build_input_section(content_frame)
        self._build_action_section(content_frame)
        self._build_result_section(content_frame)
        
        # Update scroll region after build
        self.root.after(100, self._update_scroll_after_build)

    def _update_scroll_after_build(self):
        try:
            if hasattr(self, 'scrollable_container'):
                self.scrollable_container.force_scroll_update()
        except Exception as e:
            print(f"Error updating scroll: {e}")

    def _build_input_section(self, parent):
        input_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Header
        header_frame = tk.Frame(input_frame, bg=self.header_bg, height=50)
        header_frame.pack(fill=tk.X)
        
        header_label = tk.Label(header_frame, text="✏️ Input", font=self.subtitle_font,
                               bg=self.header_bg, fg=self.text_color)
        header_label.pack(pady=15, padx=20, anchor="w")
        
        # Content
        input_content = tk.Frame(input_frame, bg=self.frame_bg)
        input_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        self.input_text = scrolledtext.ScrolledText(input_content, wrap=tk.WORD, height=10,
                                                   font=('Consolas', 10), bg='white', fg='#2c3e50')
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # Options and buttons
        options_frame = tk.Frame(input_content, bg=self.frame_bg)
        options_frame.pack(fill=tk.X, pady=(10, 0))
        
        info_label = tk.Label(options_frame, text="Enter plain text for encoding or Base64 text for decoding.",
                             font=("Segoe UI", 9), bg=self.frame_bg, fg=self.text_secondary)
        info_label.pack(side=tk.LEFT)
        
        buttons_frame = tk.Frame(options_frame, bg=self.frame_bg)
        buttons_frame.pack(side=tk.RIGHT)
        
        clear_input_btn = tk.Button(buttons_frame, text="Clear Input", command=self.clear_input,
                                   padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                   bg='#bdc3c7', fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        clear_input_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        copy_input_btn = tk.Button(buttons_frame, text="Copy Input", command=self.copy_input,
                                  padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                  bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        copy_input_btn.pack(side=tk.LEFT)
        
        self._add_button_hover(clear_input_btn, '#95a5a6', '#7f8c8d')
        self._add_button_hover(copy_input_btn, self.primary_color, '#2980b9')
        
        # Help text
        help_frame = tk.Frame(input_content, bg=self.frame_bg)
        help_frame.pack(fill=tk.X, pady=(15, 0))
        
        help_text = ("Enter any text for encoding to Base64, or enter Base64-encoded text for decoding.\n"
                    "The tool supports UTF-8 text encoding and handles multi-line content.")
        help_label = tk.Label(help_frame, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT)
        help_label.pack(anchor="w")

    def _build_action_section(self, parent):
        action_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Header
        action_header = tk.Frame(action_frame, bg=self.header_bg, height=50)
        action_header.pack(fill=tk.X)
        
        action_label = tk.Label(action_header, text="⚡ Actions", font=self.subtitle_font,
                               bg=self.header_bg, fg=self.text_color)
        action_label.pack(pady=15)
        
        # Content
        action_content = tk.Frame(action_frame, bg=self.frame_bg)
        action_content.pack(fill=tk.X, padx=20, pady=20)
        
        buttons_frame = tk.Frame(action_content, bg=self.frame_bg)
        buttons_frame.pack(pady=(0, 15))
        
        encode_btn = tk.Button(buttons_frame, text="🔒 Encode to Base64", command=self.encode_base64,
                              padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                              bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        encode_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        decode_btn = tk.Button(buttons_frame, text="🔓 Decode from Base64", command=self.decode_base64,
                              padx=self.button_padx + 2, pady=self.button_pady + 1, font=('Segoe UI', 10, 'bold'),
                              bg=self.primary_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        decode_btn.pack(side=tk.LEFT)
        
        self._add_button_hover(encode_btn, self.success_color, '#229954')
        self._add_button_hover(decode_btn, self.primary_color, '#2980b9')
        
        # Help text
        help_frame = tk.Frame(action_content, bg=self.frame_bg)
        help_frame.pack(fill=tk.X)
        
        help_text = ("Use 'Encode' to convert plain text to Base64 format. Use 'Decode' to convert Base64 back to plain text.")
        help_label = tk.Label(help_frame, text=help_text, font=("Segoe UI", 9), 
                             fg="#7f8c8d", bg=self.frame_bg, justify=tk.LEFT)
        help_label.pack(anchor="w")

    def _build_result_section(self, parent):
        result_frame = tk.Frame(parent, bg=self.frame_bg, relief='solid', bd=1)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        result_header = tk.Frame(result_frame, bg=self.header_bg, height=50)
        result_header.pack(fill=tk.X)
        
        result_label = tk.Label(result_header, text="📄 Result", font=self.subtitle_font,
                               bg=self.header_bg, fg=self.text_color)
        result_label.pack(pady=15)
        
        # Content
        result_content = tk.Frame(result_frame, bg=self.frame_bg)
        result_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        self.result_text = scrolledtext.ScrolledText(result_content, wrap=tk.WORD, height=10,
                                                    font=('Consolas', 10), bg='white', fg='#2c3e50')
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        result_buttons_frame = tk.Frame(result_content, bg=self.frame_bg)
        result_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        copy_result_btn = tk.Button(result_buttons_frame, text="Copy Result", command=self.copy_result,
                                   padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                   bg=self.success_color, fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        copy_result_btn.pack(side=tk.LEFT)
        
        clear_result_btn = tk.Button(result_buttons_frame, text="Clear Result", command=self.clear_result,
                                    padx=self.button_padx, pady=self.button_pady, font=('Segoe UI', 9),
                                    bg='#bdc3c7', fg=self.button_text_color, relief='flat', bd=0, cursor="hand2")
        clear_result_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        self._add_button_hover(copy_result_btn, self.success_color, '#229954')
        self._add_button_hover(clear_result_btn, '#95a5a6', '#7f8c8d')

    def _add_button_hover(self, button, normal_color, hover_color, normal_fg=None, hover_fg=None):
        try:
            if normal_fg is None:
                normal_fg = self.button_text_color
            if hover_fg is None:
                hover_fg = self.button_hover_text_color
                
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

    def _is_valid_base64(self, s):
        try:
            s = ''.join(s.split())
            if len(s) % 4 == 0:
                base64.b64decode(s, validate=True)
                return True
            return False
        except Exception:
            return False

    def encode_base64(self):
        input_str = self.input_text.get("1.0", tk.END).strip()
        
        if not input_str:
            self.status_label.config(text="❌ No input to encode", foreground=self.danger_color)
            return
        
        try:
            encoded = base64.b64encode(input_str.encode("utf-8")).decode("utf-8")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, encoded)
            
            char_count = len(input_str)
            encoded_length = len(encoded)
            self.status_label.config(text=f"✅ Encoded {char_count} characters to {encoded_length} Base64 characters", 
                                   foreground=self.success_color)
            
        except Exception as e:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, f"Encoding Error: {str(e)}")
            self.status_label.config(text=f"❌ Encoding failed: {str(e)}", foreground=self.danger_color)

    def decode_base64(self):
        input_str = self.input_text.get("1.0", tk.END).strip()
        
        if not input_str:
            self.status_label.config(text="❌ No input to decode", foreground=self.danger_color)
            return
        
        try:
            if not self._is_valid_base64(input_str):
                self.result_text.delete("1.0", tk.END)
                self.result_text.insert(tk.END, "Error: The input does not appear to be valid Base64.")
                self.status_label.config(text="❌ Invalid Base64 input", foreground=self.danger_color)
                return
            
            decoded = base64.b64decode(input_str).decode("utf-8", errors="replace")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, decoded)
            
            input_length = len(input_str)
            decoded_length = len(decoded)
            self.status_label.config(text=f"✅ Decoded {input_length} Base64 characters to {decoded_length} characters", 
                                   foreground=self.success_color)
            
        except Exception as e:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, f"Decoding Error: {str(e)}")
            self.status_label.config(text=f"❌ Decoding failed: {str(e)}", foreground=self.danger_color)

    def copy_input(self):
        input_str = self.input_text.get("1.0", tk.END).strip()
        if input_str:
            self.root.clipboard_clear()
            self.root.clipboard_append(input_str)
            self.root.update()
            self.status_label.config(text="📋 Input copied to clipboard", foreground=self.primary_color)
            messagebox.showinfo("Copied", "✅ Input copied to clipboard!")
        else:
            self.status_label.config(text="❌ No input to copy", foreground=self.danger_color)

    def clear_input(self):
        self.input_text.delete("1.0", tk.END)
        self.status_label.config(text="🗑️ Input cleared", foreground=self.primary_color)

    def copy_result(self):
        result_str = self.result_text.get("1.0", tk.END).strip()
        if result_str:
            self.root.clipboard_clear()
            self.root.clipboard_append(result_str)
            self.root.update()
            self.status_label.config(text="📋 Result copied to clipboard", foreground=self.primary_color)
            messagebox.showinfo("Copied", "✅ Result copied to clipboard!")
        else:
            self.status_label.config(text="❌ No result to copy", foreground=self.danger_color)

    def clear_result(self):
        """Clear result text."""
        self.result_text.delete("1.0", tk.END)
        self.status_label.config(text="🗑️ Result cleared", foreground=self.primary_color)


if __name__ == "__main__":
    root = tk.Tk()
    app = Base64Tool(root)
    root.mainloop()