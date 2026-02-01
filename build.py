"""
Build script for creating standalone AutoClickerTyper executable
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all build requirements are met"""
    print("Checking build requirements...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Install with: pip install pyinstaller")
        return False
    
    # Check required files
    required_files = ['gui.py', 'main.py', 'config.py', 'build.spec']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Required file missing: {file}")
            return False
    print("✓ All required files present")
    
    return True

def clean_build_artifacts():
    """Remove previous build artifacts"""
    print("\nCleaning previous build artifacts...")
    
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removed: {dir_name}/")
    
    # Remove .pyc files
    for pyc in Path('.').rglob('*.pyc'):
        pyc.unlink()
    
    print("✓ Cleanup complete")

def build_executable():
    """Run PyInstaller to build the executable"""
    print("\nBuilding executable with PyInstaller...")
    print("This may take a few minutes...\n")
    
    try:
        result = subprocess.run(
            ['pyinstaller', 'build.spec', '--clean'],
            check=True,
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            print("\n✓ Build successful!")
            return True
        else:
            print("\n❌ Build failed!")
            print(result.stderr)
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error: {e}")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("\n❌ PyInstaller not found in PATH")
        return False

def verify_build():
    """Verify the build output"""
    print("\nVerifying build output...")
    
    exe_path = Path('dist/ZapwebPromptAssist.exe')
    
    if not exe_path.exists():
        print("❌ Executable not found in dist/")
        return False
    
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"✓ Executable created: {exe_path}")
    print(f"  Size: {size_mb:.2f} MB")
    
    return True

def main():
    """Main build process"""
    print("=" * 60)
    print("AutoClickerTyper - Build Script")
    print("=" * 60)
    
    # Step 1: Check requirements
    if not check_requirements():
        print("\n❌ Build requirements not met. Please fix the issues above.")
        sys.exit(1)
    
    # Step 2: Clean previous builds
    clean_build_artifacts()
    
    # Step 3: Build executable
    if not build_executable():
        print("\n❌ Build process failed.")
        sys.exit(1)
    
    # Step 4: Verify build
    if not verify_build():
        print("\n❌ Build verification failed.")
        sys.exit(1)
        
    # Step 5: Copy config files to dist for testing
    print("\nCopying configuration files to dist/...")
    for f in ['quick_prompts.json', 'config.json']:
        if os.path.exists(f):
            shutil.copy2(f, 'dist/')
            print(f"  ✓ Copied {f}")
    
    print("\n" + "=" * 60)
    print("✓ BUILD COMPLETE!")
    print("=" * 60)
    print("\nYour executable is ready at: dist/ZapwebPromptAssist.exe")
    print("\nNext steps:")
    print("  1. Test the executable on this machine")
    print("  2. Create installer with Inno Setup (see installer.iss)")
    print("  3. Test on a clean Windows machine without Python")
    print("\nNote: Tesseract OCR must be installed separately on target machines")
    print("      or bundled using the Inno Setup installer.")
    print("=" * 60)

if __name__ == "__main__":
    main()
