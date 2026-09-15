"""Upload an xlsx workbook to Google Drive as a native Google Sheet.

Uses the installed-app OAuth client from ~/Downloads (project: hootro) with
the drive.file scope (can only touch files it creates). First run opens a
browser for consent; the token is cached at ~/.config/cube-roto/token.json.

Usage: python3 upload_sheet.py workbook.xlsx "Sheet Title"
"""

import glob
import json
import pathlib
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = pathlib.Path.home() / ".config" / "cube-roto" / "token.json"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"


def find_client_secret():
    for f in sorted(glob.glob(str(pathlib.Path.home() / "Downloads" / "client_secret*.json"))):
        if "installed" in json.loads(pathlib.Path(f).read_text()):
            return f
    sys.exit("no installed-app client_secret*.json found in ~/Downloads")


def get_credentials():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(find_client_secret(), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def upload(path, title, file_id=None):
    """Create a new Sheet, or replace the content of an existing one in place."""
    drive = build("drive", "v3", credentials=get_credentials())
    media = MediaFileUpload(path, mimetype=XLSX_MIME)
    if file_id:
        req = drive.files().update(fileId=file_id, media_body=media, fields="id,webViewLink")
    else:
        req = drive.files().create(
            body={"name": title, "mimeType": SHEET_MIME}, media_body=media,
            fields="id,webViewLink",
        )
    file = req.execute()
    print(file["webViewLink"])
    return file


if __name__ == "__main__":
    args = sys.argv[1:]
    file_id = None
    if "--update" in args:
        i = args.index("--update")
        file_id = args[i + 1]
        del args[i : i + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    upload(args[0], args[1], file_id)
