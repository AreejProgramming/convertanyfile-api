import sys
import requests
from bs4 import BeautifulSoup
import json

url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")

images = soup.find_all("img")
missing_alt = [img.get("src") for img in images if not img.get("alt")]

result = {
    "url": url,
    "total_images": len(images),
    "missing_alt": len(missing_alt),
    "accessibility_score": max(0, 100 - len(missing_alt)*5)
}

print(json.dumps(result))
