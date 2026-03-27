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
REPORT_DIR = config.main.report_dir

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
    FILE_TO_UPLOAD = f"{REPORT_DIR}/conflict_report.csv"
    PLOT_TO_UPLOAD = f"{REPORT_DIR}/annotation_report_visuals.png"
    upload_or_overwrite(FILE_TO_UPLOAD, FOLDER_ID)
    upload_or_overwrite(PLOT_TO_UPLOAD, FOLDER_ID)
