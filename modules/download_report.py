

import os
import zipfile
from doccano_client import DoccanoClient
from dotenv import load_dotenv
load_dotenv()


# 1. Configuration
URL = os.getenv("DOCCANO_URL")
USERNAME = os.getenv("DOCCANO_USERNAME")
PASSWORD = os.getenv("DOCCANO_PASSWORD")
PROJECT_ID = 1
EXPORT_FORMAT = 'JSONL'  # Changed to JSONL
TARGET_DIR = 'annotators'

# 2. Initialize and login
client = DoccanoClient(URL)
client.login(username=USERNAME, password=PASSWORD)

# 3. Create the target directory if it doesn't exist
os.makedirs(TARGET_DIR, exist_ok=True)

print(f"Starting download for project {PROJECT_ID} in {EXPORT_FORMAT} format...")

# 4. Download the project
# This triggers the export and downloads the zip to the current directory
client.download(
    PROJECT_ID,
    format=EXPORT_FORMAT,
    dir_name='.', 
    only_approved=False
)

# 5. Identify the downloaded zip and extract it
zip_filename = f'project_{PROJECT_ID}.zip'

if os.path.exists(zip_filename):
    print(f"Extracting {zip_filename} to '{TARGET_DIR}'...")
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(TARGET_DIR)
    
    # Clean up the zip file
    os.remove(zip_filename)
    print(f"Success! Your JSONL files are now in the '{TARGET_DIR}' folder.")
else:
    # Fallback: some versions might name it based on the project name or timestamp
    print(f"Warning: {zip_filename} not found. Checking for any project zip...")
    import glob
    zips = glob.glob("*.zip")
    if zips:
        print(f"Found {zips[0]}, attempting extraction...")
        with zipfile.ZipFile(zips[0], 'r') as zip_ref:
            zip_ref.extractall(TARGET_DIR)
        os.remove(zips[0])
    else:
        print("Error: No download file detected.")

print("Done!")