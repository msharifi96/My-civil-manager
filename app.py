import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل هوشمند برای تراز کردن عمودی و حذف کادرها
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    
    /* حذف کادر تمام دکمه‌ها */
    button, .stDownloadButton > button {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    /* تراز کردن نام فایل و آیکون‌ها در یک سطر عمودی */
    [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }

    /* نزدیک کردن آیکون‌ها به هم */
    [data-testid="column"] [data-testid="column"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: 35px !important;
        gap: 2px !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        direction: rtl;
    }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    with col_tree:
        st.subheader(f"آرشیو {label}")
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{label}'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"🔹 {prov['name']}"):
                cnts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        vls = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt['id']}", conn)
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vl['id']} AND p_type='{label}'", conn)
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"pj_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()

    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            st.info(f"🏢 شرکت: {pj['company']} | 📄 قرارداد: {pj['contract_no']}")
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj['id']}", conn)
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    for _, fl in files.iterrows():
                        # ایجاد سطر فایل
                        col_name, col_actions = st.columns([3, 1])
                        with col_name:
                            # استفاده از markdown برای کنترل بهتر فاصله عمودی متن
                            st.markdown(f"<p style='margin:0; padding:0;'>📄 {fl['file_name']}</p>", unsafe_allow_html=True)
                        with col_actions:
                            a1, a2, a3 = st.columns(3)
                            if a1.button("🗑️", key=f"del_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit(); st.rerun()
                            if a2.button("🔗", key=f"lnk_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک کپی شد")
                                st.code(f"data:file;base64,{b64[:10]}...")
                            a3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# بقیه بخش‌های آپلود و تنظیمات مشابه قبل...
# (برای طولانی نشدن پاسخ، بقیه کد نسخه ۲۶ رو اینجا تکرار نکردم ولی موقع کپی همون‌ها رو نگه دار)
