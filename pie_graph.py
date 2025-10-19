import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import logging
import json
import hashlib
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor 
from supabase import create_client
import os
from dotenv import load_dotenv
from functools import lru_cache
import time

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Database connection function with caching
@st.cache_resource
def get_pg_conn():
    try:
        return psycopg2.connect(
            host="ycqfpozukuwnwzqrhynn.supabase.co",
            database="postgres",
            user="postgres",
            password="RyanWork@Summmer25",
            port=5432,
            sslmode="require"
        )
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        # Return None to indicate connection failure
        return None

CSV_FILE = "time_log.csv"
USERS_FILE = "users.json"
PROFILE_PHOTO_DIR = "profile_photos"

#import psycopg2

#conn = psycopg2.connect(
    #host="https://ycqfpozukuwnwzqrhynn.supabase.co",
    #database="postgres",
    #user="postgres",
    #password="RyanWork@Summmer25",
   # port=5432,
    #sslmode="require"   # Supabase needs SSL
#)


# Ensure log file exists before configuring logging
Path("app.log").touch(exist_ok=True)

# Configure logging
logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logging.info("App started.")
logging.debug("DEBUG: App initialization complete.")
logging.warning("WARNING: App started with logging level DEBUG.")
logging.error("ERROR: This is a test error log at startup (for verification).")
logging.critical("CRITICAL: This is a test critical log at startup (for verification).")

st.set_page_config(page_title="Time Log App", layout="centered")
st.title("🕒 Time Log: Add, Edit, Save & Chart")

# Create profile photo directory if it doesn't exist
Path(PROFILE_PHOTO_DIR).mkdir(exist_ok=True)

# ------------------------
# Load Data into Session with caching
# ------------------------
@st.cache_data(ttl=60)  # Cache for 1 minute
def load_user_time_log_cached(user_id):
    logging.debug(f"Loading time log for user_id={user_id}")
    try:
        conn = get_pg_conn()
        if conn is None:
            # Fallback to CSV file if database connection fails
            logging.warning("Database connection failed, falling back to CSV file")
            if Path(CSV_FILE).exists():
                df = pd.read_csv(CSV_FILE)
                # Ensure 'id' column exists
                if "id" not in df.columns:
                    df["id"] = range(1, len(df) + 1)
                if user_id:
                    df = df[df["user_id"] == user_id]
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                return df
            else:
                return pd.DataFrame(columns=["id", "Date", "Time", "What I Did", "user_id"])
        
        with conn as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM time_log WHERE user_id = %s ORDER BY date, time", (user_id,))
                rows = cur.fetchall()
                logging.info(f"Loaded {len(rows)} rows for user_id={user_id}")
                if rows:
                    df = pd.DataFrame(rows)
                    df.rename(columns={"date": "Date", "time": "Time", "what_i_did": "What I Did", "user_id": "user_id"}, inplace=True)
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                    return df
                else:
                    logging.warning(f"No time log entries found for user_id={user_id}")
                    return pd.DataFrame(columns=["id", "Date", "Time", "What I Did", "user_id"])
    except Exception as e:
        logging.error(f"Error loading time log for user_id={user_id}: {e}")
        # Fallback to CSV file if any error occurs
        try:
            if Path(CSV_FILE).exists():
                df = pd.read_csv(CSV_FILE)
                # Ensure 'id' column exists
                if "id" not in df.columns:
                    df["id"] = range(1, len(df) + 1)
                if user_id:
                    df = df[df["user_id"] == user_id]
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                return df
            else:
                return pd.DataFrame(columns=["id", "Date", "Time", "What I Did", "user_id"])
        except Exception as csv_error:
            logging.error(f"Error loading CSV file: {csv_error}")
            return pd.DataFrame(columns=["id", "Date", "Time", "What I Did", "user_id"])

def load_user_time_log(user_id):
    # Use cached version for better performance
    return load_user_time_log_cached(user_id)

if "df" not in st.session_state:
    st.session_state.df = load_user_time_log(None)  # Empty by default

# Load users from JSON with caching
@st.cache_data(ttl=60)  # Cache for 1 minute
def load_users_cached():
    if Path(USERS_FILE).exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    else:
        return []

# Load users from JSON (move this above login)
users = load_users_cached()

# Function to save users and clear cache
def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)
    # Clear cache to force reload
    load_users_cached.clear()

# ------------------------
# 🔐 User Login
# ------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None

if not st.session_state.logged_in:
    st.subheader("🔐 Login")
    login_user = st.text_input("User ID", key="login_user")
    login_pass = st.text_input("Password", type="password", key="login_pass")
    signup_mode = st.checkbox("Sign Up (Create New User)")
    if signup_mode:
        st.subheader("👤 Register New User")
        reg_user = st.text_input("New User ID", key="reg_user_signup")
        reg_pass = st.text_input("New Password", type="password", key="reg_pass_signup")
        reg_full_name = st.text_input("Full Name", key="reg_full_name_signup")
        reg_email = st.text_input("Email", key="reg_email_signup")
        if st.button("Register New User"):
            if reg_user and reg_pass and reg_full_name:
                if any(u["id"] == reg_user for u in users):
                    st.error("User ID already exists!")
                    logging.warning(f"Attempted to register existing user: {reg_user}")
                else:
                    user_obj = {
                        "id": reg_user,
                        "password": hashlib.sha256(reg_pass.encode()).hexdigest(),
                        "created_at": datetime.now().isoformat(),
                        "full_name": reg_full_name,
                        "email": reg_email,
                        "role": "user",
                        "status": "active"
                    }
                    users.append(user_obj)
                    save_users(users)
                    # Add to info table in PostgreSQL
                    first_name, *last_name = reg_full_name.split(" ", 1)
                    last_name = last_name[0] if last_name else ""
                    try:
                        with get_pg_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "INSERT INTO info (user_id, first_name, last_name, email) VALUES (%s, %s, %s, %s)",
                                    (reg_user, first_name, last_name, reg_email)
                                )
                                conn.commit()
                    except Exception as e:
                        logging.error(f"Failed to add user to info table: {e}")
                    logging.info(f"Registered new user: {reg_user}")
                    st.success(f"User '{reg_user}' registered! You can now log in.")
                    st.stop()
            else:
                st.error("Please fill all required fields (User ID, Password, Full Name)")
                logging.warning("Registration failed: missing required fields.")
        st.stop()
    if st.button("Login"):
        user = next((u for u in users if u["id"] == login_user), None)
        if user and user["password"] == hashlib.sha256(login_pass.encode()).hexdigest():
            st.session_state.logged_in = True
            st.session_state.user_id = login_user
            st.success(f"Welcome, {user['full_name']}!")
            logging.info(f"User logged in: {login_user}")
        else:
            st.error("Invalid credentials.")
            logging.warning(f"Failed login attempt for user: {login_user}")
    st.stop()

current_user = st.session_state.user_id

# If no users exist, show a registration form before login
if not users:
    st.subheader("👤 Register First User (Admin)")
    st.markdown("**Add User**")
    reg_user = st.text_input("User ID", key="reg_user")
    reg_pass = st.text_input("Password", type="password", key="reg_pass")
    reg_full_name = st.text_input("Full Name", key="reg_full_name")
    reg_email = st.text_input("Email", key="reg_email")
    if st.button("Register"):
        if reg_user and reg_pass and reg_full_name:
            user_obj = {
                "id": reg_user,
                "password": hashlib.sha256(reg_pass.encode()).hexdigest(),
                "created_at": datetime.now().isoformat(),
                "full_name": reg_full_name,
                "email": reg_email,
                "role": "admin",
                "status": "active"
            }
            users.append(user_obj)
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)
            # Add to info table in PostgreSQL
            first_name, *last_name = reg_full_name.split(" ", 1)
            last_name = last_name[0] if last_name else ""
            try:
                with get_pg_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO info (user_id, first_name, last_name, email) VALUES (%s, %s, %s, %s)",
                            (reg_user, first_name, last_name, reg_email)
                        )
                        conn.commit()
            except Exception as e:
                logging.error(f"Failed to add user to info table: {e}")
            st.success(f"User '{reg_user}' registered as admin! Please restart the app and log in.")
            st.stop()
        else:
            st.error("Please fill all required fields (User ID, Password, Full Name)")
    st.stop()

# After login, show user profile info at the top
if st.session_state.logged_in:
    user_obj = next((u for u in users if u["id"] == current_user), None)
    st.markdown("---")
    st.markdown(f"### 👤 Logged in as: **{user_obj['full_name']}**  ")
    st.markdown(f"**Username:** `{user_obj['id']}`")
    if user_obj.get("photo") and Path(user_obj["photo"]).exists():
        st.image(user_obj["photo"], width=100, caption="Profile Photo")
    st.markdown("---")
    # Make admin/superadmin flags available everywhere
    is_admin = user_obj and user_obj.get("role") == "admin"
    is_super_admin = current_user == "The G.O.A.T"
else:
    is_admin = False
    is_super_admin = False

# Only show current user's data (from PostgreSQL)
def reload_user_df():
    st.session_state.df = load_user_time_log(current_user)

if st.session_state.logged_in:
    reload_user_df()
    user_df = st.session_state.df.copy()
else:
    user_df = pd.DataFrame(columns=["Date", "Time", "What I Did", "user_id"])

# ------------------------
# 📑 Sidebar Navigation (Pages)
# ------------------------
page = st.sidebar.radio(
    "Go to page:",
    [
        "Add Entry",
        "Edit Time Log",
        "View Charts",
        "Dashboard",  # <-- Added Dashboard page
        "User Management",  # <-- Added User Management to navigation
        "Profile Photo",
        "Kick Out Users"
    ],
    index=0
)

# ------------------------
# Main Page Routing
# ------------------------
if page == "Add Entry":
    # ------------------------
    # ➕ Add Entry
    # ------------------------
    st.subheader("➕ Add New Entry")
    with st.form("add_form", clear_on_submit=True):
        form_date = st.date_input("Date", value=date.today())
        form_time = st.text_input("Time (e.g. 7:30-8:00)")
        form_task = st.text_input("What I Did")
        submitted = st.form_submit_button("Add Entry")

    # ➕ Add Entry (write to PostgreSQL or CSV as fallback)
    def add_time_log_entry(date, time, what_i_did, user_id):
        conn = get_pg_conn()
        if conn is None:
            # Fallback to CSV file if database connection fails
            logging.warning("Database connection failed, saving to CSV file")
            try:
                # Read existing data
                if Path(CSV_FILE).exists():
                    df = pd.read_csv(CSV_FILE)
                else:
                    df = pd.DataFrame(columns=["id", "date", "time", "what_i_did", "user_id"])
            
                # Ensure 'id' column exists
                if "id" not in df.columns:
                    df["id"] = range(1, len(df) + 1)
            
                # Generate new ID (max ID + 1 or 1 if empty)
                new_id = df["id"].max() + 1 if not df.empty else 1
            
                # Add new entry
                new_row = pd.DataFrame([{
                    "id": new_id,
                    "date": date,
                    "time": time,
                    "what_i_did": what_i_did,
                    "user_id": user_id
                }])
            
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                # Clear cache to force reload
                load_user_time_log_cached.clear()
                logging.info(f"Entry saved to CSV: Date={date}, Time={time}, Task={what_i_did}")
            except Exception as e:
                logging.error(f"Error saving to CSV: {e}")
                raise
        else:
            with conn as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO time_log (date, time, what_i_did, user_id) VALUES (%s, %s, %s, %s)",
                        (date, time, what_i_did, user_id)
                    )
                    conn.commit()
                    # Clear cache to force reload
                    load_user_time_log_cached.clear()

    if submitted:
        if form_time.strip() and form_task.strip():
            add_time_log_entry(form_date, form_time.strip(), form_task.strip(), current_user)
            st.success("✅ Entry added!")
            reload_user_df()
            logging.info(f"Added entry: User={current_user}, Date={form_date}, Time={form_time.strip()}, Task={form_task.strip()}")
            logging.debug(f"DEBUG: Entry added for user {current_user} on {form_date} at {form_time.strip()} for task '{form_task.strip()}'")
        else:
            st.error("⚠️ Please enter both time and activity.")
            logging.warning("Attempted to add entry with missing time or activity.")
elif page == "Edit Time Log":
    # ------------------------
    # 📝 Edit Time Log with Editable Table, Delete Button, and Recent Entry Highlight
    # ------------------------
    st.subheader("📝 Edit Time Log")
    if not user_df.empty:
        # --- Search box ---
        search_query = st.text_input("🔍 Search your entries (by activity or time)", "")
        user_df_display = user_df.reset_index(drop=True)
        # Filter by search
        if search_query.strip():
            mask = (
                user_df_display["What I Did"].str.contains(search_query, case=False, na=False) |
                user_df_display["Time"].astype(str).str.contains(search_query, case=False, na=False)
            )
            user_df_display = user_df_display[mask].reset_index(drop=True)
        # Sort by Date and Time descending to show recent entries first
        user_df_display = user_df_display.sort_values(by=["Date", "Time"], ascending=[False, False]).reset_index(drop=True)
        
        # Add pagination for better performance with large datasets
        page_size = 50
        total_rows = len(user_df_display)
        total_pages = (total_rows - 1) // page_size + 1
        
        if total_pages > 1:
            page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
            start_idx = (page_number - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            user_df_display = user_df_display.iloc[start_idx:end_idx]
            st.write(f"Showing {start_idx+1}-{end_idx} of {total_rows} entries")
        
        # Add a Delete? checkbox column
        user_df_display["Delete?"] = False
        edited_df = st.data_editor(
            user_df_display.drop(columns=["user_id"]),
            num_rows="dynamic",
            use_container_width=True,
            key="edit_time_log_table",
            hide_index=True,
            column_config={"Date": {"type": "date"}, "Delete?": {"type": "checkbox"}}
        )
        # Delete selected rows
        if st.button("🗑️ Delete Selected"):
            to_delete = edited_df[edited_df["Delete?"] == True]
            if not to_delete.empty:
                conn = get_pg_conn()
                if conn is None:
                    # Fallback to CSV file if database connection fails
                    logging.warning("Database connection failed, deleting from CSV file")
                    try:
                        if Path(CSV_FILE).exists():
                            df = pd.read_csv(CSV_FILE)
                            # Ensure 'id' column exists
                            if "id" not in df.columns:
                                df["id"] = range(1, len(df) + 1)
                            # Delete matching rows
                            for _, row in to_delete.iterrows():
                                mask = (
                                    (df["date"] == str(row["Date"])) &
                                    (df["time"] == row["Time"]) &
                                    (df["what_i_did"] == row["What I Did"]) &
                                    (df["user_id"] == current_user)
                                )
                                df = df[~mask]
                            df.to_csv(CSV_FILE, index=False)
                            # Clear cache to force reload
                            load_user_time_log_cached.clear()
                            st.success(f"Deleted {len(to_delete)} entries from CSV.")
                            reload_user_df()
                            st.rerun()
                            logging.info(f"Deleted {len(to_delete)} entries for user {current_user} from CSV")
                        else:
                            st.error("CSV file not found.")
                    except Exception as e:
                        st.error(f"Error deleting from CSV: {e}")
                        logging.error(f"Error deleting from CSV: {e}")
                else:
                    with conn as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "DELETE FROM time_log WHERE date = %s AND time = %s AND what_i_did = %s AND user_id = %s",
                                (row["Date"], row["Time"], row["What I Did"], current_user)
                            )
                        conn.commit()
                        # Clear cache to force reload
                        load_user_time_log_cached.clear()
                    st.success(f"Deleted {len(to_delete)} entries.")
                    reload_user_df()
                    st.rerun()
                    logging.info(f"Deleted {len(to_delete)} entries for user {current_user}")
            else:
                st.info("No rows selected for deletion.")
                logging.debug("DEBUG: No rows selected for deletion.")
        # Save edits to PostgreSQL
        if st.button("💾 Save All Edits"):
            conn = get_pg_conn()
            if conn is None:
                # Fallback to CSV file if database connection fails
                logging.warning("Database connection failed, saving edits to CSV file")
                try:
                    if Path(CSV_FILE).exists():
                        df = pd.read_csv(CSV_FILE)
                        # Ensure 'id' column exists
                        if "id" not in df.columns:
                            df["id"] = range(1, len(df) + 1)
                        # Update matching rows
                        for idx, row in edited_df.iterrows():
                            orig_row = user_df_display.iloc[idx]
                            # Find the corresponding row in the CSV
                            mask = (
                                (df["date"] == str(orig_row["Date"])) &
                                (df["time"] == orig_row["Time"]) &
                                (df["what_i_did"] == orig_row["What I Did"]) &
                                (df["user_id"] == current_user)
                            )
                            # Update the matching row
                            df.loc[mask, ["date", "time", "what_i_did"]] = [str(row["Date"]), row["Time"], row["What I Did"]]
                        df.to_csv(CSV_FILE, index=False)
                        st.success("All edits saved to CSV!")
                        reload_user_df()
                        logging.info(f"All edits saved for user {current_user} to CSV")
                    else:
                        st.error("CSV file not found.")
                except Exception as e:
                    st.error(f"Error saving edits to CSV: {e}")
                    logging.error(f"Error saving edits to CSV: {e}")
            else:
                for idx, row in edited_df.iterrows():
                    orig_row = user_df_display.iloc[idx]
                    if (
                        str(row["Date"]) != str(orig_row["Date"]) or
                        row["Time"] != orig_row["Time"] or
                        row["What I Did"] != orig_row["What I Did"]
                    ):
                        with conn as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE time_log SET date = %s, time = %s, what_i_did = %s WHERE date = %s AND time = %s AND what_i_did = %s AND user_id = %s",
                                    (row["Date"], row["Time"], row["What I Did"], orig_row["Date"], orig_row["Time"], orig_row["What I Did"], current_user)
                                )
                            conn.commit()
                # Clear cache to force reload
                load_user_time_log_cached.clear()
                st.success("All edits saved!")
                reload_user_df()
                logging.info(f"All edits saved for user {current_user}")
    else:
        st.info("No entries to display.")
elif page == "View Charts":
    # ------------------------
    # 📊 Pie Chart Viewer (Admin can see all, user can only see their own)
    # ------------------------
    st.subheader("📊 View Time Breakdown")
    if is_admin or is_super_admin:
        # Admin: can select any user
        user_options = [u["id"] for u in users]
        selected_user_id = st.selectbox("Select a user to view their chart:", user_options, index=user_options.index(current_user))
    else:
        # Regular user: can only see their own
        selected_user_id = current_user
    selected_user_df = load_user_time_log(selected_user_id)
    valid_dates = pd.to_datetime(selected_user_df["Date"], errors="coerce").dropna().dt.date.unique()
    if len(valid_dates) == 0:
        st.info("No data available to chart for this user.")
    else:
        selected_date = st.date_input("📅 Pick a date", value=max(valid_dates),
                                      min_value=min(valid_dates), max_value=max(valid_dates), key="chart_date_"+selected_user_id)
        day_df = selected_user_df[
            pd.to_datetime(selected_user_df["Date"], errors="coerce").dt.date == selected_date
        ]
        def time_to_minutes(t, what_i_did):
            try:
                # Handle empty or None values
                if not t or pd.isna(t):
                    return 0
                
                t_lower = str(t).lower().strip()
                # Use actual time range for all sleep-related activities
                sleep_keywords = ["sleep", "slept", "sleeping", "i was sleeping", "nap", "bed", "rest"]
                is_sleep = any(kw in t_lower for kw in sleep_keywords)
                
                # Handle single time values (like "7:30" without range)
                if "-" not in t:
                    # For single time values, default to 5 minutes (or 540 for sleep)
                    return 540 if is_sleep else 5
                
                # Process time ranges
                start, end = str(t).split("-", 1)  # Split only on first dash
                start = start.strip()
                end = end.strip()
                
                # Handle cases like "5:30 -7:31" with inconsistent spacing
                s = datetime.strptime(start, "%H:%M")
                e = datetime.strptime(end, "%H:%M")
                
                # Handle overnight (end < start)
                if e <= s:
                    e = e + timedelta(days=1)
                
                duration = int((e - s).total_seconds() / 60)
                
                # Validate duration ranges
                if duration <= 0:
                    return 0
                if is_sleep:
                    if duration > 960:  # More than 16 hours of sleep is unrealistic
                        return 0
                else:
                    if duration > 720:  # More than 12 hours for other activities is unrealistic
                        return 0
                return duration
            except Exception as e:
                # Log the error for debugging
                logging.warning(f"Error parsing time '{t}': {e}")
                # Return default values based on activity type
                sleep_keywords = ["sleep", "slept", "sleeping", "i was sleeping", "nap", "bed", "rest"]
                is_sleep = any(kw in str(what_i_did).lower() for kw in sleep_keywords) if what_i_did else False
                return 540 if is_sleep else 5
        day_df = day_df.copy()
        day_df["Duration"] = day_df.apply(lambda row: time_to_minutes(row["Time"], row["What I Did"]), axis=1)
        day_df = day_df[day_df["Duration"] > 0]
        day_df["Label"] = day_df["What I Did"] + " (" + day_df["Time"] + ")"
        summary = day_df.groupby("Label")["Duration"].sum()
        if summary.empty:
            st.warning("⚠️ No valid time entries for selected date.")
        else:
            st.subheader(f"⏱ Time Breakdown for {selected_user_id} on {selected_date}")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.pie(summary, labels=summary.index, autopct="%1.1f%%", startangle=140)
            ax.axis("equal")
            st.pyplot(fig)
            logging.info(f"Displayed pie chart for {selected_date} with {len(summary)} segments.")
elif page == "User Management":
    # ------------------------
    # 👤 User Management
    # ------------------------
    st.subheader("👤 User Management")

    with st.form("add_user_form", clear_on_submit=True):
        new_user_id = st.text_input("User ID")
        new_password = st.text_input("Password", type="password")
        new_full_name = st.text_input("Full Name")
        new_email = st.text_input("Email")
        new_role = st.selectbox("Role", ["user", "admin"])
        user_submitted = st.form_submit_button("Add User")

    if user_submitted:
        if not (new_user_id and new_password and new_full_name):
            st.error("Please fill all required fields (User ID, Password, Full Name)")
        elif any(u["id"] == new_user_id for u in users):
            st.error("User ID already exists!")
        else:
            user_obj = {
                "id": new_user_id,
                "password": hashlib.sha256(new_password.encode()).hexdigest(),
                "created_at": datetime.now().isoformat(),
                "full_name": new_full_name,
                "email": new_email,
                "role": new_role,
                "status": "active"
            }
            users.append(user_obj)
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)
            st.success(f"User '{new_user_id}' added!")

    if users:
        st.write("### Registered Users")
        st.dataframe(pd.DataFrame(users).drop(columns=["password"]))

    # Admin approval and password management
    if st.session_state.logged_in:
        current_user_obj = next((u for u in users if u["id"] == current_user), None)
        is_admin = current_user_obj and current_user_obj["role"] == "admin"
        is_super_admin = current_user == "The G.O.A.T"

        # Request admin privilege
        if not is_admin:
            if "admin_request" not in st.session_state:
                st.session_state.admin_request = False
            if not st.session_state.admin_request:
                if st.button("Request Admin Access"):
                    st.session_state.admin_request = True
                    st.info("Admin access request sent. Waiting for approval from The G.O.A.T.")
            else:
                st.info("Admin access request pending approval.")

        # Super admin panel
        if is_super_admin:
            st.subheader("🛡️ Admin Approval Panel")
            pending_admins = [u for u in users if u["role"] != "admin" and u.get("admin_requested", False)]
            for u in users:
                if u["id"] != "The G.O.A.T" and not u["role"] == "admin":
                    if st.button(f"Approve admin for {u['id']}"):
                        u["role"] = "admin"
                        u.pop("admin_requested", None)
                        with open(USERS_FILE, "w") as f:
                            json.dump(users, f, indent=2)
                        st.success(f"{u['id']} is now an admin!")
            st.write("---")
    # My Profile: Users can edit their own info only
    if st.session_state.logged_in:
        user_obj = next((u for u in users if u["id"] == current_user), None)
        st.subheader("👤 My Profile")
        if user_obj:
            my_name = st.text_input("Full Name", value=user_obj["full_name"], key="my_name")
            my_email = st.text_input("Email", value=user_obj["email"], key="my_email")
            my_username = st.text_input("Username", value=user_obj["id"], key="my_username", disabled=True)
            my_new_pass = st.text_input("New Password", type="password", key="my_new_pass")
            my_confirm_pass = st.text_input("Confirm New Password", type="password", key="my_confirm_pass")
            photo_path = user_obj.get("photo")
            if photo_path and Path(photo_path).exists():
                st.image(photo_path, width=150, caption="Current Profile Photo")
            uploaded_photo = st.file_uploader("Upload a new profile photo (jpg/png)", type=["jpg", "jpeg", "png"], key="my_profile_photo_upload")
            if st.button("Save My Profile"):
                user_obj["full_name"] = my_name
                user_obj["email"] = my_email
                # Username cannot be changed by anyone
                # Update password if provided and matches
                if my_new_pass:
                    if my_new_pass == my_confirm_pass:
                        user_obj["password"] = hashlib.sha256(my_new_pass.encode()).hexdigest()
                    else:
                        st.error("Passwords do not match.")
                        st.stop()
                if uploaded_photo:
                    ext = uploaded_photo.name.split('.')[-1]
                    save_path = f"{PROFILE_PHOTO_DIR}/{user_obj['id']}.{ext}"
                    with open(save_path, "wb") as f:
                        f.write(uploaded_photo.read())
                    user_obj["photo"] = save_path
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f, indent=2)
                st.success("Profile updated!")
elif page == "Kick Out Users":
    # ------------------------
    # 🛑 Remove (Kick Out) Users
    # ------------------------
    st.subheader("🛑 Remove (Kick Out) Users")
    if is_admin or is_super_admin:
        kickable_users = [u for u in users if u["id"] != current_user and u["id"] != "The G.O.A.T"]
        if kickable_users:
            user_ids = [u["id"] for u in kickable_users]
            user_to_kick = st.selectbox("Select user to remove", user_ids, key="kick_user_select")
            if st.button("Kick Out User"):
                # Remove user from users.json
                users = [u for u in users if u["id"] != user_to_kick]
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f, indent=2)
                # Remove their entries from the time log
                st.session_state.df = st.session_state.df[st.session_state.df["user_id"] != user_to_kick]
                # Optionally, remove their profile photo
                import os
                for ext in ["jpg", "jpeg", "png"]:
                    photo_path = f"{PROFILE_PHOTO_DIR}/{user_to_kick}.{ext}"
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                st.success(f"User '{user_to_kick}' has been removed from the system (including their data and photo).")
        else:
            st.info("No users available to remove.")
    else:
        st.warning("Only admins can kick out users.")
elif page == "Profile Photo":
    # ------------------------
    # 🖼️ Profile Photo (Anyone can add or change their own profile photo)
    # ------------------------
    st.subheader("🖼️ Profile Photo")
    user_obj = next((u for u in users if u["id"] == current_user), None)
    photo_path = user_obj.get("photo") if user_obj else None
    if photo_path and Path(photo_path).exists():
        st.image(photo_path, width=150, caption="Current Profile Photo")
    uploaded_photo = st.file_uploader("Upload a new profile photo (jpg/png)", type=["jpg", "jpeg", "png"], key="profile_photo_upload")
    if uploaded_photo and user_obj:
        ext = uploaded_photo.name.split('.')[-1]
        save_path = f"{PROFILE_PHOTO_DIR}/{current_user}.{ext}"
        with open(save_path, "wb") as f:
            f.write(uploaded_photo.read())
        user_obj["photo"] = save_path
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
        st.success("Profile photo updated!")
        st.image(save_path, width=150, caption="New Profile Photo")
elif page == "Dashboard":
    # ------------------------
    # 📈 Dashboard: Detailed Analytics Over Date Range
    # ------------------------
    st.subheader("📈 Dashboard: Detailed Analytics")
    if is_admin or is_super_admin:
        user_options = ["All Users"] + [u["id"] for u in users]
        selected_user_id = st.selectbox("Select a user for dashboard analytics:", user_options, index=0)
    else:
        selected_user_id = current_user
    if selected_user_id == "All Users":
        # Aggregate all users' data with caching
        @st.cache_data(ttl=60)  # Cache for 1 minute
        def load_all_users_data(_users):
            all_dfs = []
            for u in _users:
                df = load_user_time_log(u["id"])
                if not df.empty:
                    all_dfs.append(df)
            if all_dfs:
                return pd.concat(all_dfs, ignore_index=True)
            else:
                return pd.DataFrame(columns=["Date", "Time", "What I Did", "user_id"])
        
        dash_df = load_all_users_data(users)
    else:
        dash_df = load_user_time_log(selected_user_id)
    if dash_df.empty:
        st.info("No data available for dashboard analytics.")
    else:
        dash_df = dash_df.copy()
        dash_df["Date"] = pd.to_datetime(dash_df["Date"], errors="coerce")
        dash_df = dash_df.dropna(subset=["Date"])
        
        # Check if we have any valid dates after cleaning
        if dash_df.empty:
            st.info("No valid date data available for dashboard analytics.")
        else:
            # Get min and max dates, with fallback to today if NaT
            min_date_series = dash_df["Date"].min()
            max_date_series = dash_df["Date"].max()
            
            # Handle NaT values
            if pd.isna(min_date_series) or pd.isna(max_date_series):
                st.info("No valid date data available for dashboard analytics.")
            else:
                min_date = min_date_series.date()
                max_date = max_date_series.date()
                
                # Ensure min_date is not greater than max_date
                if min_date > max_date:
                    min_date, max_date = max_date, min_date
                
                date_range = st.date_input("Select date range", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="dashboard_date_range")
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                else:
                    start_date = end_date = date_range
                if isinstance(start_date, tuple):
                    start_date = start_date[0]
                if isinstance(end_date, tuple):
                    end_date = end_date[0]
                mask = (dash_df["Date"].dt.date >= start_date) & (dash_df["Date"].dt.date <= end_date)
                period_df = dash_df[mask]
                if period_df.empty:
                    st.warning("No data in selected date range.")
                else:
                    # Ensure Duration column exists before any aggregation
                    @st.cache_data(ttl=300)  # Cache for 5 minutes
                    def time_to_minutes_cached(t, what_i_did):
                        try:
                            # Handle None or NaN values
                            if pd.isna(t) or t is None or str(t).strip() == "":
                                return 0
                            
                            t_lower = str(t).lower()
                            sleep_keywords = ["sleep", "slept", "sleeping", "i was sleeping", "nap", "bed", "rest"]
                            is_sleep = any(kw in t_lower for kw in sleep_keywords)
                            if "-" in t:
                                start, end = str(t).split("-")
                                s = datetime.strptime(start.strip(), "%H:%M")
                                e = datetime.strptime(end.strip(), "%H:%M")
                                # Handle overnight (end < start)
                                if e <= s:
                                    e = e + timedelta(days=1)
                                duration = int((e - s).total_seconds() / 60)
                                # Accept up to 16 hours (960 min) for sleep, 12 for others
                                if duration <= 0:
                                    return 0
                                if is_sleep:
                                    if duration > 960:
                                        return 0
                                else:
                                    if duration > 720:
                                        return 0
                                return duration
                            # If no time range, fallback
                            return 540 if is_sleep else 5
                        except Exception:
                            return 0
            
                    period_df["Duration"] = period_df.apply(lambda row: time_to_minutes_cached(row["Time"], row["What I Did"]), axis=1)
                    st.write(f"**Total Entries:** {len(period_df)}")
                    st.write(f"**Unique Users:** {period_df['user_id'].nunique()}")
                    # Per-user summary for admins
                    if (is_admin or is_super_admin) and selected_user_id == "All Users":
                        st.subheader("Per-User Summary Table")
                        user_summary = period_df.groupby("user_id").agg({"Duration": "sum", "What I Did": "count"}).rename(columns={"Duration": "Total Minutes", "What I Did": "Entry Count"})
                        st.dataframe(user_summary)
                    # --- existing dashboard analytics code below ---
                    # --- Combine Eating Activities ---here it acts as if i ate from 12 am to 1 am
                    def is_eating(activity):
                        eat_keywords = ["eat", "breakfast", "lunch", "dinner", "snack", "food", "meal"]
                        activity_lower = str(activity).lower()
                        return any(kw in activity_lower for kw in eat_keywords)
                    def is_sleep(activity):
                        sleep_keywords = ["sleep", "nap", "bed", "rest", "slept", "sleeping","I was sleeping"]
                        activity_lower = str(activity).lower()
                        return any(kw in activity_lower for kw in sleep_keywords)
                    # --- Remove 'ate' activity from dashboard analytics ---
                    period_df = period_df[~period_df["What I Did"].str.strip().str.lower().eq("ate")]
                    # --- Group similar activities by meaningful shared word ---
                    import re
                    # List of common stopwords to ignore in grouping
                    stopwords = set([
                        "i", "to", "the", "a", "an", "and", "of", "in", "on", "for", "with", "at", "by", "from", "up", "about", "into", "over", "after", "is", "it", "my", "me", "do", "did", "am", "are", "was", "were", "be", "been", "being", "have", "has", "had", "will", "would", "can", "could", "should", "shall", "may", "might", "must", "that", "this", "these", "those", "as", "but", "if", "or", "because", "so", "just", "not", "no", "yes", "you", "your", "we", "our", "us", "they", "their", "them", "he", "she", "his", "her", "him", "its", "who", "whom", "which", "what", "when", "where", "why", "how"
                    ])
                    
                    @st.cache_data(ttl=300)  # Cache for 5 minutes
                    def group_activity_meaningful_word(activity, period_df_sample):
                        activity_lower = str(activity).lower()
                        # Map any activity containing 'ate' (as a word or substring) to 'Eating'
                        if 'ate' in activity_lower.split() or 'ate' in activity_lower:
                            return "Eating"
                        if is_eating(activity):
                            return "Eating"
                        if is_sleep(activity):
                            return "Sleep"
                        # Custom grouping: 'track', 'field', 'school' all as 'School'
                        school_keywords = {"track", "field", "school"}
                        words = set(w for w in re.findall(r"\w+", activity_lower))
                        if words & school_keywords:
                            return "School"
                        # Custom grouping: 'home' as 'Homework'
                        if "home" in words:
                            return "Homework"
                        # Tokenize and filter out stopwords
                        words = set(w for w in re.findall(r"\w+", activity_lower) if w not in stopwords)
                        if not words:
                            words = set(re.findall(r"\w+", activity_lower))
                        # For performance, only check against a sample of activities
                        sample_activities = period_df_sample.head(50)["What I Did"].unique() if len(period_df_sample) > 50 else period_df_sample["What I Did"].unique()
                        for other in sample_activities:
                            other_lower = str(other).lower()
                            if other == activity:
                                continue
                            other_words = set(w for w in re.findall(r"\w+", other_lower) if w not in stopwords)
                            if words & other_words:
                                return sorted(words & other_words)[0].capitalize()
                        if words:
                            # Prevent 'Ate' as a group label
                            first_word = sorted(words)[0].capitalize()
                            if first_word == "Ate":
                                return "Eating"
                            return first_word
                        return activity.strip().capitalize()
                    
                    # Apply grouping with a sample of the dataframe for performance
                    period_df_sample = period_df.sample(n=min(100, len(period_df))) if len(period_df) > 100 else period_df
                    period_df["Activity Group"] = period_df["What I Did"].apply(lambda x: group_activity_meaningful_word(x, period_df_sample))
                    # --- Activity Breakdown Pie Chart ---
                    activity_summary = period_df.groupby("Activity Group")["Duration"].sum().sort_values(ascending=False)
                    # --- Custom labels for user based on activity totals ---
                    label_message = None
                    sleep_time = activity_summary.get("Sleep", 0)
                    homework_time = activity_summary.get("Homework", 0)
                    eating_time = activity_summary.get("Eating", 0)
                    watch_time = activity_summary.get("Watch", 0)
                    play_time = activity_summary.get("Play", 0)
                    max_activity = activity_summary.idxmax() if not activity_summary.empty else None
                    # Dynamic sleep threshold based on date range
                    num_days = len(period_df["Date"].dt.date.unique())
                    if num_days >= 365:
                        sleep_threshold = 36000  # 1 year
                    elif num_days >= 60:
                        sleep_threshold = 6000   # 2 months
                    elif num_days >= 28:
                        sleep_threshold = 3000   # 1 month
                    else:
                        sleep_threshold = 1000   # fallback for short ranges
                    # --- END: Dynamic sleep threshold ---
                    if homework_time >= max(watch_time, play_time):
                        label_message = "businessman! (Homework more than Play or Watch)"
                    elif (watch_time is not None and watch_time == activity_summary.max()) or (play_time is not None and play_time == activity_summary.max()):
                        label_message = "🚽 Toilet Cleaner! (Watched/Played more than anything)"
                    elif eating_time > sleep_time:
                        label_message = "🤪 Idiot! (Ate more than slept)"
                    if label_message:
                        st.subheader("Summary of Who You Are")
                        st.info(label_message)
                    if not activity_summary.empty:
                        st.subheader("Activity Breakdown")
                        fig1, ax1 = plt.subplots(figsize=(7, 5))
                        ax1.pie(activity_summary, labels=activity_summary.index, autopct="%1.1f%%", startangle=140)
                        ax1.axis("equal")
                        st.pyplot(fig1)
                    # --- Average time spent on key activities ---
                    key_activities = ["Sleep", "Eating", "Watch", "Homework", "Play"]
                    num_days = len(period_df["Date"].dt.date.unique())
                    st.subheader("Average Time Spent Per Day (Key Activities)")
                    avg_data = {}
                    for act in key_activities:
                        total = activity_summary.get(act, 0)
                        avg = total / num_days if num_days > 0 else 0
                        avg_data[act] = avg
                    avg_df = pd.DataFrame(list(avg_data.items()), columns=["Activity", "Average Minutes"])
                    st.table(avg_df.set_index("Activity"))
                    # --- Additional Dashboards ---
                    import seaborn as sns
                    import numpy as np
                    # 1. Bar chart: Total minutes per user (if admin and All Users)
                    if (is_admin or is_super_admin) and selected_user_id == "All Users":
                        st.subheader("Total Minutes Logged Per User")
                        user_minutes = period_df.groupby("user_id")["Duration"].sum().sort_values(ascending=False)
                        fig2, ax2 = plt.subplots(figsize=(8, 4))
                        sns.barplot(x=user_minutes.index, y=user_minutes.values, ax=ax2)
                        ax2.set_ylabel("Total Minutes")
                        ax2.set_xlabel("User ID")
                        st.pyplot(fig2)
                    # 2. Bar chart: Top 10 activities (all or per user)
                    st.subheader("Top 10 Activities by Time Spent")
                    top_acts = period_df.groupby("Activity Group")["Duration"].sum().sort_values(ascending=False).head(10)
                    fig3, ax3 = plt.subplots(figsize=(8, 4))
                    sns.barplot(x=top_acts.values, y=top_acts.index, ax=ax3, orient="h")
                    ax3.set_xlabel("Total Minutes")
                    ax3.set_ylabel("Activity Group")
                    st.pyplot(fig3)
                    # 3. Line chart: Time trend (total minutes per day)
                    st.subheader("Time Trend: Total Minutes Per Day")
                    trend_df = period_df.groupby(period_df["Date"].dt.date)["Duration"].sum().reset_index()
                    # Remove daily cap (no clip)
                    # Format dates for neat x-axis labels
                    trend_df["DateStr"] = pd.to_datetime(trend_df["Date"]).dt.strftime("%b %d, %Y")
                    fig4, ax4 = plt.subplots(figsize=(8, 4))
                    ax4.plot(trend_df["DateStr"], trend_df["Duration"], marker="o")
                    ax4.set_xlabel("Date")
                    ax4.set_ylabel("Total Minutes")
                    ax4.set_title("Total Minutes Logged Per Day")
                    plt.setp(ax4.get_xticklabels(), rotation=45, ha="right")
                    st.pyplot(fig4)
                    # 4. Heatmap: Activity vs. Day of Week
                    st.subheader("Activity Heatmap (Activity Group vs. Day of Week)")
                    # Special handling: set 'Bath' to 5 min, 'Eating' to 60 min per day
                    period_df = period_df.copy()
                    period_df.loc[period_df["Activity Group"] == "Bath", "Duration"] = 5
                    period_df.loc[period_df["Activity Group"] == "Eating", "Duration"] = 60
                    # Remove 'ate' from heatmap as well
                    period_df = period_df[~period_df["What I Did"].str.strip().str.lower().eq("ate")]
                    period_df["DayOfWeek"] = period_df["Date"].dt.day_name()
                    heatmap_df = period_df.pivot_table(index="Activity Group", columns="DayOfWeek", values="Duration", aggfunc="sum", fill_value=0)
                    # Reorder columns to standard week order
                    week_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    heatmap_df = heatmap_df.reindex(columns=week_order, fill_value=0)
                    fig5, ax5 = plt.subplots(figsize=(10, 6))
                    sns.heatmap(heatmap_df, annot=True, fmt=".0f", cmap="YlGnBu", ax=ax5)
                    ax5.set_xlabel("Day of Week")
                    ax5.set_ylabel("Activity Group")
                    st.pyplot(fig5)
                    # 5. Line chart: Time spent on Python per day
                    st.subheader("Time Spent on Python Per Day")
                    python_df = period_df[period_df["Activity Group"] == "Python"]
                    if not python_df.empty:
                        python_trend = python_df.groupby(python_df["Date"].dt.date)["Duration"].sum().reset_index()
                        python_trend["DateStr"] = pd.to_datetime(python_trend["Date"]).dt.strftime("%b %d, %Y")
                        fig_py, ax_py = plt.subplots(figsize=(8, 4))
                        ax_py.plot(python_trend["DateStr"], python_trend["Duration"], marker="o", color="orange")
                        ax_py.set_xlabel("Date")
                        ax_py.set_ylabel("Minutes Spent on Python")
                        ax_py.set_title("Time Spent on Python Per Day")
                        plt.setp(ax_py.get_xticklabels(), rotation=45, ha="right")
                        st.pyplot(fig_py)
                    else:
                        st.info("No Python activity found in selected date range.")
                    # Show table of all Python entries
                    if not python_df.empty:
                        st.subheader("Python Activity Log Entries")
                        st.dataframe(python_df[["Date", "Time", "What I Did", "Duration"]].sort_values(by=["Date", "Time"]))
