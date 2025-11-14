#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legal Document Comparator - Project Setup Script
Run this to create the complete project structure
"""

import sys
import os

# Force UTF-8 output on all platforms
def print_utf8(text):
    try:
        sys.stdout.write(text + "\n")
    except:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))

def create_project_structure():
    """Create all necessary folders and files"""

    structure = {
        'backend': {
            'comparison_engine': ['__init__.py'],
            'static': [],
            'uploads': []
        },
        'frontend': [],
        'scripts': [],
        'tests': [],
        'docs': []
    }

    print_utf8("Creating project structure...")

    for main_dir, subdirs in structure.items():
        os.makedirs(main_dir, exist_ok=True)
        print_utf8(f"[OK] Created {main_dir}/")

        if isinstance(subdirs, dict):
            for subdir, files in subdirs.items():
                path = os.path.join(main_dir, subdir)
                os.makedirs(path, exist_ok=True)
                print_utf8(f"  [OK] Created {path}/")

                for file in files:
                    filepath = os.path.join(path, file)
                    open(filepath, 'a').close()
                    print_utf8(f"    [OK] Created {filepath}")

    print_utf8("\nProject structure created successfully!\n")

def create_requirements():
    requirements = """# Core Framework
fastapi==0.104.0
uvicorn==0.24.0
python-multipart==0.0.6

# Document Processing
pymupdf==1.23.0
pytesseract==0.3.10
pillow==10.1.0
pdf2image==1.16.3

# Smart Text Processing
spacy==3.7.0
sentence-transformers==2.2.0
scikit-learn==1.3.0
numpy==1.24.3

# Utilities
python-dotenv==1.0.0
aiofiles==23.2.1
"""
    with open('backend/requirements.txt', 'w', encoding="utf-8") as f:
        f.write(requirements.strip())

    print_utf8("[OK] Created backend/requirements.txt")

def create_readme():
    readme = """# Legal Document Comparator
(… content unchanged for brevity …)
"""

    with open('README.md', 'w', encoding="utf-8") as f:
        f.write(readme.strip())

    print_utf8("[OK] Created README.md")

def create_gitignore():
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project Specific
backend/uploads/*
!backend/uploads/.gitkeep
*.pdf
*.png
*.jpg
*.jpeg

# Models
backend/models/

# Environment
.env
.env.local
"""

    with open('.gitignore', 'w', encoding="utf-8") as f:
        f.write(gitignore.strip())

    print_utf8("[OK] Created .gitignore")

def create_env_template():
    env = """# Environment Configuration

HOST=0.0.0.0
PORT=8000
DEBUG=True

MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg

SPACY_MODEL=en_core_web_sm
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2

TESSERACT_PATH=/usr/bin/tesseract

SIMILARITY_THRESHOLD=0.85
CONTEXT_WINDOW=2
"""
    with open('.env.example', 'w', encoding="utf-8") as f:
        f.write(env.strip())

    print_utf8("[OK] Created .env.example")

def main():
    print_utf8("""
============================================================
   LEGAL DOCUMENT COMPARATOR - PROJECT SETUP
   Context-Aware Document Verification with AI
============================================================
""")

    response = input("Continue? (y/n): ").lower().strip()
    if response != 'y':
        print_utf8("Setup cancelled.")
        sys.exit(0)

    print_utf8("\n" + "="*60 + "\n")

    try:
        create_project_structure()
        create_requirements()
        create_readme()
        create_gitignore()
        create_env_template()

        print_utf8("\nSetup Complete! Read README.md for next steps.\n")

    except Exception as e:
        print_utf8(f"\nERROR during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
