import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل ایمن برای جلوگیری از به هم ریختن تب‌ها و حذف مربع آیکون‌ها
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    
    /* حذف کادر دور دکمه‌های آیکونی در داشبورد */
    div[data-testid="column"] button, 
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    /* اصلاح نمایش تب‌ها */
    .stTabs [data-baseweb="tab-list"] {
        direction: rtl;
        gap: 20px;
    }
    
    /* استایل اختصاصی برای ورودی‌های تنظیمات */
    .stSelectbox, .stTextInput {
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

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
                        c_icons, c_name = st.columns([1, 4])
                        with c_name: st.markdown(f"<div style='padding-top:5px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        with c_icons:
                            i1, i2, i3 = st.columns(3)
                            if i1.button("🗑️", key=f"del_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}"); conn.commit(); st.rerun()
                            if i2.button("🔗", key=f"lnk_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode(); st.toast("لینک کپی شد")
                            i3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش مقصد:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    all_p = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not all_p.empty:
        s_p = st.selectbox("انتخاب پروژه:", all_p['name'].tolist())
        p_id = all_p[all_p['name']==s_p]['id'].values[0]
        fs = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={p_id}", conn)
        if not fs.empty:
            s_f = st.selectbox("انتخاب پوشه:", fs['name'].tolist())
            f_id = fs[fs['name']==s_f]['id'].values[0]
            up_file = st.file_uploader("انتخاب فایل")
            if st.button("🚀 ثبت نهایی") and up_file:
                c.execute("INSERT INTO project_files (proj_id,folder_id,file_name,file_blob) VALUES (?,?,?,?)", (int(p_id), int(f_id), up_file.name, up_file.read()))
                conn.commit(); st.success("فایل ذخیره شد")

with tabs[3]:
    st.subheader("⚙️ تنظیمات ساختار و پروژه‌ها")
    m_sec = st.radio("بخش مورد نظر برای ویرایش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    
    st.markdown("---")
    # مدیریت لوکیشن‌ها به صورت پله‌ای برای جلوگیری از ریختن بهم ظاهر
    st.write("### 📍 ۱. تعریف محل (استان، شهرستان، روستا)")
    ps = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{m_sec}'", conn)
    s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="set_p")
    
    if s_p == "--- جدید ---":
        np = st.text_input("نام استان جدید را وارد کنید:")
        if st.button("➕ ثبت استان"):
            c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec))
            conn.commit(); st.rerun()
    else:
        p_id = ps[ps['name']==s_p]['id'].values[0]
        cs = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={p_id}", conn)
        s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="set_c")
        
        if s_c == "--- جدید ---":
            nc = st.text_input("نام شهرستان جدید:")
            if st.button("➕ ثبت شهرستان"):
                c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id)))
                conn.commit(); st.rerun()
        else:
            c_id = cs[cs['name']==s_c]['id'].values[0]
            vs = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={c_id}", conn)
            s_v = st.selectbox("شهر/روستا:", ["--- جدید ---"] + vs['name'].tolist(), key="set_v")
            
            if s_v == "--- جدید ---":
                nv = st.text_input("نام شهر یا روستا:")
                if st.button("➕ ثبت محل نهایی"):
                    c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nv,"شهر یا روستا",m_sec,int(c_id)))
                    conn.commit(); st.rerun()
                
    st.markdown("---")
    st.write("### 🏗️ ۲. تعریف پروژه و پوشه‌ها")
    v_list = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type='{m_sec}'", conn)
    if not v_list.empty:
        sv = st.selectbox("انتخاب محل پروژه:", v_list['name'].tolist())
        col1, col2, col3 = st.columns(3)
        with col1: pn = st.text_input("نام پروژه:")
        with col2: cp = st.text_input("نام شرکت:")
        with col3: cn = st.text_input("شماره قرارداد:")
        if st.button("🏗️ ثبت پروژه جدید"):
            v_id = v_list[v_list['name']==sv]['id'].values[0]
            c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(v_id),pn,cp,cn,m_sec))
            conn.commit(); st.rerun()
    
    st.markdown("---")
    all_projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{m_sec}'", conn)
    if not all_projs.empty:
        spj = st.selectbox("انتخاب پروژه برای ایجاد پوشه:", all_projs['name'].tolist())
        nf = st.text_input("نام پوشه (مثلاً: نقشه‌ها، صورت‌وضعیت):")
        if st.button("📁 ایجاد پوشه"):
            pid = all_projs[all_projs['name']==spj]['id'].values[0]
            c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec))
            conn.commit(); st.rerun()
