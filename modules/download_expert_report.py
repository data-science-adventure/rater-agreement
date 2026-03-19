

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
member_progress = client.get_members_progress(project_id=PROJECT_ID)


print(member_progress)
member_progress = filter(lambda p: p.username != 'heidi', member_progress)

for member in member_progress:
    print(f"{member.username} - {member.progress.total}")
