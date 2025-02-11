import json
import requests

STATUS_FILE = "reference/status.json"
NUGET_API_URL = "https://api.nuget.org/v3-flatcontainer/{}/index.json"

# Load existing status.json
with open(STATUS_FILE, "r", encoding="utf-8") as f:
    status_data = json.load(f)

updates_needed = {}

# Check latest NuGet versions
for family, data in status_data.items():
    nuget_name = data["nuget"]
    response = requests.get(NUGET_API_URL.format(nuget_name))

    if response.status_code == 200:
        versions = response.json().get("versions", [])
        latest_version = versions[-1] if versions else None

        if latest_version and latest_version != data["version"]:
            updates_needed[family] = {"nuget": nuget_name, "version": latest_version}

# Output results for GitHub Actions
print(json.dumps(updates_needed))
