#%%writefile student_app.py
import streamlit as st
import pandas as pd
from datetime import date
import os

# --- Page Setup ---
st.set_page_config(page_title="Student Attendance Tracker", layout="wide")

# --- Load Table 1 and Table 2 ---
@st.cache_data
def load_data():
    try:
        table1 = pd.read_excel("https://docs.google.com/spreadsheets/d/1QBEXA0UVnpfXGpxbhYsqiaIhXPhRS60H/edit?usp=sharing&ouid=101250663179398377883&rtpof=true&sd=true", sheet_name='S1 - Student Details')
        # table2 = pd.read_excel("/content/Attendance.xlsx", sheet_name='S2 - Attendance')
        return table1#, table2
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.stop()

table1 = load_data()
# students = table2.merge(table1, on="Student Name", how="left")
students = table1
st.info("Enter your registered Phone Number in sidebar")
st.sidebar.title("User Login")

phone_input = st.sidebar.text_input("Enter your registered Phone Number", "").strip().replace(" ", "")

if not phone_input:
    st.sidebar.info("Please enter your phone number to continue.")
    st.stop()

# Identify role: Parent or Teacher
# Check if phone matches any Parent 1 or Parent 2
is_parent = ((students["Parents Number 1"].astype(str) == phone_input) | 
             (students["Parents Number 2"].astype(str) == phone_input)).any()

# Check if phone matches any Teacher's phone number
# Assuming teacher's phone number is stored in a column 'Teacher Phone' in table1
# If not present, you'll need to add or manage teacher phone numbers accordingly
if 'Teacher Phone Number' in table1.columns:
    is_teacher = (table1['Teacher Phone Number'].astype(str) == phone_input).any()
else:
    # If no teacher phone column, treat as non-teacher by default
    is_teacher = False

if not is_parent and not is_teacher:
    st.sidebar.error("❌ Phone number not found in system.")
    st.stop()

# If both roles possible, ask user to select role (optional)
if is_parent and is_teacher:
    role = st.sidebar.selectbox("Select Role", ["Parent", "Teacher"])
elif is_parent:
    role = "Parent"
else:
    role = "Teacher"

st.sidebar.success(f"Logged in as: {role}")

# Parent can view only their linked children
if role == "Parent":
    authorized_students = students[
        (students["Parents Number 1"].astype(str) == phone_input) |
        (students["Parents Number 2"].astype(str) == phone_input)
    ]
    mode = st.sidebar.radio("Choose Mode", ["📊 View Attendance Summary"])
else:
    # Teacher can choose both modes
    mode = st.sidebar.radio("Choose Mode", ["📊 View Attendance Summary", "📝 Mark Attendance"])

# --- View Attendance Summary ---
if mode == "📊 View Attendance Summary":
    st.title("📊 Attendance Summary")
    if role == "Parent":
        student_list = authorized_students["Student Name"].dropna().unique().tolist()
    else:
        student_list = students["Student Name"].dropna().unique().tolist()
    
    selected_student = st.selectbox("Select Student", student_list)

    if selected_student:
        st.markdown("---")
        info = students[students["Student Name"] == selected_student].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Student Name:** {selected_student}")
            st.info(f"**Class:** {info['Class']}")
        with col2:
            st.info(f"**Teacher:** {info['Teacher Name']}")
            st.info(f"**Parent 1:** {int(info['Parents Number 1'])}")
            if pd.notna(info['Parents Number 2']):
                st.info(f"**Parent 2:** {int(info['Parents Number 2'])}")

        try:
            log = pd.read_csv("attendance_log.csv")
            # For parents, ensure they only see their child's attendance
            if role == "Parent":
                student_log = log[log["Student Name"] == selected_student]
            else:
                student_log = log[log["Student Name"] == selected_student]

            if not student_log.empty:
                present = student_log['Status'].value_counts().get('Present', 0)
                absent = student_log['Status'].value_counts().get('Absent', 0)
                total = present + absent
                percent = (present / total) * 100 if total else 0

                st.metric("✅ Present", present)
                st.metric("❌ Absent", absent)
                st.progress(percent / 100)
                st.write(f"**Attendance %:** `{percent:.2f}%`")
                st.dataframe(student_log[['Date', 'Status']].sort_values('Date'))
            else:
                st.warning("No attendance records found.")
        except FileNotFoundError:
            st.warning("Attendance log file not found.")

# --- Mark Attendance (only for Teacher) ---
elif mode == "📝 Mark Attendance":
    if role != "Teacher":
        st.error("🚫 Only teachers can mark attendance.")
        st.stop()

    st.title("📝 Mark Attendance")

    selected_date = st.date_input("📅 Select Attendance Date", date.today())
    today = selected_date.strftime("%Y-%m-%d")
    st.write(f"### Mark Attendance for: `{today}`")

    attendance_status = {}

    for _, row in students.iterrows():
        name = row['Student Name']
        student_class = row['Class']
        parent1 = str(row['Parents Number 1'])
        unique_key = f"{name}_{student_class}_{parent1}"

        status = st.radio(
            f"{name} (Class: {student_class}, Parent: {parent1})",
            options=["Present", "Absent", "No Class"],
            key=unique_key,
            horizontal=True
        )
        attendance_status[unique_key] = {
            "Student Name": name,
            "Class": student_class,
            "Parent 1": parent1,
            "Status": status
        }

    if st.button("✅ Submit Attendance"):
        existing_log = pd.read_csv("attendance_log.csv") if os.path.exists("attendance_log.csv") else pd.DataFrame(columns=["Date", "Student Name", "Class", "Teacher", "Parent 1", "Status"])
        existing_today = existing_log[existing_log["Date"] == today]

        if not existing_today.empty:
            st.warning("⚠️ Attendance for this date already exists!")
            update = st.radio("Do you want to update it?", ["No", "Yes"], index=0)
            if update == "No":
                st.stop()
            else:
                existing_log = existing_log[existing_log["Date"] != today]

        attendance_log = []
        for entry in attendance_status.values():
            teacher = students[
                (students["Student Name"] == entry["Student Name"]) &
                (students["Class"] == entry["Class"]) &
                (students["Parents Number 1"].astype(str) == entry["Parent 1"])
            ]['Teacher Name'].values[0]

            attendance_log.append({
                "Date": today,
                "Student Name": entry["Student Name"],
                "Class": entry["Class"],
                "Teacher": teacher,
                "Parent 1": entry["Parent 1"],
                "Status": entry["Status"]
            })

        df_log = pd.DataFrame(attendance_log)
        final_log = pd.concat([existing_log, df_log], ignore_index=True)
        final_log.to_csv("attendance_log.csv", index=False)

        st.success("✅ Attendance saved successfully!")
        st.download_button(
            label="📥 Download Attendance",
            data=df_log.to_csv(index=False),
            file_name=f"attendance_log_{today}.csv",
            mime="text/csv"
        )
