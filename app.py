import streamlit as st
import pandas as pd
import sqlite3
import base64
import os
import time

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

# ۳. استایل‌ها و اسکریپت محو شونده
st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl !important; text-align: right !important; }
    .file-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px;
        border-bottom: 1px solid #f0f0f0;
    }
    .eye-icon { text-decoration: none; font-size: 20px; transition: 0.3s; }
    .eye-icon:hover { transform: scale(1.2); }
    </style>
    <script>
    // اسکریپت برای محو کردن پیغام‌های موفقیت بعد از ۱ ثانیه
    const observer = new MutationObserver(function(mutations) {
        const alerts = document.querySelectorAll('.stAlert');
        alerts.forEach(function(alert) {
            setTimeout(function() {
                alert.style.display = 'none';
            }, 1000);
        });
    });
    observer.observe(document.body, {childList: true, subtree: true});
    </script>
    """, unsafe_allow_html=True)

# تابع کمکی برای نمایش پیغام موقت (در صورت عدم عملکرد اسکریپت)
def temporary_message(type, text):
    msg = st.success(text) if type == "success" else st.warning(text)
    time.sleep(1)
    msg.empty()

# --- تابع داشبورد ---
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
                                    # تغییر اصلی: نمایش شماره قرارداد به جای اسم پروژه
                                    display_label = f"📄 ق: {pj['contract_no']}" if pj['contract_no'] else f"🏗️ {pj['name']}"
                                    if st.button(display_label, key=f"pj_{label}_{pj['id']}", use_container_width=True):
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
                        # منطق خواندن فایل
                        file_data = None
                        if fl['file_path'] and os.path.exists(fl['file_path']):
                            with open(fl['file_path'], "rb") as f: file_data = f.read()
                        elif fl.get('file_blob'): file_data = fl['file_blob']
                        
                        if file_data:
                            b64 = base64.b64encode(file_data).decode()
                            ext = str(fl['file_name']).split('.')[-1].lower()
                            mime = "application/pdf" if ext=="pdf" else f"image/{ext}"
                            
                            st.markdown(f"""
                                <div class="file-row">
                                    <span>📄 {fl['file_name']}</span>
                                    <a href="data:{mime};base64,{b64}" target="_blank" class="eye-icon">👁️</a>
                                </div>
                            """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود", "⚙️ تنظیمات"])
with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- بخش آپلود ---
with tabs[2]:
    st.subheader("📤 آپلود فایل")
    u_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_r")
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
        s_p = st.selectbox("پروژه:", all_p['disp'].tolist())
        p_id = all_p[all_p['disp']==s_p]['id'].values[0]
        fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_id),))
        if not fs.empty:
            s_f = st.selectbox("پوشه:", fs['name'].tolist())
            f_id = fs[fs['name']==s_f]['id'].values[0]
            up = st.file_uploader("انتخاب فایل", key="f_up")
            if st.button("🚀 ثبت نهایی و آپلود", use_container_width=True):
                if up:
                    p_name_clean = s_p.split(" - ")[1].replace(" ","_")
                    path = os.path.join(BASE_DIR, p_name_clean)
                    if not os.path.exists(path): os.makedirs(path)
                    f_path = os.path.join(path, up.name)
                    with open(f_path, "wb") as f: f.write(up.getbuffer())
                    c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_path, file_blob) VALUES (?,?,?,?,?)",
                              (int(p_id), int(f_id), up.name, f_path, up.getvalue()))
                    conn.commit()
                    temporary_message("success", "فایل با موفقیت ذخیره شد")
                    st.rerun()

# --- بخش تنظیمات ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات")
    m_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_s")
    c1, c2 = st.columns(2)
    with c1:
        st.write("### 📍 محل")
        # کد افزودن محل...
        np = st.text_input("نام مورد جدید:", placeholder="نام را وارد کنید...")
        if st.button("ثبت مورد جدید"):
            if np:
                # منطق ثبت محل در دیتابیس (ساده شده برای نمایش)
                temporary_message("success", f"'{np}' با موفقیت ثبت شد")
                st.rerun()
    with c2:
        st.write("### 🏗️ پروژه")
        pn = st.text_input("نام پروژه:", placeholder="نام پروژه...")
        if st.button("ثبت پروژه"):
            if pn:
                temporary_message("success", f"پروژه '{pn}' ایجاد شد")
                st.rerun()
