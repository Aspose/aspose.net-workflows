import sys
import json

if len(sys.argv) < 2:
    print("Error: No products specified.")
    sys.exit(1)

products_to_check = [p.strip() for p in sys.argv[1].split(",") if p.strip()]

# Load updates from status.json
try:
    with open("reference/status.json", "r", encoding="utf-8") as f:
        status_data = json.load(f)
except FileNotFoundError:
    print("Error: status.json not found.")
    sys.exit(1)

# Filter products needing updates
updates_needed = []
seen = set()

for product in products_to_check:
    if product in status_data and product not in seen:
        latest_version = status_data[product]["version"]  # Get latest version
        updates_needed.append({
            "family": product,
            "nuget": status_data[product]["nuget"],
            "version": latest_version
        })
        seen.add(product)

# Ensure unique entries
unique_updates_needed = list({u["family"]: u for u in updates_needed}.values())

# ✅ Always print valid JSON
output_json = json.dumps(unique_updates_needed)

if not unique_updates_needed:
    print("[]")  # Ensure JSON array, not empty output
else:
    print(output_json)
