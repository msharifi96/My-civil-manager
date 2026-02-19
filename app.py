import streamlit as st
import pandas as pd
import sqlite3
import io

# اتصال به دیتابیس
conn = sqlite3.connect('civil_pro_v10.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل RTL و تفکیک ستون‌ها
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; font-weight: bold; }
    .sidebar-tree { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 3px solid #004a99; height: 85vh; overflow-y: auto; }
    .content-viewer { background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 10px; min-height: 85vh; }
    .stat-box { background-color: #f1f3f5; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-right: 5px solid #28a745; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'view_state' not in st.session_state:
    st.session_state.view_state = {'level': None, 'id': None, 'name': ''}

tab_main, tab_admin = st.tabs(["📊 داشبورد و آرشیو", "⚙️ مدیریت و بارگذاری"])

# --- تب مدیریت و بارگذاری ---
with tab_admin:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("تعریف مناطق و پروژه‌ها")
        m_level = st.selectbox("سطح جدید", ["استان", "شهرستان", "شهر یا روستا", "پروژه"])
        
        if m_level == "استان":
            n_name = st.text_input("نام استان")
            if st.button("ثبت استان"):
                c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (n_name, "استان", 0))
                conn.commit(); st.success("انجام شد")
        
        elif m_level == "شهرستان":
            provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
            if not provs.empty:
                sel_p = st.selectbox("انتخاب استان", provs['name'].tolist())
                p_id = provs[provs['name'] == sel_p]['id'].values[0]
                n_name = st.text_input("نام شهرستان")
                if st.button("ثبت شهرستان"):
                    c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (n_name, "شهرستان", p_id))
                    conn.commit(); st.success("انجام شد")

        elif m_level == "شهر یا روستا":
            counts = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان'", conn)
            if not counts.empty:
                sel_c = st.selectbox("انتخاب شهرستان", counts['name'].tolist())
                c_id = counts[counts['name'] == sel_c]['id'].values[0]
                n_name = st.text_input("نام شهر یا روستا")
                if st.button("ثبت شهر یا روستا"):
                    c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (n_name, "شهر یا روستا", c_id))
                    conn.commit(); st.success("انجام شد")

        elif m_level == "پروژه":
            vills = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا'", conn)
            if not vills.empty:
                sel_v = st.selectbox("انتخاب شهر یا روستا", vills['name'].tolist())
                v_id = vills[vills['name'] == sel_v]['id'].values[0]
                p_type = st.radio("بخش", ["نظارتی 🛡️", "پیمانکاری 👷"], horizontal=True)
                p_name = st.text_input("نام پروژه")
                if st.button("ثبت پروژه"):
                    c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(v_id), p_name, p_type))
                    conn.commit(); st.success("انجام شد")

    with col_b:
        st.subheader("مدیریت پوشه‌ها و بارگذاری فایل")
        projs = pd.read_sql("SELECT * FROM projects", conn)
        if not projs.empty:
            sel_proj_name = st.selectbox("انتخاب پروژه هدف", projs['name'].tolist())
            sel_proj_id = projs[projs['name'] == sel_proj_name]['id'].values[0]
            
            st.divider()
            new_f = st.text_input("نام پوشه جدید")
            if st.button("ایجاد پوشه"):
                c.execute("INSERT INTO project_folders (proj_id, name) VALUES (?,?)", (sel_proj_id, new_f))
                conn.commit(); st.success("انجام شد")
            
            st.divider()
            folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={sel_proj_id}", conn)
            if not folders.empty:
                sel_f_name = st.selectbox("انتخاب پوشه مقصد", folders['name'].tolist())
                sel_f_id = folders[folders['name'] == sel_f_name]['id'].values[0]
                up_file = st.file_uploader("انتخاب فایل")
                if st.button("بارگذاری فایل"):
                    if up_file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)",
                                  (sel_proj_id, sel_f_id, up_file.name, up_file.read()))
                        conn.commit(); st.success("انجام شد")
        else: st.info("هنوز پروژه‌ای ثبت نشده است.")

# --- تب داشبورد و آرشیو ---
with tab_main:
    col_tree, col_view = st.columns([1, 2])

    with col_tree:
        st.markdown('<div class="sidebar-tree">', unsafe_allow_html=True)
        st.subheader("بایگانی درختی")
        p_filter = st.radio("بخش:", ["نظارتی 🛡️", "پیمانکاری 👷"], horizontal=True)
        
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
        for _, prov in provs.iterrows():
            if st.button(f"📁 استان {prov['name']}", key=f"t_p_{prov['id']}"):
                st.session_state.view_state = {'level': 'prov', 'id': prov['id'], 'name': prov['name']}
            
            counts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
            for _, count in counts.iterrows():
                if st.button(f"---- 📂 {count['name']}", key=f"t_c_{count['id']}"):
                    st.session_state.view_state = {'level': 'count', 'id': count['id'], 'name': count['name']}
                
                vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={count['id']}", conn)
                for _, vill in vills.iterrows():
                    if st.button(f"-------- 📍 {vill['name']}", key=f"t_v_{vill['id']}"):
                        st.session_state.view_state = {'level': 'vill', 'id': vill['id'], 'name': vill['name']}
                    
                    projs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vill['id']} AND p_type='{p_filter}'", conn)
                    for _, proj in projs.iterrows():
                        if st.button(f"------------ 🏗️ {proj['name']}", key=f"t_proj_{proj['id']}"):
                            st.session_state.view_state = {'level': 'proj', 'id': proj['id'], 'name': proj['name']}
        st.markdown('</div>', unsafe_allow_html=True)

    with col_view:
        st.markdown('<div class="content-viewer">', unsafe_allow_html=True)
        state = st.session_state.view_state
        if state['id']:
            st.header(state['name'])
            
            if state['level'] == 'prov':
                f_count = pd.read_sql(f"""SELECT COUNT(pf.id) as total FROM project_files pf 
                                          JOIN projects p ON pf.proj_id = p.id 
                                          JOIN locations vill ON p.loc_id = vill.id
                                          JOIN locations count ON vill.parent_id = count.id
                                          WHERE count.parent_id = {state['id']}""", conn)['total'].values[0]
                st.markdown(f'<div class="stat-box">تعداد کل فایل‌های این استان: {f_count}</div>', unsafe_allow_html=True)
                
            elif state['level'] == 'vill':
                f_count = pd.read_sql(f"""SELECT COUNT(pf.id) as total FROM project_files pf 
                                          JOIN projects p ON pf.proj_id = p.id 
                                          WHERE p.loc_id = {state['id']}""", conn)['total'].values[0]
                st.markdown(f'<div class="stat-box">تعداد کل فایل‌های این شهر یا روستا: {f_count}</div>', unsafe_allow_html=True)

            elif state['level'] == 'proj':
                folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={state['id']}", conn)
                if not folders.empty:
                    for _, fld in folders.iterrows():
                        files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                        with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                            for _, fl in files.iterrows():
                                c_n, c_d = st.columns([4, 1])
                                c_n.text(f"📄 {fl['file_name']}")
                                c_d.download_button("📥 دریافت فایل", fl['file_blob'], fl['file_name'], key=f"d_f_{fl['id']}")
                else:
                    st.info("پوشه‌ای برای این پروژه تعریف نشده است.")
                
                st.divider()
                if st.button("🗑️ حذف کامل پروژه"):
                    c.execute("DELETE FROM projects WHERE id=?", (state['id'],))
                    c.execute("DELETE FROM project_folders WHERE proj_id=?", (state['id'],))
                    c.execute("DELETE FROM project_files WHERE proj_id=?", (state['id'],))
                    conn.commit(); st.success("انجام شد"); st.rerun()
        else:
            st.info("یک مورد را از درختواره انتخاب کنید.")
        st.markdown('</div>', unsafe_allow_html=True)
