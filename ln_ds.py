import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# -----------------------------
# Authenticate with Service Account
# -----------------------------
# Load credentials from Streamlit secrets
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build("drive", "v3", credentials=creds)

# Google Drive Folder ID
FOLDER_ID = "1RLpdHEJGIY4-MofCEzvqxDOWQmSMOpNU"

# -----------------------------
# List all files in the folder
# -----------------------------
def list_files():
    query = f"'{FOLDER_ID}' in parents and trashed=false"
    results = drive_service.files().list(q=query).execute()
    return results.get("files", [])

# -----------------------------
# Download and load a file
# -----------------------------
def load_file(file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    if file_name.endswith(".csv"):
        return pd.read_csv(fh)
    else:
        return pd.read_excel(fh)

# -----------------------------
# Dashboard
# -----------------------------
st.title("🏦 Branchwise Loan Dashboard")

files = list_files()
file_names = ["All Files (Combined)"] + [f["name"] for f in files]
choice = st.selectbox("📂 Select File", file_names)

if choice == "All Files (Combined)":
    df_list = [load_file(f["id"], f["name"]) for f in files]
    df = pd.concat(df_list, ignore_index=True)
else:
    file = next(f for f in files if f["name"] == choice)
    df = load_file(file["id"], file["name"])

st.dataframe(df)

