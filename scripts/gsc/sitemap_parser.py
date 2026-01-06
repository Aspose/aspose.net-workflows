import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Constants
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

SITEMAP_RECORD_FILE = os.path.join(LOGS_DIR, "processed_urls.json")
BATCH_FILE = os.path.join(LOGS_DIR, "batches_to_submit.json")
SUBDOMAINS = [
    "www.aspose.net", "products.aspose.net", "blog.aspose.net",
    "docs.aspose.net", "kb.aspose.net", "about.aspose.net",
    "reference.aspose.net", "websites.aspose.net"
]
FAMILY_SUBDOMAINS = [
    "kb.aspose.net", "docs.aspose.net", "products.aspose.net", "reference.aspose.net"
]
FAMILIES = ['words', 'pdf', 'cells', 'imaging', 'barcode', 'tasks', 'ocr', 'cad', 'html', 'zip', 'page', 'psd', 'tex', 'svg', 'email', 'medical']
BATCH_SIZE = 200
REPROCESS_DAYS_LIMIT = 30  

# Extract nested sitemaps (including multilingual ones)
def extract_sitemaps_from_index(sitemap_url):
    """Extracts only sitemap URLs (.xml) from an index sitemap."""
    try:
        if not sitemap_url.endswith(".xml"):
            print(f"[WARNING] Skipping non-sitemap URL: {sitemap_url}")
            return []

        response = requests.get(sitemap_url, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] {sitemap_url} returned status {response.status_code}")
            return []
        
        content = response.text.strip()
        if not content.startswith("<?xml"):
            print(f"[ERROR] {sitemap_url} is not a valid XML sitemap.")
            return []

        tree = ET.ElementTree(ET.fromstring(content))
        return [url.text for url in tree.findall(".//{*}loc") if url.text.endswith(".xml")]
    except Exception as e:
        print(f"[ERROR] Failed to fetch sitemaps from {sitemap_url}: {e}")
    return []

# Fetch all sitemaps for a subdomain
def get_all_sitemaps(subdomain):
    """Gets all sitemaps for a given subdomain, including multilingual and family-based sitemaps."""
    index_sitemap_url = f"https://{subdomain}/sitemap.xml"
    extracted_sitemaps = [index_sitemap_url]

    try:
        response = requests.get(index_sitemap_url, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch {index_sitemap_url}, Status Code: {response.status_code}")
            return []

        content = response.text.strip()
        if not content.startswith("<?xml"):
            print(f"[ERROR] {index_sitemap_url} is not valid XML.")
            return []

        tree = ET.ElementTree(ET.fromstring(content))
        extracted_sitemaps.extend([sitemap.text for sitemap in tree.findall(".//{*}loc") if sitemap.text.endswith(".xml")])

        # Extract multilingual & nested sitemaps
        for sitemap in extracted_sitemaps.copy():
            multilingual_sitemaps = extract_sitemaps_from_index(sitemap)
            extracted_sitemaps.extend(multilingual_sitemaps)

        # If the subdomain has family-based sitemaps, check for them
        if subdomain in FAMILY_SUBDOMAINS:
            for family in FAMILIES:
                family_sitemap_url = f"https://{subdomain}/{family}/sitemap.xml"
                response = requests.head(family_sitemap_url, timeout=5)  # Lightweight check
                if response.status_code == 200:
                    print(f"[INFO] Found family-based sitemap: {family_sitemap_url}")
                    extracted_sitemaps.append(family_sitemap_url)

                    # Extract multilingual & nested sitemaps from family sitemap
                    multilingual_sitemaps = extract_sitemaps_from_index(family_sitemap_url)
                    extracted_sitemaps.extend(multilingual_sitemaps)

    except Exception as e:
        print(f"[ERROR] Failed to extract sub-sitemaps from {index_sitemap_url}: {e}")
    
    return extracted_sitemaps

# Extract URLs from sitemap (excluding .xml)
def extract_sitemap_urls(sitemap_url):
    """Extracts actual URLs (not .xml sitemaps) from a sitemap file."""
    try:
        if not sitemap_url.endswith(".xml"):
            print(f"[WARNING] Skipping non-sitemap URL: {sitemap_url}")
            return []

        response = requests.get(sitemap_url, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] {sitemap_url} returned status {response.status_code}")
            return []
        
        content = response.text.strip()
        if not content.startswith("<?xml"):
            print(f"[ERROR] {sitemap_url} is not valid XML.")
            return []

        tree = ET.ElementTree(ET.fromstring(content))
        urls = []
        for url_elem in tree.findall(".//{*}loc"):
            url = url_elem.text
            if not url.endswith(".xml"):  # ✅ Ensure only non-sitemap URLs are added
                lastmod_elem = url_elem.find("./../{*}lastmod")
                lastmod = lastmod_elem.text if lastmod_elem is not None else None
                urls.append((url, lastmod))
        return urls
    except Exception as e:
        print(f"[ERROR] Failed to fetch {sitemap_url}: {e}")
    return []

# Load & Save JSON data
def load_json(file):
    """Loads JSON data from a file."""
    return json.load(open(file)) if os.path.exists(file) else {}

def save_json(file, data):
    """Saves JSON data to a file."""
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# Prepare URL batches for submission
def prepare_batches():
    """Prepares URL batches for submission, ensuring no sitemap URLs are included."""
    processed_urls = load_json(SITEMAP_RECORD_FILE)
    batches = {}

    for subdomain in SUBDOMAINS:
        print(f"[INFO] Processing subdomain: {subdomain}")
        all_sitemaps = get_all_sitemaps(subdomain)
        urls_to_submit = []

        for sitemap_url in all_sitemaps:
            extracted_urls = extract_sitemap_urls(sitemap_url)
            for url, lastmod in extracted_urls:
                try:
                    lastmod_date = datetime.strptime(lastmod, "%Y-%m-%d") if lastmod else None
                except ValueError:
                    lastmod_date = None

                last_processed = processed_urls.get(url)

                # Include only URLs not processed in the last 30 days
                if not last_processed or (lastmod_date and last_processed < (datetime.now() - timedelta(days=REPROCESS_DAYS_LIMIT)).isoformat()):
                    urls_to_submit.append(url)

        # ✅ Ensure only valid URLs (no .xml)
        urls_to_submit = [url for url in urls_to_submit if not url.endswith(".xml")]

        batches[subdomain] = [urls_to_submit[i:i + BATCH_SIZE] for i in range(0, len(urls_to_submit), BATCH_SIZE)]

    save_json(BATCH_FILE, batches)
    print(f"[INFO] Batches prepared for submission.")

if __name__ == "__main__":
    prepare_batches()
