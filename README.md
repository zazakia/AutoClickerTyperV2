# Autonomous Auto Clicker & Typing Tool

## Overview
This tool is an autonomous agent designed to visually scan your screen, detect specific keywords using OCR, and perform actions (Click or Type) to automate workflows like software installation, bulk acceptance of dialogs, or routine form entry.

## Requirements
- Windows 10/11
- Python 3.10+
- Tesseract OCR (Must be installed at `C:\Program Files\Tesseract-OCR\tesseract.exe` or in your PATH)

---

## 📥 Installation (End Users)

### Option 1: Download Installer (Recommended)
1. Download the latest `AutoClickerTyper_Setup_v*.exe` from [Releases](https://github.com/yourusername/AutoClickerTyperV2/releases)
2. Run the installer
3. The installer will bundle Tesseract OCR if found on your system
4. Launch from Start Menu or Desktop shortcut

### Option 2: Download Standalone Executable
1. Download `AutoClickerTyper.exe` from [Releases](https://github.com/yourusername/AutoClickerTyperV2/releases)
2. Install Tesseract OCR separately: https://github.com/UB-Mannheim/tesseract/wiki
3. Run the executable

---

## 🛠️ Development Setup

### Installation from Source
1. Ensure you have Python 3.10+ installed
2. Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
3. Clone this repository:
   ```powershell
   git clone https://github.com/yourusername/AutoClickerTyperV2.git
   cd AutoClickerTyperV2
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

### Configuration
Edit `config.py` to customize:
- `CLICK_KEYWORDS`: List of words to find and click
- `TYPE_KEYWORDS`: List of words that trigger typing
- `OCR_CONFIDENCE_THRESHOLD`: Adjust sensitivity
- `TESSERACT_CMD_PATH`: Path to your Tesseract executable
- `TARGET_WINDOW_TITLE`: Specific window to target (or None for full screen)

### Usage
1. **GUI Mode** (Recommended):
   ```powershell
   python gui.py
   ```

2. **Command Line Mode**:
   ```powershell
   python main.py
   ```

3. **Test Run**:
   Run the test harness to see how it works safely:
   ```powershell
   python test_harness.py
   ```
   Then, in a separate terminal:
   ```powershell
   python main.py
   ```

---

## 📦 Building & Distribution

### Build Standalone Executable

1. Install build dependencies:
   ```powershell
   pip install -r requirements-dev.txt
   ```

2. Run the build script:
   ```powershell
   python build.py
   ```

3. Find your executable at `dist/AutoClickerTyper.exe`

### Create Windows Installer

1. Install [Inno Setup 6.0+](https://jrsoftware.org/isinfo.php)

2. Build the executable first (see above)

3. Compile the installer:
   ```powershell
   iscc installer.iss
   ```

4. Find your installer at `installer_output/AutoClickerTyper_Setup_v*.exe`

**Note**: The installer will bundle Tesseract OCR if found at `C:\Program Files\Tesseract-OCR\`

### Distribution Checklist
- [ ] Update version in `installer.iss`
- [ ] Build executable with `python build.py`
- [ ] Test executable on clean Windows VM
- [ ] Create installer with Inno Setup
- [ ] Test installer on clean Windows VM
- [ ] Create GitHub Release with tag (e.g., `v1.0.0`)
- [ ] Upload both `.exe` and installer to release

---

## 🚀 Features
- **Auto-Discovery**: Finds keywords anywhere on screen
- **Human-like Interaction**: Randomized movement and delays
- **Verification**: Re-scans to ensure actions took effect
- **Self-Healing**: Retries failed actions automatically
- **GUI Control Panel**: Easy-to-use interface for workflows
- **Quick Prompts**: Save and reuse common automation sequences
- **Color Detection**: Optional blue button filtering

## 🔒 Safety
- Move your mouse manually to the corners of the screen to trigger PyAutoGUI's failsafe if the bot goes rogue
- Use "Always on Top" mode to keep control panel accessible
- Test thoroughly in safe environments before production use

## 📝 License
MIT License - See LICENSE.txt for details

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

