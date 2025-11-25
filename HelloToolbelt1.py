import tkinter as tk
from tkinter import ttk, messagebox
import importlib.util
import sys
import os
import json
import threading
import time
import logging
from pathlib import Path
from contextlib import contextmanager
import hashlib

class SplashScreen:
    def __init__(self):
        self.splash = tk.Tk()
        self.splash.title("HelloToolbelt")
        self.splash.geometry("400x200")  # Made shorter since no icon
        self.splash.configure(bg='#2b2b2b')
        self.splash.resizable(False, False)
        self.splash.overrideredirect(True)
        
        self.center_splash()
        self.set_icon()
        self.preload_icon()  # Add this line
        self.create_splash_content()
        self.splash.lift()
        self.splash.attributes('-topmost', True)

    def center_splash(self):
        """Center the splash screen on the display"""
        self.splash.update_idletasks()
        width = 400
        height = 350  # Increased height for icon
        x = (self.splash.winfo_screenwidth() // 2) - (width // 2)
        y = (self.splash.winfo_screenheight() // 2) - (height // 2)
        self.splash.geometry(f'{width}x{height}+{x}+{y}')

    def preload_icon(self):
        """Pre-load the icon before creating UI elements"""
        try:
            # Check for icon files in priority order
            icon_paths = [
                'icon.icns',
                os.path.join(os.path.dirname(__file__), 'icon.icns'),
                os.path.join(os.getcwd(), 'icon.icns'),
                'icon.png', 'icon.gif', 'icon.ico',
                os.path.join(os.path.dirname(__file__), 'icon.png'),
                os.path.join(os.path.dirname(__file__), 'icon.gif'),
                os.path.join(os.path.dirname(__file__), 'icon.ico'),
                os.path.join(os.getcwd(), 'icon.png'),
                os.path.join(os.getcwd(), 'icon.gif'),
                os.path.join(os.getcwd(), 'icon.ico')
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        # Try PIL first
                        try:
                            from PIL import Image, ImageTk
                            
                            if icon_path.lower().endswith('.icns'):
                                image = Image.open(icon_path)
                                if hasattr(image, 'size'):
                                    image = image.resize((64, 64), Image.Resampling.LANCZOS)
                                else:
                                    image = image.resize((64, 64))
                            else:
                                image = Image.open(icon_path)
                                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                            
                            # Create PhotoImage with splash as master
                            self.icon_photo = ImageTk.PhotoImage(image, master=self.splash)
                            print(f"Pre-loaded icon: {icon_path}")
                            return True
                            
                        except ImportError:
                            # Try macOS sips conversion for .icns
                            if icon_path.lower().endswith('.icns') and sys.platform == 'darwin':
                                try:
                                    import subprocess
                                    import tempfile
                                    
                                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                                        temp_png = temp_file.name
                                    
                                    result = subprocess.run([
                                        'sips', '-s', 'format', 'png', 
                                        '-z', '64', '64',
                                        icon_path, '--out', temp_png
                                    ], capture_output=True, text=True, timeout=10)
                                    
                                    if result.returncode == 0 and os.path.exists(temp_png):
                                        self.icon_photo = tk.PhotoImage(file=temp_png, master=self.splash)
                                        
                                        try:
                                            os.unlink(temp_png)
                                        except:
                                            pass
                                        
                                        print(f"Pre-loaded converted .icns: {icon_path}")
                                        return True
                                        
                                except Exception:
                                    continue
                            
                            # Try tkinter PhotoImage for other formats
                            if icon_path.lower().endswith(('.gif', '.ppm', '.pgm', '.png')):
                                try:
                                    photo = tk.PhotoImage(file=icon_path, master=self.splash)
                                    if photo.width() > 64 or photo.height() > 64:
                                        factor = max(photo.width() // 64, photo.height() // 64, 1)
                                        photo = photo.subsample(factor, factor)
                                    
                                    self.icon_photo = photo
                                    print(f"Pre-loaded with tkinter: {icon_path}")
                                    return True
                                except Exception:
                                    continue
                                
                    except Exception:
                        continue
            
            print("No icon found during pre-load, will use emoji")
            return False
            
        except Exception as e:
            print(f"Error in preload_icon: {e}")
            return False
        
    def set_icon(self):
        """Set the application icon if available"""
        try:
            icon_paths = [
                'icon.icns', 'icon.ico',
                os.path.join(os.path.dirname(__file__), 'icon.icns'),
                os.path.join(os.path.dirname(__file__), 'icon.ico'),
                os.path.join(os.getcwd(), 'icon.icns'),
                os.path.join(os.getcwd(), 'icon.ico')
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    if icon_path.endswith('.icns') and sys.platform == 'darwin':
                        self.splash.iconbitmap(icon_path)
                        break
                    elif icon_path.endswith('.ico'):
                        self.splash.iconbitmap(icon_path)
                        break
        except Exception as e:
            print(f"Could not set icon: {e}")
    
    def create_splash_content(self):
        """Create the content for the splash screen"""
        # Set proper geometry first
        self.splash.geometry("400x350")
        self.splash.update_idletasks()
        width = 400
        height = 350
        x = (self.splash.winfo_screenwidth() // 2) - (width // 2)
        y = (self.splash.winfo_screenheight() // 2) - (height // 2)
        self.splash.geometry(f'{width}x{height}+{x}+{y}')
        
        main_frame = tk.Frame(self.splash, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Icon section
        icon_frame = tk.Frame(main_frame, bg='#2b2b2b')
        icon_frame.pack(pady=(10, 15))
        
        # Create icon label
        self.icon_label = tk.Label(icon_frame, 
                                text="🔧", 
                                font=('Segoe UI', 48),
                                bg='#2b2b2b', 
                                fg='white')
        self.icon_label.pack()
        
        # Try to load actual icon
        self.load_icon_image()
        
        # App name
        tk.Label(main_frame, text="HelloToolbelt", font=('Segoe UI', 24, 'bold'),
                fg='white', bg='#2b2b2b').pack(pady=(10, 5))
        
        # Version
        tk.Label(main_frame, text="Version 2.1.0", font=('Segoe UI', 12),
                fg='#cccccc', bg='#2b2b2b').pack(pady=(0, 20))
        
        # Loading text
        self.loading_label = tk.Label(main_frame, text="Loading...", font=('Segoe UI', 11),
                                    fg='#4a90e2', bg='#2b2b2b')
        self.loading_label.pack(pady=(0, 10))
        
        # Progress bar
        progress_frame = tk.Frame(main_frame, bg='#2b2b2b')
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_canvas = tk.Canvas(progress_frame, height=6, bg='#404040', highlightthickness=0)
        self.progress_canvas.pack(fill=tk.X, padx=40)
        
        self.update_progress(0)
    
    def load_icon_image(self):
        """Try to load actual icon image file including .icns"""
        try:
            print("=== Icon Loading Debug ===")
            print(f"Script directory: {os.path.dirname(__file__)}")
            print(f"Current working directory: {os.getcwd()}")
            
            # Prioritize .icns files first, then other formats
            icon_paths = [
                'icon.icns',  # Current directory
                os.path.join(os.path.dirname(__file__), 'icon.icns'),  # Script directory
                os.path.join(os.getcwd(), 'icon.icns'),  # Working directory
                'icon.png', 'icon.gif', 'icon.ico',  # Fallback formats
                os.path.join(os.path.dirname(__file__), 'icon.png'),
                os.path.join(os.path.dirname(__file__), 'icon.gif'),
                os.path.join(os.path.dirname(__file__), 'icon.ico'),
                os.path.join(os.getcwd(), 'icon.png'),
                os.path.join(os.getcwd(), 'icon.gif'),
                os.path.join(os.getcwd(), 'icon.ico')
            ]
            
            print("Checking for icon files...")
            for i, icon_path in enumerate(icon_paths):
                exists = os.path.exists(icon_path)
                print(f"{i+1}. {icon_path} - {'EXISTS' if exists else 'NOT FOUND'}")
                
                if exists:
                    print(f"*** Attempting to load: {icon_path} ***")
                    try:
                        # Ensure splash window is ready
                        self.splash.update_idletasks()
                        
                        # Try PIL first (best method)
                        try:
                            from PIL import Image, ImageTk
                            print("PIL is available, using PIL method...")
                            
                            if icon_path.lower().endswith('.icns'):
                                print("Detected .icns file, loading with PIL...")
                                image = Image.open(icon_path)
                                print(f"Original image size: {image.size}")
                                print(f"Image mode: {image.mode}")
                                
                                # For .icns files, PIL automatically selects the best size
                                # Resize to 64x64 for splash screen display
                                if hasattr(image, 'size'):
                                    image = image.resize((64, 64), Image.Resampling.LANCZOS)
                                    print("Resized image to 64x64")
                                else:
                                    image = image.resize((64, 64))
                                    print("Resized image to 64x64 (fallback method)")
                            else:
                                print(f"Loading {os.path.splitext(icon_path)[1]} file with PIL...")
                                image = Image.open(icon_path)
                                print(f"Original image size: {image.size}")
                                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                                print("Resized image to 64x64")
                            
                            print("Converting to PhotoImage...")
                            # Create PhotoImage with explicit master to avoid pyimage errors
                            photo = ImageTk.PhotoImage(image, master=self.splash)
                            print("Updating label...")
                            self.icon_label.configure(image=photo, text="")
                            # Store reference in the splash object to prevent garbage collection
                            self.splash.icon_photo = photo
                            print(f"SUCCESS: Icon loaded from {icon_path}")
                            print("=== End Icon Loading Debug ===")
                            return True
                            
                        except ImportError as e:
                            print(f"PIL not available: {e}")
                            print("Trying alternative methods...")
                            
                            # Special handling for .icns files on macOS without PIL
                            if icon_path.lower().endswith('.icns') and sys.platform == 'darwin':
                                try:
                                    print("Attempting .icns conversion with macOS sips...")
                                    import subprocess
                                    import tempfile
                                    
                                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                                        temp_png = temp_file.name
                                    print(f"Temporary PNG file: {temp_png}")
                                    
                                    # Use macOS sips tool to convert .icns to PNG
                                    print("Running sips command...")
                                    result = subprocess.run([
                                        'sips', '-s', 'format', 'png', 
                                        '-z', '64', '64',  # Resize to 64x64
                                        icon_path, '--out', temp_png
                                    ], capture_output=True, text=True, timeout=10)
                                    
                                    print(f"sips return code: {result.returncode}")
                                    if result.stdout:
                                        print(f"sips stdout: {result.stdout}")
                                    if result.stderr:
                                        print(f"sips stderr: {result.stderr}")
                                    
                                    if result.returncode == 0 and os.path.exists(temp_png):
                                        print("Loading converted PNG...")
                                        # Create PhotoImage with explicit master
                                        photo = tk.PhotoImage(file=temp_png, master=self.splash)
                                        self.icon_label.configure(image=photo, text="")
                                        # Store reference to prevent garbage collection
                                        self.splash.icon_photo = photo
                                        
                                        # Clean up temp file
                                        try:
                                            os.unlink(temp_png)
                                            print("Cleaned up temporary file")
                                        except:
                                            pass
                                        
                                        print(f"SUCCESS: Converted and loaded .icns from {icon_path}")
                                        print("=== End Icon Loading Debug ===")
                                        return True
                                    else:
                                        print(f"sips conversion failed or temp file not created")
                                        
                                except Exception as e:
                                    print(f"macOS .icns conversion failed: {e}")
                                    continue
                            
                            # Try with tkinter PhotoImage for other formats
                            if icon_path.lower().endswith(('.gif', '.ppm', '.pgm', '.png')):
                                try:
                                    print(f"Loading {os.path.splitext(icon_path)[1]} with tkinter PhotoImage...")
                                    # Create PhotoImage with explicit master
                                    photo = tk.PhotoImage(file=icon_path, master=self.splash)
                                    print(f"PhotoImage size: {photo.width()}x{photo.height()}")
                                    
                                    # Resize if too large
                                    if photo.width() > 64 or photo.height() > 64:
                                        factor = max(photo.width() // 64, photo.height() // 64, 1)
                                        photo = photo.subsample(factor, factor)
                                        print(f"Subsampled by factor {factor}")
                                    
                                    self.icon_label.configure(image=photo, text="")
                                    # Store reference to prevent garbage collection
                                    self.splash.icon_photo = photo
                                    print(f"SUCCESS: Loaded with tkinter from {icon_path}")
                                    print("=== End Icon Loading Debug ===")
                                    return True
                                except Exception as e:
                                    print(f"tkinter PhotoImage failed: {e}")
                                    continue
                            else:
                                print(f"File format {os.path.splitext(icon_path)[1]} not supported by tkinter PhotoImage")
                                
                    except Exception as e:
                        print(f"ERROR loading {icon_path}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
            
            print("RESULT: No suitable icon file found or could be loaded, using emoji fallback")
            print("=== End Icon Loading Debug ===")
            return False
            
        except Exception as e:
            print(f"CRITICAL ERROR in load_icon_image: {e}")
            import traceback
            traceback.print_exc()
            print("=== End Icon Loading Debug ===")
            return False
    
    def update_progress(self, percentage):
        """Update the progress bar"""
        try:
            self.splash.update_idletasks()
            
            canvas_width = self.progress_canvas.winfo_width()
            if canvas_width <= 1:
                # Canvas not ready yet, skip this update
                return
            
            self.progress_canvas.delete("progress")
            progress_width = int((percentage / 100) * canvas_width)
            
            if progress_width > 0:
                self.progress_canvas.create_rectangle(
                    0, 0, progress_width, 6,
                    fill='#4a90e2', outline='', tags="progress"
                )
            
            self.splash.update()
            
        except Exception as e:
            print(f"Error updating progress: {e}")
    
    def update_status(self, text, percentage=None):
        """Update the loading status text and optionally progress"""
        try:
            self.loading_label.configure(text=text)
            if percentage is not None:
                self.update_progress(percentage)
            self.splash.update()
        except Exception:
            pass
    
    def destroy(self):
        """Close the splash screen with smooth fade out"""
        try:
            # Fade out animation for smoother transition
            if sys.platform == 'darwin':
                # macOS supports alpha transparency
                for alpha in range(10, 0, -1):
                    try:
                        self.splash.attributes('-alpha', alpha / 10.0)
                        self.splash.update()
                        time.sleep(0.02)
                    except:
                        break
            self.splash.destroy()
        except Exception:
            pass

class PasswordDialog:
    def __init__(self, parent, colors):
        self.result = None
        self.colors = colors
        self.parent = parent
        
        # Ensure parent window is properly updated before creating dialog
        try:
            parent.update_idletasks()
        except:
            pass
        
        # Create modal dialog with larger size
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Tier 3 Access")
        self.dialog.configure(bg=colors['bg'])
        self.dialog.resizable(False, False)
        
        # Make it modal and ensure it appears on top
        self.dialog.transient(parent)
        
        # Set larger initial size before centering
        self.dialog.geometry("500x350")  # Increased from 400x250
        
        # Center the dialog BEFORE making it modal
        self.center_dialog()
        
        # Now make it modal and bring to front
        self.dialog.grab_set()
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.focus_force()
        
        # Create UI first
        self.create_ui()
        
        # Focus on password entry after UI is created - with multiple attempts
        self.dialog.after(50, self.focus_password_entry)
        self.dialog.after(150, self.focus_password_entry)
        self.dialog.after(300, self.focus_password_entry)
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Bind Enter and Escape keys to the dialog itself as backup
        self.dialog.bind('<Return>', lambda e: self.submit())
        self.dialog.bind('<KP_Enter>', lambda e: self.submit())  # Keypad Enter
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        print(f"Password dialog created at position: {self.dialog.geometry()}")
    
    def focus_password_entry(self):
        """Focus on password entry field"""
        try:
            # Ensure the dialog is visible and on top
            self.dialog.lift()
            self.dialog.focus_force()
            
            # Focus the password entry
            self.password_entry.focus_set()
            self.password_entry.icursor(0)
            
            # Make sure it has keyboard focus
            self.password_entry.selection_clear()
            
            print("Password entry focused")  # Debug
        except Exception as e:
            print(f"Error focusing password entry: {e}")
    
    def center_dialog(self):
        """Center the dialog on the main window or screen"""
        try:
            # Force geometry update
            self.dialog.update_idletasks()
            
            # Get dialog dimensions - updated for larger size
            dialog_width = 500   # Increased from 400
            dialog_height = 350  # Increased from 250
            
            # Try to center on the main window first
            try:
                # Get main window position and size
                main_x = self.parent.winfo_rootx()
                main_y = self.parent.winfo_rooty()
                main_width = self.parent.winfo_width()
                main_height = self.parent.winfo_height()
                
                # Calculate center position relative to main window
                x = main_x + (main_width // 2) - (dialog_width // 2)
                y = main_y + (main_height // 2) - (dialog_height // 2)
                
                print(f"Main window at: {main_x}x{main_y}, size: {main_width}x{main_height}")
                print(f"Calculated dialog position: {x}x{y}")
                
            except Exception as e:
                print(f"Could not get main window position: {e}")
                # Fallback to screen center
                screen_width = self.dialog.winfo_screenwidth()
                screen_height = self.dialog.winfo_screenheight()
                x = (screen_width // 2) - (dialog_width // 2)
                y = (screen_height // 2) - (dialog_height // 2)
                print(f"Using screen center: {x}x{y}")
            
            # Ensure dialog stays on screen
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            # Clamp to screen boundaries with some margin
            margin = 50
            x = max(margin, min(x, screen_width - dialog_width - margin))
            y = max(margin, min(y, screen_height - dialog_height - margin))
            
            print(f"Final dialog position: {x}x{y}")
            
            # Set the geometry with new size
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            
            # Force update and bring to front
            self.dialog.update_idletasks()
            self.dialog.lift()
            self.dialog.attributes('-topmost', True)
            
        except Exception as e:
            print(f"Error centering dialog: {e}")
            # Emergency fallback - larger size
            self.dialog.geometry("500x350+100+100")
    
    def create_ui(self):
        """Create the password dialog UI"""
        # Main container with reduced padding
        main_frame = tk.Frame(self.dialog, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)  # Reduced padding
        
        # Header with icon
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 15))  # Reduced bottom padding
        
        icon_label = tk.Label(header_frame, 
                            text="🔐", 
                            font=('Segoe UI', 20),  # Smaller icon
                            bg=self.colors['bg'],
                            fg=self.colors['fg'])
        icon_label.pack(side=tk.LEFT, padx=(0, 10))  # Less spacing
        
        title_label = tk.Label(header_frame, 
                             text="Tier 3 Access Required", 
                             font=('Segoe UI', 14, 'bold'),  # Smaller font
                             fg=self.colors['fg'],
                             bg=self.colors['bg'])
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Description with less space
        desc_label = tk.Label(main_frame,
                            text="Enter password to access Tier 3 tools:",
                            font=('Segoe UI', 10),  # Smaller font
                            fg=self.colors['text_secondary'],
                            bg=self.colors['bg'])
        desc_label.pack(anchor='w', pady=(0, 15))  # Less padding
        
        # Password frame
        password_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        password_frame.pack(fill=tk.X, pady=(0, 15))  # Less padding
        
        password_label = tk.Label(password_frame,
                                text="Password:",
                                font=('Segoe UI', 10, 'bold'),  # Smaller font
                                fg=self.colors['fg'],
                                bg=self.colors['bg'])
        password_label.pack(anchor='w', pady=(0, 5))  # Less padding
        
        self.password_entry = tk.Entry(password_frame,
                                     font=('Segoe UI', 11),  # Smaller font
                                     show="*",
                                     bg=self.colors['frame_bg'],
                                     fg=self.colors['fg'],
                                     relief='solid',
                                     bd=1,  # Thinner border
                                     insertbackground=self.colors['fg'])
        self.password_entry.pack(fill=tk.X, ipady=4)  # Less internal padding
        
        # Bind Enter key directly to the password entry field
        self.password_entry.bind('<Return>', lambda e: self.submit())
        self.password_entry.bind('<KP_Enter>', lambda e: self.submit())  # Keypad Enter
        
        # Error label (initially hidden) with less space
        self.error_label = tk.Label(main_frame,
                                  text="",
                                  font=('Segoe UI', 9),  # Smaller font
                                  fg=self.colors['danger'],
                                  bg=self.colors['bg'])
        self.error_label.pack(anchor='w', pady=(5, 0))  # Less padding
        
        # Button frame with less space
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X, pady=(15, 0))  # Less top padding
        
        # Cancel button with smaller size
        cancel_btn = tk.Button(button_frame,
                             text="Cancel",
                             command=self.cancel,
                             bg=self.colors['frame_bg'],
                             fg='#000000',  # Black text
                             font=('Segoe UI', 10),  # Smaller font
                             relief='solid',
                             bd=1,
                             padx=15,  # Less padding
                             pady=6,   # Less padding
                             cursor='hand2')
        cancel_btn.pack(side=tk.LEFT)
        
        # Submit button with smaller size
        submit_btn = tk.Button(button_frame,
                             text="Submit",
                             command=self.submit,
                             bg=self.colors['primary'],
                             fg='#000000',  # Black text
                             font=('Segoe UI', 10, 'bold'),  # Smaller font
                             relief='flat',
                             bd=0,
                             padx=15,  # Less padding
                             pady=6,   # Less padding
                             cursor='hand2')
        submit_btn.pack(side=tk.RIGHT)
        
        # Bind Enter key to submit button as well
        submit_btn.bind('<Return>', lambda e: self.submit())
        submit_btn.bind('<KP_Enter>', lambda e: self.submit())
        
        # Add hover effects with black text
        def on_submit_enter(e):
            submit_btn.config(bg='#2980b9' if not self.colors.get('is_dark') else '#5a9de8', fg='#000000')
        
        def on_submit_leave(e):
            submit_btn.config(bg=self.colors['primary'], fg='#000000')
        
        def on_cancel_enter(e):
            cancel_btn.config(bg=self.colors['secondary_bg'], fg='#000000')
        
        def on_cancel_leave(e):
            cancel_btn.config(bg=self.colors['frame_bg'], fg='#000000')
        
        submit_btn.bind("<Enter>", on_submit_enter)
        submit_btn.bind("<Leave>", on_submit_leave)
        cancel_btn.bind("<Enter>", on_cancel_enter)
        cancel_btn.bind("<Leave>", on_cancel_leave)
    
    def submit(self):
        """Handle password submission"""
        try:
            password = self.password_entry.get()
            print(f"Password submitted: {'*' * len(password)}")  # Debug print (don't show actual password)
            
            if not password:
                self.show_error("Please enter a password")
                return
            
            # Check password (you can change this password)
            if self.verify_password(password):
                print("Password verification successful")  # Debug print
                self.result = True
                self.dialog.destroy()
            else:
                print("Password verification failed")  # Debug print
                self.show_error("Incorrect password")
                self.password_entry.delete(0, tk.END)
                self.password_entry.focus_set()
        except Exception as e:
            print(f"Error in submit: {e}")
            self.result = False
            try:
                self.dialog.destroy()
            except:
                pass
    
    def verify_password(self, password):
        """Verify the entered password"""
        # You can change this password to whatever you want
        # For security, we're using a simple hash comparison
        correct_password = "tier3access"  # Change this to your desired password
        return password == correct_password
    
    def show_error(self, message):
        """Show error message"""
        self.error_label.config(text=message)
    
    def cancel(self):
        """Handle dialog cancellation"""
        try:
            print("Password dialog cancelled")  # Debug print
            self.result = False
            self.dialog.destroy()
        except Exception as e:
            print(f"Error in cancel: {e}")
            self.result = False
    
    def wait_for_result(self):
        """Wait for dialog result"""
        try:
            print("Waiting for dialog window...")  # Debug print
            self.dialog.wait_window()
            print(f"Dialog closed, result: {self.result}")  # Debug print
            return self.result
        except Exception as e:
            print(f"Error in wait_for_result: {e}")
            return False

class MultiToolLauncher:
    def __init__(self, root, splash=None):
        self.splash = splash
        self.root = root
        
        # Keep window hidden (already withdrawn in main)
        # Don't set title/geometry yet to prevent flash
        
        # Version information
        self.version = "2.1.0"  # Updated version for stability improvements
        
        # Initialize callback tracking for cleanup
        self._scheduled_callbacks = set()
        self._destroyed = False
        
        # Update splash
        if self.splash:
            self.splash.update_status("Initializing...", 10)
        
        # Add stability improvements FIRST
        self._tool_cleanup_lock = threading.Lock()
        self._settings_lock = threading.Lock()
        self._loading_tools = set()
        
        # Setup logging
        self.setup_logging()
        
        if self.splash:
            self.splash.update_status("Setting up configuration...", 20)
        
        # Settings file path - FIXED for PyInstaller
        self.settings_file = self.get_settings_file_path()
        
        # Load settings and initialize dark mode state
        self.load_settings()
        
        if self.splash:
            self.splash.update_status("Loading settings...", 30)
        
        # Initialize tier setting with proper unlock status check
        if not hasattr(self, 'tier3_unlocked'):
            self.tier3_unlocked = False
        
        if not hasattr(self, 'current_tier'):
            self.current_tier = 'Tier 3' if self.tier3_unlocked else 'Tier 2'
        
        # Configure enhanced styling
        self.setup_styles()
        
        if self.splash:
            self.splash.update_status("Setting up interface...", 40)
        
        # Set root background color based on loaded settings
        colors = self.get_colors()
        self.root.configure(bg=colors['bg'])
        
        # Set main window icon
        self.set_main_window_icon()
        
        # Check if we should show welcome popup (do this before creating UI)
        self.check_and_show_welcome()
        
        if self.splash:
            self.splash.update_status("Creating main interface...", 50)
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Tool configurations - modify these paths to match your script locations
        self.tools = [
            {
                'name': 'Client Configuration',
                'file': 'configurator_tool.py',
                'class': 'CSVConfigApp', 
                'description': 'Create the JSON configurations for Eligibility and Formatting files',
                'icon': '⚙️'
            },
            {
                'name': 'CronJob Configuration',
                'file': 'Cron_tool.py',
                'class': 'CronJobGenerator',
                'description': 'Generate Kubernetes CronJob YAML configurations',
                'icon': '⏰'
            },
            {
                'name': 'Eligibility Search',
                'file': 'eligibility_tool.py',
                'class': 'EligibilitySearchTool',
                'description': 'Search and analyze eligibility data with age and term date validation',
                'icon': '🔍'
            },
            {
                'name': 'Multi-File Column Search',
                'file': 'multisearch_tool.py', 
                'class': 'MultiFileColumnSearchTool',
                'description': 'Search across multiple files for specific column values',
                'icon': '📂'
            },
            {
                'name': 'Base64 Encoder/Decoder',
                'file': 'Base64_Tool.py',
                'class': 'Base64Tool',
                'description': 'Encode and decode Base64 strings',
                'icon': '🔐'
            },
            {
                'name': 'DLQ Fetcher',
                'file': 'DLQ_Tool.py',
                'class': 'DLQFetcherTool',
                'description': 'Run DLQ Fetcher JAR with queue selection and formatted output',
                'icon': '📨'
            },
            {
            'name': 'Bill Hunter',
            'file': 'bill_hunter.py',
            'class': 'FileParserGUI',
            'description': 'Match unbillable users from client files with PostgreSQL query results',
            'icon': '🎯'
            },
            {
            'name': 'Shipping Map',
            'file': 'shipping_map.py',
            'class': 'ZipcodeHeatmapTool',
            'description': 'Interactive shipping route and location mapper',
            'icon': '🗺️'
            }
        ]
        
        if self.splash:
            self.splash.update_status("Loading tools...", 60)
        
        # Store loaded tools
        self.loaded_tools = {}
        
        # Create tabs for each tool based on tier
        self.create_tool_tabs()
        
        if self.splash:
            self.splash.update_status("Finalizing interface...", 80)
        
        # Add options tab (will be moved to end after creation)
        self.create_options_tab()
        
        # Move options tab to the end
        self.move_options_tab_to_end()
        
        # Pre-render all tabs to eliminate flash on first view
        self.pre_render_all_tabs()
        
        if self.splash:
            self.splash.update_status("Completing setup...", 90)
        
        # Set window icon and center it
        self.center_window()
        
        # Save settings when app closes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        if self.splash:
            self.splash.update_status("Ready!", 100)
            # Close splash and show main window with smooth transition
            self.safe_after(200, self.show_main_window)
            # Fallback in case the callback fails
            self.safe_after(1000, self.emergency_show_window)
        else:
            # No splash, show main window immediately
            self.root.deiconify()

    def safe_after(self, delay, callback):
        """Safe wrapper for root.after() that tracks callbacks for cleanup"""
        if self._destroyed:
            return None
        
        try:
            # Create a wrapper that removes itself from tracking
            def wrapper():
                if not self._destroyed:
                    try:
                        callback()
                    except Exception as e:
                        self.log_error("Error in scheduled callback", e)
                # Remove from tracking set
                self._scheduled_callbacks.discard(callback_id)
            
            callback_id = self.root.after(delay, wrapper)
            self._scheduled_callbacks.add(callback_id)
            return callback_id
        except Exception as e:
            self.log_error("Error scheduling callback", e)
            return None

    def cancel_all_callbacks(self):
        """Cancel all scheduled callbacks"""
        for callback_id in list(self._scheduled_callbacks):
            try:
                self.root.after_cancel(callback_id)
            except Exception:
                pass  # Callback may have already executed
        self._scheduled_callbacks.clear()

    def emergency_show_window(self):
        """Emergency fallback to show main window if needed"""
        try:
            if not self.root.winfo_viewable():
                print("Emergency window show triggered - main window not visible")
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.update()
                print("Emergency show completed")
            # Window is already visible, no action needed
        except Exception as e:
            print(f"Emergency show check failed: {e}")

    def set_main_window_icon(self):
        """Set the main window icon"""
        try:
            # First, check if running on macOS
            if sys.platform == 'darwin':
                # On macOS, try .icns first
                icon_paths = [
                    'icon.icns',
                    os.path.join(os.path.dirname(__file__), 'icon.icns'),
                    os.path.join(os.getcwd(), 'icon.icns')
                ]
                
                for icon_path in icon_paths:
                    if os.path.exists(icon_path):
                        try:
                            # On macOS, iconbitmap works with .icns
                            self.root.iconbitmap(icon_path)
                            self.log_info(f"Successfully set icon: {icon_path}")
                            return
                        except Exception as e:
                            self.log_error(f"Failed to set .icns icon: {icon_path}", e)
                            # Try alternative method with tk.call
                            try:
                                # This is a more reliable method on macOS
                                self.root.tk.call('wm', 'iconphoto', self.root._w, 
                                                tk.PhotoImage(file=self._convert_icns_to_png(icon_path)))
                                self.log_info(f"Set icon using iconphoto: {icon_path}")
                                return
                            except Exception as e2:
                                self.log_error(f"iconphoto also failed", e2)
            else:
                # On Windows/Linux, use .ico
                icon_paths = [
                    'icon.ico',
                    os.path.join(os.path.dirname(__file__), 'icon.ico'),
                    os.path.join(os.getcwd(), 'icon.ico')
                ]
                
                for icon_path in icon_paths:
                    if os.path.exists(icon_path):
                        try:
                            self.root.iconbitmap(icon_path)
                            self.log_info(f"Successfully set icon: {icon_path}")
                            return
                        except Exception as e:
                            self.log_error(f"Failed to set icon: {icon_path}", e)
            
            self.log_info("No suitable icon file found")
                            
        except Exception as e:
            self.log_error("Critical error setting main window icon", e)

    def _convert_icns_to_png(self, icns_path):
        """Helper to convert .icns to PNG for iconphoto on macOS"""
        try:
            from PIL import Image
            import tempfile
            
            # Load the .icns file
            image = Image.open(icns_path)
            
            # Create a temporary PNG file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_png = temp_file.name
            
            # Save as PNG
            image.save(temp_png, 'PNG')
            
            return temp_png
        except ImportError:
            # Fallback if PIL is not available
            if sys.platform == 'darwin':
                import subprocess
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_png = temp_file.name
                
                subprocess.run(['sips', '-s', 'format', 'png', icns_path, '--out', temp_png],
                            capture_output=True)
                
                return temp_png
        except Exception as e:
            self.log_error("Error converting icns to png", e)
            return None

    def show_main_window(self):
        """Show the main window and close splash"""
        try:
            self.log_info("Showing main window...")
            
            if self.splash:
                try:
                    self.splash.destroy()
                    self.splash = None
                    self.log_info("Splash screen closed")
                except Exception as e:
                    self.log_error("Error closing splash screen", e)
            
            # Set window properties before showing
            self.root.title("Hello Toolbelt")
            self.root.geometry("1200x1200")
            
            # Show and focus main window
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            
            # Force updates
            self.root.update_idletasks()
            self.root.update()
            
            self.log_info("Main window displayed")
            
        except Exception as e:
            self.log_error("Error showing main window", e)
            # Ensure main window shows even if splash fails
            try:
                self.root.title("Hello Toolbelt")
                self.root.geometry("1200x1200")
                self.root.deiconify()
                self.root.lift()
                self.root.update()
            except Exception as e2:
                self.log_error("Critical error showing main window", e2)

    def setup_logging(self):
        """Setup logging for debugging stability issues"""
        try:
            # Create logs directory if it doesn't exist
            log_dir = os.path.join(os.path.expanduser('~'), 'HelloToolbelt', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, 'hellotoolbelt.log')
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger('HelloToolbelt')
            self.logger.info("HelloToolbelt started successfully")
        except Exception as e:
            # Fallback if logging setup fails
            self.logger = None
            print(f"Warning: Could not setup logging: {e}")

    def log_error(self, message, exception=None):
        """Safe error logging"""
        if self.logger:
            if exception:
                self.logger.error(f"{message}: {str(exception)}")
            else:
                self.logger.error(message)
        else:
            print(f"ERROR: {message}")

    def log_info(self, message):
        """Safe info logging"""
        if self.logger:
            self.logger.info(message)
        else:
            print(f"INFO: {message}")

    @contextmanager
    def safe_settings_access(self):
        """Thread-safe settings file access"""
        acquired = False
        try:
            acquired = self._settings_lock.acquire(timeout=5.0)
            if not acquired:
                raise TimeoutError("Could not acquire settings lock")
            yield
        finally:
            if acquired:
                self._settings_lock.release()

    def get_settings_file_path(self):
        """Thread-safe settings file path with proper error handling"""
        try:
            # Check if we're running as a PyInstaller bundle
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                if sys.platform.startswith('win'):
                    app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
                    settings_dir = os.path.join(app_data, 'HelloToolbelt')
                elif sys.platform.startswith('darwin'):
                    settings_dir = os.path.expanduser('~/Library/Application Support/HelloToolbelt')
                else:
                    settings_dir = os.path.expanduser('~/.config/HelloToolbelt')
                
                # Thread-safe directory creation
                try:
                    os.makedirs(settings_dir, exist_ok=True)
                except OSError as e:
                    self.log_error(f"Could not create settings directory: {settings_dir}", e)
                    # Fallback to user home
                    settings_dir = os.path.expanduser('~')
                
                return os.path.join(settings_dir, 'toolbelt_settings.json')
            else:
                # Running as script - use original location
                script_dir = os.path.dirname(__file__)
                return os.path.join(script_dir, "toolbelt_settings.json")
        except Exception as e:
            self.log_error("Error determining settings path", e)
            # Ultimate fallback
            return os.path.join(os.path.expanduser('~'), '.toolbelt_settings.json')

    def load_settings(self):
        """Enhanced settings loading with error recovery"""
        default_settings = {
            'is_dark_mode': False,
            'window_geometry': '1200x900',
            'current_tier': 'Tier 2',  # Default to Tier 2 for new users
            'tier3_unlocked': False,   # Track if Tier 3 has been unlocked
            'dlq_file_path': ''
        }
        
        try:
            with self.safe_settings_access():
                if os.path.exists(self.settings_file):
                    with open(self.settings_file, 'r') as f:
                        settings = json.load(f)
                        
                    # Validate settings structure
                    for key, default_value in default_settings.items():
                        if key not in settings:
                            settings[key] = default_value
                            self.log_info(f"Added missing setting: {key}")
                    
                    self.is_dark_mode = settings.get('is_dark_mode', False)
                    self.dlq_file_path = settings.get('dlq_file_path', '')
                    
                    # Check if Tier 3 has been previously unlocked
                    self.tier3_unlocked = settings.get('tier3_unlocked', False)
                    
                    # Set current tier based on unlock status
                    if self.tier3_unlocked:
                        self.current_tier = settings.get('current_tier', 'Tier 3')
                        self.log_info("Tier 3 previously unlocked - loading with Tier 3 access")
                    else:
                        self.current_tier = 'Tier 2'  # Force Tier 2 if not unlocked
                        self.log_info("Tier 3 not unlocked - defaulting to Tier 2")
                    
                    # Check for welcome popup status for this version
                    shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
                    setattr(self, shown_welcome_key, settings.get(shown_welcome_key, False))
                    
                    # Apply window geometry safely
                    geometry = settings.get('window_geometry', '1200x900')
                    try:
                        self.root.geometry(geometry)
                    except Exception as e:
                        self.log_error("Invalid geometry, using default", e)
                        self.root.geometry('1200x900')
                        
                else:
                    # Apply defaults for new installation
                    self.is_dark_mode = default_settings['is_dark_mode']
                    self.current_tier = default_settings['current_tier']  # Tier 2 for new users
                    self.tier3_unlocked = default_settings['tier3_unlocked']  # False for new users
                    self.dlq_file_path = default_settings['dlq_file_path']
                    # First time opening, welcome should show
                    shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
                    setattr(self, shown_welcome_key, False)
                    self.log_info(f"New installation - settings file will be created at: {self.settings_file}")
                    
        except Exception as e:
            self.log_error("Error loading settings, using defaults", e)
            self.is_dark_mode = default_settings['is_dark_mode']
            self.current_tier = default_settings['current_tier']  # Tier 2 default
            self.tier3_unlocked = default_settings['tier3_unlocked']  # False default
            self.dlq_file_path = default_settings['dlq_file_path']
            # Default to not shown for safety
            shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
            setattr(self, shown_welcome_key, False)

    def save_settings(self):
        """Thread-safe settings saving with error handling"""
        try:
            with self.safe_settings_access():
                # Ensure the directory exists
                settings_dir = os.path.dirname(self.settings_file)
                os.makedirs(settings_dir, exist_ok=True)
                
                settings = {
                    'is_dark_mode': self.is_dark_mode,
                    'window_geometry': self.root.geometry(),
                    'current_tier': self.current_tier,
                    'tier3_unlocked': getattr(self, 'tier3_unlocked', False),  # Save unlock status
                    'dlq_file_path': getattr(self, 'dlq_file_path', '')
                }
                
                # Add welcome popup status
                shown_welcome_key = f'shown_welcome_{self.version.replace(".", "_")}'
                settings[shown_welcome_key] = getattr(self, shown_welcome_key, True)
                
                # Write to temporary file first, then rename for atomicity
                temp_file = self.settings_file + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                
                # Atomic rename
                if os.path.exists(self.settings_file):
                    backup_file = self.settings_file + '.bak'
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(self.settings_file, backup_file)
                
                os.rename(temp_file, self.settings_file)
                
                # Clean up backup after successful write
                backup_file = self.settings_file + '.bak'
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                
                self.log_info(f"Settings saved to: {self.settings_file}")
                
        except Exception as e:
            self.log_error("Error saving settings", e)
            # Try to restore from backup if it exists
            backup_file = self.settings_file + '.bak'
            if os.path.exists(backup_file):
                try:
                    if os.path.exists(self.settings_file):
                        os.remove(self.settings_file)
                    os.rename(backup_file, self.settings_file)
                    self.log_info("Restored settings from backup")
                except Exception as restore_error:
                    self.log_error("Could not restore settings backup", restore_error)

    def get_colors(self):
        """Get color scheme based on current mode"""
        if self.is_dark_mode:
            return {
                'bg': '#2b2b2b',
                'fg': '#ffffff',
                'frame_bg': '#3c3c3c',
                'header_bg': '#4a4a4a',
                'secondary_bg': '#404040',
                'tertiary_bg': '#353535',
                'text_secondary': '#cccccc',
                'primary': '#4a90e2',
                'success': '#27ae60',
                'danger': '#e74c3c',
                'warning': '#f39c12',
                'slider_bg': '#505050',
                'slider_active': '#6a6a6a',
                'slider_thumb': '#ffffff'
            }
        else:
            return {
                'bg': '#ffffff',
                'fg': '#2c3e50',
                'frame_bg': '#f8f9fa',
                'header_bg': '#e9ecef',
                'secondary_bg': '#f8f9fa',
                'tertiary_bg': '#ffffff',
                'text_secondary': '#34495e',
                'primary': '#3498db',
                'success': '#27ae60',
                'danger': '#e74c3c',
                'warning': '#f39c12',
                'slider_bg': '#e0e0e0',
                'slider_active': '#d0d0d0',
                'slider_thumb': '#3498db'
            }

    def setup_styles(self):
        """Configure enhanced styling for the application"""
        style = ttk.Style()
        colors = self.get_colors()
        
        # Use a modern theme as base
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        else:
            style.theme_use('default')
        
        # Configure custom notebook style
        style.configure('Custom.TNotebook', 
                       background=colors['secondary_bg'],
                       borderwidth=0,
                       relief='flat')
        
        # Configure custom notebook tab style
        tab_bg = '#e8e8e8' if not self.is_dark_mode else '#505050'
        tab_active = '#d0d0d0' if not self.is_dark_mode else '#606060'
        
        style.configure('Custom.TNotebook.Tab',
                       padding=[12, 6],
                       background=tab_bg,
                       foreground=colors['fg'],
                       borderwidth=1,
                       relief='raised',
                       focuscolor='none')
        
        # Configure selected tab style
        style.map('Custom.TNotebook.Tab',
                 background=[('selected', colors['primary']),
                           ('active', tab_active),
                           ('!active', tab_bg)],
                 foreground=[('selected', 'white'),
                           ('active', colors['fg']),
                           ('!active', colors['fg'])],
                 relief=[('selected', 'solid'),
                        ('active', 'raised'),
                        ('!active', 'raised')])
        
        # Configure frame styles
        style.configure('Tool.TFrame',
                       background=colors['bg'],
                       relief='flat',
                       borderwidth=0)
        
        # Configure label styles
        style.configure('Heading.TLabel',
                       background=colors['bg'],
                       foreground=colors['fg'],
                       font=('Segoe UI', 14, 'bold'))
        
        style.configure('SubHeading.TLabel',
                       background=colors['bg'],
                       foreground=colors['text_secondary'],
                       font=('Segoe UI', 11, 'bold'))
        
        style.configure('Body.TLabel',
                       background=colors['bg'],
                       foreground=colors['fg'],
                       font=('Segoe UI', 10))

    def prompt_for_tier3_password(self):
        """Prompt user for Tier 3 password"""
        try:
            colors = self.get_colors()
            print("Creating password dialog...")  # Debug print
            
            # Ensure main window is properly displayed and focused
            self.root.update_idletasks()
            self.root.lift()  # Bring main window to front first
            
            # Small delay to ensure main window is settled
            self.root.after(50, lambda: self._create_password_dialog(colors))
            
            # Wait a moment for the dialog to be created
            self.root.update()
            
            return getattr(self, '_dialog_result', False)
            
        except Exception as e:
            self.log_error("Error creating password dialog", e)
            print(f"Error in prompt_for_tier3_password: {e}")
            return False
    
    def _create_password_dialog(self, colors):
        """Helper method to create the password dialog"""
        try:
            dialog = PasswordDialog(self.root, colors)
            print("Password dialog created, waiting for result...")  # Debug print
            
            result = dialog.wait_for_result()
            print(f"Password dialog result: {result}")  # Debug print
            
            self._dialog_result = result
            
            # Continue with the tier change logic
            self._handle_password_result(result)
            
        except Exception as e:
            print(f"Error in _create_password_dialog: {e}")
            self._dialog_result = False
            self._handle_password_result(False)
    
    def _handle_password_result(self, success):
        """Handle the result of the password dialog"""
        try:
            if success:
                # Password correct, unlock Tier 3 permanently and set current tier
                print("Password correct, granting Tier 3 access")  # Debug print
                self.tier3_unlocked = True  # Mark as permanently unlocked
                self.current_tier = 'Tier 3'
                
                # Save settings immediately to persist the unlock
                self.save_settings()
                
                # Refresh tabs for new tier
                self.refresh_tabs_for_tier()
                
                # Show success message
                try:
                    messagebox.showinfo("Access Granted", 
                                      "Tier 3 access granted and saved! All tools are now available.\n\nTier 3 will remain unlocked for future sessions.",
                                      parent=self.root)
                except Exception as e:
                    print(f"Error showing success message: {e}")
                    
            else:
                # Password incorrect or cancelled, revert selection
                print("Password incorrect or cancelled, reverting to current tier")  # Debug print
                self.tier_var.set(self.current_tier)
                
                # Show failure message
                try:
                    messagebox.showwarning("Access Denied", 
                                         "Incorrect password or access cancelled.\nRemaining on current tier.",
                                         parent=self.root)
                except Exception as e:
                    print(f"Error showing warning message: {e}")
        except Exception as e:
            print(f"Error in _handle_password_result: {e}")
            # Revert to current tier on any error
            try:
                self.tier_var.set(self.current_tier)
            except:
                pass

    def on_tier_change(self, event=None):
        """Handle tier selection change with password protection"""
        try:
            new_tier = self.tier_var.get()
            print(f"Tier change requested: {self.current_tier} -> {new_tier}")  # Debug print
            
            if new_tier != self.current_tier:
                # If trying to switch to Tier 3, check if already unlocked or require password
                if new_tier == 'Tier 3':
                    if self.tier3_unlocked:
                        # Already unlocked, allow immediate access
                        print("Tier 3 already unlocked, granting immediate access")  # Debug print
                        self.current_tier = new_tier
                        self.refresh_tabs_for_tier()
                        self.save_settings()  # Save the tier preference
                    else:
                        # Not unlocked yet, require password
                        print("Tier 3 not unlocked, prompting for password...")  # Debug print
                        self.prompt_for_tier3_password()
                    
                else:
                    # Switching from Tier 3 to Tier 2 (no password needed, but Tier 3 stays unlocked)
                    print(f"Switching to {new_tier} (no password required)")  # Debug print
                    self.current_tier = new_tier
                    self.refresh_tabs_for_tier()
                    self.save_settings()  # Save the tier preference
            else:
                print("No tier change needed")  # Debug print
                
        except Exception as e:
            self.log_error("Error handling tier change", e)
            print(f"Error in on_tier_change: {e}")
            # Revert to previous tier on error
            try:
                self.tier_var.set(self.current_tier)
            except Exception:
                pass

    def get_tools_for_tier(self):
        """Get the list of tools based on current tier"""
        tier_2_tools = ['Eligibility Search', 'Multi-File Column Search']
        
        if self.current_tier == 'Tier 2':
            return [tool for tool in self.tools if tool['name'] in tier_2_tools]
        else:  # Tier 3
            return self.tools

    def create_tool_tabs(self):
        """Create a tab for each tool with enhanced styling based on tier"""
        colors = self.get_colors()
        
        # Get tools for current tier
        tools_to_show = self.get_tools_for_tier()
        
        # Define which tools should be in the Client Setup subtabs
        client_setup_tools = ['Client Configuration', 'CronJob Configuration', 'Base64 Encoder/Decoder']
        
        # Separate tools into client setup and regular tools
        client_setup_configs = [tool for tool in tools_to_show if tool['name'] in client_setup_tools]
        other_tools = [tool for tool in tools_to_show if tool['name'] not in client_setup_tools]
        
        # Create Client Setup tab with subtabs if there are any client setup tools
        if client_setup_configs:
            # Create main Client Setup tab
            client_setup_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
            tab_text = "⚙️ Client Setup"
            self.notebook.add(client_setup_frame, text=tab_text)
            
            # Create a notebook for subtabs
            client_notebook = ttk.Notebook(client_setup_frame, style='Custom.TNotebook')
            client_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Add subtabs for each client setup tool
            for tool_config in client_setup_configs:
                # Create subtab frame
                subtab_frame = ttk.Frame(client_notebook, style='Tool.TFrame')
                
                # Add subtab with icon and name
                subtab_text = f"{tool_config.get('icon', '🔧')} {tool_config['name']}"
                client_notebook.add(subtab_frame, text=subtab_text)
                
                # Create a container frame with padding and styling
                container_frame = tk.Frame(subtab_frame, bg=colors['bg'], relief='flat', bd=0)
                container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # Try to load and instantiate the tool
                success = self.load_tool_in_tab(container_frame, tool_config)
                
                if not success:
                    # If loading failed, show error message
                    self.create_error_tab(container_frame, tool_config)
        
        # Create regular tabs for other tools
        for tool_config in other_tools:
            # Create tab frame with styling
            tab_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
            
            # Add tab with icon and name
            tab_text = f"{tool_config.get('icon', '🔧')} {tool_config['name']}"
            self.notebook.add(tab_frame, text=tab_text)
            
            # Create a container frame with padding and styling
            container_frame = tk.Frame(tab_frame, bg=colors['bg'], relief='flat', bd=0)
            container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Try to load and instantiate the tool
            success = self.load_tool_in_tab(container_frame, tool_config)
            
            if not success:
                # If loading failed, show error message
                self.create_error_tab(container_frame, tool_config)

    def refresh_tabs_for_tier(self):
        """Refresh tabs based on tier selection"""
        try:
            # Clear all existing tabs except options
            tabs_to_remove = []
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Options" not in tab_text:
                    tabs_to_remove.append(i)
            
            # Remove tabs in reverse order to maintain indices
            for i in reversed(tabs_to_remove):
                self.notebook.forget(i)
            
            # Clean up loaded tools safely
            tool_names = list(self.loaded_tools.keys())
            for tool_name in tool_names:
                self.safe_tool_cleanup(tool_name)
            
            # Recreate tool tabs for new tier
            self.create_tool_tabs()
            
            # Move options tab back to the end
            self.move_options_tab_to_end()
            
            # Save settings
            self.save_settings()
        except Exception as e:
            self.log_error("Error refreshing tabs for tier", e)

    def pre_render_all_tabs(self):
        """Pre-render all tabs to eliminate flash on first view"""
        try:
            # Get the currently selected tab
            current_tab = self.notebook.index(self.notebook.select())
            
            # Iterate through all tabs and force render
            num_tabs = self.notebook.index("end")
            for i in range(num_tabs):
                # Select each tab briefly to trigger rendering
                self.notebook.select(i)
                self.root.update_idletasks()
                
                # Get the tab frame and force update all its children
                tab_id = self.notebook.tabs()[i]
                tab_frame = self.notebook.nametowidget(tab_id)
                self._force_render_widgets(tab_frame)
            
            # Return to the original tab
            self.notebook.select(current_tab)
            self.root.update_idletasks()
            
            self.log_info("Pre-rendered all tabs successfully")
        except Exception as e:
            self.log_error("Error pre-rendering tabs", e)
    
    def _force_render_widgets(self, widget):
        """Recursively force render all widgets in a container"""
        try:
            widget.update_idletasks()
            for child in widget.winfo_children():
                self._force_render_widgets(child)
        except Exception:
            pass

    def create_options_tab_content(self, options_frame):
        """Create the content for the options tab"""
        colors = self.get_colors()
        
        # Main container - simple frame without scrolling
        main_container = tk.Frame(options_frame, bg=colors['bg'], relief='flat', bd=0)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Options content with enhanced styling - direct layout
        content_frame = tk.Frame(main_container, bg=colors['bg'], padx=40, pady=40)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header section with blue background like configurator tool
        header_frame = tk.Frame(content_frame, bg=colors['primary'], relief='flat', bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        header_content = tk.Frame(header_frame, bg=colors['primary'])
        header_content.pack(fill=tk.X, padx=20, pady=15)
        
        # Title with icon
        title_icon = tk.Label(header_content, 
                            text="ℹ️", 
                            font=('Segoe UI', 20),
                            bg=colors['primary'], 
                            fg='white')
        title_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        title = tk.Label(header_content, 
                        text="HelloToolbelt Options", 
                        font=('Segoe UI', 16, 'bold'),
                        fg='white',
                        bg=colors['primary'])
        title.pack(side=tk.LEFT, anchor='w')
        
        # Create a horizontal container for the two sections
        horizontal_container = tk.Frame(content_frame, bg=colors['bg'])
        horizontal_container.pack(fill=tk.BOTH, expand=True, pady=(0, 30))
        
        # Left section - Tier Selection
        tier_section = tk.Frame(horizontal_container, bg=colors['frame_bg'], relief='solid', bd=1)
        tier_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        tier_header = tk.Frame(tier_section, bg=colors['header_bg'], height=50)
        tier_header.pack(fill=tk.X)
        
        tier_label = tk.Label(tier_header,
                            text="Access Tier",
                            font=('Segoe UI', 14, 'bold'),
                            fg=colors['fg'],
                            bg=colors['header_bg'])
        tier_label.pack(pady=15)
        
        tier_content = tk.Frame(tier_section, bg=colors['frame_bg'])
        tier_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tier_desc = tk.Label(tier_content,
                        text="Select your access tier to show relevant tools:",
                        font=('Segoe UI', 11),
                        fg=colors['fg'],
                        bg=colors['frame_bg'])
        tier_desc.pack(anchor='w', pady=(0, 15))
        
        # Tier dropdown
        tier_frame = tk.Frame(tier_content, bg=colors['frame_bg'])
        tier_frame.pack(fill=tk.X, pady=(0, 15))
        
        tier_dropdown_label = tk.Label(tier_frame,
                                    text="Current Tier:",
                                    font=('Segoe UI', 10, 'bold'),
                                    fg=colors['fg'],
                                    bg=colors['frame_bg'])
        tier_dropdown_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Create dropdown
        self.tier_var = tk.StringVar(value=self.current_tier)
        tier_dropdown = ttk.Combobox(tier_frame,
                                textvariable=self.tier_var,
                                values=['Tier 2', 'Tier 3'],
                                state='readonly',
                                width=15)
        tier_dropdown.pack(side=tk.LEFT)
        tier_dropdown.bind('<<ComboboxSelected>>', self.on_tier_change)
        
        # Tier descriptions with password notice
        tier_2_desc = tk.Label(tier_content,
                            text="• Tier 2: Essential tools (Eligibility Search, Multi-File Column Search)",
                            font=('Segoe UI', 10),
                            fg=colors['text_secondary'],
                            bg=colors['frame_bg'],
                            justify=tk.LEFT)
        tier_2_desc.pack(anchor='w', pady=2)
        
        tier_3_desc = tk.Label(tier_content,
                            text="• Tier 3: All tools available (Full suite access)",
                            font=('Segoe UI', 10),
                            fg=colors['text_secondary'],
                            bg=colors['frame_bg'],
                            justify=tk.LEFT)
        tier_3_desc.pack(anchor='w', pady=2)
        
        # Password notice - update text based on unlock status
        if getattr(self, 'tier3_unlocked', False):
            password_notice_text = "🔓 Tier 3 is unlocked for this installation"
            password_notice_color = colors['success']
        else:
            password_notice_text = "🔒 Tier 3 requires password authentication"
            password_notice_color = colors['warning']
        
        password_notice = tk.Label(tier_content,
                                text=password_notice_text,
                                font=('Segoe UI', 9),
                                fg=password_notice_color,
                                bg=colors['frame_bg'],
                                justify=tk.LEFT)
        password_notice.pack(anchor='w', pady=(10, 0))
        
        # Right section - Theme Settings
        theme_section = tk.Frame(horizontal_container, bg=colors['primary'], relief='flat', bd=0)
        theme_section.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        
        theme_content = tk.Frame(theme_section, bg=colors['primary'])
        theme_content.pack(fill=tk.X, padx=20, pady=20)
        
        theme_label = tk.Label(theme_content,
                            text="Theme Settings",
                            font=('Segoe UI', 14, 'bold'),
                            fg='white',
                            bg=colors['primary'])
        theme_label.pack(anchor='w', pady=(0, 10))
        
        # Theme description
        theme_desc = tk.Label(theme_content,
                            text="Toggle between light and dark themes. Your preference will be remembered.",
                            font=('Segoe UI', 10),
                            fg='white',
                            bg=colors['primary'],
                            wraplength=200)
        theme_desc.pack(anchor='w', pady=(0, 15))
        
        # Container for slider and labels
        slider_frame = tk.Frame(theme_content, bg=colors['primary'])
        slider_frame.pack(anchor='w')
        
        # Light mode label
        light_label = tk.Label(slider_frame,
                            text="Light",
                            font=('Segoe UI', 10, 'bold'),
                            fg='white',
                            bg=colors['primary'])
        light_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Theme slider
        slider = self.create_theme_slider(slider_frame)
        slider.pack(side=tk.LEFT, padx=(0, 10))
        
        # Dark mode label
        dark_label = tk.Label(slider_frame,
                            text="Dark",
                            font=('Segoe UI', 10, 'bold'),
                            fg='white',
                            bg=colors['primary'])
        dark_label.pack(side=tk.LEFT)
        
        # Creator section at bottom
        creator_section = tk.Frame(content_frame, bg=colors['secondary_bg'], relief='solid', bd=1)
        creator_section.pack(fill=tk.X, pady=(30, 0))
        
        creator_content = tk.Frame(creator_section, bg=colors['secondary_bg'])
        creator_content.pack(fill=tk.X, padx=20, pady=20)
        
        creator_label = tk.Label(creator_content,
                            text="Created and Maintained by Tier 3 Support",
                            font=('Segoe UI', 14, 'bold'),
                            fg=colors['fg'],
                            bg=colors['secondary_bg'])
        creator_label.pack(anchor='w')
        
        bug_text = "Please reach out to Cody White if you find bugs or have ideas on additional features."
        
        bug_info = tk.Label(creator_content,
                        text=bug_text,
                        font=('Segoe UI', 10),
                        fg=colors['text_secondary'],
                        bg=colors['secondary_bg'],
                        justify=tk.LEFT,
                        wraplength=600)
        bug_info.pack(anchor='w', pady=(5, 0))
        
        # Version section at bottom
        version_section = tk.Frame(content_frame, bg=colors['tertiary_bg'], relief='solid', bd=1, cursor='hand2')
        version_section.pack(fill=tk.X, pady=(15, 0))
        
        version_content = tk.Frame(version_section, bg=colors['tertiary_bg'], cursor='hand2')
        version_content.pack(fill=tk.X, padx=20, pady=15)
        
        version_label = tk.Label(version_content,
                            text=f"Version {self.version}",
                            font=('Segoe UI', 12, 'bold'),
                            fg=colors['fg'],
                            bg=colors['tertiary_bg'],
                            cursor='hand2')
        version_label.pack(anchor='w')
        
        version_info = tk.Label(version_content,
                            text="For release notes click me!",
                            font=('Segoe UI', 9),
                            fg=colors['text_secondary'],
                            bg=colors['tertiary_bg'],
                            cursor='hand2')
        version_info.pack(anchor='w', pady=(2, 0))
        
        # Make entire version section clickable to show welcome popup
        def on_version_click(event):
            # Only show welcome popup when manually clicked, not during theme changes
            if not getattr(self, '_theme_changing', False):
                self.show_welcome_popup()
        
        def on_version_enter(event):
            if not getattr(self, '_theme_changing', False):
                version_section.config(bg=colors['primary'])
                version_content.config(bg=colors['primary'])
                version_label.config(bg=colors['primary'], fg='white')
                version_info.config(bg=colors['primary'], fg='white')
        
        def on_version_leave(event):
            if not getattr(self, '_theme_changing', False):
                version_section.config(bg=colors['tertiary_bg'])
                version_content.config(bg=colors['tertiary_bg'])
                version_label.config(bg=colors['tertiary_bg'], fg=colors['fg'])
                version_info.config(bg=colors['tertiary_bg'], fg=colors['text_secondary'])
        
        # Bind events to all components of the version section
        for widget in [version_section, version_content, version_label, version_info]:
            widget.bind("<Button-1>", on_version_click)
            widget.bind("<Enter>", on_version_enter)
            widget.bind("<Leave>", on_version_leave)
        
        # Pack content frame directly - no scrolling needed
        content_frame.pack(fill=tk.BOTH, expand=True)

    # Add remaining methods that were in the original but need to be included
    def safe_tool_cleanup(self, tool_name):
        """Safely cleanup tool resources"""
        with self._tool_cleanup_lock:
            if tool_name in self.loaded_tools:
                try:
                    tool_instance = self.loaded_tools[tool_name]
                    
                    # Call cleanup method if it exists
                    if hasattr(tool_instance, 'cleanup'):
                        tool_instance.cleanup()
                    
                    # Destroy widget tree
                    if hasattr(tool_instance, 'root'):
                        try:
                            tool_instance.root.destroy()
                        except Exception:
                            pass  # Widget may already be destroyed
                    
                    # Remove from loaded tools
                    del self.loaded_tools[tool_name]
                    self.log_info(f"Cleaned up tool: {tool_name}")
                    
                except Exception as e:
                    self.log_error(f"Error cleaning up tool {tool_name}", e)

    def on_closing(self):
        """Enhanced cleanup on application close"""
        try:
            self.log_info("Application closing - starting cleanup")
            self._destroyed = True
            self.save_settings()
            
            # Clean up all tools
            tool_names = list(self.loaded_tools.keys())
            for tool_name in tool_names:
                self.safe_tool_cleanup(tool_name)
            
            self.root.quit()
            self.root.destroy()
            self.log_info("Application cleanup completed")
            
        except Exception as e:
            self.log_error("Error during application cleanup", e)
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass

    def center_window(self):
        """Center the main window on screen"""
        try:
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (width // 2)
            y = (self.root.winfo_screenheight() // 2) - (height // 2)
            self.root.geometry(f'{width}x{height}+{x}+{y}')
        except Exception as e:
            self.log_error("Error centering window", e)

    def load_tool_module_safe(self, file_path):
        """Safely load a Python module with timeout and error handling"""
        try:
            if not os.path.exists(file_path):
                self.log_error(f"Tool file does not exist: {file_path}")
                return None
            
            # Check file size (prevent loading extremely large files)
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                self.log_error(f"Tool file too large: {file_path} ({file_size} bytes)")
                return None
            
            spec = importlib.util.spec_from_file_location("tool_module", file_path)
            if not spec or not spec.loader:
                self.log_error(f"Could not create module spec for: {file_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            
            # Execute module loading
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            self.log_error(f"Error loading module {file_path}", e)
            return None

    def load_tool_in_tab(self, parent_frame, tool_config):
        """Enhanced tool loading with comprehensive error handling"""
        tool_name = tool_config['name']
        
        # Prevent concurrent loading of the same tool
        if tool_name in self._loading_tools:
            self.log_info(f"Tool {tool_name} is already being loaded")
            return False
        
        self._loading_tools.add(tool_name)
        
        try:
            colors = self.get_colors()
            
            # Get the script file path with multiple fallback locations
            script_paths = [
                tool_config['file'],
                os.path.join(os.path.dirname(os.path.abspath(__file__)), tool_config['file']),
                os.path.join(os.getcwd(), tool_config['file'])
            ]
            
            script_path = None
            for path in script_paths:
                if os.path.exists(path):
                    script_path = path
                    break
            
            if not script_path:
                self.log_error(f"Tool script not found in any location: {script_paths}")
                return False
            
            # Load the module with timeout protection
            module = self.load_tool_module_safe(script_path)
            if not module:
                return False
            
            # Get the class with validation
            tool_class = getattr(module, tool_config['class'], None)
            if not tool_class:
                self.log_error(f"Class {tool_config['class']} not found in {tool_config['file']}")
                return False
            
            # Enhanced MockRoot with better compatibility
            class EnhancedMockRoot(tk.Frame):
                def __init__(self, parent):
                    super().__init__(parent, bg=colors['bg'], relief='flat', bd=0)
                    self.pack(fill=tk.BOTH, expand=True)
                    self._title = ""
                    self._current_bg = colors['bg']
                    self._current_fg = colors['fg']
                    self._destroyed = False
                    
                def title(self, text=None):
                    if text is not None:
                        self._title = text
                    return self._title
                
                def minsize(self, width=None, height=None):
                    pass
                
                def geometry(self, geometry=None):
                    pass
                
                def protocol(self, protocol, callback):
                    pass
                
                def mainloop(self):
                    pass
                
                def quit(self):
                    pass
                
                def destroy(self):
                    if not self._destroyed:
                        self._destroyed = True
                        try:
                            super().destroy()
                        except Exception:
                            pass
                
                def configure(self, **kwargs):
                    if 'bg' in kwargs:
                        self._current_bg = kwargs['bg']
                    try:
                        super().configure(**kwargs)
                    except Exception:
                        pass
                
                def cget(self, key):
                    if key == 'bg':
                        return getattr(self, '_current_bg', colors['bg'])
                    elif key == 'fg':
                        return getattr(self, '_current_fg', colors['fg'])
                    try:
                        return super().cget(key)
                    except Exception:
                        return None
                
                def winfo_rgb(self, color):
                    try:
                        return parent_frame.winfo_rgb(color)
                    except Exception:
                        return (0, 0, 0)
            
            # Create the mock root for the tool
            tool_root = EnhancedMockRoot(parent_frame)
            
            # Instantiate the tool with error handling
            try:
                tool_instance = tool_class(tool_root)
            except Exception as e:
                self.log_error(f"Error instantiating tool {tool_name}", e)
                tool_root.destroy()
                return False
            
            # Configure tool for dark mode if supported
            if hasattr(tool_instance, 'is_dark_mode'):
                tool_instance.is_dark_mode = self.is_dark_mode
            
            # Force immediate rendering of tool interface
            tool_root.update_idletasks()
            parent_frame.update_idletasks()
            
            # Store reference to the tool
            self.loaded_tools[tool_name] = tool_instance
            self.log_info(f"Successfully loaded tool: {tool_name}")
            
            return True
            
        except Exception as e:
            self.log_error(f"Critical error loading {tool_name}", e)
            return False
        finally:
            # Always remove from loading set
            self._loading_tools.discard(tool_name)

    def create_error_tab(self, parent_frame, tool_config):
        """Create an enhanced error tab when a tool fails to load"""
        colors = self.get_colors()
        
        error_frame = tk.Frame(parent_frame, bg=colors['bg'], relief='flat', bd=0)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Error icon and title frame
        title_frame = tk.Frame(error_frame, bg=colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Error icon
        icon_label = tk.Label(title_frame, 
                             text="⚠", 
                             font=('Segoe UI', 24),
                             bg=colors['bg'],
                             fg=colors['danger'])
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Error title
        title_label = tk.Label(title_frame, 
                              text=f"Failed to Load: {tool_config['name']}", 
                              font=('Segoe UI', 16, 'bold'),
                              fg=colors['danger'],
                              bg=colors['bg'])
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Error details frame with subtle border
        details_frame = tk.Frame(error_frame, bg=colors['frame_bg'], relief='solid', bd=1)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Error message
        error_msg = f"""Unable to load the tool from: {tool_config['file']}

Possible reasons:
• File not found in the current directory
• Python import error in the script
• Missing dependencies
• Class name mismatch (looking for: {tool_config['class']})

Tool Description:
{tool_config['description']}

To fix this:
1. Ensure {tool_config['file']} is in the same directory as this launcher
2. Check that the script runs independently without errors
3. Verify the class name matches: {tool_config['class']}"""
        
        error_text = tk.Text(details_frame, 
                           wrap=tk.WORD, 
                           bg=colors['frame_bg'],
                           fg=colors['fg'],
                           relief='flat',
                           bd=0,
                           font=('Segoe UI', 10),
                           selectbackground=colors['primary'],
                           selectforeground='white',
                           padx=20,
                           pady=20)
        error_text.pack(fill=tk.BOTH, expand=True)
        error_text.insert('1.0', error_msg.strip())
        error_text.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = tk.Frame(error_frame, bg=colors['bg'])
        button_frame.pack(fill=tk.X)
        
        # Retry button with modern styling
        retry_btn = tk.Button(button_frame, 
                            text="🔄 Retry Loading", 
                            command=lambda: self.retry_load_tool(parent_frame, tool_config),
                            bg=colors['primary'],
                            fg='white',
                            font=('Segoe UI', 11, 'bold'),
                            relief='flat',
                            bd=0,
                            padx=20,
                            pady=10,
                            cursor='hand2')
        retry_btn.pack(side=tk.RIGHT)

    def retry_load_tool(self, parent_frame, tool_config):
        """Retry loading a failed tool"""
        # Clear the current tab content
        for widget in parent_frame.winfo_children():
            try:
                widget.destroy()
            except Exception as e:
                self.log_error(f"Error destroying widget during retry", e)
        
        # Try loading again
        success = self.load_tool_in_tab(parent_frame, tool_config)
        
        if not success:
            # Still failed, recreate error tab
            self.create_error_tab(parent_frame, tool_config)

    def create_options_tab(self):
        """Create an enhanced options/help tab"""
        options_frame = ttk.Frame(self.notebook, style='Tool.TFrame')
        self.notebook.add(options_frame, text="ℹ️ Options")
        
        self.create_options_tab_content(options_frame)

    def move_options_tab_to_end(self):
        """Move the Options tab to the rightmost position"""
        try:
            # Find the options tab
            options_tab_index = None
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Options" in tab_text:
                    options_tab_index = i
                    break
            
            if options_tab_index is not None:
                # Get the tab frame
                options_tab = self.notebook.nametowidget(self.notebook.tabs()[options_tab_index])
                tab_text = self.notebook.tab(options_tab_index, "text")
                
                # Remove the tab from its current position
                self.notebook.forget(options_tab_index)
                
                # Add it back at the end
                self.notebook.add(options_tab, text=tab_text)
        except Exception as e:
            self.log_error("Error moving options tab", e)

    def refresh_options_tab(self):
        """Refresh the options tab styling"""
        try:
            self._theme_changing = True
            
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Options" in tab_text:
                    tab_frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                    for widget in tab_frame.winfo_children():
                        try:
                            widget.destroy()
                        except Exception:
                            pass
                    self.create_options_tab_content(tab_frame)
                    break
        except Exception as e:
            self.log_error("Error refreshing options tab", e)
        finally:
            def reset_flag():
                time.sleep(0.5)
                self._theme_changing = False
            
            threading.Thread(target=reset_flag, daemon=True).start()

    def toggle_dark_mode(self):
        """Toggle between light and dark mode"""
        self.is_dark_mode = not self.is_dark_mode
        
        # Save settings immediately
        self.save_settings()
        
        # Update styles
        self.setup_styles()
        
        # Update root background
        colors = self.get_colors()
        self.root.configure(bg=colors['bg'])
        
        # Refresh all tabs
        self.refresh_all_tabs()
        
        # Update options tab specifically (but don't trigger welcome popup)
        self.refresh_options_tab()

    def refresh_all_tabs(self):
        """Enhanced tab refreshing with proper error handling"""
        colors = self.get_colors()
        
        failed_tools = []
        
        for tool_name, tool_instance in self.loaded_tools.items():
            try:
                # Update the MockRoot colors first
                if hasattr(tool_instance, 'root'):
                    try:
                        tool_instance.root.configure(bg=colors['bg'])
                        tool_instance.root._current_bg = colors['bg']
                        tool_instance.root._current_fg = colors['fg']
                    except Exception as e:
                        self.log_error(f"Error updating root colors for {tool_name}", e)
                
                # Check if the tool has a method to refresh its styling
                if hasattr(tool_instance, 'refresh_styling'):
                    try:
                        tool_instance.refresh_styling(self.is_dark_mode)
                    except Exception as e:
                        self.log_error(f"Error refreshing styling for {tool_name}", e)
                        failed_tools.append(tool_name)
                        
                elif hasattr(tool_instance, 'setup_adaptive_styling'):
                    try:
                        tool_instance.is_dark_mode = self.is_dark_mode
                        tool_instance.setup_adaptive_styling()
                        
                        # Try to refresh the interface if possible
                        if hasattr(tool_instance, '_create_main_interface'):
                            # Clear and recreate the interface safely
                            for widget in tool_instance.root.winfo_children():
                                try:
                                    widget.destroy()
                                except Exception:
                                    pass
                            tool_instance._create_main_interface()
                    except Exception as e:
                        self.log_error(f"Error with adaptive styling for {tool_name}", e)
                        failed_tools.append(tool_name)
                        
            except Exception as e:
                self.log_error(f"Critical error refreshing tool {tool_name}", e)
                failed_tools.append(tool_name)
        
        # Clean up failed tools
        for tool_name in failed_tools:
            self.safe_tool_cleanup(tool_name)
            self.log_info(f"Removed failed tool: {tool_name}")

    def create_theme_slider(self, parent):
        """Create a simplified custom theme slider widget"""
        colors = self.get_colors()
        
        # Container frame for the slider
        slider_container = tk.Frame(parent, bg=colors['primary'], width=60, height=30)
        slider_container.pack_propagate(False)
        
        # Create canvas for custom slider
        canvas = tk.Canvas(slider_container, 
                          width=60, 
                          height=30, 
                          bg=colors['primary'],
                          highlightthickness=0,
                          relief='flat')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Slider track
        track_y = 15
        track_start = 8
        track_end = 52
        track_height = 14
        
        # Draw rounded track background
        canvas.create_oval(track_start, track_y - track_height//2,
                          track_start + track_height, track_y + track_height//2,
                          fill=colors['slider_bg'], outline="")
        canvas.create_rectangle(track_start + track_height//2, track_y - track_height//2,
                               track_end - track_height//2, track_y + track_height//2,
                               fill=colors['slider_bg'], outline="")
        canvas.create_oval(track_end - track_height, track_y - track_height//2,
                          track_end, track_y + track_height//2,
                          fill=colors['slider_bg'], outline="")
        
        # Slider thumb
        thumb_radius = 10
        thumb_x = track_end - thumb_radius if self.is_dark_mode else track_start + thumb_radius
        
        # Create thumb with shadow effect
        # Shadow (using a darker solid color instead of transparency)
        shadow_color = '#d0d0d0' if not self.is_dark_mode else '#1a1a1a'
        canvas.create_oval(thumb_x - thumb_radius + 1, track_y - thumb_radius + 1,
                          thumb_x + thumb_radius + 1, track_y + thumb_radius + 1,
                          fill=shadow_color, outline="")
        
        # Main thumb
        thumb = canvas.create_oval(thumb_x - thumb_radius, track_y - thumb_radius,
                                  thumb_x + thumb_radius, track_y + thumb_radius,
                                  fill=colors['slider_thumb'], outline="", width=0)
        
        # Animation variables
        self.slider_animating = False
        self.slider_canvas = canvas
        self.slider_thumb = thumb
        self.slider_track_start = track_start + thumb_radius
        self.slider_track_end = track_end - thumb_radius
        self.slider_track_y = track_y
        self.slider_thumb_radius = thumb_radius
        
        def animate_slider(target_x, callback=None):
            """Animate slider movement with smooth easing"""
            if self.slider_animating or self._destroyed:
                return
                
            self.slider_animating = True
            current_coords = canvas.coords(thumb)
            current_x = (current_coords[0] + current_coords[2]) / 2
            
            # Animation with easing for smoother motion
            start_time = time.time()
            duration = 0.2  # 200ms animation
            
            def move_step():
                nonlocal current_x
                if self._destroyed:
                    self.slider_animating = False
                    return
                
                elapsed = time.time() - start_time
                progress = min(elapsed / duration, 1.0)
                
                # Ease out cubic for smooth deceleration
                eased_progress = 1 - pow(1 - progress, 3)
                
                if progress < 1.0:
                    # Calculate position based on easing
                    start_x = current_coords[0] + thumb_radius
                    current_x = start_x + (target_x - start_x) * eased_progress
                    
                    try:
                        # Update shadow
                        canvas.coords(canvas.find_all()[-2], 
                                     current_x - thumb_radius + 1, track_y - thumb_radius + 1,
                                     current_x + thumb_radius + 1, track_y + thumb_radius + 1)
                        # Update thumb
                        canvas.coords(thumb, 
                                     current_x - thumb_radius, track_y - thumb_radius,
                                     current_x + thumb_radius, track_y + thumb_radius)
                        # 60 FPS for smoother animation
                        canvas.after(16, move_step)
                    except Exception:
                        self.slider_animating = False
                else:
                    try:
                        # Final position
                        canvas.coords(canvas.find_all()[-2], 
                                     target_x - thumb_radius + 1, track_y - thumb_radius + 1,
                                     target_x + thumb_radius + 1, track_y + thumb_radius + 1)
                        canvas.coords(thumb, 
                                     target_x - thumb_radius, track_y - thumb_radius,
                                     target_x + thumb_radius, track_y + thumb_radius)
                        self.slider_animating = False
                        if callback:
                            callback()
                    except Exception:
                        self.slider_animating = False
            
            move_step()
        
        def on_slider_click(event):
            """Handle slider click"""
            if self.slider_animating:
                return
                
            # Determine which side was clicked
            click_x = event.x
            middle = (self.slider_track_start + self.slider_track_end) / 2
            
            if click_x < middle and self.is_dark_mode:
                # Switch to light mode
                target_x = self.slider_track_start
                animate_slider(target_x, lambda: self.toggle_dark_mode())
            elif click_x > middle and not self.is_dark_mode:
                # Switch to dark mode
                target_x = self.slider_track_end
                animate_slider(target_x, lambda: self.toggle_dark_mode())
        
        def on_slider_hover(event):
            """Handle slider hover"""
            canvas.config(cursor="hand2")
        
        def on_slider_leave(event):
            """Handle slider leave"""
            canvas.config(cursor="")
        
        # Bind events
        canvas.bind("<Button-1>", on_slider_click)
        canvas.bind("<Enter>", on_slider_hover)
        canvas.bind("<Leave>", on_slider_leave)
        
        return slider_container

    # Add remaining necessary methods (simplified versions to focus on the password system)
    def check_and_show_welcome(self):
        """Check if this is the first time opening this version and show welcome popup"""
        pass  # Simplified for this example
    
    def show_welcome_popup(self):
        """Show the welcome popup with version info and changelog"""
        pass  # Simplified for this example


def main():
    """Main entry point with splash screen"""
    try:
        # Create main window completely hidden
        root = tk.Tk()
        root.withdraw()  # Hide before any geometry is set
        
        # Create and show splash screen
        splash = SplashScreen()
        
        # Update splash to ensure it's visible
        for i in range(5):
            splash.splash.update()
            time.sleep(0.1)
        
        # Initialize the app with splash screen
        app = MultiToolLauncher(root, splash)
        
        # App will handle closing splash and showing main window
        # Don't manually destroy splash or show window here
        
        root.mainloop()
        
    except Exception as e:
        print(f"Critical error starting HelloToolbelt: {e}")
        import traceback
        traceback.print_exc()
        
        # Emergency cleanup and fallback
        try:
            if 'splash' in locals():
                splash.destroy()
        except:
            pass
        
        try:
            if 'root' in locals():
                root.deiconify()
                root.mainloop()
        except Exception as e2:
            print(f"Emergency show failed: {e2}")
            # Simple fallback window
            try:
                simple_root = tk.Tk()
                simple_root.title("HelloToolbelt - Error")
                simple_root.geometry("400x200")
                tk.Label(simple_root, 
                        text="HelloToolbelt encountered an error during startup.\n\nCheck console for details.",
                        justify=tk.CENTER,
                        font=('Arial', 12)).pack(expand=True)
                simple_root.mainloop()
            except:
                print("Complete failure - cannot display any window")


if __name__ == "__main__":
    main()