import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()
from util.config_util import ConfigUtil

config = ConfigUtil.get_config()

TOKEN_FILE = config.upload_report.token_file
CREDENTIALS_FILE = config.upload_report.credentials_file
FILES_TO_UPLOAD = config.upload_report.files_to_upload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def find_file_id(service, name, folder_id):
    """Search for a file by name in a specific folder."""
    query = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    response = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    files = response.get("files", [])
    return files[0]["id"] if files else None


def upload_or_overwrite(file_path, folder_id):
    service = get_drive_service()
    file_name = os.path.basename(file_path)

    # 1. Check if the file already exists
    existing_file_id = find_file_id(service, file_name, folder_id)

    media = MediaFileUpload(file_path, resumable=True)

    if existing_file_id:
        # --- OVERWRITE (Update) ---
        print(
            f"🔄 Existing file found (ID: {existing_file_id}). Overwriting content..."
        )
        file = (
            service.files().update(fileId=existing_file_id, media_body=media).execute()
        )
        print(f"✅ Successfully updated: {file_name}")
    else:
        # --- CREATE NEW ---
        print(f"⬆️ No existing file found. Creating new file...")
        file_metadata = {"name": file_name, "parents": [folder_id]}
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        print(f"✅ Successfully created: {file_name} (ID: {file.get('id')})")


if __name__ == "__main__":
    FOLDER_ID = os.getenv("REPORT_FOLDER_ID")
    for file_path in FILES_TO_UPLOAD:
        # 1. Local Validation: Check if the file exists on your machine
        if os.path.exists(file_path):
            print(f"📄 Processing: {file_path}")
            try:
                upload_or_overwrite(file_path, FOLDER_ID)
            except Exception as e:
                print(f"❌ Failed to upload {file_path}. Error: {e}")
        else:
            # 2. Skip and Continue: Log the missing file and move to the next
            print(f"⚠️ Skip: File not found at '{file_path}'. Moving to next file...")
        print("-" * 30)
