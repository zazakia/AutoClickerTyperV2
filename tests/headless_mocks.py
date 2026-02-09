from unittest.mock import MagicMock

class MockCTk:
    def __init__(self, *args, **kwargs):
        pass
    def title(self, t): pass
    def geometry(self, g): pass
    def grid_columnconfigure(self, *args, **kwargs): pass
    def grid_rowconfigure(self, *args, **kwargs): pass
    def withdraw(self): pass
    def destroy(self): pass
    def mainloop(self): pass
    def attributes(self, *args, **kwargs): pass
    def after(self, ms, func):
        # For testing, we might want to call it immediately or ignore
        pass
    
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def bind(self, seq, func): pass

class MockCTkFrame:
    def __init__(self, master, *args, **kwargs):
        self.master = master
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def grid_columnconfigure(self, *args, **kwargs): pass
    def grid_rowconfigure(self, *args, **kwargs): pass
    def bind(self, seq, func): pass
    def winfo_children(self): return []

class MockCTkLabel:
    def __init__(self, master, text="", font=None, **kwargs):
        self.text = text
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def configure(self, *args, **kwargs): pass
    def bind(self, seq, func): pass

class MockCTkButton:
    def __init__(self, master, text="", command=None, **kwargs):
        self.text = text
        self.command = command
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def configure(self, *args, **kwargs): pass

class MockCTkSwitch:
    def __init__(self, master, text="", command=None, **kwargs):
        self.text = text
        self.command = command
        self._val = 0
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def select(self): self._val = 1
    def deselect(self): self._val = 0
    def get(self): return self._val
    def configure(self, *args, **kwargs): pass

class MockCTkTabview:
    def __init__(self, master, **kwargs):
        self.tabs = {}
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def add(self, name):
        self.tabs[name] = MockCTkFrame(self)
        return self.tabs[name]
    def tab(self, name):
        return self.tabs.get(name)

class MockCTkEntry:
    def __init__(self, master, **kwargs):
        self._text = ""
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def insert(self, idx, text):
        self._text = text # Simplified
    def delete(self, start, end):
        self._text = ""
    def get(self):
        return self._text
    def bind(self, seq, func): pass

class MockCTkTextbox:
    def __init__(self, master, **kwargs):
        self._text = ""
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def get(self, start, end):
        return self._text
    def insert(self, idx, text):
        self._text += text
    def configure(self, *args, **kwargs): pass
    def see(self, idx): pass
    def delete(self, start, end): self._text = ""
    def after(self, ms, func):
        # Execute immediately for testing purposes
        func()

class MockCTkSlider:
    def __init__(self, master, command=None, **kwargs):
        self.command = command
        self._val = 0
    def pack(self, *args, **kwargs): pass
    def set(self, val): self._val = val
    def get(self): return self._val

class MockCTkInputDialog:
    def __init__(self, text="", title=""):
        pass
    def get_input(self):
        return "Mock Input"

def mock_font(**kwargs):
    return "MockFont"
