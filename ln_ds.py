import streamlit as st
import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import io

# -----------------------------
# Connect Google Drive
# -----------------------------
@st.cache_resource
def connect_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # opens browser for login first time
    return GoogleDrive(gauth)

drive = connect_drive()

# Replace with your Google Drive folder ID
FOLDER_ID = "YOUR_FOLDER_ID_HERE"

# -----------------------------
# List files in folder
# -----------------------------
def list_files():
    query = f"'{FOLDER_ID}' in parents and trashed=false"
    return drive.ListFile({'q': query}).GetList()

# -----------------------------
# Load a single file
# -----------------------------
def load_file(file):
    if file['title'].endswith(".csv"):
        return pd.read_csv(io.StringIO(file.GetContentString()))
    else:
        return pd.read_excel(io.BytesIO(file.GetContentBinary()))

# -----------------------------
# Dashboard
# -----------------------------
st.title("🏦 Branchwise Loan Dashboard")

# Step 1: Get all files from Drive
files = list_files()
file_names = ["All Files (Combined)"] + [f['title'] for f in files]

# Step 2: File Selection (remember last choice)
if "file_choice" not in st.session_state:
    st.session_state.file_choice = "All Files (Combined)"

choice = st.selectbox(
    "📂 Select File",
    file_names,
    index=file_names.index(st.session_state.file_choice),
    key="file_choice"
)

# Step 3: Load data
if choice == "All Files (Combined)":
    df_list = [load_file(f) for f in files]
    df = pd.concat(df_list, ignore_index=True)
else:
    file = next(f for f in files if f['title'] == choice)
    df = load_file(file)

# Step 4: Show raw data
with st.expander("📄 View Raw Data"):
    st.dataframe(df)

# Step 5: Filters with memory
branches = ["All"] + sorted(df["Branch"].dropna().unique().tolist())
statuses = ["All"] + sorted(df["Status"].dropna().unique().tolist())

if "branch_choice" not in st.session_state:
    st.session_state.branch_choice = "All"
if "status_choice" not in st.session_state:
    st.session_state.status_choice = "All"

branch_choice = st.selectbox(
    "Select Branch",
    branches,
    index=branches.index(st.session_state.branch_choice),
    key="branch_choice"
)

status_choice = st.selectbox(
    "Select Loan Status",
    statuses,
    index=statuses.index(st.session_state.status_choice),
    key="status_choice"
)

# Step 6: Filter data
filtered_df = df.copy()
if branch_choice != "All":
    filtered_df = filtered_df[filtered_df["Branch"] == branch_choice]
if status_choice != "All":
    filtered_df = filtered_df[filtered_df["Status"] == status_choice]

# Step 7: Summary
st.subheader("📊 Summary")
total_loans = filtered_df.shape[0]
total_amount = filtered_df["Loan_Amount"].sum()

col1, col2 = st.columns(2)
col1.metric("Total Loans", total_loans)
col2.metric("Total Loan Amount", f"{total_amount:,.2f}")

# Step 8: Branchwise summary
st.subheader("🏢 Branchwise Loan Summary")
branch_summary = (
    filtered_df.groupby(["Branch", "Status"], as_index=False)
    .agg({"Loan_Amount": "sum", "Loan_ID": "count"})
    .rename(columns={"Loan_ID": "No_of_Loans"})
)
st.dataframe(branch_summary)
