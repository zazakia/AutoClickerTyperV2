import tkinter as tk
import sys

def check_content(text_widget, root):
    content = text_widget.get("1.0", tk.END)
    # print(f"Current content: {repr(content)}")
    if "MAKE UI FOR THIS" in content and "Test Prompt" in content:
        print("VERIFICATION_SUCCESS")
        sys.stdout.flush()
        root.destroy()
    else:
        # Keep checking
        root.after(500, lambda: check_content(text_widget, root))

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Target Window")
    root.geometry("400x300")
    
    lbl = tk.Label(root, text="I am the Target Window")
    lbl.pack()
    
    text = tk.Text(root)
    text.pack()
    text.focus_set()
    
    # Auto-close after 15 seconds if failed
    root.after(15000, root.destroy)
    
    # Start checking
    root.after(1000, lambda: check_content(text, root))
    
    root.mainloop()
