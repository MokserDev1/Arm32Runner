import urllib.request
import re
import sys
import os

base_url = "https://archive.org/download/talking-bacteria-john-john-john-for-iphone/"
print("Fetching directory listing from archive.org...")
req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", "ignore")
except Exception as e:
    print(f"Error fetching {base_url}: {e}")
    sys.exit(1)

# Find ipa links
ipa_links = [m for m in re.findall(r'href=[\"\']([^\"\']+\.ipa)[\"\']', html)]
print(f"Found IPA links: {ipa_links}")

if not ipa_links:
    print("No .ipa links found in listing!")
    sys.exit(1)

target_ipa = ipa_links[0]
download_url = base_url + target_ipa
out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", target_ipa)
print(f"Downloading {download_url} to {out_path}...")

req_dl = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req_dl, timeout=30) as resp, open(out_path, "wb") as f:
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    while True:
        chunk = resp.read(65536)
        if not chunk:
            break
        f.write(chunk)
        downloaded += len(chunk)
        if total:
            done = int(50 * downloaded / total)
            sys.stdout.write(f"\r[{'=' * done}{' ' * (50-done)}] {downloaded}/{total} bytes")
            sys.stdout.flush()

print(f"\nDownload completed: {out_path} ({os.path.getsize(out_path)} bytes)")
