import streamlit as st
import pandas as pd
import sqlite3
import time
import base64

# اتصال به دیتابیس (نسخه ۲۵)
DB_NAME = 'civil_pro_final_v25.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def get_shareable_link(file_name, file_blob):
    b64 = base64.b64encode(file_blob).decode()
    return f"data:application/octet-stream;base64,{b64}"

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل نهایی برای حذف کامل هرگونه کادر، مربع، سایه و خط دور دکمه‌ها
st.markdown("""
    <style>
    /* راست‌چین کردن کل صفحه */
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { 
        direction: rtl; 
        text-align: right; 
    }
    
    /* حذف مطلق کادر و مربع دور دکمه‌های آیکونی در داشبورد */
    div[data-testid="column"] button, 
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        border-width: 0 !important;
        outline: none !important;
        background-color: transparent !important;
        box-shadow: none !important;
        background: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: auto !important;
        height: auto !important;
        min-height: unset !important;
        line-height: unset !important;
    }

    /* حذف افکت تغییر رنگ هنگام نگه داشتن موس روی دکمه (Hover) */
    div[data-testid="column"] button:hover,
    div[data-testid="stDownloadButton"] button:hover,
    div[data-testid="column"] button:active,
    div[data-testid="column"] button:focus {
        background-color: transparent !important;
        border: none !important;
        color: #ff4b4b !important; /* فقط رنگ آیکون کمی تغییر کند */
        box-shadow: none !important;
    }

    /* تنظیم فاصله ردیف فایل */
    .file-row-custom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 5px 0;
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
                        # ایجاد دو ستون اصلی: آیکون‌ها در چپ (بسیار باریک) و نام در راست
                        c_icons, c_name = st.columns([0.5, 3])
                        
                        # نام فایل - کاملاً راست‌چین
                        c_name.markdown(f"<div style='text-align:right; font-size:15px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        
                        # آیکون‌ها - در منتهی‌الیه سمت چپ و بدون هیچ کادر یا مربعی
                        with c_icons:
                            ic1, ic2, ic3 = st.columns(3)
                            ic1.button("🗑️", key=f"del_{fl['id']}", help="حذف")
                            # اجرای دستور حذف اگر کلیک شد
                            if st.session_state.get(f"del_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit()
                                st.rerun()
                                
                            if ic2.button("🔗", key=f"lnk_{fl['id']}", help="کپی لینک"):
                                link = get_shareable_link(fl['file_name'], fl['file_blob'])
                                st.code(link[:25] + "...")
                                st.toast("لینک تولید شد")
                                
                            ic3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# سایر بخش‌ها (آپلود و تنظیمات) طبق منطق نسخه ۲۵ عمل می‌کنند.
