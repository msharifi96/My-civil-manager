import streamlit as st
import pandas as pd
import sqlite3
import base64
import os

# ۱. تنظیمات حافظه داخلی (پوشه ذخیره‌سازی فایل‌ها)
BASE_DIR = "Engineering_Data"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# ۲. اتصال به دیتابیس (فقط برای ذخیره مسیرها و اطلاعات متنی)
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('civil_pro_final_v26.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# ایجاد جداول پایه
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_path TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل راست‌چین و دکمه اختصاصی "باز کردن"
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .block-container { direction: rtl !important; text-align: right !important; font-family: 'Segoe UI', Tahoma, sans-serif; }
    h1, h2, h3, h4, h5, h6, label, .stMarkdown, p, span { text-align: right !important; direction: rtl !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl !important; display: flex !important; justify-content: flex-start !important; }
    .open-btn {
        display: inline-block;
        padding: 6px 20px;
        background-color: #ff4b4b;
        color: white !important;
        text-decoration: none;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        transition: 0.3s;
    }
    .open-btn:hover { background-color: #e63939; box-shadow: 0px 2px 5px rgba(0,0,0,0.2); }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود در حافظه", "📍 تنظیمات سیستم"])

# --- تابع داشبورد با دکمه "باز کردن" ---
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
                                    btn_txt = f"📄 ق: {pj['contract_no']}" if pj['contract_no'] else f"🏗️ {pj['name']}"
                                    if st.button(btn_txt, key=f"pj_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()
    
    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"🏗️ {pj['name']}")
            st.info(f"🏢 شرکت: {pj['company']} | 📄 قرارداد: {pj['contract_no']}")
            
            flds = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(pj['id']),))
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql("SELECT * FROM project_files WHERE folder_id=?", conn, params=(int(fld['id']),))
                    for _, fl in files.iterrows():
                        c_name, c_open = st.columns([4, 1.2])
                        with c_name:
                            st.write(f"📄 {fl['file_name']}")
                        with c_open:
                            if fl['file_path'] and os.path.exists(fl['file_path']):
                                with open(fl['file_path'], "rb") as f:
                                    data = f.read()
                                    ext = fl['file_name'].split('.')[-1].lower()
                                    b64 = base64.b64encode(data).decode()
                                    mime = "application/pdf" if ext=="pdf" else f"image/{ext}"
                                    href = f'<a href="data:{mime};base64,{b64}" target="_blank" class="open-btn">👁️ باز کردن</a>'
                                    st.markdown(href, unsafe_allow_html=True)
                            else:
                                st.write("❌ فایل موجود نیست")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- ۳. بخش آپلود فایل در حافظه داخلی ---
with tabs[2]:
    st.subheader("📤 آپلود مستقیم در حافظه دستگاه")
    u_sec = st.radio("انتخاب بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_local_radio")
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - پروژه: {x['name']}", axis=1)
        s_p_d = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist(), key="up_pj_select")
        p_row = all_p[all_p['disp']==s_p_d].iloc[0]
        
        fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_row['id']),))
        if not fs.empty:
            s_f = st.selectbox("انتخاب پوشه:", fs['name'].tolist(), key="up_fld_select")
            f_id = fs[fs['name']==s_f]['id'].values[0]
            
            up_file = st.file_uploader("انتخاب فایل (PDF یا تصویر)", key="main_uploader")
            if st.button("🚀 ذخیره در حافظه محلی", use_container_width=True):
                if up_file:
                    # ایجاد مسیر فیزیکی در هارد
                    proj_path = os.path.join(BASE_DIR, str(p_row['name']).replace(" ", "_"), s_f.replace(" ", "_"))
                    if not os.path.exists(proj_path): os.makedirs(proj_path)
                    
                    full_path = os.path.join(proj_path, up_file.name)
                    with open(full_path, "wb") as f:
                        f.write(up_file.getbuffer())
                    
                    c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_path) VALUES (?,?,?,?)", 
                              (int(p_row['id']), int(f_id), up_file.name, full_path))
                    conn.commit()
                    st.success("فایل با موفقیت در حافظه داخلی ذخیره شد."); st.rerun()
        else:
            st.warning("⚠️ ابتدا در تنظیمات برای این پروژه پوشه بسازید.")
    else:
        st.info("پروژه‌ای یافت نشد.")

# --- ۴. تنظیمات سیستم (مدیریت محل، پروژه و حذف) ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_set_main")
    cl, cr = st.columns(2)
    
    with cl:
        st.subheader("📍 مدیریت محل")
        mode_l = st.radio("عملیات:", ["افزودن", "ویرایش", "حذف"], horizontal=True, key="l_op")
        if mode_l == "افزودن":
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="p_add")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان جدید:", placeholder="مثلاً: بوشهر", key="in_p") 
                if st.button("ثبت استان"):
                    if np: c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec)); conn.commit(); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="c_add")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان جدید:", placeholder="مثلاً: عسلویه", key="in_c") 
                    if st.button("ثبت شهرستان"):
                        if nc: c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id))); conn.commit(); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    s_v = st.selectbox("محل:", ["--- جدید ---"] + vs['name'].tolist(), key="v_add")
                    if s_v == "--- جدید ---":
                        nv = st.text_input("نام محل جدید:", placeholder="نام شهر یا روستا...", key="in_v")
                        t = st.selectbox("نوع:",["شهر","روستا"])
                        if st.button("ثبت محل"):
                            if nv: c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id))); conn.commit(); st.rerun()

    with cr:
        st.subheader("🏗️ مدیریت پروژه‌ها")
        mode_p = st.radio("عملیات پروژه:", ["افزودن", "حذف"], horizontal=True, key="p_op")
        if mode_p == "افزودن":
            v_l = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
            if not v_l.empty:
                sv = st.selectbox("انتخاب محل:", v_l['name'].tolist(), key="pj_loc")
                pn = st.text_input("نام پروژه:", placeholder="مثلاً: فاز ۱ پارس جنوبی", key="pj_n")
                cp = st.text_input("شرکت:", placeholder="شرکت نفت...", key="pj_c")
                cn = st.text_input("قرارداد:", placeholder="۱۴۰۳/۰۰۱", key="pj_cont")
                if st.button("ثبت پروژه"):
                    vid = v_l[v_l['name']==sv]['id'].values[0]
                    c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(vid),pn,cp,cn,m_sec)); conn.commit(); st.rerun()
            
            st.divider()
            all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
            if not all_p.empty:
                st.write("### 📁 ایجاد پوشه")
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                spj = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist(), key="f_p")
                nf = st.text_input("نام پوشه جدید:", placeholder="مثلاً: صورت‌وضعیت‌ها", key="f_n") 
                if st.button("ایجاد پوشه"):
                    if nf:
                        pid = all_p[all_p['disp']==spj]['id'].values[0]
                        c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec)); conn.commit(); st.rerun()
        
        elif mode_p == "حذف":
            all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
            if not all_p.empty:
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                target = st.selectbox("پروژه برای حذف:", all_p['disp'].tolist())
                if st.button("حذف کامل پروژه و فایل‌ها"):
                    pid = all_p[all_p['disp']==target]['id'].values[0]
                    # در اینجا می‌توان کد حذف فیزیکی پوشه را هم اضافه کرد
                    c.execute("DELETE FROM project_files WHERE proj_id=?", (int(pid),))
                    c.execute("DELETE FROM project_folders WHERE proj_id=?", (int(pid),))
                    c.execute("DELETE FROM projects WHERE id=?", (int(pid),))
                    conn.commit(); st.rerun()
