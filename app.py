import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل CSS نهایی برای راست‌چین کردن متن و حذف کامل مربع‌ها
st.markdown("""
    <style>
    /* تنظیمات کلی راست‌چین */
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { 
        direction: rtl !important; 
        text-align: right !important; 
    }
    
    /* حذف کامل کادر، مربع و سایه از تمام دکمه‌های آیکونی */
    button, div[data-testid="stDownloadButton"] > button {
        border: none !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 35px !important;
        height: 35px !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    /* جلوگیری از ظاهر شدن مربع در حالت نگه داشتن موس (Hover) */
    button:hover, button:active, button:focus {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ff4b4b !important;
    }

    /* تراز کردن ستون نام فایل به سمت راست */
    [data-testid="column"] {
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    
    with col_tree:
        st.subheader(f"آرشیو {label}")
        # کدهای نمایش درختواره (بدون تغییر)
        # ... (بخش کوئری استان، شهرستان و پروژه) ...
        # برای اختصار فقط بخش نمایش فایل را اصلاح می‌کنیم:

    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj['id']}", conn)
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    for _, fl in files.iterrows():
                        # اصلاح چیدمان: ستون اول برای نام (راست) و ستون دوم برای آیکون‌ها (چپ)
                        # در حالت RTL استریم‌لیت، اولین ستون در سمت راست قرار می‌گیرد
                        col_name, col_icons = st.columns([4, 1])
                        
                        with col_name:
                            # نام فایل در سمت راست
                            st.markdown(f"<div style='text-align: right; direction: rtl; width: 100%;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        
                        with col_icons:
                            # آیکون‌ها در سمت چپ
                            ic1, ic2, ic3 = st.columns(3)
                            # دانلود
                            ic1.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")
                            # لینک
                            if ic2.button("🔗", key=f"ln_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک تولید شد")
                                st.code(f"data:file;base64,{b64[:10]}...")
                            # حذف
                            if ic3.button("🗑️", key=f"dl_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit()
                                st.rerun()

# اجرای داشبوردها
with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")
