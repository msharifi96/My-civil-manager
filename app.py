import streamlit as st
import pandas as pd
import sqlite3
import time

# اتصال به دیتابیس
conn = sqlite3.connect('civil_pro_v19.db', check_same_thread=False)
c = conn.cursor()

def show_done(text="✅ ثبت شد"):
    msg = st.empty()
    msg.success(text)
    time.sleep(1)
    msg.empty()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# مدیریت وضعیت‌ها در Session State
if 'loc_step' not in st.session_state:
    st.session_state.loc_step = "استان"
if 'active_project_id' not in st.session_state:
    st.session_state.active_project_id = None
if 'active_project_name' not in st.session_state:
    st.session_state.active_project_name = ""

st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #004a99; color: white; height: 3em; font-weight: bold; }
    .stInfo { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- توابع داشبورد و آپلود ---
def render_dash(p_type_label):
    col_tree, col_view = st.columns([1, 2])
    with col_tree:
        st.subheader(f"🗂️ آرشیو {p_type_label}")
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{p_type_label}'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"🔹 {prov['name']}"):
                cnts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        vls = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt['id']}", conn)
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vl['id']} AND p_type='{p_type_label}'", conn)
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"d_{p_type_label}_{pj['id']}"):
                                        st.session_state[f'act_p_{p_type_label}'] = (pj['id'], pj['name'])
    with col_view:
        key_act = f'act_p_{p_type_label}'
        if key_act in st.session_state:
            pid, pname = st.session_state[key_act]
            st.header(f"پروژه: {pname}")
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pid}", conn)
            for _, fld in flds.iterrows():
                files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                    for _, fl in files.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"📄 {fl['file_name']}")
                        c2.download_button("📥", fl['file_blob'], fl['file_name'], key=f"f_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

with tabs[2]: # تب آپلود
    st.subheader("📤 بارگذاری مدرک جدید")
    u_sec = st.radio("بخش مورد نظر:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_sec_choice")
    projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not projs.empty:
        c1, c2 = st.columns(2)
        with c1:
            sel_p = st.selectbox("۱. پروژه را انتخاب کنید:", projs['name'].tolist(), key="up_p_select")
            pid = projs[projs['name'] == sel_p]['id'].values[0]
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pid}", conn)
            if not flds.empty:
                sel_f = st.selectbox("۲. پوشه را انتخاب کنید:", flds['name'].tolist(), key="up_f_select")
                fid = flds[flds['name'] == sel_f]['id'].values[0]
            else: st.warning("⚠️ پوشه‌ای یافت نشد."); fid = None
        with c2:
            if fid:
                file = st.file_uploader("۳. انتخاب فایل", key="file_up_widget")
                if st.button("💾 ثبت در دیتابیس"):
                    if file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", (pid, fid, file.name, file.read()))
                        conn.commit(); show_done()

# --- تب تنظیمات با جریان یکپارچه ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات و تعریف پایه")
    m_sec = st.radio("تنظیمات برای بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_set_sec")
    st.divider()
    col_a, col_b = st.columns(2)
    
    with col_a: # مدیریت محل (همان جریان مرحله‌ای قبل)
        st.subheader("📍 مدیریت محل پروژه‌ها")
        levels = ["استان", "شهرستان", "شهر یا روستا"]
        lvl = st.radio("گام فعلی:", levels, index=levels.index(st.session_state.loc_step), horizontal=True, key="lvl_flow")
        st.session_state.loc_step = lvl

        if lvl == "استان":
            n = st.text_input("نام استان جدید:", key="in_p_flow")
            if st.button("ثبت استان و گام بعد ➡️"):
                if n:
                    c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,0)", (n, "استان", m_sec))
                    conn.commit(); st.session_state.loc_step = "شهرستان"; show_done(); st.rerun()
        
        elif lvl == "شهرستان":
            ps = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{m_sec}'", conn)
            if not ps.empty:
                sp = st.selectbox("استان مادر:", ps['name'].tolist())
                pi = ps[ps['name'] == sp]['id'].values[0]
                n = st.text_input("نام شهرستان جدید:", key="in_c_flow")
                if st.button("ثبت شهرستان و گام بعد ➡️"):
                    if n:
                        c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (n, "شهرستان", m_sec, int(pi)))
                        conn.commit(); st.session_state.loc_step = "شهر یا روستا"; show_done(); st.rerun()
            else: st.warning("ابتدا استان را ثبت کنید.")
            
        else: # شهر یا روستا (تکرارپذیر)
            cs = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND p_type='{m_sec}'", conn)
            if not cs.empty:
                sc = st.selectbox("شهرستان مادر:", cs['name'].tolist())
                pi = cs[cs['name'] == sc]['id'].values[0]
                tp = st.selectbox("نوع محل:", ["شهر 🏙️", "روستا 🏡"])
                n = st.text_input("نام شهر یا روستا:", key="in_v_flow")
                if st.button("ثبت محل (تکرارپذیر) ✅"):
                    if n:
                        fn = f"{tp} {n}"
                        c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (fn, "شهر یا روستا", m_sec, int(pi)))
                        conn.commit(); show_done(); st.rerun()
            else: st.warning("ابتدا شهرستان را ثبت کنید.")

    with col_b: # مدیریت پروژه و ساخت پوشه (بدون دکمه رادیویی - جریان یکپارچه)
        st.subheader("🏗️ مدیریت پروژه‌ها")
        
        if st.session_state.active_project_id is None:
            # مرحله ۱: تعریف پروژه
            vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type='{m_sec}'", conn)
            if not vills.empty:
                sv = st.selectbox("محل پروژه:", vills['name'].tolist(), key="p_loc_sel")
                vi = vills[vills['name'] == sv]['id'].values[0]
                pn = st.text_input("نام پروژه جدید:")
                if st.button("ثبت پروژه و تعریف پوشه‌ها ➡️"):
                    if pn:
                        c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(vi), pn, m_sec))
                        conn.commit()
                        # پیدا کردن ID پروژه‌ای که همین الان ثبت شد
                        new_id = c.lastrowid
                        st.session_state.active_project_id = new_id
                        st.session_state.active_project_name = pn
                        show_done(f"پروژه {pn} ثبت شد.")
                        st.rerun()
            else: st.info("ابتدا محل پروژه را در ستون سمت راست تعریف کنید.")
        
        else:
            # مرحله ۲: ساخت پوشه (به محض ثبت پروژه این بخش ظاهر می‌شود)
            st.info(f"🏗️ در حال ساخت پوشه برای پروژه: **{st.session_state.active_project_name}**")
            fn = st.text_input("نام پوشه جدید را وارد کنید (مثلاً: نقشه‌ها):", key="in_folder_auto")
            
            col_save, col_new = st.columns(2)
            if col_save.button("➕ ثبت این پوشه"):
                if fn:
                    c.execute("INSERT INTO project_folders (proj_id, name, p_type) VALUES (?,?,?)", 
                              (st.session_state.active_project_id, fn, m_sec))
                    conn.commit()
                    show_done(f"پوشه {fn} اضافه شد.")
                    st.rerun()
            
            if col_new.button("🆕 اتمام و ثبت پروژه دیگر"):
                st.session_state.active_project_id = None
                st.session_state.active_project_name = ""
                st.rerun()

            # نمایش پوشه‌های ثبت شده فعلی برای اطمینان کاربر
            current_flds = pd.read_sql(f"SELECT name FROM project_folders WHERE proj_id={st.session_state.active_project_id}", conn)
            if not current_flds.empty:
                st.write("📁 پوشه‌های ثبت شده:")
                st.caption(" ، ".join(current_flds['name'].tolist()))
