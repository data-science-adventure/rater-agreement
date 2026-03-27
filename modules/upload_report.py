import os
import mimetypes
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
            # FIX: Used CREDENTIALS_FILE variable instead of hardcoded string
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

def find_file_id(service, name, folder_id):
    """
    Robust Search: Looks for the exact name OR the name without extension 
    to catch existing Google Sheets that had their extension stripped.
    """
    name_no_ext = os.path.splitext(name)[0]
    
    # Query logic: (Name match OR Name-without-extension match) inside the specific folder
    query = (f"(name = '{name}' or name = '{name_no_ext}') "
             f"and '{folder_id}' in parents and trashed = false")
    
    response = service.files().list(
        q=query, 
        spaces="drive", 
        fields="files(id, name, mimeType)"
    ).execute()
    
    files = response.get("files", [])
    return files[0]["id"] if files else None

def upload_or_overwrite(file_path, folder_id):
    service = get_drive_service()
    file_name = os.path.basename(file_path)
    is_csv = file_name.lower().endswith('.csv')

    # 1. Search for existing file ID first
    existing_file_id = find_file_id(service, file_name, folder_id)

    # 2. Setup Metadata & Media
    file_metadata = {"name": file_name}
    
    if is_csv:
        # Request conversion to Google Sheet
        file_metadata["mimeType"] = "application/vnd.google-apps.spreadsheet"
        media_mime = 'text/csv'
    else:
        # Detect mime type for other files (jsonl, txt, etc.)
        media_mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    media = MediaFileUpload(file_path, mimetype=media_mime, resumable=True)

    # 3. Decision: Update or Create
    if existing_file_id:
        print(f"🔄 Match found (ID: {existing_file_id}). Updating content...")
        # For updates, we pass the metadata (body) and the content (media_body)
        service.files().update(
            fileId=existing_file_id,
            body=file_metadata,
            media_body=media
        ).execute()
        print(f"✅ Successfully updated: {file_name}")
    else:
        print(f"⬆️ No existing file found. Creating new...")
        file_metadata["parents"] = [folder_id]
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        print(f"✅ Successfully created: {file_name} (ID: {file.get('id')})")

if __name__ == "__main__":
    FOLDER_ID = os.getenv("REPORT_FOLDER_ID")
    
    if not FOLDER_ID:
        print("❌ Error: REPORT_FOLDER_ID environment variable is missing.")
    else:
        for file_path in FILES_TO_UPLOAD:
            if os.path.exists(file_path):
                print(f"📄 Processing: {file_path}")
                try:
                    upload_or_overwrite(file_path, FOLDER_ID)
                except Exception as e:
                    print(f"❌ API Error for {file_path}: {e}")
            else:
                print(f"⚠️ Skip: '{file_path}' not found locally.")
            print("-" * 30)