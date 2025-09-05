import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseDownload

# ===========================
# 🔑 Authenticate with Service Account
# ===========================
# Load secrets from Streamlit Cloud (Secrets Manager)
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/drive"]
)

# Google Drive service
drive_service = build("drive", "v3", credentials=creds)

# Put your Google Drive folder ID here
FOLDER_ID = "1RLpdHEJGIY4-MofCEzvqxDOWQmSMOpNU"

# ===========================
# 📂 List Files from Drive
# ===========================
def list_files():
    query = (
        f"'{FOLDER_ID}' in parents and trashed=false and "
        "(mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' "
        "or mimeType='text/csv')"
    )
    results = drive_service.files().list(q=query).execute()
    files = results.get("files", [])
    return files

# ===========================
# 📥 Download & Read File
# ===========================
def load_file(file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)

    # Detect file type
    if file_name.endswith(".csv"):
        df = pd.read_csv(fh)
    else:
        df = pd.read_excel(fh, engine="openpyxl")
    return df

# ===========================
# 🚀 Streamlit App
# ===========================
st.title("🏦 Branchwise Loan Dashboard")
st.caption("This dashboard reads data directly from Google Drive (shared folder).")

# --- File selection ---
files = list_files()
file_options = ["All Files (Combined)"] + [f["name"] for f in files]

if "file_choice" not in st.session_state:
    st.session_state.file_choice = "All Files (Combined)"

file_choice = st.selectbox(
    "📂 Select File",
    file_options,
    index=file_options.index(st.session_state.file_choice),
    key="file_choice"
)

# --- Load data ---
if file_choice == "All Files (Combined)":
    df_list = []
    for f in files:
        df_list.append(load_file(f["id"], f["name"]))
    if df_list:
        df = pd.concat(df_list, ignore_index=True)
    else:
        st.warning("No files found in the folder.")
        st.stop()
else:
    selected_file = next(f for f in files if f["name"] == file_choice)
    df = load_file(selected_file["id"], selected_file["name"])

# --- Show raw data ---
with st.expander("📄 View Raw Data"):
    st.dataframe(df)

# --- Filters ---
branches = ["All"] + sorted(df["Branch"].dropna().unique().tolist())
statuses = ["All"] + sorted(df["Status"].dropna().unique().tolist())

if "branch_choice" not in st.session_state:
    st.session_state.branch_choice = "All"
if "status_choice" not in st.session_state:
    st.session_state.status_choice = "All"

branch_choice = st.selectbox(
    "🏢 Select Branch",
    branches,
    index=branches.index(st.session_state.branch_choice),
    key="branch_choice"
)
status_choice = st.selectbox(
    "📌 Select Loan Status",
    statuses,
    index=statuses.index(st.session_state.status_choice),
    key="status_choice"
)

filtered_df = df.copy()
if branch_choice != "All":
    filtered_df = filtered_df[filtered_df["Branch"] == branch_choice]
if status_choice != "All":
    filtered_df = filtered_df[filtered_df["Status"] == status_choice]

# --- Summary Metrics ---
st.subheader("📊 Summary")
total_loans = filtered_df.shape[0]
total_amount = filtered_df["Loan_Amount"].sum()

col1, col2 = st.columns(2)
col1.metric("Total Loans", total_loans)
col2.metric("Total Loan Amount", f"{total_amount:,.2f}")

# --- Branchwise Summary ---
st.subheader("🏢 Branchwise Loan Summary")
branch_summary = (
    filtered_df.groupby(["Branch", "Status"], as_index=False)
    .agg({"Loan_Amount": "sum", "Loan_ID": "count"})
    .rename(columns={"Loan_ID": "No_of_Loans"})
)
st.dataframe(branch_summary)

