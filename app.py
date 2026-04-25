import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, timezone, timedelta
from PIL import Image
import os
import base64

# =========================
# ABSOLUTE FILE PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_FILE = os.path.join(BASE_DIR, "logo.png")
WALLPAPER_FILE = os.path.join(BASE_DIR, "wallpaper.png")

# =========================
# PAGE CONFIGURATION
# =========================
st.set_page_config(page_title="Bridges", page_icon=LOGO_FILE if os.path.exists(LOGO_FILE) else None, layout="wide")

# =========================
# DYNAMIC HTML & CSS INJECTION
# =========================
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Base CSS (Hide Headers & Set Font)
custom_style = """
    <style>
        /* 1. NUKE THE ENTIRE HEADER */
        [data-testid="stHeader"] {display: none !important; visibility: hidden !important;}
        .stAppDeployButton {display: none !important;}
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        
        /* 2. Force Apple Font (San Francisco) */
        html, body, [class*="css"], .stTextInput>label, .stMarkdown, p, h1, h2, h3, h4, h5, h6 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            color: #ffffff !important;
        }
"""

# If wallpaper.png exists, inject it as the background
if os.path.exists(WALLPAPER_FILE):
    img_base64 = get_base64_of_bin_file(WALLPAPER_FILE)
    custom_style += f"""
        /* 3. Inject Full-Screen Wallpaper */
        .stApp {{
            background-image: url("data:image/png;base64,{img_base64}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
        }}
        
        /* 4. Apple Glassmorphism Effect for Readability */
        .block-container {{
            background-color: rgba(10, 10, 10, 0.85) !important;
            padding: 2.5rem !important;
            border-radius: 20px !important;
            margin-top: 3rem !important;
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5) !important;
        }}
        
        /* Sidebar styling to match */
        [data-testid="stSidebar"] {{
            background-color: rgba(10, 10, 10, 0.95) !important;
        }}
    """
else:
    # Fallback to Pitch Black if the image isn't found
    custom_style += """
        .stApp {
            background-color: #000000 !important;
        }
    """

custom_style += "</style>"
st.markdown(custom_style, unsafe_allow_html=True)

# =========================
# MAIN APP DASHBOARD
# =========================
with st.sidebar:
    if os.path.exists(LOGO_FILE):
        img = Image.open(LOGO_FILE)
        st.image(img, use_container_width=True)

    st.markdown("---")
    
    st.markdown("### 🗂️ Active Modules")
    nav_selection = st.radio("Go to:", ["Data Formatter", "My Work", "Your Learning"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🚀 Coming Soon")
    st.button("Purchase Formats", disabled=True, use_container_width=True)
    st.button("Bank Statements", disabled=True, use_container_width=True)

# --- MODULE 1: DATA FORMATTER ---
if nav_selection == "Data Formatter":
    st.markdown("<h1 style='text-align: center;'>Bridges Data Engine</h1>", unsafe_allow_html=True)

    uf_col1, uf_col2, uf_col3 = st.columns([1, 1.5, 1])
    with uf_col2:
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
            melted["voucher no"] = melted["Party"].map(voucher_map)
            melted = melted.sort_values("voucher no").reset_index(drop=True)

            final_df = pd.DataFrame()
            final_df["SL"] = range(1, len(melted) + 1)
            final_df["voucher no"] = melted["voucher no"]
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

            karnataka_cities = [
                "bengaluru", "mysuru", "mangaluru", "hubballi", "dharwad", "belagavi",
                "kalaburagi", "ballari", "vijayapura", "shivamogga", "tumakuru", "raichur",
                "bidar", "hospet", "gadag", "udupi", "chitradurga", "hassan", "mandya",
                "kolar", "chikkaballapur", "ramanagara", "chikkamagaluru", "madikeri",
                "karwar", "bagalkot", "yadgir", "koppal", "haveri", "davanagere",
                "chamarajanagar", "kodagu", "bhadravati", "robertsonpet", "kolar gold fields",
                "sirsi", "dandeli", "ranebennur", "gokak", "jamkhandi", "sindhanur",
                "gangavati", "ilkal", "sagar"
            ]

            file_name_lower = uploaded_file.name.lower()
            is_karnataka_file = any(city in file_name_lower for city in karnataka_cities)

            if is_karnataka_file:
                final_df["Cgst"] = (total_tax / 2).round(2)
                final_df["SGST"] = (total_tax / 2).round(2)
                final_df["IGST"] = 0.0
            else:
                final_df["Cgst"] = 0.0
                final_df["SGST"] = 0.0
                final_df["IGST"] = total_tax.round(2)

            final_df["Total"] = (final_df["Rate per Qty excl.GST"] * final_df["Qty"]) + final_df["Cgst"] + final_df["SGST"] + final_df["IGST"]
            final_df["Total"] = final_df["Total"].round(2)

            st.subheader("Preview")
            st.dataframe(final_df.head(20), use_container_width=True)
            st.success(f"Rows Generated: {len(final_df)} | Tax Applied: {'CGST & SGST (Karnataka Detected)' if is_karnataka_file else 'IGST'}")

            output = BytesIO()
            final_df.to_excel(output, index=False)
            output.seek(0)

            dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 1])
            with dl_col2:
                st.download_button(
                    label="Download Excel",
                    data=output,
                    file_name="Bridges_Output.xlsx",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Error: {e}")

# --- MODULE 2: MY WORK ---
elif nav_selection == "My Work":
    st.markdown("<h1 style='text-align: center;'>My Work</h1>", unsafe_allow_html=True)
    st.info("This is your blank canvas! You can build out your own tools, add daily tasks, or write custom Python scripts in this section later.")

# --- MODULE 3: YOUR LEARNING ---
elif nav_selection == "Your Learning":
    st.markdown("<h1 style='text-align: center;'>Your Learning</h1>", unsafe_allow_html=True)
    st.info("Your personal knowledge hub. Keep track of what you learn about coding, new software, or business logic right here.")
