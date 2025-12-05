import os
import subprocess
import sys
from datetime import datetime

# Mapping of FAMILY names to corresponding FOLDER_NAME
FOLDER_MAP = {
    "Aspose.Words": "words",
    "Aspose.Cells": "cells",
    "Aspose.PDF": "pdf",
    "Aspose.Slides": "slides",
    "Aspose.Email": "email",
    "Aspose.Imaging": "imaging",
    "Aspose.BarCode": "barcode",
    "Aspose.Tasks": "tasks",
    "Aspose.Diagram": "diagram",
    "Aspose.OCR": "ocr",
    "Aspose.CAD": "cad",
    "Aspose.Note": "note",
    "Aspose.Page": "page",
    "Aspose.Zip": "zip",
    "Aspose.Font": "font",
    "Aspose.3D": "3d",
    "Aspose.TeX": "tex",
    "Aspose.HTML": "html",
    "Aspose.PSD": "psd",
    "Aspose.GIS": "gis",
    "Aspose.PUB": "pub",
    "Aspose.SVG": "svg",
    "Aspose.Finance": "finance",
    "Aspose.OMR": "omr",
    "Aspose.Drawing": "drawing",
    "Aspose.Medical": "medical"
}

# ✅ Log all received arguments for debugging
print(f"DEBUG: Received arguments: {sys.argv}")

# ✅ Fix: Ensure argument is received
if len(sys.argv) < 2 or not sys.argv[1].strip():
    print("ERROR: FAMILY argument is missing or empty. Ensure it is passed correctly in the workflow.")
    sys.exit(1)

FAMILY = sys.argv[1].strip()
FOLDER_NAME = FOLDER_MAP.get(FAMILY, "").strip()

# ✅ Fix: Validate mapped folder name
if not FOLDER_NAME:
    print(f"ERROR: No folder mapping found for FAMILY '{FAMILY}'. Check the mapping dictionary.")
    sys.exit(1)

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
BRANCH_NAME = f"api-update-{FOLDER_NAME}-{timestamp}"

GITHUB_TOKEN = os.getenv("REPO_TOKEN")
if not GITHUB_TOKEN:
    print("ERROR: GitHub token not set. Skipping repository push.")
    sys.exit(1)

repo_url = f"https://{GITHUB_TOKEN}@github.com/Aspose/aspose.net.git"
DEST_PATH = f"aspose.net/content/reference.aspose.net/{FOLDER_NAME}/en/"

print(f"DEBUG: Cloning repository to update API reference for '{FAMILY}'.")

# Clone repository
try:
    subprocess.run(["git", "clone", repo_url], check=True)
except subprocess.CalledProcessError:
    print("ERROR: Failed to clone repository.")
    sys.exit(1)

# ✅ Fix: Create the destination path if it does not exist
print(f"DEBUG: Copying updated API files to '{DEST_PATH}'...")
os.makedirs(DEST_PATH, exist_ok=True)

try:
    subprocess.run(["cp", "-r", "workspace/docfx/api/.", DEST_PATH], check=True)
except subprocess.CalledProcessError:
    print("ERROR: Failed to copy API files.")
    sys.exit(1)

# Change directory to cloned repo
os.chdir("aspose.net")

try:
    # Configure Git user
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)

    # Create and checkout the branch
    subprocess.run(["git", "checkout", "-b", BRANCH_NAME], check=True)

    # ✅ Fix: Ensure correct path for staging
    subprocess.run(["git", "add", f"content/reference.aspose.net/{FOLDER_NAME}/en/"], check=True)

    # Check if there are any changes
    commit_status = subprocess.run(["git", "diff", "--cached", "--exit-code"], check=False)
    if commit_status.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"Update API reference for {FAMILY}"], check=True)
        subprocess.run(["git", "push", "--set-upstream", "origin", BRANCH_NAME], check=True)

        # ✅ Fix: Authenticate GitHub CLI before creating PR
        print("DEBUG: Authenticating GitHub CLI...")
        auth_check = subprocess.run(["gh", "auth", "status"], check=False)
        if auth_check.returncode != 0:
            print("WARNING: GitHub CLI is not authenticated. PR creation may fail.")

        # ✅ Fix: Ensure valid PR title & body
        print("DEBUG: Creating a pull request...")
        pr_result = subprocess.run([
            "gh", "pr", "create",
            "--repo", "Aspose/aspose.net",
            "--title", f"Update API Docs for {FAMILY}",
            "--body", f"This PR updates the API documentation for {FAMILY}.",
            "--base", "main",
            "--head", BRANCH_NAME
        ], check=False)

        if pr_result.returncode == 0:
            print(f"Pull request created for {BRANCH_NAME}.")
        else:
            print("WARNING: PR creation failed. Check GitHub CLI authentication.")

    else:
        print("DEBUG: No changes detected. Skipping commit and push.")

except subprocess.CalledProcessError as e:
    print(f"ERROR: Git operations failed: {e}")
    sys.exit(1)
