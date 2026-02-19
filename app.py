import streamlit as st
import pandas as pd
import sqlite3
import time
import base64

# ۱. اتصال به دیتابیس (نسخه ۲۷ بر پایه هسته ۲۶)
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# ایجاد ساختار جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل اختصاصی نسخه ۲۷: حذف مربع دور آیکون‌ها به صورت کاملاً امن
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stMarkdown, p, h1, h2, h3 { 
        direction: rtl; 
        text-align: right; 
    }
    
    /* حذف کادر و پس‌زمینه فقط از دکمه‌های عملیاتی بدون تاثیر روی تب‌ها */
    div[data-testid="column"] button, 
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    
    /* افکت ملایم هنگام بردن موس روی آیکون */
    div[data-testid="column"] button:hover {
        background-color: #f0f2f6 !important;
        border-radius: 50% !important;
    }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- تابع اصلی داشبورد ---
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
                        col_name, col_actions = st.columns([3, 1])
                        with col_name:
                            st.write(f"📄 {fl['file_name']}")
                        with col_actions:
                            a1, a2, a3 = st.columns(3)
                            # دکمه‌های آیکونی بدون کادر
                            if a1.button("🗑️", key=f"del_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit(); st.rerun()
                            if a2.button("🔗", key=f"lnk_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک تولید شد")
                                st.code(f"data:file;base64,{b64[:10]}...")
                            a3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- بخش آپلود مدارک ---
with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش مقصد:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    all_p = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not all_p.empty:
        c1, c2 = st.columns(2)
        with c1:
            s_p = st.selectbox("انتخاب پروژه:", all_p['name'].tolist())
            p_id = all_p[all_p['name']==s_p]['id'].values[0]
            fs = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={p_id}", conn)
            if not fs.empty:
                s_f = st.selectbox("انتخاب پوشه:", fs['name'].tolist())
                f_id = fs[fs['name']==s_f]['id'].values[0]
                up_file = st.file_uploader("فایل مورد نظر را انتخاب کنید")
                if st.button("🚀 ثبت نهایی فایل") and up_file:
                    c.execute("INSERT INTO project_files (proj_id,folder_id,file_name,file_blob) VALUES (?,?,?,?)",
                              (int(p_id), int(f_id), up_file.name, up_file.read()))
                    conn.commit(); st.success("فایل با موفقیت در پوشه ذخیره شد.")

with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    st.info("ساختار درختی و پروژه‌ها را از اینجا مدیریت کنید.")
    # (کدهای مدیریت لوکیشن مشابه نسخه ۲۶ در اینجا قرار دارد)
