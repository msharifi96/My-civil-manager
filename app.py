import streamlit as st
import pandas as pd
import sqlite3
import time

# اتصال به دیتابیس نسخه ۲۱ برای اعمال ساختار جدید قراردادها
conn = sqlite3.connect('civil_pro_v21.db', check_same_thread=False)
c = conn.cursor()

# ایجاد ساختار جداول با فیلدهای قرارداد
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('''CREATE TABLE IF NOT EXISTS projects 
             (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)''')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

def show_done(text="✅ با موفقیت ثبت شد"):
    msg = st.empty()
    msg.success(text)
    time.sleep(1.2)
    msg.empty()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل RTL
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #004a99; color: white; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- توابع داشبورد و آپلود (به‌روز شده برای نمایش اطلاعات قرارداد) ---
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
                files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                    for _, fl in files.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"📄 {fl['file_name']}")
                        c2.download_button("📥", fl['file_blob'], fl['file_name'], key=f"f_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- بخش آپلود ---
with tabs[2]:
    st.subheader("📤 بارگذاری مدارک")
    u_sec = st.radio("انتخاب بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_sec")
    projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not projs.empty:
        c1, c2 = st.columns(2)
        with c1:
            sel_p = st.selectbox("۱. انتخاب پروژه:", projs['name'].tolist())
            pj_row = projs[projs['name'] == sel_p].iloc[0]
            st.caption(f"شرکت: {pj_row['company']} | قرارداد: {pj_row['contract_no']}")
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj_row['id']}", conn)
            if not flds.empty:
                sel_f = st.selectbox("۲. انتخاب پوشه:", flds['name'].tolist())
                fid = flds[flds['name'] == sel_f]['id'].values[0]
            else: st.warning("پوشه‌ای تعریف نشده است."); fid = None
        with c2:
            if fid:
                file = st.file_uploader("۳. انتخاب فایل", key="file_up")
                if st.button("🚀 ثبت نهایی"):
                    if file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                                  (int(pj_row['id']), int(fid), file.name, file.read()))
                        conn.commit(); show_done()
    else: st.info("ابتدا در تنظیمات پروژه بسازید.")

# --- بخش تنظیمات هوشمند (جلوگیری از تکرار) ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات و مدیریت قراردادها")
    m_sec = st.radio("تنظیمات برای:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="set_sec")
    st.divider()
    
    col_loc, col_proj = st.columns(2)
    
    with col_loc:
        st.subheader("📍 مدیریت محل")
        # مرحله ۱: استان
        all_provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{m_sec}'", conn)
        existing_p = st.selectbox("انتخاب استان موجود:", ["--- جدید ---"] + all_provs['name'].tolist())
        
        if existing_p == "--- جدید ---":
            new_p = st.text_input("نام استان جدید:")
            if st.button("ثبت استان جدید"):
                if new_p and new_p not in all_provs['name'].values:
                    c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,0)", (new_p, "استان", m_sec))
                    conn.commit(); st.rerun()
        
        # مرحله ۲: شهرستان
        if existing_p != "--- جدید ---":
            p_id = all_provs[all_provs['name'] == existing_p]['id'].values[0]
            all_city = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={p_id}", conn)
            existing_c = st.selectbox("انتخاب شهرستان:", ["--- جدید ---"] + all_city['name'].tolist())
            
            if existing_c == "--- جدید ---":
                new_c = st.text_input("نام شهرستان جدید:")
                if st.button("ثبت شهرستان جدید"):
                    if new_c and new_c not in all_city['name'].values:
                        c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (new_c, "شهرستان", m_sec, int(p_id)))
                        conn.commit(); st.rerun()
            
            # مرحله ۳: شهر یا روستا
            if existing_c != "--- جدید ---":
                c_id = all_city[all_city['name'] == existing_c]['id'].values[0]
                all_vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={c_id}", conn)
                existing_v = st.selectbox("انتخاب شهر یا روستا:", ["--- جدید ---"] + all_vills['name'].tolist())
                
                if existing_v == "--- جدید ---":
                    tp = st.selectbox("نوع:", ["شهر 🏙️", "روستا 🏡"])
                    new_v = st.text_input("نام محل جدید:")
                    if st.button("ثبت محل جدید"):
                        full_v = f"{tp} {new_v}"
                        if new_v and full_v not in all_vills['name'].values:
                            c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (full_v, "شهر یا روستا", m_sec, int(c_id)))
                            conn.commit(); st.rerun()

    with col_proj:
        st.subheader("🏗️ تعریف پروژه و قرارداد")
        # انتخاب محل از لیست‌های ثبت شده
        vills_list = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type='{m_sec}'", conn)
        if not vills_list.empty:
            target_v = st.selectbox("محل پروژه:", vills_list['name'].tolist())
            v_id = vills_list[vills_list['name'] == target_v]['id'].values[0]
            
            p_name = st.text_input("نام پروژه:")
            p_comp = st.text_input("نام شرکت پیمانکار/مشاور:")
            p_cont = st.text_input("شماره قرارداد:")
            
            if st.button("ثبت پروژه و قرارداد"):
                if p_name:
                    c.execute("INSERT INTO projects (loc_id, name, company, contract_no, p_type) VALUES (?,?,?,?,?)", 
                              (int(v_id), p_name, p_comp, p_cont, m_sec))
                    conn.commit(); show_done(); st.rerun()
        
        st.divider()
        st.subheader("📁 مدیریت پوشه‌ها")
        all_pjs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{m_sec}'", conn)
        if not all_pjs.empty:
            sel_pj_f = st.selectbox("انتخاب پروژه برای پوشه‌بندی:", all_pjs['name'].tolist())
            pj_f_id = all_pjs[all_pjs['name'] == sel_pj_f]['id'].values[0]
            
            new_fld = st.text_input("نام پوشه جدید (مثلاً: نقشه‌ها):")
            if st.button("ایجاد پوشه"):
                if new_fld:
                    c.execute("INSERT INTO project_folders (proj_id, name, p_type) VALUES (?,?,?)", (int(pj_f_id), new_fld, m_sec))
                    conn.commit(); show_done(); st.rerun()
