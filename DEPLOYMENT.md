# Deployment Guide

This guide provides step-by-step instructions for building and deploying the AutoClickerTyper application.

## Prerequisites

### For Building Executable
- Python 3.10+
- All dependencies from `requirements.txt` and `requirements-dev.txt`
- Tesseract OCR installed at `C:\Program Files\Tesseract-OCR\`

### For Creating Installer
- All of the above
- [Inno Setup 6.0+](https://jrsoftware.org/isinfo.php)

## Quick Start

### 1. Build Standalone Executable

```powershell
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run build script
python build.py
```

The executable will be created at `dist/AutoClickerTyper.exe`

### 2. Create Windows Installer

```powershell
# Build executable first (if not already done)
python build.py

# Compile installer with Inno Setup
iscc installer.iss
```

The installer will be created at `installer_output/AutoClickerTyper_Setup_v1.0.0.exe`

## Manual Build Process

### PyInstaller Build

If you need to customize the build:

1. Edit `build.spec` to modify:
   - Hidden imports
   - Data files to include
   - Icon file
   - Console mode (True/False)

2. Run PyInstaller manually:
   ```powershell
   pyinstaller build.spec --clean
   ```

### Inno Setup Customization

Edit `installer.iss` to customize:

- **Version**: Update `#define MyAppVersion`
- **Publisher**: Update `#define MyAppPublisher`
- **URL**: Update `#define MyAppURL`
- **Tesseract Path**: Modify `Source:` line for Tesseract files
- **Desktop Icon**: Enable/disable in `[Tasks]` section

## Testing Checklist

### Before Release

- [ ] Test executable on development machine
- [ ] Test executable on clean Windows VM (no Python)
- [ ] Verify Tesseract OCR detection works
- [ ] Test all GUI features
- [ ] Test AutoClicker loop functionality
- [ ] Test workflow prompts
- [ ] Test quick prompts saving/loading

### Installer Testing

- [ ] Install on clean Windows VM
- [ ] Verify Start Menu shortcuts work
- [ ] Verify desktop shortcut (if enabled)
- [ ] Test application launches correctly
- [ ] Test uninstaller removes all files
- [ ] Verify registry entries are cleaned up

## Creating a GitHub Release

### Automated (Recommended)

1. Update version in `installer.iss`:
   ```iss
   #define MyAppVersion "1.0.0"
   ```

2. Commit all changes:
   ```powershell
   git add .
   git commit -m "Release v1.0.0"
   ```

3. Create and push version tag:
   ```powershell
   git tag v1.0.0
   git push origin v1.0.0
   ```

4. GitHub Actions will automatically:
   - Build the executable
   - Create the installer
   - Create a GitHub Release
   - Upload both files as release assets

### Manual Release

1. Build executable and installer locally (see above)

2. Create release on GitHub:
   - Go to repository → Releases → Draft a new release
   - Create new tag (e.g., `v1.0.0`)
   - Add release title and description
   - Upload both files:
     - `AutoClickerTyper.exe`
     - `AutoClickerTyper_Setup_v1.0.0.exe`

## Troubleshooting

### Build Issues

**PyInstaller fails with import errors**
- Add missing modules to `hiddenimports` in `build.spec`
- Check that all dependencies are installed

**Executable is too large**
- Consider using `--onedir` instead of `--onefile`
- Remove unnecessary dependencies

### Installer Issues

**Tesseract not bundled**
- Verify Tesseract is installed at `C:\Program Files\Tesseract-OCR\`
- Check Inno Setup console output for errors
- Update `Source:` path in `installer.iss` if needed

**Installer fails to compile**
- Ensure Inno Setup 6.0+ is installed
- Check that `dist/AutoClickerTyper.exe` exists
- Verify all referenced files exist

### Runtime Issues

**Executable shows "Failed to execute script"**
- Run from command line to see error messages
- Check that Tesseract OCR is installed on target machine
- Verify all required DLLs are bundled

**OCR not working in deployed version**
- Ensure Tesseract path is correct in `config.py`
- For installer version, Tesseract should be bundled
- For standalone, user must install Tesseract separately

## Code Signing (Optional)

For production distribution, consider code signing to avoid Windows Defender warnings:

1. Obtain a code signing certificate
2. Sign the executable:
   ```powershell
   signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist/AutoClickerTyper.exe
   ```
3. Sign the installer similarly

## Distribution Channels

- **GitHub Releases**: Primary distribution method
- **Direct Download**: Host files on your own server
- **Microsoft Store**: Requires app packaging and submission
- **Chocolatey**: Create a Chocolatey package for easy installation

## Version Management

Follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Update version in:
- `installer.iss` → `#define MyAppVersion`
- Git tag → `v1.0.0`
- GitHub Release title

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs in `execution.log`
