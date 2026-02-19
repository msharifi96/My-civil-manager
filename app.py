import streamlit as st
import pandas as pd
import sqlite3
import time
import base64

# اتصال به دیتابیس نسخه ۲۲
conn = sqlite3.connect('civil_pro_v22.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

def show_done(text="✅ انجام شد"):
    msg = st.empty()
    msg.success(text)
    time.sleep(1)
    msg.empty()

# تابع تبدیل فایل به لینک دانلود (Base64) برای اشتراک‌گذاری سریع
def get_shareable_link(file_name, file_blob):
    b64 = base64.b64encode(file_blob).decode()
    return f"data:application/octet-stream;base64,{b64}"

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل RTL و دکمه‌ها
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; }
    .delete-btn>button { background-color: #ff4b4b !important; color: white !important; }
    .share-btn>button { background-color: #28a745 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- داشبورد با قابلیت حذف و اشتراک ---
def render_dash(label):
    col_t, col_v = st.columns([1, 2])
    with col_t:
        st.subheader(f"🗂️ آرشیو {label}")
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
                                    if st.button(f"🏗️ {pj['name']}", key=f"d_{label}_{pj['id']}"):
                                        st.session_state[f'act_{label}'] = pj.to_dict()

    with col_v:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            st.info(f"🏢 شرکت: {pj['company']} | 📄 قرارداد: {pj['contract_no']}")
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj['id']}", conn)
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}"):
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    for _, fl in files.iterrows():
                        c_name, c_down, c_link, c_del = st.columns([3, 1, 1, 1])
                        c_name.text(f"📄 {fl['file_name']}")
                        
                        # دکمه دانلود مستقیم
                        c_down.download_button("📥", fl['file_blob'], fl['file_name'], key=f"down_{fl['id']}")
                        
                        # دکمه تولید لینک اشتراک
                        if c_link.button("🔗", key=f"link_{fl['id']}", help="تولید لینک اشتراک"):
                            link = get_shareable_link(fl['file_name'], fl['file_blob'])
                            st.code(link, language=None)
                            st.toast("لینک تولید شد. می‌توانید آن را کپی کنید.")

                        # دکمه حذف فایل
                        if c_del.button("🗑️", key=f"del_{fl['id']}", help="حذف فایل"):
                            c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                            conn.commit()
                            show_done("فایل حذف شد.")
                            st.rerun()

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- بخش آپلود و تنظیمات (همان منطق v21 با دیتابیس جدید) ---
with tabs[2]:
    st.subheader("📤 بارگذاری مدارک")
    u_sec = st.radio("انتخاب بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not projs.empty:
        c1, c2 = st.columns(2)
        with c1:
            sel_p = st.selectbox("۱. انتخاب پروژه:", projs['name'].tolist())
            pj_row = projs[projs['name'] == sel_p].iloc[0]
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj_row['id']}", conn)
            if not flds.empty:
                sel_f = st.selectbox("۲. انتخاب پوشه:", flds['name'].tolist())
                fid = flds[flds['name'] == sel_f]['id'].values[0]
            else: st.warning("پوشه‌ای تعریف نشده است."); fid = None
        with c2:
            if fid:
                file = st.file_uploader("۳. انتخاب فایل")
                if st.button("🚀 ثبت نهایی"):
                    if file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                                  (int(pj_row['id']), int(fid), file.name, file.read()))
                        conn.commit(); show_done()

with tabs[3]:
    st.subheader("⚙️ تنظیمات و مدیریت")
    m_sec = st.radio("تنظیمات برای:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    st.divider()
    col_loc, col_proj = st.columns(2)
    with col_loc:
        st.subheader("📍 مدیریت محل")
        all_provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{m_sec}'", conn)
        existing_p = st.selectbox("استان:", ["--- جدید ---"] + all_provs['name'].tolist())
        if existing_p == "--- جدید ---":
            new_p = st.text_input("نام استان جدید:")
            if st.button("ثبت استان"):
                if new_p: c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,0)", (new_p, "استان", m_sec)); conn.commit(); st.rerun()
        else:
            p_id = all_provs[all_provs['name'] == existing_p]['id'].values[0]
            all_city = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={p_id}", conn)
            existing_c = st.selectbox("شهرستان:", ["--- جدید ---"] + all_city['name'].tolist())
            if existing_c == "--- جدید ---":
                new_c = st.text_input("نام شهرستان جدید:")
                if st.button("ثبت شهرستان"):
                    if new_c: c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (new_c, "شهرستان", m_sec, int(p_id))); conn.commit(); st.rerun()
            else:
                c_id = all_city[all_city['name'] == existing_c]['id'].values[0]
                all_vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={c_id}", conn)
                existing_v = st.selectbox("شهر یا روستا:", ["--- جدید ---"] + all_vills['name'].tolist())
                if existing_v == "--- جدید ---":
                    tp = st.selectbox("نوع:", ["شهر 🏙️", "روستا 🏡"])
                    new_v = st.text_input("نام محل:")
                    if st.button("ثبت محل"):
                        if new_v: c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (f"{tp} {new_v}", "شهر یا روستا", m_sec, int(c_id))); conn.commit(); st.rerun()

    with col_proj:
        st.subheader("🏗️ تعریف پروژه و پوشه")
        vills_list = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type='{m_sec}'", conn)
        if not vills_list.empty:
            target_v = st.selectbox("محل پروژه:", vills_list['name'].tolist())
            v_id = vills_list[vills_list['name'] == target_v]['id'].values[0]
            p_name = st.text_input("نام پروژه:")
            p_comp = st.text_input("نام شرکت:")
            p_cont = st.text_input("شماره قرارداد:")
            if st.button("ثبت پروژه"):
                if p_name: c.execute("INSERT INTO projects (loc_id, name, company, contract_no, p_type) VALUES (?,?,?,?,?)", (int(v_id), p_name, p_comp, p_cont, m_sec)); conn.commit(); st.rerun()
        
        st.divider()
        all_pjs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{m_sec}'", conn)
        if not all_pjs.empty:
            sel_pj_f = st.selectbox("انتخاب پروژه برای پوشه‌بندی:", all_pjs['name'].tolist())
            new_fld = st.text_input("نام پوشه جدید:")
            if st.button("ایجاد پوشه"):
                if new_fld: c.execute("INSERT INTO project_folders (proj_id, name, p_type) VALUES (?,?,?)", (int(all_pjs[all_pjs['name']==sel_pj_f]['id'].values[0]), new_fld, m_sec)); conn.commit(); st.rerun()
