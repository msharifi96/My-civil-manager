import streamlit as st
import pandas as pd
import sqlite3
import base64
import os
import time

# ۱. تنظیمات حافظه محلی
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

# ۳. استایل راست‌چین و اسکریپت حذف خودکار پیغام
st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main { direction: rtl !important; text-align: right !important; }
    h1, h2, h3, h4, h5, h6, label, p, span, .stMarkdown { text-align: right !important; direction: rtl !important; }
    .file-row { display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid #eee; }
    .eye-icon { text-decoration: none; font-size: 20px; }
    </style>
    <script>
    const observer = new MutationObserver(function(mutations) {
        const alerts = document.querySelectorAll('.stAlert');
        alerts.forEach(function(alert) {
            setTimeout(function() { alert.style.display = 'none'; }, 1000);
        });
    });
    observer.observe(document.body, {childList: true, subtree: true});
    </script>
    """, unsafe_allow_html=True)

def temporary_msg(text):
    msg = st.success(text)
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
                                    # نمایش شماره قرارداد به جای نام پروژه
                                    d_label = f"📄 ق: {pj['contract_no']}" if pj['contract_no'] else f"🏗️ {pj['name']}"
                                    if st.button(d_label, key=f"pj_{label}_{pj['id']}", use_container_width=True):
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
                        file_data = None
                        if fl['file_path'] and os.path.exists(fl['file_path']):
                            with open(fl['file_path'], "rb") as f: file_data = f.read()
                        elif fl.get('file_blob'): file_data = fl['file_blob']
                        
                        if file_data:
                            b64 = base64.b64encode(file_data).decode()
                            ext = str(fl['file_name']).split('.')[-1].lower()
                            mime = "application/pdf" if ext=="pdf" else f"image/{ext}"
                            st.markdown(f'<div class="file-row"><span>📄 {fl["file_name"]}</span><a href="data:{mime};base64,{b64}" target="_blank" class="eye-icon">👁️</a></div>', unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود", "⚙️ تنظیمات"])
with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- بخش آپلود ---
with tabs[2]:
    st.subheader("📤 آپلود فایل")
    u_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="u_r")
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
            if st.button("🚀 ثبت نهایی", use_container_width=True):
                if up:
                    p_name = s_p.split(" - ")[1].replace(" ","_")
                    f_path = os.path.join(BASE_DIR, p_name, up.name)
                    if not os.path.exists(os.path.dirname(f_path)): os.makedirs(os.path.dirname(f_path))
                    with open(f_path, "wb") as f: f.write(up.getbuffer())
                    c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_path, file_blob) VALUES (?,?,?,?,?)", (int(p_id), int(f_id), up.name, f_path, up.getvalue()))
                    conn.commit()
                    temporary_msg("انجام شد")
                    st.rerun()

# --- بخش تنظیمات (دقیقا مطابق ساختار اصلی شما) ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_s")
    cl, cr = st.columns(2)
    with cl:
        st.subheader("📍 مدیریت محل")
        mode_l = st.radio("عملیات:", ["افزودن", "ویرایش", "حذف"], horizontal=True, key="l_op")
        if mode_l == "افزودن":
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="p_add")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان جدید:") 
                if st.button("ثبت استان"):
                    if np:
                        c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec))
                        conn.commit(); temporary_msg("انجام شد"); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="c_add")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان جدید:") 
                    if st.button("ثبت شهرستان"):
                        if nc:
                            c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id)))
                            conn.commit(); temporary_msg("انجام شد"); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    s_v = st.selectbox("محل:", ["--- جدید ---"] + vs['name'].tolist(), key="v_add")
                    if s_v == "--- جدید ---":
                        nv = st.text_input("نام محل جدید:")
                        t = st.selectbox("نوع:",["شهر","روستا"])
                        if st.button("ثبت محل"):
                            if nv:
                                c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id)))
                                conn.commit(); temporary_msg("انجام شد"); st.rerun()
    with cr:
        st.subheader("🏗️ مدیریت پروژه‌ها")
        mode_p = st.radio("عملیات پروژه:", ["افزودن", "حذف"], horizontal=True, key="p_op")
        if mode_p == "افزودن":
            v_l = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
            if not v_l.empty:
                sv = st.selectbox("انتخاب محل:", v_l['name'].tolist())
                pn = st.text_input("نام پروژه:")
                cp = st.text_input("شرکت:")
                cn = st.text_input("قرارداد:")
                if st.button("ثبت پروژه"):
                    vid = v_l[v_l['name']==sv]['id'].values[0]
                    c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(vid),pn,cp,cn,m_sec))
                    conn.commit(); temporary_msg("انجام شد"); st.rerun()
