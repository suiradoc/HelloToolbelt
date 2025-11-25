import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import base64

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg=None, bg_color=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Determine background color (prefer explicit bg, then bg_color, then parent bg)
        if bg is None:
            if bg_color is not None:
                bg = bg_color
            else:
                try:
                    bg = parent.cget("bg")
                except Exception:
                    bg = "#ffffff"

        # Canvas + vertical scrollbar
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.v_scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Inner frame where content is placed
        self.inner = tk.Frame(self.canvas, bg=bg)
        # Backwards-compatible alias used by existing tools
        self.scrollable_frame = self.inner

        # Create window on canvas
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        # Configure scrolling region when content or canvas size changes
        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Initial mousewheel bindings
        self._bind_mousewheel_to_children(self.inner)

    def _on_frame_configure(self, event):
        """Update scrollregion to match inner frame size."""
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _on_canvas_configure(self, event):
        """Keep inner frame width in sync with canvas width."""
        try:
            self.canvas.itemconfig(self.window_id, width=event.width)
        except Exception:
            pass

    def _on_mousewheel(self, event):
        """Basic vertical mousewheel scrolling."""
        try:
            # On most platforms, event.delta is a multiple of 120
            delta = int(-1 * (event.delta / 120))
            self.canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def _bind_mousewheel(self, *_):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, *_):
        self.canvas.unbind_all("<MouseWheel>")

    def _bind_mousewheel_to_children(self, widget):
        """Recursively bind enter/leave events so scrolling works across all children."""
        try:
            widget.bind("<Enter>", self._bind_mousewheel)
            widget.bind("<Leave>", self._unbind_mousewheel)
            for child in widget.winfo_children():
                self._bind_mousewheel_to_children(child)
        except Exception:
            pass

    def _update_scroll_region(self):
        """Force update of the scrollregion (used after dynamic layout changes)."""
        try:
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def force_scroll_update(self):
        """Public helper used by tools after building their UI."""
        try:
            self.canvas.after_idle(self._update_scroll_region)
            self.canvas.after_idle(lambda: self._bind_mousewheel_to_children(self.scrollable_frame))
        except Exception:
            pass


class Base64Tool:
    def __init__(self, root):
        self.root = root
        self.root.title("Base64 Encoder/Decoder")
        
        # Check if this is running in HelloToolbelt (MockRoot) or standalone
        self.is_in_toolbelt = hasattr(root, '_title') and hasattr(root, 'pack')
        
        if not self.is_in_toolbelt:
            # Only configure background if running standalone
            self.root.configure(bg='#ffffff')
        
        # Use system default colors that will adapt to light/dark mode
        self.setup_adaptive_styling()
        
        self.root.minsize(800, 700)
        
        # Center the window when running standalone
        if not self.is_in_toolbelt:
            self._center_window()
        
        # Build the interface
        self.build_gui()
    
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
            self.text_color = parent_fg if parent_fg else '#2c3e50'
            self.text_secondary = '#34495e'
            # Button text colors - black for both modes
            self.button_text_color = '#000000'  # Black text for good contrast
            self.button_hover_text_color = '#000000'  # Black text for hover state

    def refresh_styling(self, is_dark_mode):
        """Refresh styling when dark mode is toggled from HelloToolbelt"""
        self.is_dark_mode = is_dark_mode
        
        # Force update the colors based on the new dark mode state
        if self.is_in_toolbelt:
            # Get the updated colors from HelloToolbelt container
            try:
                parent_bg = self.root.cget('bg')
                parent_fg = self.root.cget('fg')
            except:
                # Fallback if we can't get colors from parent
                if is_dark_mode:
                    parent_bg = '#2b2b2b'
                    parent_fg = '#ffffff'
                else:
                    parent_bg = '#ffffff'
                    parent_fg = '#2c3e50'
        else:
            # When standalone, we assume system theme has changed
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
            self.text_color = parent_fg
            self.text_secondary = '#34495e'
            # Button text colors - black for both modes
            self.button_text_color = '#000000'
            self.button_hover_text_color = '#000000'
        
        # Clear and recreate the interface
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Reinitialize the interface
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
        # Main container with padding (non-scrollable)
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header (stays fixed at top)
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
        
        header_subtitle = tk.Label(header_text_frame, 
                                  font=("Segoe UI", 9), bg=self.primary_color, fg='#ecf0f1')
        header_subtitle.pack(anchor="w", pady=(2, 0))
        
        # Create scrollable container for content (scrolls independently)
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
        
        # Main content
        content_frame = tk.Frame(content_container, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input, action, result sections stacked vertically
        self._build_input_section(content_frame)
        self._build_action_section(content_frame)
        self._build_result_section(content_frame)
        
        # Force scroll update after interface is built
        def update_scroll_after_build():
            try:
                if hasattr(self, 'scrollable_container'):
                    self.scrollable_container.force_scroll_update()
                    # Also update mouse wheel bindings for new children
                    self.scrollable_container._bind_mousewheel_to_children(self.scrollable_container.scrollable_frame)
            except Exception as e:
                print(f"Error updating scroll: {e}")
        
        # Multiple attempts to ensure scrolling works
        self.root.after(100, update_scroll_after_build)
        self.root.after(500, update_scroll_after_build)
        self.root.after(1000, update_scroll_after_build)

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
        
        # Input text area
        self.input_text = scrolledtext.ScrolledText(input_content, wrap=tk.WORD, height=10,
                                                   font=('Consolas', 10), bg='white', fg='#2c3e50')
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # Input options and buttons
        options_frame = tk.Frame(input_content, bg=self.frame_bg)
        options_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Info label
        info_label = tk.Label(options_frame, text="Enter plain text for encoding or Base64 text for decoding.",
                             font=("Segoe UI", 9), bg=self.frame_bg, fg=self.text_secondary)
        info_label.pack(side=tk.LEFT)
        
        # Buttons
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
        
        # Add hover effects
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
        
        # Main action buttons
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
        
        # Add hover effects
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
        
        # Result text area
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
        
        # Add hover effects
        self._add_button_hover(copy_result_btn, self.success_color, '#229954')
        self._add_button_hover(clear_result_btn, '#95a5a6', '#7f8c8d')

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

    def _is_valid_base64(self, s):
        """Check if string is valid Base64"""
        try:
            # Remove whitespace
            s = ''.join(s.split())
            # Check if it's valid Base64
            if len(s) % 4 == 0:
                base64.b64decode(s, validate=True)
                return True
            return False
        except Exception:
            return False

    def encode_base64(self):
        """Encode the input text to Base64"""
        input_str = self.input_text.get("1.0", tk.END).strip()
        
        if not input_str:
            self.status_label.config(text="❌ No input to encode", foreground=self.danger_color)
            return
        
        try:
            # Encode to Base64
            encoded = base64.b64encode(input_str.encode("utf-8")).decode("utf-8")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, encoded)
            
            # Update status
            char_count = len(input_str)
            encoded_length = len(encoded)
            self.status_label.config(text=f"✅ Encoded {char_count} characters to {encoded_length} Base64 characters", 
                                   foreground=self.success_color)
            
        except Exception as e:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, f"Encoding Error: {str(e)}")
            self.status_label.config(text=f"❌ Encoding failed: {str(e)}", foreground=self.danger_color)

    def decode_base64(self):
        """Decode the input text from Base64"""
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
            
            # Decode from Base64
            decoded = base64.b64decode(input_str).decode("utf-8", errors="replace")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, decoded)
            
            # Update status
            input_length = len(input_str)
            decoded_length = len(decoded)
            self.status_label.config(text=f"✅ Decoded {input_length} Base64 characters to {decoded_length} characters", 
                                   foreground=self.success_color)
            
        except Exception as e:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, f"Decoding Error: {str(e)}")
            self.status_label.config(text=f"❌ Decoding failed: {str(e)}", foreground=self.danger_color)

    def copy_input(self):
        """Copy input text to clipboard"""
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
        """Clear input text"""
        self.input_text.delete("1.0", tk.END)
        self.status_label.config(text="🗑️ Input cleared", foreground=self.primary_color)

    def copy_result(self):
        """Copy result text to clipboard"""
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
        """Clear result text"""
        self.result_text.delete("1.0", tk.END)
        self.status_label.config(text="🗑️ Result cleared", foreground=self.primary_color)


if __name__ == "__main__":
    root = tk.Tk()
    app = Base64Tool(root)
    root.mainloop()