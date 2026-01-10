# Autonomous Auto Clicker & Typing Tool

## Overview
This tool is an autonomous agent designed to visually scan your screen, detect specific keywords using OCR, and perform actions (Click or Type) to automate workflows like software installation, bulk acceptance of dialogs, or routine form entry.

## Requirements
- Windows 10/11
- Python 3.10+
- Tesseract OCR (Mus be installed at `C:\Program Files\Tesseract-OCR\tesseract.exe` or in your PATH)

## Installation
1.  Ensure you have Python installed.
2.  Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
3.  Install dependencies:
    ```powershell
    pip install -r requirements.txt
    ```

## Configuration
Edit `config.py` to customize:
- `CLICK_KEYWORDS`: List of words to find and click.
- `TYPE_KEYWORDS`: List of words that trigger typing.
- `OCR_CONFIDENCE_THRESHOLD`: Adjust sensitivity.
- `TESSERACT_CMD_PATH`: Path to your Tesseract executable.

## Usage
1.  **Test Run**:
    Run the test harness to see how it works safely.
    ```powershell
    python test_harness.py
    ```
    Then, in a separate terminal:
    ```powershell
    python main.py
    ```

2.  **Production Run**:
    ```powershell
    python main.py
    ```
    The tool will continuously scan, log actions to `execution.log`, and perform clicks/types until stopped (Ctrl+C).

## Features
- **Auto-Discovery**: Finds keywords anywhere on screen.
- **Human-like Interaction**: Randomized movement and delays.
- **Verification**: Re-scans to ensure actions took effect.
- **Self-Healing**: Retries failed actions automatically.

## Safety
- Move your mouse manually to the corners of the screen to trigger PyAutoGUI's failsafe if the bot goes rogue.
