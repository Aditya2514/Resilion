"""
Check if the API keys for EIA and Guardian are set and test their connections.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Allow running from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env from project root folder
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from data_sources.eia import fetch_petroleum_prices
from data_sources.guardian import fetch_guardian_articles

def check():
    print("=" * 60)
    print("RESILION — API Key Connection Test")
    print("=" * 60)
    
    # 1. Check EIA API Key
    eia_key = os.getenv("EIA_API_KEY", "Not Set")
    print(f"\nEIA_API_KEY: {eia_key[:4]}..." if eia_key != "Not Set" else "\nEIA_API_KEY: Not Set")
    
    if eia_key == "Not Set" or eia_key == "INSERT_EIA_API_KEY_HERE":
        print("  [FAIL] EIA API Key is not configured.")
    else:
        # Patch the key inside the current execution context config
        import config
        config.EIA_API_KEY = eia_key
        
        print("  Testing connection to EIA API...")
        res = fetch_petroleum_prices(num_records=1)
        if res.get("status") == "NO_KEY":
            print("  [FAIL] Config indicates NO_KEY.")
        elif "error" in res:
            print(f"  [FAIL] EIA API returned error: {res['error']}")
        else:
            print("  [SUCCESS] EIA API Connection working! Sample record:")
            print(f"    {res.get('data', [])}")

    # 2. Check Guardian API Key
    guardian_key = os.getenv("GUARDIAN_API_KEY", "Not Set")
    print(f"\nGUARDIAN_API_KEY: {guardian_key[:4]}..." if guardian_key != "Not Set" else "\nGUARDIAN_API_KEY: Not Set")
    
    if guardian_key == "Not Set" or guardian_key == "INSERT_GUARDIAN_API_KEY_HERE":
        print("  [FAIL] Guardian API Key is not configured.")
    else:
        import config
        config.GUARDIAN_API_KEY = guardian_key
        
        print("  Testing connection to Guardian API...")
        res = fetch_guardian_articles(page_size=1)
        if res.get("status") == "NO_KEY":
            print("  [FAIL] Config indicates NO_KEY.")
        elif "error" in res:
            print(f"  [FAIL] Guardian API returned error: {res['error']}")
        else:
            print("  [SUCCESS] Guardian API Connection working! Sample article:")
            if res.get("data"):
                print(f"    Title: {res['data'][0]['title']}")
                print(f"    URL: {res['data'][0]['url']}")
            else:
                print("    (No articles returned but connection was successful)")

if __name__ == "__main__":
    check()
