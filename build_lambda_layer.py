#!/usr/bin/env python3
"""
Lambda Layer builder script for Python 3.13
Creates a zip file containing dependencies for Lambda Layer
"""

import os
import shutil
import subprocess
import sys
import zipfile

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

LAYER_DIR = "layer"
LAYER_ZIP = "layer.zip"
TEMP_VENV = ".venv-layer"
PYTHON_LIB_DIR = os.path.join(LAYER_DIR, "python", "lib", "python3.13", "site-packages")


def clean_layer_dir():
    """Clean up layer directory and temp venv"""
    if os.path.exists(LAYER_DIR):
        shutil.rmtree(LAYER_DIR)
    if os.path.exists(TEMP_VENV):
        shutil.rmtree(TEMP_VENV)
    os.makedirs(PYTHON_LIB_DIR, exist_ok=True)


def install_dependencies():
    """Install dependencies for Python 3.13, targeting Linux (Lambda runtime)."""
    print("Installing dependencies for Python 3.13 Lambda Layer (Linux target)...")
    # Lambda runs on Amazon Linux 2; use --python-platform linux to get Linux wheels
    # (Pillow etc. have C extensions that must match the runtime OS)
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            "3.13",
            "--target",
            PYTHON_LIB_DIR,
            "--python-platform",
            "linux",
            "boto3",
            "pillow",
            "requests",
            "python-dotenv",
            "--no-compile",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Error: Failed to install dependencies")
        print(result.stderr)
        return False
    print("Dependencies installed successfully")
    return True


def create_zip():
    """Create zip file from layer directory"""
    print(f"Creating {LAYER_ZIP}...")
    if os.path.exists(LAYER_ZIP):
        os.remove(LAYER_ZIP)

    with zipfile.ZipFile(LAYER_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(LAYER_DIR):
            # Exclude __pycache__ and *.pyc files
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if not file.endswith(".pyc"):
                    file_path = os.path.join(root, file)
                    # Keep the layer/python/lib/python3.13/site-packages structure
                    arcname = os.path.relpath(file_path, LAYER_DIR)
                    zipf.write(file_path, arcname)

    size_mb = os.path.getsize(LAYER_ZIP) / (1024 * 1024)
    print(f"Created {LAYER_ZIP} ({size_mb:.2f} MB)")


def main():
    print("=" * 50)
    print("Lambda Layer Builder")
    print("For Python 3.13")
    print("=" * 50)

    # Check if pyproject.toml exists
    if not os.path.exists("pyproject.toml"):
        print("Error: pyproject.toml not found")
        return

    clean_layer_dir()

    if not install_dependencies():
        return

    create_zip()

    print("\n" + "=" * 50)
    print("Done!")
    print(f"Upload {LAYER_ZIP} to Lambda Layer")
    print("Layer structure: python/lib/python3.13/site-packages/")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Upload layer.zip to AWS Lambda Layer")
    print("2. Set compatible runtime to Python 3.13")
    print("3. Attach the layer to your Lambda function")
    print("4. Update Lambda function runtime to Python 3.13")


if __name__ == "__main__":
    main()
