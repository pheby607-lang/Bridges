import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image
import json
import os
import hashlib

# =========================
# PAGE CONFIGURATION & LOGO
# =========================
st.set_page_config(page_title="Bridges Formatter", page_icon="logo.png", layout="wide")

AUTH_FILE = "secure_auth.json"

# =========================
# ENCRYPTION ENGINE
# =========================
def encrypt_text(text):
    """Encrypts passwords and security answers using SHA-256 hashing"""
    return hashlib.sha256(str(text).encode()).hexdigest()

def load_auth_data():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    return None

def save_auth_data(user_id, password, security_answer):
    data = {
        "user_id": user_id,
        "password_hash": encrypt_text(password),
        "security_answer_hash": encrypt_text(security_answer.lower().strip())
    }
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f)

# Initialize Session States
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "reset_mode" not in st.session_state:
    st.session_state["reset_mode"] = False

# =========================
# AUTHENTICATION UI
# =========================
auth_data = load_auth_data()

# Show Logo at the top of all pages
try:
    img = Image.open("logo.png")
    st.image(img, width=250)
except FileNotFoundError:
    pass

if not auth_data:
    # -------------------------
    # 1. FIRST TIME SETUP
    # -------------------------
    st.title("Admin Account Setup")
    st.info("No account detected. Please create your secure login for Bridges.")
    
    with st.form("setup_form"):
        new_id = st.text_input("Create Login ID")
        new_pass = st.text_input("Create Password", type="password")
        st.markdown("---")
        st.write("**Account Recovery Setup**")
        st.caption("Since this is a secure offline app, you cannot reset your password via email. You MUST remember this answer to reset your password.")
        security_q = st.text_input("Security Question: What city were you born in?")
        
        submitted = st.form_submit_button("Create & Encrypt Account")
        if submitted:
            if new_id and new_pass and security_q:
                save_auth_data(new_id, new_pass, security_q)
                st.success("Account securely created! Please refresh the app to login.")
            else:
                st.error("Please fill out all fields.")
    st.stop()

elif not st.session_state["logged_in"]:
    # -------------------------
    # 2. LOGIN OR RESET PAGE
    # -------------------------
    if not st.session_state["reset_mode"]:
        # Standard Login
        st.title("🔒 Secure Login")
        with st.form("login_form"):
            login_id = st.text_input("Login ID")
            login_pass = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")
            
            if login_btn:
                if login_id == auth_data["user_id"] and encrypt_text(login_pass) == auth_data["password_hash"]:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid Login ID or Password.")
                    
        if st.button("Forgot Password?"):
            st.session_state["reset_mode"] = True
            st.rerun()
        st.stop()
        
    else:
        # Reset Password Mode
        st.title("🔄 Reset Password")
        with st.form("reset_form"):
            reset_id = st.text_input("Confirm Login ID")
            reset_answer = st.text_input("Security Question: What city were you born in?", type="password")
            new_pass = st.text_input("New Password", type="password")
            
            reset_btn = st.form_submit_button("Reset Password")
            
            if reset_btn:
                if reset_id == auth_data["user_id"] and encrypt_text(reset_answer.lower().strip()) == auth_data["security_answer_hash"]:
                    save_auth_data(reset_id, new_pass, reset_answer)
                    st.success("Password successfully reset!")
                    st.session_state["reset_mode"] = False
                    st.rerun()
                else:
                    st.error("Incorrect Login ID or Security Answer.")
                    
        if st.button("Back to Login"):
            st.session_state["reset_mode"] = False
            st.rerun()
        st.stop()

# =========================
# MAIN APP (ONLY ACCESSIBLE IF LOGGED IN)
# =========================
st.title("Bridges - Data Formatter")

# Add a logout button to the sidebar
with st.sidebar:
    st.write(f"Logged in as: **{auth_data['user_id']}**")
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None)

        ist = timezone(timedelta(hours=5, minutes=30))
        today_ist = datetime.now(ist).strftime('%d/%m/%Y')

        header_1 = df_raw.iloc[0]
        header_2 = df_raw.iloc[1]

        combined_headers = []

        for h1, h2 in zip(header_1, header_2):
            party = str(h1).strip()
            store = str(h2).strip()

            if store and store.lower() != "nan":
                combined_headers.append(f"{party} {store}".strip())
            else:
                combined_headers.append("")

        df = df_raw[2:].reset_index(drop=True)
        df.columns = combined_headers

        df = df.loc[:, df.columns != ""]
        df = df.loc[:, ~df.columns.duplicated()]

        product_col = None
        for col in df.columns:
            if "system" in col.lower() or "product" in col.lower() or "item" in col.lower():
                product_col = col
                break
        
        if product_col is None:
            product_col = df.columns[1] 

        billing_col = None
        gst_col = None
        
        for col in df.columns:
            lower_col = col.lower()
            if "billing" in lower_col:
                billing_col = col
            elif "gst" in lower_col and gst_col is None:
                gst_col = col

        if billing_col is None:
            billing_col = df.columns[3] 
            
        if gst_col is None:
            gst_col = df.columns[2]

        billing_idx = list(df.columns).index(billing_col)
        raw_store_cols = df.columns[billing_idx + 1:]
        store_cols = [col for col in raw_store_cols if "total" not in str(col).lower()]

        melted = df.melt(
            id_vars=[product_col, billing_col, gst_col],
            value_vars=store_cols,
            var_name="Party",
            value_name="Qty"
        )

        melted["Qty"] = melted["Qty"].astype(str).str.replace(r"[^\d.]", "", regex=True)
        melted["Qty"] = pd.to_numeric(melted["Qty"], errors="coerce")
        melted = melted.dropna(subset=["Qty"])

        voucher_map = {party: i + 1 for i, party in enumerate(store_cols)}

        melted = melted.sort_values("Party").reset_index(drop=True)

        final_df = pd.DataFrame()

        final_df["SL"] = range(1, len(melted) + 1)
        final_df["voucher no"] = melted["Party"].map(voucher_map)
        final_df["voucher date"] = today_ist
        final_df["Party name"] = melted["Party"]
        final_df["Product"] = melted[product_col]
        final_df["Qty"] = melted["Qty"]
        
        raw_gst = melted[gst_col].astype(str).str.replace(r"[^\d.]", "", regex=True)
        raw_gst = raw_gst.replace("", "0")
        gst_numeric = pd.to_numeric(raw_gst, errors="coerce").fillna(0)
        
        gst_percentage = gst_numeric.apply(lambda x: x * 100 if x < 1 and x > 0 else x).round().astype(int)
        final_df["GST %"] = gst_percentage

        billing_price = pd.to_numeric(
            melted[billing_col].astype(str).str.replace(r"[^\d.]", "", regex=True),
            errors="coerce"
        ).fillna(0)
        
        rates = []
        for bp, gst in zip(billing_price, final_df["GST %"]):
            if gst == 5:
                rates.append(bp / 1.05)
            elif gst == 12:
                rates.append(bp / 1.12)
            elif gst == 18:
                rates.append(bp / 1.18)
            elif gst == 28:
                rates.append(bp / 1.28)
            elif gst == 40:
                rates.append(bp / 1.40)
            else:
                rates.append(bp / (1 + (gst / 100)))
                
        final_df["Rate per Qty excl.GST"] = pd.Series(rates).round(2)

        total_tax = final_df["Rate per Qty excl.GST"] * (final_df["GST %"] / 100) * final_df["Qty"]

        karnataka_keywords = [
            "karnataka", "bangalore", "bengaluru", "hoskote", "nelamangala", 
            "k r puram", "frazer town", "sahakaranagar", "kalyan nagar", 
            "vidyaranyapura", "kammanahalli", "jeevan bima nagar", 
            "kempapura", "t c palya", "kannamangala", "hal"
        ]

        def calculate_taxes(row):
            party_name = str(row["Party name"]).lower()
            tax_amt = row["_total_tax"]
            
            is_karnataka = any(kw in party_name for kw in karnataka_keywords)
            
            if is_karnataka:
                return pd.Series([tax_amt / 2, tax_amt / 2, 0])
            else:
                return pd.Series([0, 0, tax_amt])

        temp_df = pd.DataFrame({"Party name": final_df["Party name"], "_total_tax": total_tax})
        final_df[["Cgst", "SGST", "IGST"]] = temp_df.apply(calculate_taxes, axis=1).round(2)

        final_df["Total"] = (final_df["Rate per Qty excl.GST"] * final_df["Qty"]) + final_df["Cgst"] + final_df["SGST"] + final_df["IGST"]
        final_df["Total"] = final_df["Total"].round(2)

        st.subheader("Preview")
        st.dataframe(final_df.head(20))
        st.success(f"Rows Generated: {len(final_df)}")

        output = BytesIO()
        final_df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            label="Download Excel",
            data=output,
            file_name="Bridges_Formatted_Output.xlsx"
        )

    except Exception as e:
        st.error(f"Error: {e}")