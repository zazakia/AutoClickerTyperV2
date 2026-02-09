import customtkinter as ctk
import tkinter as tk
import threading
import logging
import time
import pyautogui
import pygetwindow as gw
import json
import os
import main
from core.config_manager import config_manager, get_resource_path
from utils.logger import logger
from core.ocr import scan_for_keywords

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TextHandler(logging.Handler):
    """Allows logging to a CustomTkinter Text widget"""
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)
        self.text_widget.after(0, append)

class InputDialog(ctk.CTkToplevel):
    def __init__(self, title="Input", text="Type:", default_value=""):
        super().__init__()
        self.title(title)
        self.lift()  # lift window on top
        self.attributes("-topmost", True)  # stay on top
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(10, self._create_widgets, text, default_value)  # create widgets with slight delay to avoid white flash
        self.resizable(False, False)
        self.grab_set()  # make other windows incorrectable

        self._user_input = None

    def _create_widgets(self, text, default_value):
        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        self._label = ctk.CTkLabel(master=self,
                                   width=300,
                                   wraplength=300,
                                   fg_color="transparent",
                                   text=text)
        self._label.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        self._entry = ctk.CTkEntry(master=self,
                                   width=230)
        self._entry.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self._entry.insert(0, default_value) # Insert default value

        self._ok_button = ctk.CTkButton(master=self,
                                        width=100,
                                        border_width=0,
                                        fg_color=None,
                                        text='Ok',
                                        command=self._ok_event)
        self._ok_button.grid(row=2, column=0, padx=20, pady=(0, 20))

        self._entry.bind("<Return>", self._ok_event)
        self.after(100, lambda: self._entry.focus())  # set focus to entry

    def _ok_event(self, event=None):
        self._user_input = self._entry.get()
        self.grab_release()
        self.destroy()

    def _on_closing(self):
        self.grab_release()
        self.destroy()

    def get_input(self):
        self.master.wait_window(self)
        return self._user_input

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(config_manager.get("APP_TITLE", "Zapweb.app Prompt Assist and AutoClicker"))
        self.geometry("900x700")

        # Variables for Docking
        self.is_docked = False
        self.restore_geometry = "900x700"
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.dock_width = 320
        self.dock_hidden_width = 15 
        self.autohide_loop_running = False
        self.just_docked = False # Flag to prevent immediate hide
        self.dock_is_expanded = False # Track dock state explicitly
        self.autohide_job = None

        # Grid Layout for Root
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Main View Container ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # --- Dock View Container ---
        self.dock_container = ctk.CTkFrame(self, fg_color="transparent")
        # Hidden by default

        # Bind double click to background (approximate by binding to root and containers)
        self.bind("<Double-Button-1>", self.on_double_click_background)
        self.main_container.bind("<Double-Button-1>", self.on_double_click_background)

        # Sidebar (Inside Main Container)
        self.sidebar_frame = ctk.CTkFrame(self.main_container, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.sidebar_frame.bind("<Double-Button-1>", self.on_double_click_background)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Zapweb.app", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.start_btn = ctk.CTkButton(self.sidebar_frame, text="Start Loops", command=self.toggle_autoclicker, fg_color="green")
        self.start_btn.grid(row=1, column=0, padx=20, pady=10)
        
        self.always_on_top_switch = ctk.CTkSwitch(self.sidebar_frame, text="Always on Top", command=self.toggle_always_on_top)
        self.always_on_top_switch.grid(row=2, column=0, padx=20, pady=10)
        if config_manager.get("ALWAYS_ON_TOP"):
            self.always_on_top_switch.select()
        self.toggle_always_on_top()

        self.add_prompt_btn = ctk.CTkButton(self.sidebar_frame, text="+ Add Quick Prompt", command=self.add_new_prompt)
        self.add_prompt_btn.grid(row=3, column=0, padx=20, pady=10)

        self.dock_mode_btn = ctk.CTkButton(self.sidebar_frame, text="Dock to Side", command=self.toggle_dock_mode, fg_color="gray")
        self.dock_mode_btn.grid(row=4, column=0, padx=20, pady=10)

        # Sidebar Quick Prompts List
        self.sidebar_qp_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="Quick Prompts", height=300)
        self.sidebar_qp_frame.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")

        # Tabs (Inside Main Container)
        self.tabview = ctk.CTkTabview(self.main_container)
        self.tabview.grid(row=0, column=1, padx=20, pady=0, sticky="nsew")
        self.tabview.add("Dashboard")
        self.tabview.add("Settings")
        
        # Load Quick Prompts Data once
        self.quick_prompts = self.load_quick_prompts()
        
        self.setup_dashboard()
        self.setup_settings()
        self.setup_dock_view()
        
        # Initial Render
        self.refresh_all_qp_views()

        # State
        self.autoclicker_thread = None
        self.running = False

    def setup_dashboard(self):
        dash = self.tabview.tab("Dashboard")
        dash.grid_columnconfigure(0, weight=1)
        
        # --- Workflow Section ---
        wf_frame = ctk.CTkFrame(dash)
        wf_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        wf_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(wf_frame, text="Target Window:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.target_entry = ctk.CTkEntry(wf_frame)
        self.target_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.target_entry.insert(0, config_manager.get("TARGET_WINDOW_TITLE", "Manager"))
        self.target_entry.bind("<FocusOut>", self.save_target_window)
        
        ctk.CTkLabel(wf_frame, text="Prompt:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        self.prompt_text = ctk.CTkTextbox(wf_frame, height=80)
        self.prompt_text.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(wf_frame, text="Suffix:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.suffix_entry = ctk.CTkEntry(wf_frame)
        self.suffix_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.suffix_entry.insert(0, config_manager.get("DEFAULT_SUFFIX", "Proceed"))
        
        self.run_wf_btn = ctk.CTkButton(wf_frame, text="Run Workflow (Focus -> Type -> Send)", command=self.start_workflow_thread)
        self.run_wf_btn.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        # --- Quick Prompts (Using Scrollable Frame) ---
        qp_frame = ctk.CTkScrollableFrame(dash, label_text="Quick Prompts", height=200)
        qp_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Use Helper to render buttons
        self.render_quick_prompts(qp_frame, is_docked=False)

        # --- Logs ---
        log_frame = ctk.CTkFrame(dash)
        log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        dash.grid_rowconfigure(2, weight=1)
        
        # Log Header
        log_head = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_head.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(log_head, text="Execution Logs").pack(side="left")
        ctk.CTkButton(log_head, text="Clear Logs", width=80, height=24, command=self.clear_logs, fg_color="gray").pack(side="right")
        self.log_area = ctk.CTkTextbox(log_frame, state="disabled")
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Logging Handler
        handler = TextHandler(self.log_area)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    def setup_settings(self):
        sett = self.tabview.tab("Settings")
        sett.grid_columnconfigure(0, weight=1)
        
        # OCR Confidence
        c_frame = ctk.CTkFrame(sett)
        c_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(c_frame, text="OCR Confidence Threshold").pack(side="left", padx=10)
        self.conf_slider = ctk.CTkSlider(c_frame, from_=0, to=100, command=self.update_conf)
        self.conf_slider.set(config_manager.get("OCR_CONFIDENCE_THRESHOLD"))
        self.conf_slider.pack(side="right", padx=10, fill="x", expand=True)
        
        # Scan Interval
        s_frame = ctk.CTkFrame(sett)
        s_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(s_frame, text="Scan Interval (s)").pack(side="left", padx=10)
        self.scan_slider = ctk.CTkSlider(s_frame, from_=0.1, to=5.0, command=self.update_scan)
        self.scan_slider.set(config_manager.get("SCAN_INTERVAL"))
        self.scan_slider.pack(side="right", padx=10, fill="x", expand=True)
        
        # Keywords
        k_frame = ctk.CTkFrame(sett)
        k_frame.pack(fill="both", padx=10, pady=5, expand=True)
        ctk.CTkLabel(k_frame, text="Click Keywords (comma separated)").pack(anchor="w", padx=10)
        self.click_kw_entry = ctk.CTkEntry(k_frame)
        self.click_kw_entry.pack(fill="x", padx=10, pady=5)
        self.click_kw_entry.insert(0, ", ".join(config_manager.get("CLICK_KEYWORDS")))
        
        ctk.CTkButton(k_frame, text="Save Keywords", command=self.save_keywords).pack(pady=10)
        
        # Test Tools
        t_frame = ctk.CTkFrame(sett)
        t_frame.pack(fill="x", padx=10, pady=20)
        ctk.CTkLabel(t_frame, text="Diagnostics").pack(anchor="w", padx=10, pady=5)
        ctk.CTkButton(t_frame, text="Run One-Time OCR Test", command=self.test_ocr).pack(fill="x", padx=10, pady=10)

    def update_conf(self, val):
        config_manager.set("OCR_CONFIDENCE_THRESHOLD", int(val))

    def update_scan(self, val):
        config_manager.set("SCAN_INTERVAL", float(val))

    def save_keywords(self):
        try:
            text = self.click_kw_entry.get()
            kws = [k.strip() for k in text.split(",") if k.strip()]
            config_manager.set("CLICK_KEYWORDS", kws)
            logger.info("Keywords saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save keywords: {e}")

    def save_target_window(self, event=None):
        try:
            val = self.target_entry.get()
            config_manager.set("TARGET_WINDOW_TITLE", val)
            logger.info(f"Target window updated to: {val}")
        except Exception as e:
            logger.error(f"Failed to update target window: {e}")

    def toggle_always_on_top(self):
        try:
            val = self.always_on_top_switch.get()
            self.attributes('-topmost', val)
            config_manager.set("ALWAYS_ON_TOP", bool(val))
        except Exception as e:
            logger.error(f"Failed to toggle Always on Top: {e}")

    def toggle_autoclicker(self):
        try:
            if self.running:
                logger.info("Stopping AutoClicker...")
                main.stop_event.set()
                self.running = False
                self.start_btn.configure(text="Start Loops", fg_color="green")
            else:
                logger.info("Starting AutoClicker...")
                main.stop_event.clear()
                self.autoclicker_thread = threading.Thread(target=main.main, daemon=True)
                self.autoclicker_thread.start()
                self.running = True
                self.start_btn.configure(text="Stop Loops", fg_color="red")
        except Exception as e:
            logger.error(f"Failed to toggle AutoClicker: {e}")

    def load_quick_prompts(self):
        default = [{"label": f"Prompt {i+1}", "prompt": ""} for i in range(15)]
        try:
            path = os.path.join(config_manager.base_path, 'quick_prompts.json')
            if not os.path.exists(path):
                # Try to load from bundled resources
                bundled_path = get_resource_path('quick_prompts.json')
                if os.path.exists(bundled_path):
                    with open(bundled_path, 'r') as f:
                        data = json.load(f)
                        if len(data) < 15: data += default[len(data):]
                        self.quick_prompts = data[:15]
                        self.save_quick_prompts() # Persist to external file
                        logger.info(f"Loaded bundled quick prompts from {bundled_path}")
                        return self.quick_prompts
                return default
            
            with open(path, 'r') as f:
                data = json.load(f)
                if len(data) < 15: data += default[len(data):]
                return data[:15]
        except Exception as e:
             logger.error(f"Failed to load quick prompts: {e}")
             return default

    def save_quick_prompts(self):
        try:
            path = os.path.join(config_manager.base_path, 'quick_prompts.json')
            with open(path, 'w') as f:
                json.dump(self.quick_prompts, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save quick prompts: {e}")

    def edit_prompt(self, index):
        try:
            current_label = self.quick_prompts[index].get("label", "")
            dialog = InputDialog(text="Enter new label:", title="Edit Label", default_value=current_label)
            new_label = dialog.get_input()
            if not new_label: return
            
            current_prompt = self.quick_prompts[index].get("prompt", "")
            dialog2 = InputDialog(text="Enter new prompt content:", title="Edit Content", default_value=current_prompt)
            new_prompt = dialog2.get_input()
            if new_prompt is None: return
            
            self.quick_prompts[index] = {"label": new_label, "prompt": new_prompt}
            self.save_quick_prompts()
            self.refresh_all_qp_views()
        except Exception as e:
            logger.error(f"Failed to edit prompt: {e}", exc_info=True)

    def add_new_prompt(self):
        try:
            new_index = len(self.quick_prompts)
            self.quick_prompts.append({"label": f"New Prompt {new_index+1}", "prompt": ""})
            self.edit_prompt(new_index)
            self.refresh_all_qp_views()
        except Exception as e:
            logger.error(f"Failed to add new prompt: {e}")

    def refresh_all_qp_views(self):
        try:
            # Sidebar
            self.render_quick_prompts(self.sidebar_qp_frame, is_docked=True)
            # Dashboard
            for widget in self.tabview.tab("Dashboard").winfo_children():
                if isinstance(widget, ctk.CTkScrollableFrame) and getattr(widget, "_label", None) and widget._label.cget("text") == "Quick Prompts":
                    self.render_quick_prompts(widget, is_docked=False)
            # Dock
            if hasattr(self, 'dock_inner_frame'):
                self.render_quick_prompts(self.dock_inner_frame, is_docked=True)
        except Exception as e:
            logger.error(f"Failed to refresh QP views: {e}")

    def send_quick_prompt(self, index):
        try:
            logger.info(f"Quick prompt button {index+1} clicked")
            prompt = self.quick_prompts[index]['prompt']
            if not prompt:
                logger.warning("Empty prompt!")
                return
            logger.info(f"Sending quick prompt: {prompt[:50]}...")
            threading.Thread(target=self.run_workflow, args=(prompt,), daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to send quick prompt: {e}")

    def start_workflow_thread(self):
        logger.info("=== Run Workflow button clicked ===")
        try:
            prompt = self.prompt_text.get("1.0", "end-1c")
            if not prompt.strip():
                logger.warning("No prompt text entered. Please enter some text to send.")
                return
            logger.info(f"Starting workflow with prompt: {prompt[:50]}...")
            threading.Thread(target=self.run_workflow, args=(prompt,), daemon=True).start()
        except Exception as e:
            logger.error(f"Error starting workflow: {e}", exc_info=True)

    def run_workflow(self, prompt_text):
        logger.info("=== Starting Workflow Execution ===")
        target = self.target_entry.get()
        suffix = self.suffix_entry.get()
        
        if not target:
            logger.error("No target window set. Please enter a window title.")
            return

        logger.info(f"Targeting window: '{target}'")
        try:
            all_matches = gw.getWindowsWithTitle(target)
            app_title = config_manager.get("APP_TITLE")
            wins = [w for w in all_matches if w.title != app_title]
            
            if not wins:

                logger.error(f"Window '{target}' not found. Available windows:")
                all_wins = gw.getAllTitles()
                for w in all_wins[:10]:  # Show first 10 windows
                    if w.strip():
                        logger.info(f"  - {w}")
                return
            
            win = wins[0]
            logger.info(f"Found window: {win.title}")
            
            if not win.isActive:
                logger.info("Activating window...")
                try: 
                    win.activate()
                except: 
                    logger.info("Trying minimize/restore...")
                    win.minimize()
                    win.restore()
            time.sleep(1)
            
            # Click Plus
            logger.info("Scanning for '+' button...")
            matches = scan_for_keywords(["+"], [])
            if matches:
                box = matches[0]['box']
                x, y, w, h = box
                logger.info(f"Found '+' at ({x}, {y}), clicking...")
                pyautogui.click(x + w//2, y + h//2)
                time.sleep(0.5)
            else:
                logger.warning("'+' button not found, skipping click step")
            
            # Type
            full = prompt_text.replace("\n", " ").strip()
            if suffix: 
                full += " " + suffix
                logger.info(f"Added suffix: {suffix}")
            
            if full:
                # Safety: Move mouse to center of window to avoid fail-safe if near corner
                cx, cy = win.left + win.width//2, win.top + win.height//2
                pyautogui.moveTo(cx, cy, duration=0.1)
                
                logger.info(f"Typing text ({len(full)} chars): {full[:50]}...")
                pyautogui.write(full, interval=0.01)
                time.sleep(0.5)
                logger.info("Pressing Enter...")
                pyautogui.press('enter')
                logger.info("✓ Workflow completed successfully!")
            else:
                logger.warning("Nothing to send - prompt is empty.")
                
        except Exception as e:
            logger.error(f"Workflow Error: {e}", exc_info=True)
        finally:
            logger.info("=== Workflow Execution Finished ===")

    # --- Docking & Picking Toolbar Logic ---
    
    def on_double_click_background(self, event):
        # Only toggle if double-click is not on a specific interactive widget
        # (Tkinter events bubble up, but we can check target if needed. 
        # For now, binding to background frames is usually sufficient.)
        logger.info("Double-click backdrop detected. Toggling dock...")
        self.toggle_dock_mode()

    def setup_dock_view(self):
        # Create a vertical toolbar look
        self.dock_container.grid_columnconfigure(0, weight=1)
        self.dock_container.grid_rowconfigure(1, weight=1)

        # Header / Drag handle
        hdr = ctk.CTkLabel(self.dock_container, text=":: Zapweb ::", font=("Arial", 12), cursor="hand2")
        hdr.grid(row=0, column=0, pady=5, sticky="ew")
        hdr.bind("<Double-Button-1>", lambda e: self.toggle_dock_mode())

        # Scrollable area for buttons
        self.dock_inner_frame = ctk.CTkScrollableFrame(self.dock_container)
        self.dock_inner_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        
        self.render_quick_prompts(self.dock_inner_frame, is_docked=True)
        
        # Tools at bottom
        tools = ctk.CTkFrame(self.dock_container)
        tools.grid(row=2, column=0, sticky="ew", padx=2, pady=5)
        
        ctk.CTkButton(tools, text="Undock", command=self.toggle_dock_mode, height=25).pack(pady=2, fill="x")

    def render_quick_prompts(self, parent_frame, is_docked=False):
        # Clear existing
        for w in parent_frame.winfo_children():
            w.destroy()
            
        for i, item in enumerate(self.quick_prompts):
            lbl = item['label']
            if not lbl.strip(): lbl = f"Prompt {i+1}"
            
            # Row container
            row = ctk.CTkFrame(parent_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            if is_docked:
                # Compact view
                btn = ctk.CTkButton(row, text=lbl, command=lambda idx=i: self.send_quick_prompt(idx), height=35)
                btn.pack(fill="x")
            else:
                # Dashboard view with Edit
                btn = ctk.CTkButton(row, text=lbl, command=lambda idx=i: self.send_quick_prompt(idx))
                btn.pack(side="left", fill="x", expand=True, padx=(0,5))
                
                edit = ctk.CTkButton(row, text="Edit", width=50, command=lambda idx=i: self.edit_prompt(idx), fg_color="gray")
                edit.pack(side="right")

    def toggle_dock_mode(self):
        if not self.is_docked:
            # Enter Dock Mode
            logger.info("Entering Dock Mode...")
            self.restore_geometry = self.geometry()
            self.is_docked = True
            self.dock_is_expanded = True
            self.just_docked = True # Set flag to prevent immediate hide
            
            # Use withdraw/deiconify for cleaner transition with overrideredirect
            self.withdraw()
            
            self.main_container.grid_forget()
            self.dock_container.grid(row=0, column=0, sticky="nsew")
            
            # Refresh screen dimensions in case of changes
            self.screen_width = self.winfo_screenwidth()
            self.screen_height = self.winfo_screenheight()
            
            # Resize and Move
            x_pos = self.screen_width - self.dock_width
            self.geometry(f"{self.dock_width}x{self.screen_height}+{x_pos}+0")
            self.attributes('-topmost', True)
            self.overrideredirect(True) # Remove title bar for cleaner look
            
            self.deiconify()
            self.start_autohide_loop()
            
            # Clear "just docked" flag after 2 seconds or if mouse enters
            self.after(2000, self._clear_just_docked)
        else:
            # Exit Dock Mode
            logger.info("Exiting Dock Mode...")
            self.is_docked = False
            self.stop_autohide_loop()
            
            self.withdraw()
            
            self.dock_container.grid_forget()
            self.main_container.grid(row=0, column=0, sticky="nsew")
            
            self.overrideredirect(False)
            self.geometry(self.restore_geometry)
            
            self.deiconify()
            # Restore previous always on top preference
            self.toggle_always_on_top() 

    def _clear_just_docked(self):
        self.just_docked = False
        logger.debug("Dock: just_docked flag cleared")

    def start_autohide_loop(self):
        self.autohide_loop_running = True
        if self.autohide_job:
            self.after_cancel(self.autohide_job)
        self.check_autohide()

    def stop_autohide_loop(self):
        self.autohide_loop_running = False
        if self.autohide_job:
            self.after_cancel(self.autohide_job)
            self.autohide_job = None

    def expand_dock(self):
        if not self.dock_is_expanded:
            logger.info("Auto-hide: Expanding dock")
            self.geometry(f"{self.dock_width}x{self.screen_height}+{self.screen_width - self.dock_width}+0")
            self.attributes('-alpha', 1.0)
            self.dock_is_expanded = True

    def collapse_dock(self):
        if self.dock_is_expanded:
            logger.info("Auto-hide: Collapsing dock")
            self.geometry(f"{self.dock_hidden_width}x{self.screen_height}+{self.screen_width - self.dock_hidden_width}+0")
            self.attributes('-alpha', 0.05) # Slightly visible strip
            self.dock_is_expanded = False

    def check_autohide(self):
        if not self.autohide_loop_running: return
        
        try:
            # Use pyautogui for better global coordinates across multiple monitors
            import pyautogui
            mx, my = pyautogui.position()
            
            # Use self.screen_width (refreshed when docked)
            dock_x_start = self.screen_width - self.dock_width
            
            # Logic: If mouse is inside the zone where the dock would be, 
            # we definitely don't want it to collapse.
            if mx >= dock_x_start and mx <= self.screen_width:
                self.just_docked = False

            if not self.just_docked:
                # thresholds for showing (mouse at very edge)
                # and hiding (mouse moved significantly away)
                show_threshold = self.screen_width - 5
                
                # We hide if mouse is far to the left OR if it's moved to another monitor on the right
                # (mx > self.screen_width + 10)
                hide_threshold_left = dock_x_start - 60
                
                if not self.dock_is_expanded:
                    # When collapsed, show if mouse is at the right edge
                    if mx >= show_threshold and mx <= self.screen_width + 20: 
                        self.expand_dock()
                else:
                    # When expanded, hide if mouse is far left or moved off-screen to the right
                    if mx < hide_threshold_left or mx > self.screen_width + 50:
                        self.collapse_dock()
            
        except Exception as e:
            logger.error(f"Error in autohide loop: {e}")
            
        self.autohide_job = self.after(150, self.check_autohide)

    def clear_logs(self):
        self.log_area.configure(state='normal')
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state='disabled')
        logger.info("Logs cleared.")

    def test_ocr(self):
        def _run_test():
            logger.info("=== Starting OCR Diagnostics ===")
            try:
                # Force a scan
                matches = scan_for_keywords(config_manager.get("CLICK_KEYWORDS", []), config_manager.get("TYPE_KEYWORDS", []))
                logger.info(f"Scan finished. Found {len(matches)} candidate(s).")
                for i, m in enumerate(matches):
                    logger.info(f" {i+1}. Found '{m['keyword']}' (type={m['type']})")
                    logger.info(f"    Text: '{m['found_text']}' | Conf: {m['conf']}")
                    logger.info(f"    Box: {m['box']}")
                if not matches:
                    logger.info("No keywords matched current screen content.")
            except Exception as e:
                logger.error(f"OCR Test Failed: {e}", exc_info=True)
            logger.info("=== End OCR Diagnostics ===")
        
        threading.Thread(target=_run_test, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
