#%%writefile student_app.py
import streamlit as st
import pandas as pd
from datetime import date
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Page Setup ---
st.set_page_config(page_title="Student Attendance Tracker", layout="wide")

# Google Sheets API Setup
SPREADSHEET_ID = '1dwju2Um-3RXlaOKwRS7jaNEmIXBGMIbMxIOv4t5Lpnw'  # Replace with actual sheet ID
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Initialize Session State for Login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_phone' not in st.session_state:
    st.session_state.user_phone = None
if 'auth_students' not in st.session_state:
    st.session_state.auth_students = None

# Load student data from Google Sheets (no cache)
def load_data():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='S1 - Student Details'
        ).execute()

        values = result.get('values', [])
        if not values:
            st.error("❌ No data found.")
            st.stop()

        df = pd.DataFrame(values[1:], columns=values[0])

        for col in ['Parents Number 1', 'Parents Number 2', "Teacher Phone Number", "Password"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()
        return df

    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheets: {e}")
        st.stop()

students = load_data()

# st.info("Enter your registered Phone Number in sidebar")
# st.sidebar.title("User Login")

# phone_input = st.sidebar.text_input("Enter your registered Phone Number", "").strip().replace(" ", "")

# if not phone_input:
#     st.sidebar.info("Please enter your phone number to continue.")
#     st.stop()

# is_parent = ((students["Parents Number 1"] == phone_input) | 
#              (students["Parents Number 2"] == phone_input)).any()

# if 'Teacher Phone Number' in students.columns:
#     is_teacher = (students['Teacher Phone Number'] == phone_input).any()
# else:
#     is_teacher = False

# if not is_parent and not is_teacher:
#     st.sidebar.error("❌ Phone number not found in system.")
#     st.stop()

# if is_parent and is_teacher:
#     role = st.sidebar.selectbox("Select Role", ["Parent", "Teacher"])
# elif is_parent:
#     role = "Parent"
# else:
#     role = "Teacher"

# st.sidebar.success(f"Logged in as: {role}")

# if role == "Parent":
#     authorized_students = students[
#         (students["Parents Number 1"] == phone_input) |
#         (students["Parents Number 2"] == phone_input)
#     ]
#     mode = st.sidebar.radio("Choose Mode", ["📊 View Attendance Summary"])
# else:
#     mode = st.sidebar.radio("Choose Mode", ["📊 View Attendance Summary", "📝 Mark Attendance"])
# --- SIDEBAR LOGIC ---
st.sidebar.title("Attendance Portal")

if not st.session_state.logged_in:
    # --- SHOW LOGIN FORM ---
    st.sidebar.subheader("User Login")
    phone_input = st.sidebar.text_input("Registered Phone Number").strip().replace(" ", "")
    password_input = st.sidebar.text_input("Password (Parents only)", type="password").strip()
    
    if st.sidebar.form_submit_button("Login"):
        if not phone_input:
            st.sidebar.error("Please enter a phone number.")
        else:
            user_record = students[
                (students["Parents Number 1"] == phone_input) |
                (students["Parents Number 2"] == phone_input) |
                (students.get("Teacher Phone Number", "") == phone_input)
            ]

            if user_record.empty:
                st.sidebar.error("❌ Phone number not found.")
            else:
                record_count = len(user_record)
                is_teacher_num = (students.get('Teacher Phone Number', "") == phone_input).any()

                # Teacher Logic: Bypass password if > 1 record or flagged as teacher
                if record_count > 1 or is_teacher_num:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "Teacher"
                    st.session_state.user_phone = phone_input
                    st.rerun()
                else:
                    # Parent Logic: Check Password
                    correct_password = str(user_record.iloc[0].get("Password", "")).strip()
                    if password_input == correct_password:
                        st.session_state.logged_in = True
                        st.session_state.user_role = "Parent"
                        st.session_state.user_phone = phone_input
                        st.session_state.auth_students = user_record
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Incorrect Password.")

    st.info("👋 Welcome! Please login in the sidebar to access the tracker.")
    st.stop() # Prevent app from running until logged in

else:
    # --- SHOW LOGGED IN UI ---
    st.sidebar.success(f"Logged in as: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.rerun()

    role = st.session_state.user_role
    phone_input = st.session_state.user_phone

    if role == "Parent":
        mode = st.sidebar.radio("Choose Mode", ["📊 View Attendance Summary"])
    else:
        mode = st.sidebar.radio("Choose Mode", ["📊 View Attendance Summary", "📝 Mark Attendance"])

# # --- View Attendance Summary ---
# if mode == "📊 View Attendance Summary":
#     st.title("📊 Attendance Summary")
#     if role == "Parent":
#         student_list = authorized_students["Student Name"].dropna().unique().tolist()
#     else:
#         student_list = students["Student Name"].dropna().unique().tolist()
    
#     selected_student = st.selectbox("Select Student", student_list)

#     if selected_student:
#         st.markdown("---")
#         info = students[students["Student Name"] == selected_student].iloc[0]
#         col1, col2 = st.columns(2)
#         with col1:
#             st.info(f"**Student Name:** {selected_student}")
#             st.info(f"**Class:** {info['Class']}")
#         with col2:
#             st.info(f"**Teacher:** {info['Teacher Name']}")
#             st.info(f"**Parent 1:** {info['Parents Number 1']}")
#             if pd.notna(info['Parents Number 2']):
#                 st.info(f"**Parent 2:** {info['Parents Number 2']}")

#         try:
#             # Load attendance log (no caching)
#             SPREADSHEET_ID_2 = "1iZHggnfAjbNPZD_lV0fDCLmbVc1s7Kj0vCZYm5YLPtY"
#             creds_dict = st.secrets["gcp_service_account"]
#             creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
#             service = build('sheets', 'v4', credentials=creds)
#             sheet = service.spreadsheets()
#             result = sheet.values().get(
#                 spreadsheetId=SPREADSHEET_ID_2,
#                 range='Attendance Log!A1:Z1000'
#             ).execute()

#             values = result.get("values", [])
#             headers = values[0] if values else ["Date", "Student Name", "Class", "Teacher", "Parent 1", "Status"]
#             log = pd.DataFrame(values[1:], columns=headers) if len(values) > 1 else pd.DataFrame(columns=headers)

#             student_log = log[(log["Student Name"] == selected_student) & (log["Status"] != "No Class")]

#             if not student_log.empty:
#                 present = student_log['Status'].value_counts().get('Present', 0)
#                 absent = student_log['Status'].value_counts().get('Absent', 0)
#                 total = present + absent
#                 percent = (present / total) * 100 if total else 0

#                 st.metric("✅ Present", present)
#                 st.metric("❌ Absent", absent)
#                 st.progress(percent / 100)
#                 st.write(f"**Attendance %:** `{percent:.2f}%`")
#                 st.dataframe(student_log[['Date', 'Status']].sort_values('Date'))
#             else:
#                 st.warning("No attendance records found.")
#         except Exception as e:
#             st.warning(f"Error loading attendance log: {e}")

# # --- Mark Attendance (Teacher only) ---
# elif mode == "📝 Mark Attendance":
#     if role != "Teacher":
#         st.error("🚫 Only teachers can mark attendance.")
#         st.stop()

#     st.title("📝 Mark Attendance")

#     selected_date = st.date_input("📅 Select Attendance Date", date.today())
#     today = selected_date.strftime("%Y-%m-%d")
#     st.write(f"### Mark Attendance for: `{today}`")

#     attendance_status = {}

#     for _, row in students.iterrows():
#         name = row['Student Name']
#         student_class = row['Class']
#         parent1 = row['Parents Number 1']
#         unique_key = f"{name}_{student_class}_{parent1}"

#         status = st.radio(
#             f"{name} (Class: {student_class}, Parent: {parent1})",
#             options=["Present", "Absent", "No Class"],
#             index = 2,
#             key=unique_key,
#             horizontal=True
#         )
#         attendance_status[unique_key] = {
#             "Student Name": name,
#             "Class": student_class,
#             "Parent 1": parent1,
#             "Status": status
#         }

#     if st.button("✅ Submit Attendance"):
#         SPREADSHEET_ID_2 = "1iZHggnfAjbNPZD_lV0fDCLmbVc1s7Kj0vCZYm5YLPtY"
#         creds_dict = st.secrets["gcp_service_account"]
#         creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
#         service = build('sheets', 'v4', credentials=creds)
#         sheet = service.spreadsheets()
#         result = sheet.values().get(
#             spreadsheetId=SPREADSHEET_ID_2,
#             range='Attendance Log!A1:Z1000'
#         ).execute()

#         values = result.get("values", [])
#         headers = values[0] if values else ["Date", "Student Name", "Class", "Teacher", "Parent 1", "Status"]
#         existing_data = pd.DataFrame(values[1:], columns=headers) if len(values) > 1 else pd.DataFrame(columns=headers)

#         existing_today = existing_data[existing_data["Date"] == today]

#         if not existing_today.empty:
#             st.warning("⚠️ Attendance for this date already exists!")
#             update = st.radio("Do you want to update it?", ["No", "Yes"], index=0)
#             if update == "No":
#                 st.stop()
#             else:
#                 existing_data = existing_data[existing_data["Date"] != today]

#         attendance_log = []
#         for entry in attendance_status.values():
#             teacher = students[
#                 (students["Student Name"] == entry["Student Name"]) &
#                 (students["Class"] == entry["Class"]) &
#                 (students["Parents Number 1"] == entry["Parent 1"])
#             ]['Teacher Name'].values[0]

#             attendance_log.append([
#                 today,
#                 entry["Student Name"],
#                 entry["Class"],
#                 teacher,
#                 entry["Parent 1"],
#                 entry["Status"]
#             ])

#         updated_data = existing_data.values.tolist() + attendance_log
#         sheet.values().update(
#             spreadsheetId=SPREADSHEET_ID_2,
#             range='Attendance Log!A1:Z1000',
#             valueInputOption="RAW",
#             body={"values": [headers] + updated_data}
#         ).execute()

#         st.success("✅ Attendance saved to Google Sheet successfully!")
#         df_log = pd.DataFrame(attendance_log, columns=headers)
#         st.download_button(
#             label="📥 Download Attendance",
#             data=df_log.to_csv(index=False),
#             file_name=f"attendance_log_{today}.csv",
#             mime="text/csv"
#         )
# --- View Attendance Summary ---
    if mode == "📊 View Attendance Summary":
        st.title("📊 Attendance Summary")
        if role == "Parent":
            student_list = st.session_state.auth_students["Student Name"].dropna().unique().tolist()
        else:
            student_list = students["Student Name"].dropna().unique().tolist()

        selected_student = st.selectbox("Select Student", student_list)

        if selected_student:
            st.markdown("---")
            info = students[students["Student Name"] == selected_student].iloc[0]
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Student Name:** {selected_student}\n\n**Class:** {info['Class']}")
            with col2:
                st.info(f"**Teacher:** {info['Teacher Name']}\n\n**Parent 1:** {info['Parents Number 1']}")

            try:
                SPREADSHEET_ID_2 = "1iZHggnfAjbNPZD_lV0fDCLmbVc1s7Kj0vCZYm5YLPtY"
                creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                service = build('sheets', 'v4', credentials=creds)
                result = service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID_2, range='Attendance Log!A1:Z1000'
                ).execute()

                values = result.get("values", [])
                headers = values[0] if values else ["Date", "Student Name", "Class", "Teacher", "Parent 1", "Status"]
                log = pd.DataFrame(values[1:], columns=headers) if len(values) > 1 else pd.DataFrame(columns=headers)

                student_log = log[(log["Student Name"] == selected_student) & (log["Status"] != "No Class")]

                if not student_log.empty:
                    present = student_log['Status'].value_counts().get('Present', 0)
                    absent = student_log['Status'].value_counts().get('Absent', 0)
                    total = present + absent
                    percent = (present / total) * 100 if total else 0

                    st.metric("✅ Present", present)
                    st.metric("❌ Absent", absent)
                    st.progress(percent / 100)
                    st.write(f"**Attendance %:** `{percent:.2f}%`")
                    st.dataframe(student_log[['Date', 'Status']].sort_values('Date', ascending=False))
                else:
                    st.warning("No attendance records found.")
            except Exception as e:
                st.warning(f"Attendance log could not be loaded: {e}")

    # --- Mark Attendance (Teacher Only) ---
    elif mode == "📝 Mark Attendance":
        st.title("📝 Mark Attendance")
        selected_date = st.date_input("📅 Date", date.today())
        today = selected_date.strftime("%Y-%m-%d")
        
        attendance_status = {}
        for _, row in students.iterrows():
            unique_key = f"{row['Student Name']}_{row['Class']}_{row['Parents Number 1']}"
            status = st.radio(f"{row['Student Name']} ({row['Class']})", 
                             ["Present", "Absent", "No Class"], index=2, key=unique_key, horizontal=True)
            attendance_status[unique_key] = {"Name": row['Student Name'], "Class": row['Class'], "P1": row['Parents Number 1'], "Status": status}

        if st.button("✅ Submit Attendance"):
            SPREADSHEET_ID_2 = "1iZHggnfAjbNPZD_lV0fDCLmbVc1s7Kj0vCZYm5YLPtY"
            creds_dict = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            
            # Load existing to prevent duplicates for same day
            res = sheet.values().get(spreadsheetId=SPREADSHEET_ID_2, range='Attendance Log!A1:Z1000').execute()
            vals = res.get("values", [])
            headers = vals[0] if vals else ["Date", "Student Name", "Class", "Teacher", "Parent 1", "Status"]
            existing_df = pd.DataFrame(vals[1:], columns=headers) if len(vals) > 1 else pd.DataFrame(columns=headers)
            
            # Remove today's old data if updating
            existing_df = existing_df[existing_df["Date"] != today]

            new_entries = []
            for entry in attendance_status.values():
                t_search = students[students["Student Name"] == entry["Name"]]
                teacher = t_search['Teacher Name'].values[0] if not t_search.empty else "Unknown"
                new_entries.append([today, entry["Name"], entry["Class"], teacher, entry["P1"], entry["Status"]])

            final_data = [headers] + existing_df.values.tolist() + new_entries
            sheet.values().update(spreadsheetId=SPREADSHEET_ID_2, range="Attendance Log!A1", 
                                 valueInputOption="RAW", body={"values": final_data}).execute()
            st.success("✅ Attendance submitted!")
