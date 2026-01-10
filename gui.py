import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import threading
import logging
import time
import pyautogui
import pygetwindow as gw
import json
import os
from config import TARGET_WINDOW_TITLE, SHORTCUT_SEQUENCE, ALWAYS_ON_TOP
import config
import main
from utils.logger import logger

class TextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget"""
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        # Schedule the update in the main GUI thread
        self.text_widget.after(0, append)

class AutoClickerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoClicker Controller")
        self.root.geometry("600x950")

        # --- Controls Area ---
        control_frame = tk.Frame(root)
        control_frame.pack(fill='x', padx=10, pady=10)

        # Output Window Target
        tk.Label(control_frame, text="Target Project Name (Window Title):").pack(anchor='w')
        self.project_name_var = tk.StringVar(value="Manager")
        self.entered_project_name = tk.Entry(control_frame, textvariable=self.project_name_var, width=50)
        self.entered_project_name.pack(fill='x', pady=(0, 10))

        # Prompt Input
        tk.Label(control_frame, text="Workflow Prompt:").pack(anchor='w')
        self.prompt_text = tk.Text(control_frame, height=5, width=50)
        self.prompt_text.pack(fill='x', pady=(0, 10))

        # Suffix Input
        tk.Label(control_frame, text="Suffix Command:").pack(anchor='w')
        self.suffix_var = tk.StringVar(value="Proceed")
        self.suffix_entry = tk.Entry(control_frame, textvariable=self.suffix_var, width=50)
        self.suffix_entry.pack(fill='x', pady=(0, 10))

        # Workflow Button
        self.workflow_btn = tk.Button(control_frame, text="Run Workflow\n(Focus -> Type Prompt -> Suffix -> Send)", 
                                      command=self.start_workflow_thread, bg="#ddddff")
        self.workflow_btn.pack(fill='x', pady=5)

        # Always on Top
        self.always_on_top_var = tk.BooleanVar(value=ALWAYS_ON_TOP)
        self.always_on_top_chk = tk.Checkbutton(control_frame, text="Always on Top", 
                                                variable=self.always_on_top_var, 
                                                command=self.toggle_always_on_top)
        self.always_on_top_chk.pack(anchor='w')
        
        # Apply initial state
        self.toggle_always_on_top()

        # Separator
        tk.Frame(control_frame, height=2, bd=1, relief="sunken").pack(fill='x', pady=10)

        # AutoClicker Controls
        self.toggle_btn = tk.Button(control_frame, text="Start AutoClicker Loops", 
                                    command=self.toggle_autoclicker, bg="#ddffdd", height=2)
        self.toggle_btn.pack(fill='x', pady=5)

        # --- Quick Prompts ---
        tk.Frame(control_frame, height=2, bd=1, relief="sunken").pack(fill='x', pady=10)
        tk.Label(control_frame, text="Quick Prompts:").pack(anchor='w')
        
        self.quick_prompts = self.load_quick_prompts()
        self.prompt_buttons = []
        
        qp_frame = tk.Frame(control_frame)
        qp_frame.pack(fill='x', pady=5)
        
        for i in range(7):
            row = tk.Frame(qp_frame)
            row.pack(fill='x', pady=2)
            
            p_data = self.quick_prompts[i]
            
            btn = tk.Button(row, text=f"Send {p_data['label']}", 
                           command=lambda idx=i: self.send_quick_prompt(idx),
                           bg="#e6f2ff", width=40, anchor='w')
            btn.pack(side='left', fill='x', expand=True)
            self.prompt_buttons.append(btn)
            
            edit_btn = tk.Button(row, text="Edit", width=6,
                                command=lambda idx=i: self.edit_prompt(idx))
            edit_btn.pack(side='right', padx=(5,0))

        # --- Logs Area ---
        log_frame = tk.Frame(root)
        log_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        tk.Label(log_frame, text="Execution Logs:").pack(anchor='w')
        
        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=15)
        self.log_area.pack(fill='both', expand=True)

        # Setup Logging
        text_handler = TextHandler(self.log_area)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        text_handler.setFormatter(formatter)
        logger.addHandler(text_handler)

        # State
        self.autoclicker_thread = None

    def load_quick_prompts(self):
        default_prompts = [{"label": f"Prompt {i+1}", "prompt": ""} for i in range(7)]
        if not os.path.exists('quick_prompts.json'):
            return default_prompts
        try:
            with open('quick_prompts.json', 'r') as f:
                data = json.load(f)
                # Ensure we have at least 7
                if len(data) < 7:
                    data.extend([{"label": f"Prompt {i+1}", "prompt": ""} for i in range(len(data), 7)])
                return data[:7]
        except Exception as e:
            logger.error(f"Failed to load quick prompts: {e}")
            return default_prompts

    def save_quick_prompts(self):
        try:
            with open('quick_prompts.json', 'w') as f:
                json.dump(self.quick_prompts, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save quick prompts: {e}")

    def edit_prompt(self, index):
        current = self.quick_prompts[index]
        new_label = simpledialog.askstring("Edit Prompt Label", f"Enter label for button {index+1}:", initialvalue=current['label'], parent=self.root)
        if new_label is None: return
        
        new_prompt = simpledialog.askstring("Edit Prompt Text", "Enter the workflow prompt:", initialvalue=current['prompt'], parent=self.root)
        if new_prompt is None: return
        
        self.quick_prompts[index] = {"label": new_label, "prompt": new_prompt}
        self.save_quick_prompts()
        
        # Update Button Text
        self.prompt_buttons[index].config(text=f"Send {new_label}")

    def send_quick_prompt(self, index):
        prompt_text = self.quick_prompts[index]['prompt']
        if not prompt_text:
            messagebox.showwarning("Empty Prompt", "This quick prompt is empty. Click Edit to set a prompt.")
            return
        
        # Start workflow with override
        threading.Thread(target=self.run_workflow, args=(prompt_text,), daemon=True).start()

    def start_workflow_thread(self):
        threading.Thread(target=self.run_workflow, daemon=True).start()

    def run_workflow(self, override_prompt=None):
        target = self.project_name_var.get()
        if override_prompt is not None:
            # Replace newlines in quick prompts to send as one line
            prompt = override_prompt.replace("\n", " ").replace("\r", " ").strip()
        else:
            # Replace newlines in textbox prompt to send as one line
            prompt = self.prompt_text.get("1.0", tk.END).replace("\n", " ").replace("\r", " ").strip()
        suffix = self.suffix_var.get().strip()

        if not target:
            logger.error("No Target Project Name specified!")
            return

        logger.info(f"Looking for window: {target}")
        
        try:
            windows = gw.getWindowsWithTitle(target)
            if not windows:
                logger.error(f"Could not find window containing '{target}'")
                # Log all available titles to help the user debug
                all_titles = gw.getAllTitles()
                logger.info(f"Available Windows: {all_titles}")
                return
            
            # Find the best match (sometimes getWindowsWithTitle returns partial matches)
            # We'll just take the first one but log what we found
            win = windows[0]
            logger.info(f"Focusing window: '{win.title}'")
            
            # Minimize and Maximize to force focus sometimes helps on Windows
            if not win.isActive:
                try:
                    win.activate()
                except Exception:
                    win.minimize()
                    win.restore()
            
            time.sleep(1.0) # Wait for focus

            # Combine prompt and suffix into one continuous string
            full_text = ""
            if prompt:
                full_text = prompt
            
            if suffix:
                if full_text:
                    full_text += " " + suffix
                else:
                    full_text = suffix
            
            if full_text:
                logger.info(f"Typing complete prompt: {full_text[:50]}...")
                # Type the entire combined text as one prompt
                pyautogui.write(full_text, interval=0.01)
                time.sleep(0.5)
                logger.info("Sending...")
                pyautogui.press('enter')
            else:
                logger.warning("No prompt or suffix to send!")
            
            logger.info("Workflow Complete.")

        except Exception as e:
            logger.error(f"Workflow failed: {e}")

    def toggle_always_on_top(self):
        is_top = self.always_on_top_var.get()
        self.root.attributes('-topmost', is_top)
        logger.info(f"Always on Top set to: {is_top}")

    def toggle_autoclicker(self):
        if self.autoclicker_thread and self.autoclicker_thread.is_alive():
            # Stop it
            logger.info("Stopping AutoClicker...")
            main.stop_event.set()
            self.toggle_btn.config(text="Stopping...", state='disabled')
            
            # Start polling for stop
            self.check_stop_complete()
            
        else:
            # Start it
            logger.info("Starting AutoClicker...")
            main.stop_event.clear()
            
            # Update config with current target if changed (though main reads config global)
            config.TARGET_WINDOW_TITLE = self.project_name_var.get()
            
            self.autoclicker_thread = threading.Thread(target=main.main, daemon=True)
            self.autoclicker_thread.start()
            self.reset_btn_state(stopped=False)

    def check_stop_complete(self):
        if self.autoclicker_thread.is_alive():
            # Check again in 100ms
            self.root.after(100, self.check_stop_complete)
        else:
            self.reset_btn_state(stopped=True)

    def reset_btn_state(self, stopped):
        if stopped:
            self.toggle_btn.config(text="Start AutoClicker Loops", bg="#ddffdd", state='normal')
        else:
            self.toggle_btn.config(text="Stop AutoClicker Loops", bg="#ffdddd", state='normal')

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AutoClickerGUI(root)
        root.mainloop()
    except Exception as e:
        # Fallback logging if GUI fails
        print(f"Failed to start GUI: {e}")
        import traceback
        traceback.print_exc()
