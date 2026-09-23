"""Compatibility entry point for the shared Google Sheets uploader."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from sheets import (SCOPES, TOKEN_PATH, XLSX_MIME, SHEET_MIME,
                    find_client_secret, get_credentials, upload, main)


if __name__ == "__main__":
    main()
