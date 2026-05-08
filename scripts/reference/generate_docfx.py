import json
import sys
import os
import shutil
import subprocess
import time
import zipfile
import urllib.request

REFERENCE_DIR = "reference/"
WORKSPACE_DIR = "workspace/"
DOCFX_OUTPUT_DIR = "workspace/docfx/"
DOCFX_DOWNLOAD_URL = "https://github.com/dotnet/docfx/releases/download/v2.77.0/docfx-win-x64-v2.77.0.zip"
DOCFX_DIR = "workspace/docfx/"
DOCFX_EXECUTABLE = os.path.join(DOCFX_DIR, "docfx.exe")

DOCFX_TEMPLATE = {
    "metadata": [
        {
            "src": [{"files": []}],
            "dest": "api",
            "outputFormat": "markdown"
        }
    ]
}

def download_and_extract_docfx():
    """Downloads and extracts DocFX if it's not already available in the workspace."""
    if os.path.exists(DOCFX_EXECUTABLE):
        print(f"DocFX already exists at {DOCFX_EXECUTABLE}")
        return

    print(f"Downloading DocFX from {DOCFX_DOWNLOAD_URL}...")
    zip_path = os.path.join(WORKSPACE_DIR, "docfx.zip")
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Downloading DocFX (attempt {attempt}/{max_attempts})...")
            urllib.request.urlretrieve(DOCFX_DOWNLOAD_URL, zip_path)
            print("DocFX download complete.")
            break
        except Exception as e:
            print(f"ERROR: Download attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                wait = 2 ** attempt  # 2s, 4s exponential backoff
                print(f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print("ERROR: All download attempts exhausted.")
                sys.exit(1)

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(DOCFX_DIR)
        print("DocFX extracted successfully.")
    except zipfile.BadZipFile:
        print("ERROR: DocFX zip file is corrupted.")
        sys.exit(1)

    os.remove(zip_path)

def generate_docfx(nuget_name):
    """Generates docfx.json, downloads DocFX, and runs metadata processing in the correct order."""

    # Normalize family name by removing 'Aspose.' and converting to lowercase
    family_name = nuget_name.replace("Aspose.", "").lower()

    files_txt = os.path.join(WORKSPACE_DIR, f"{nuget_name}_files.txt")
    if not os.path.exists(files_txt):
        print(f"ERROR: DLL path file {files_txt} not found. Run extract_files.py first.")
        sys.exit(1)

    # Ensure docfx workspace directory exists
    os.makedirs(DOCFX_OUTPUT_DIR, exist_ok=True)

    api_dir = os.path.join(DOCFX_OUTPUT_DIR, "api")

    # Check if API already exists, prevent redundant processing
    if os.path.exists(api_dir) and len(os.listdir(api_dir)) > 0:
        print(f"Skipping DocFX processing: API directory already exists at {api_dir}")
        return

    with open(files_txt, "r") as f:
        paths = [line.strip() for line in f.readlines()]
    
    dll_path = paths[0] if paths else None
    xml_path = paths[1] if len(paths) > 1 else None

    if not dll_path or not os.path.exists(dll_path):
        print(f"ERROR: DLL file not found for {nuget_name}.")
        sys.exit(1)

    # Copy DLL and XML to docfx output directory
    copied_dll_path = os.path.join(DOCFX_OUTPUT_DIR, os.path.basename(dll_path))
    shutil.copy(dll_path, copied_dll_path)

    copied_xml_path = None
    if xml_path and os.path.exists(xml_path):
        copied_xml_path = os.path.join(DOCFX_OUTPUT_DIR, os.path.basename(xml_path))
        shutil.copy(xml_path, copied_xml_path)

    # Copy filterConfig.yml if it exists
    filter_config_path = os.path.join(REFERENCE_DIR, family_name, "filterConfig.yml")
    copied_filter_path = None
    if os.path.exists(filter_config_path):
        copied_filter_path = os.path.join(DOCFX_OUTPUT_DIR, "filterConfig.yml")
        shutil.copy(filter_config_path, copied_filter_path)
        print(f"Copied filterConfig.yml for {nuget_name}.")

    # Prepare docfx.json content
    docfx = DOCFX_TEMPLATE.copy()
    docfx["metadata"][0]["src"][0]["files"] = [os.path.basename(copied_dll_path)]
    
    if copied_xml_path:
        docfx["metadata"][0]["src"][0]["files"].append(os.path.basename(copied_xml_path))
    
    if copied_filter_path:
        docfx["metadata"][0]["filter"] = "filterConfig.yml"

    # Write docfx.json in the same directory
    docfx_json_path = os.path.join(DOCFX_OUTPUT_DIR, "docfx.json")
    with open(docfx_json_path, "w", encoding="utf-8") as f:
        json.dump(docfx, f, indent=2)

    print(f"Generated docfx.json for {nuget_name}: {json.dumps(docfx, indent=2)}")

    # Step 2: Download and extract DocFX (AFTER docfx.json is created)
    download_and_extract_docfx()

    # Step 3: Run DocFX metadata processing
    try:
        print("Running DocFX metadata...")
        subprocess.run([DOCFX_EXECUTABLE, "metadata"], cwd=DOCFX_OUTPUT_DIR, check=True)
        print("DocFX metadata processing completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: DocFX metadata processing failed. {e}")
        sys.exit(1)

    # Step 4: Ensure the `api/` directory was created
    if not os.path.exists(api_dir):
        print("ERROR: DocFX did not generate the 'api/' directory.")
        sys.exit(1)

    print(f"API directory generated at: {api_dir}")


if __name__ == "__main__":
    generate_docfx(sys.argv[1])
