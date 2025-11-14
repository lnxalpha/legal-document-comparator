#!/usr/bin/env python3
"""
Quick start script for local development
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Ensure Python 3.7+"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✓ Python version: {sys.version.split()[0]}")

def check_venv():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("\n⚠️  Warning: Not running in a virtual environment")
        print("   Recommended: Create a venv first")
        print("   python -m venv venv")
        print("   source venv/bin/activate  # or venv\\Scripts\\activate on Windows")
        response = input("\nContinue anyway? (y/n): ").lower().strip()
        if response != 'y':
            sys.exit(0)

def install_dependencies():
    """Install required packages"""
    print("\n📦 Installing dependencies...")
    
    requirements_path = Path(__file__).parent.parent / "backend" / "requirements.txt"
    
    if not requirements_path.exists():
        print(f"❌ requirements.txt not found at {requirements_path}")
        sys.exit(1)
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            check=True
        )
        print("✓ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def download_spacy_model():
    """Download spaCy English model"""
    print("\n📥 Downloading spaCy model...")
    
    try:
        # Check if model is already installed
        import spacy
        try:
            spacy.load("en_core_web_sm")
            print("✓ spaCy model already installed")
            return
        except OSError:
            pass
        
        # Download model
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
            check=True
        )
        print("✓ spaCy model downloaded")
    except subprocess.CalledProcessError:
        print("⚠️  Failed to download spaCy model")
        print("   You can download it manually later with:")
        print("   python -m spacy download en_core_web_sm")
    except ImportError:
        print("⚠️  spaCy not installed yet, will download model after installation")

def check_tesseract():
    """Check if Tesseract is installed"""
    print("\n🔍 Checking for Tesseract OCR...")
    
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True
        )
        print("✓ Tesseract is installed")
        return True
    except FileNotFoundError:
        print("⚠️  Tesseract OCR not found")
        print("\n   Install instructions:")
        print("   macOS:    brew install tesseract")
        print("   Ubuntu:   sudo apt-get install tesseract-ocr")
        print("   Windows:  Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print("\n   OCR features will not work without Tesseract")
        print("   You can still compare digital PDFs")
        return False

def copy_frontend_files():
    """Copy frontend files to backend/static"""
    print("\n📂 Setting up frontend files...")
    
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / "frontend"
    static_dir = project_root / "backend" / "static"
    
    static_dir.mkdir(exist_ok=True)
    
    # Copy files
    files_to_copy = ["index.html", "styles.css", "app.js"]
    
    for filename in files_to_copy:
        src = frontend_dir / filename
        dst = static_dir / filename
        
        if src.exists():
            import shutil
            shutil.copy2(src, dst)
            print(f"   ✓ Copied {filename}")
        else:
            print(f"   ⚠️  {filename} not found")

def start_server():
    """Start the FastAPI server"""
    print("\n" + "="*60)
    print("🚀 Starting Legal Document Comparator...")
    print("="*60 + "\n")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    os.chdir(backend_dir)
    
    print("Server will start at: http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app:app", "--reload", "--port", "8000"],
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server failed to start: {e}")
        sys.exit(1)

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     📄 Legal Document Comparator - Quick Start          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Check Python
    check_python_version()
    
    # Step 2: Check venv
    check_venv()
    
    # Step 3: Install dependencies
    response = input("\nInstall/update dependencies? (y/n): ").lower().strip()
    if response == 'y':
        install_dependencies()
        download_spacy_model()
    
    # Step 4: Check Tesseract
    check_tesseract()
    
    # Step 5: Copy frontend
    copy_frontend_files()
    
    # Step 6: Start server
    print("\n" + "="*60)
    response = input("Ready to start server? (y/n): ").lower().strip()
    if response == 'y':
        start_server()
    else:
        print("\nTo start manually:")
        print("cd backend")
        print("python -m uvicorn app:app --reload --port 8000")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled")
        sys.exit(0)
