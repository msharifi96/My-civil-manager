import streamlit as st
import pandas as pd
import sqlite3
import io

# اتصال به دیتابیس
conn = sqlite3.connect('civil_explorer_v8.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی", layout="wide")

# استایل RTL و چیدمان دو ستونه
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; }
    .sidebar-content { background-color: #f1f3f6; padding: 15px; border-radius: 10px; border-left: 2px solid #004a99; }
    .content-area { background-color: #ffffff; padding: 15px; border: 1px solid #ddd; border-radius: 10px; min-height: 500px; }
    </style>
    """, unsafe_allow_html=True)

# مدیریت وضعیت انتخاب در داشبورد
if 'selected_item' not in st.session_state:
    st.session_state.selected_item = {'type': None, 'id': None, 'name': ''}

tabs = st.tabs(["📊 داشبورد مدیریتی", "📥 ثبت اطلاعات اولیه", "📍 تعریف مناطق"])

# --- تب تعریف مناطق ---
with tabs[2]:
    st.subheader("تعریف مناطق")
    level = st.radio("سطح:", ["استان", "شهرستان", "شهر یا روستا"], horizontal=True)
    parent_id = 0
    if level != "استان":
        p_level = "استان" if level == "شهرستان" else "شهرستان"
        parents = pd.read_sql(f"SELECT * FROM locations WHERE level='{p_level}'", conn)
        if not parents.empty:
            sel_p = st.selectbox(f"انتخاب {p_level}", parents['name'].tolist())
            parent_id = parents[parents['name'] == sel_p]['id'].values[0]
    
    loc_n = st.text_input(f"نام {level}")
    if st.button(f"ثبت {level}"):
        if loc_n:
            c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (loc_n, level, int(parent_id)))
            conn.commit(); st.rerun()

# --- تب ثبت پروژه ---
with tabs[1]:
    st.subheader("ثبت پروژه")
    vills = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا'", conn)
    if not vills.empty:
        col_r1, col_r2 = st.columns(2)
        target_v = col_r1.selectbox("انتخاب شهر یا روستا", vills['name'].tolist())
        v_id = vills[vills['name'] == target_v]['id'].values[0]
        p_type = col_r1.radio("نوع:", ["نظارتی 🛡️", "پیمانکاری 👷"])
        p_name = col_r2.text_input("نام پروژه")
        if st.button("ثبت پروژه جدید"):
            if p_name:
                c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(v_id), p_name, p_type))
                conn.commit(); st.success("پروژه ثبت شد.")
    else: st.warning("ابتدا منطقه را تعریف کنید.")

# --- تب داشبورد (File Explorer Style) ---
with tabs[0]:
    col_tree, col_view = st.columns([1, 2])

    with col_tree:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.subheader("ساختار درختی")
        p_type_filter = st.radio("بخش:", ["نظارتی 🛡️", "پیمانکاری 👷"], horizontal=True)
        
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"➕ استان {prov['name']}"):
                if st.button(f"مشاهده {prov['name']}", key=f"btn_prov_{prov['id']}"):
                    st.session_state.selected_item = {'type': 'prov', 'id': prov['id'], 'name': prov['name']}
                
                counts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, count in counts.iterrows():
                    with st.expander(f"🔹 {count['name']}"):
                        if st.button(f"مشاهده {count['name']}", key=f"btn_count_{count['id']}"):
                            st.session_state.selected_item = {'type': 'count', 'id': count['id'], 'name': count['name']}
                        
                        vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={count['id']}", conn)
                        for _, vill in vills.iterrows():
                            with st.expander(f"📍 {vill['name']}"):
                                if st.button(f"مشاهده {vill['name']}", key=f"btn_vill_{vill['id']}"):
                                    st.session_state.selected_item = {'type': 'vill', 'id': vill['id'], 'name': vill['name']}
                                
                                projs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vill['id']} AND p_type='{p_type_filter}'", conn)
                                for _, proj in projs.iterrows():
                                    if st.button(f"🏗️ {proj['name']}", key=f"btn_proj_{proj['id']}"):
                                        st.session_state.selected_item = {'type': 'proj', 'id': proj['id'], 'name': proj['name']}
        st.markdown('</div>', unsafe_allow_html=True)

    with col_view:
        st.markdown('<div class="content-area">', unsafe_allow_html=True)
        item = st.session_state.selected_item
        if item['id']:
            st.subheader(f"محتویات: {item['name']}")
            
            if item['type'] == 'proj':
                # مدیریت پوشه‌های اختصاصی پروژه
                col_f1, col_f2 = st.columns([2, 1])
                new_f = col_f1.text_input("نام پوشه جدید برای این پروژه")
                if col_f2.button("افزودن پوشه"):
                    if new_f:
                        c.execute("INSERT INTO project_folders (proj_id, name) VALUES (?,?)", (item['id'], new_f))
                        conn.commit(); st.rerun()
                
                # نمایش پوشه‌ها و آپلود فایل
                folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={item['id']}", conn)
                for _, fld in folders.iterrows():
                    with st.expander(f"📂 {fld['name']}"):
                        c_up, c_del = st.columns([3, 1])
                        up = c_up.file_uploader("آپلود فایل", key=f"up_{fld['id']}")
                        if up and c_up.button("ذخیره فایل", key=f"sv_{fld['id']}"):
                            c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)",
                                      (item['id'], fld['id'], up.name, up.read()))
                            conn.commit(); st.success("انجام شد")
                        
                        if c_del.button("حذف پوشه", key=f"df_{fld['id']}"):
                            c.execute("DELETE FROM project_folders WHERE id=?", (fld['id'],))
                            conn.commit(); st.rerun()
                        
                        # لیست فایل‌های داخل پوشه
                        files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                        for _, fl in files.iterrows():
                            col_n, col_d = st.columns([4, 1])
                            col_n.text(fl['file_name'])
                            col_d.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dl_{fl['id']}")

                if st.button("❌ حذف کل پروژه"):
                    c.execute("DELETE FROM projects WHERE id=?", (item['id'],))
                    conn.commit(); st.session_state.selected_item = {'id':None}; st.rerun()
            else:
                st.info("یک پروژه را از درختواره سمت راست انتخاب کنید تا پوشه‌ها و فایل‌ها نمایش داده شوند.")
        else:
            st.write("برای شروع، از سمت راست یک مورد را انتخاب کنید.")
        st.markdown('</div>', unsafe_allow_html=True)
