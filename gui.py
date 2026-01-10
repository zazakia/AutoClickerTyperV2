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
from core.config_manager import config_manager
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

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AutoClicker Pro")
        self.geometry("900x700")

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="AutoClicker", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.start_btn = ctk.CTkButton(self.sidebar_frame, text="Start Loops", command=self.toggle_autoclicker, fg_color="green")
        self.start_btn.grid(row=1, column=0, padx=20, pady=10)
        
        self.always_on_top_switch = ctk.CTkSwitch(self.sidebar_frame, text="Always on Top", command=self.toggle_always_on_top)
        self.always_on_top_switch.grid(row=2, column=0, padx=20, pady=10)
        if config_manager.get("ALWAYS_ON_TOP"):
            self.always_on_top_switch.select()
        self.toggle_always_on_top()

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, px=20, pady=0, sticky="nsew")
        self.tabview.add("Dashboard")
        self.tabview.add("Settings")
        
        self.setup_dashboard()
        self.setup_settings()

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
        
        ctk.CTkLabel(wf_frame, text="Target Window:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, px=10, py=5, sticky="w")
        self.target_entry = ctk.CTkEntry(wf_frame)
        self.target_entry.grid(row=0, column=1, px=10, py=5, sticky="ew")
        self.target_entry.insert(0, config_manager.get("TARGET_WINDOW_TITLE", "Manager"))
        self.target_entry.bind("<FocusOut>", self.save_target_window)
        
        ctk.CTkLabel(wf_frame, text="Prompt:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, px=10, py=5, sticky="nw")
        self.prompt_text = ctk.CTkTextbox(wf_frame, height=80)
        self.prompt_text.grid(row=1, column=1, px=10, py=5, sticky="ew")
        
        ctk.CTkLabel(wf_frame, text="Suffix:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, px=10, py=5, sticky="w")
        self.suffix_entry = ctk.CTkEntry(wf_frame)
        self.suffix_entry.grid(row=2, column=1, px=10, py=5, sticky="ew")
        self.suffix_entry.insert(0, "Proceed")
        
        self.run_wf_btn = ctk.CTkButton(wf_frame, text="Run Workflow (Focus -> Type -> Send)", command=self.start_workflow_thread)
        self.run_wf_btn.grid(row=3, column=1, px=10, py=10, sticky="ew")
        
        # --- Quick Prompts ---
        qp_frame = ctk.CTkFrame(dash)
        qp_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(qp_frame, text="Quick Prompts", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.quick_prompts = self.load_quick_prompts()
        self.qp_buttons = []
        
        grid_f = ctk.CTkFrame(qp_frame, fg_color="transparent")
        grid_f.pack(fill="x", padx=5)
        
        for i in range(7):
            f = ctk.CTkFrame(grid_f, fg_color="transparent")
            f.pack(fill="x", pady=2)
            
            p_label = self.quick_prompts[i]['label']
            btn = ctk.CTkButton(f, text=f"Send {p_label}", command=lambda idx=i: self.send_quick_prompt(idx))
            btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self.qp_buttons.append(btn)
            
            edit_btn = ctk.CTkButton(f, text="Edit", width=60, command=lambda idx=i: self.edit_prompt(idx), fg_color="gray")
            edit_btn.pack(side="right")

        # --- Logs ---
        log_frame = ctk.CTkFrame(dash)
        log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        dash.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(log_frame, text="Execution Logs").pack(anchor="w", px=5)
        self.log_area = ctk.CTkTextbox(log_frame, state="disabled")
        self.log_area.pack(fill="both", expand=True, px=5, py=5)
        
        # Logging Handler
        handler = TextHandler(self.log_area)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    def setup_settings(self):
        sett = self.tabview.tab("Settings")
        sett.grid_columnconfigure(0, weight=1)
        
        # OCR Confidence
        c_frame = ctk.CTkFrame(sett)
        c_frame.pack(fill="x", px=10, py=5)
        ctk.CTkLabel(c_frame, text="OCR Confidence Threshold").pack(side="left", px=10)
        self.conf_slider = ctk.CTkSlider(c_frame, from_=0, to=100, command=self.update_conf)
        self.conf_slider.set(config_manager.get("OCR_CONFIDENCE_THRESHOLD"))
        self.conf_slider.pack(side="right", px=10, fill="x", expand=True)
        
        # Scan Interval
        s_frame = ctk.CTkFrame(sett)
        s_frame.pack(fill="x", px=10, py=5)
        ctk.CTkLabel(s_frame, text="Scan Interval (s)").pack(side="left", px=10)
        self.scan_slider = ctk.CTkSlider(s_frame, from_=0.1, to=5.0, command=self.update_scan)
        self.scan_slider.set(config_manager.get("SCAN_INTERVAL"))
        self.scan_slider.pack(side="right", px=10, fill="x", expand=True)
        
        # Keywords
        k_frame = ctk.CTkFrame(sett)
        k_frame.pack(fill="both", px=10, py=5, expand=True)
        ctk.CTkLabel(k_frame, text="Click Keywords (comma separated)").pack(anchor="w", px=10)
        self.click_kw_entry = ctk.CTkEntry(k_frame)
        self.click_kw_entry.pack(fill="x", px=10, py=5)
        self.click_kw_entry.insert(0, ", ".join(config_manager.get("CLICK_KEYWORDS")))
        
        ctk.CTkButton(k_frame, text="Save Keywords", command=self.save_keywords).pack(pady=10)

    def update_conf(self, val):
        config_manager.set("OCR_CONFIDENCE_THRESHOLD", int(val))

    def update_scan(self, val):
        config_manager.set("SCAN_INTERVAL", float(val))

    def save_keywords(self):
        text = self.click_kw_entry.get()
        kws = [k.strip() for k in text.split(",") if k.strip()]
        config_manager.set("CLICK_KEYWORDS", kws)
        logger.info("Keywords saved successfully.")

    def save_target_window(self, event=None):
        val = self.target_entry.get()
        config_manager.set("TARGET_WINDOW_TITLE", val)
        logger.info(f"Target window updated to: {val}")

    def toggle_always_on_top(self):
        val = self.always_on_top_switch.get()
        self.attributes('-topmost', val)
        config_manager.set("ALWAYS_ON_TOP", bool(val))

    def toggle_autoclicker(self):
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

    def load_quick_prompts(self):
        default = [{"label": f"Prompt {i+1}", "prompt": ""} for i in range(7)]
        if not os.path.exists('quick_prompts.json'): return default
        try:
            with open('quick_prompts.json', 'r') as f:
                data = json.load(f)
                if len(data) < 7: data += default[len(data):]
                return data[:7]
        except: return default

    def save_quick_prompts(self):
        with open('quick_prompts.json', 'w') as f:
            json.dump(self.quick_prompts, f, indent=4)

    def edit_prompt(self, index):
        dialog = ctk.CTkInputDialog(text="Enter new label:", title="Edit Label")
        new_label = dialog.get_input()
        if not new_label: return
        
        dialog2 = ctk.CTkInputDialog(text="Enter new prompt content:", title="Edit Content")
        new_prompt = dialog2.get_input()
        if new_prompt is None: return
        
        self.quick_prompts[index] = {"label": new_label, "prompt": new_prompt}
        self.save_quick_prompts()
        self.qp_buttons[index].configure(text=f"Send {new_label}")

    def send_quick_prompt(self, index):
        prompt = self.quick_prompts[index]['prompt']
        if not prompt:
            logger.warning("Empty prompt!")
            return
        threading.Thread(target=self.run_workflow, args=(prompt,), daemon=True).start()

    def start_workflow_thread(self):
        prompt = self.prompt_text.get("1.0", "end-1c")
        threading.Thread(target=self.run_workflow, args=(prompt,), daemon=True).start()

    def run_workflow(self, prompt_text):
        target = self.target_entry.get()
        suffix = self.suffix_entry.get()
        
        if not target:
            logger.error("No target window set.")
            return

        logger.info(f"Targeting '{target}'...")
        try:
            wins = gw.getWindowsWithTitle(target)
            if not wins:
                logger.error("Window not found.")
                return
            win = wins[0]
            if not win.isActive:
                try: win.activate()
                except: win.minimize(); win.restore()
            time.sleep(1)
            
            # Click Plus
            matches = scan_for_keywords(["+"], [])
            if matches:
                box = matches[0]['box']
                x, y, w, h = box
                pyautogui.click(x + w//2, y + h//2)
                time.sleep(0.5)
            
            # Type
            full = prompt_text.replace("\n", " ").strip()
            if suffix: full += " " + suffix
            
            if full:
                logger.info(f"Typing: {full[:30]}...")
                pyautogui.write(full, interval=0.01)
                time.sleep(0.5)
                pyautogui.press('enter')
                logger.info("Sent.")
            else:
                logger.warning("Nothing to send.")
                
        except Exception as e:
            logger.error(f"Workflow Error: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
