import tkinter as tk
import random
import threading
import time

class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker Test Harness")
        self.root.geometry("600x400")
        self.root.attributes("-topmost", True)  # Keep on top for OCR

        self.label = tk.Label(root, text="Test Environment", font=("Arial", 16))
        self.label.pack(pady=10)

        self.frame = tk.Frame(root)
        self.frame.pack(expand=True, fill='both')

        # Keywords from config
        self.click_keywords = ["Accept", "Run", "Allow", "Proceed", "Confirm", "Continue", "Expand"]
        self.type_keywords = ["Type Here"] # Modified for visual clarity vs typing content

        self.widgets = []
        
        self.spawn_widgets()

    def spawn_widgets(self):
        # Spawn buttons with keywords
        for kw in self.click_keywords:
            self.create_button(kw)
        
        # Spawn entry for typing
        # Note: The prompt says "Keywords to TYPE" means "If keyword appears... TYPE".
        # Prompt 4.2 lists "accept", "run" as keywords to TYPE.
        # It says: "If keyword appears inside or near an input field -> TYPE".
        # This implies if we see text "accept" near an input, we type "accept".
        # For this test, let's just make a label "Type 'run' below" and an input field.
        
        input_frame = tk.Frame(self.frame)
        input_frame.pack(pady=20)
        lbl = tk.Label(input_frame, text="allow", font=("Arial", 12)) # Trigger keyword
        lbl.pack(side=tk.LEFT, padx=5)
        entry = tk.Entry(input_frame)
        entry.pack(side=tk.LEFT)
        # We can't easily auto-verify typing in this simple harness without complex binding,
        # but the auto-clicker will try to type "allow" into it.

    def create_button(self, text):
        btn = tk.Button(self.frame, text=text, font=("Arial", 12),
                        bg="#0000FF", fg="white",
                        command=lambda t=text: self.on_click(t))
        # Place randomly
        x = random.randint(50, 400)
        y = random.randint(50, 250)
        btn.place(x=x, y=y)
        self.widgets.append(btn)

    def on_click(self, text):
        print(f"Clicked: {text}")
        # Find the widget and remove it to simulate success
        for w in self.frame.winfo_children():
            if isinstance(w, tk.Button) and w['text'] == text:
                w.destroy()
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()
