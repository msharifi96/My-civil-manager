import streamlit as st
import pandas as pd
import sqlite3
import base64
import os

# ۱. تنظیمات مسیرها
BASE_DIR = "Engineering_Data"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# ۲. اتصال به دیتابیس
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('civil_pro_final_v26.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# اطمینان از وجود ستون file_path در جدول
try:
    c.execute("ALTER TABLE project_files ADD COLUMN file_path TEXT")
    conn.commit()
except:
    pass

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل اختصاصی برای دکمه "باز کردن"
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl !important; text-align: right !important; }
    .open-link {
        display: inline-block;
        padding: 8px 25px;
        background-color: #007bff;
        color: white !important;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
        margin-right: 10px;
    }
    .open-link:hover { background-color: #0056b3; }
    </style>
    """, unsafe_allow_html=True)

# --- تابع داشبورد (بخش اصلاح شده برای نمایش دکمه باز کردن) ---
def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    with col_tree:
        st.subheader(f"آرشیو {label}")
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(label,))
        for _, prov in provs.iterrows():
            with st.expander(f"🔹 {prov['name']}"):
                cnts = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(prov['id']),))
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        vls = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(cnt['id']),))
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql("SELECT * FROM projects WHERE loc_id=? AND p_type=?", conn, params=(int(vl['id']), label))
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"pj_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()
    
    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"🏗️ {pj['name']}")
            flds = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(pj['id']),))
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql("SELECT * FROM project_files WHERE folder_id=?", conn, params=(int(fld['id']),))
                    for _, fl in files.iterrows():
                        c_file, c_btn = st.columns([3, 1])
                        with c_file:
                            st.write(f"📄 {fl['file_name']}")
                        
                        with c_btn:
                            # منطق استخراج فایل (از حافظه یا دیتابیس)
                            file_data = None
                            if fl['file_path'] and os.path.exists(fl['file_path']):
                                with open(fl['file_path'], "rb") as f:
                                    file_data = f.read()
                            elif fl['file_blob']: # اگر در حافظه نبود، از دیتابیس بخواند
                                file_data = fl['file_blob']
                            
                            if file_data:
                                b64 = base64.b64encode(file_data).decode()
                                ext = fl['file_name'].split('.')[-1].lower()
                                mime = "application/pdf" if ext=="pdf" else f"image/{ext}"
                                # نمایش دکمه باز کردن
                                st.markdown(f'<a href="data:{mime};base64,{b64}" target="_blank" class="open-link">👁️ باز کردن</a>', unsafe_allow_html=True)
                            else:
                                st.write("⚠️ خطا در فایل")

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود", "⚙️ تنظیمات"])
with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- بخش آپلود (با ثبت همزمان در حافظه و دیتابیس برای اطمینان) ---
with tabs[2]:
    st.subheader("📤 آپلود فایل")
    u_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
        s_p = st.selectbox("پروژه:", all_p['disp'].tolist())
        p_id = all_p[all_p['disp']==s_p]['id'].values[0]
        fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_id),))
        if not fs.empty:
            s_f = st.selectbox("پوشه:", fs['name'].tolist())
            f_id = fs[fs['name']==s_f]['id'].values[0]
            up = st.file_uploader("انتخاب فایل")
            if st.button("ثبت نهایی", use_container_width=True):
                if up:
                    # ۱. ذخیره در حافظه داخلی
                    p_name = s_p.split(" - ")[1].replace(" ","_")
                    path = os.path.join(BASE_DIR, p_name)
                    if not os.path.exists
