import os
import sys
import time
import requests
import zipfile

if len(sys.argv) < 4:
    print("Error: python extract_files.py <nuget_name> <version> <family_name>")
    sys.exit(1)

nuget_name = sys.argv[1]  # e.g., "Aspose.Slides.NET"
nuget_version = sys.argv[2]  # e.g., "25.2.0"
family_name = sys.argv[3]  # e.g., "Aspose.Slides"

download_url = f"https://www.nuget.org/api/v2/package/{nuget_name}/{nuget_version}"
nupkg_path = f"packages/{nuget_name}.{nuget_version}.nupkg"

# Ensure packages directory exists
os.makedirs("packages", exist_ok=True)

# Download NuGet package
max_attempts = 3
for attempt in range(1, max_attempts + 1):
    try:
        print(f"Downloading {nuget_name} {nuget_version} (attempt {attempt}/{max_attempts})...")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        with open(nupkg_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded: {nupkg_path}")
        break
    except requests.RequestException as e:
        print(f"Error downloading NuGet package (attempt {attempt}): {e}")
        if attempt < max_attempts:
            wait = 2 ** attempt  # 2s, 4s exponential backoff
            print(f"Retrying in {wait}s...")
            time.sleep(wait)
        else:
            print("ERROR: All download attempts exhausted.")
            sys.exit(1)

extract_folder = f"workspace/{nuget_name}"
os.makedirs(extract_folder, exist_ok=True)

try:
    with zipfile.ZipFile(nupkg_path, "r") as zip_ref:
        zip_ref.extractall(extract_folder)
    print(f"Extraction complete: {nuget_name} -> {extract_folder}")
except zipfile.BadZipFile:
    print(f"Error: Corrupt or invalid zip file {nupkg_path}.")
    sys.exit(1)

# Search for XML and DLL using the correct family_name
largest_xml_path = None
largest_xml_size = -1
selected_dll_path = None

for root, _, files in os.walk(extract_folder):
    for file in files:
        # Look for {family_name}.xml (e.g., Aspose.Slides.xml)
        if file.lower() == f"{family_name.lower()}.xml":
            xml_path = os.path.join(root, file)
            xml_size = os.path.getsize(xml_path)
            if xml_size > largest_xml_size:
                largest_xml_size = xml_size
                largest_xml_path = xml_path
        
        # Look for {family_name}.dll (e.g., Aspose.Slides.dll)
        if file.lower() == f"{family_name.lower()}.dll":
            selected_dll_path = os.path.join(root, file)

# Ensure valid DLL and XML paths
if not largest_xml_path or not os.path.exists(selected_dll_path):
    print(f"Error: Could not find valid DLL and XML files for {family_name}.")
    sys.exit(1)

# Save the correct paths to a text file for later processing in generate_docfx.py
with open(f"workspace/{nuget_name}_files.txt", "w") as f:
    f.write(f"{selected_dll_path}\n")
    f.write(f"{largest_xml_path}\n")

print(f"Selected DLL: {selected_dll_path}")
print(f"Selected XML (largest): {largest_xml_path}")
