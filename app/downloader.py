import requests
import os

def download_and_save(url: str, save_as: str):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        filepath = os.path.join("downloads", save_as)
        with open(filepath, "wb") as f:
            f.write(response.content)

        return filepath
    except Exception as e:
        return f"Failed to download {url}: {str(e)}"
