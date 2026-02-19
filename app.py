import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس (ماندگاری دائمی داده‌ها)
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('civil_pro_final_v26.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# ایجاد جداول پایه در صورت عدم وجود
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# ۲. استایل اختصاصی (راست‌چین تب‌ها و تراز دقیق آیکون‌ها در مرکز سطر)
st.markdown("""
    <style>
    /* راست‌چین کردن کل صفحه و متون */
    [data-testid="stAppViewContainer"], .main, .stMarkdown, p, h1, h2, h3 { 
        direction: rtl; 
        text-align: right; 
    }
    
    /* راست‌چین کردن تب‌ها */
    .stTabs [data-baseweb="tab-list"] {
        direction: rtl;
        display: flex;
        justify-content: flex-start !important;
    }

    /* تراز کردن نام فایل و آیکون‌ها در یک سطر و وسط‌چین عمودی دقیق */
    .file-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        direction: rtl;
        padding: 5px 0;
    }

    /* استایل دکمه‌های آیکونی فشرده و بدون حاشیه */
    div[data-testid="column"] button {
        border: none !important;
        background: transparent !important;
        padding: 0 8px !important;
        font-size: 1.3rem !important;
        box-shadow: none !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* حذف فاصله اضافی بین ستون‌ها برای چسبیدن آیکون‌ها */
    [data-testid="column"] { gap: 0px !important; }
    
    /* فونت فارسی استاندارد */
    * { font-family: 'Tahoma', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

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
                                    if st.button(f"🏗️ {pj['name']}", key=f"pj_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()

    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            st.info(f"🏢 {pj['company']} | 📄 {pj['contract_no']}")
            flds = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(pj['id']),))
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql("SELECT * FROM project_files WHERE folder_id=?", conn, params=(int(fld['id']),))
                    for _, fl in files.iterrows():
                        # ایجاد سطر هماهنگ برای نام فایل و دکمه‌ها
                        c_name, c_btns = st.columns([3.5, 1.5])
                        with c_name:
                            # متن فایل دقیقاً در مرکز عمودی ستون
                            st.markdown(f"<div style='display:flex; align-items:center; height:45px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        with c_btns:
                            # دکمه‌ها در یک ردیف و تراز شده در مرکز
                            a1, a2, a3 = st.columns([1, 1, 1])
                            if a1.button("🗑️", key=f"del_{fl['id']}", help="حذف"):
                                c.execute("DELETE FROM project_files WHERE id=?", (int(fl['id']),))
                                conn.commit(); st.rerun()
                            if a2.button("🔗", key=f"lnk_{fl['id']}", help="کپی لینک"):
                                st.toast("لینک آماده کپی است")
                                st.code(f"data:file;base64,{base64.b64encode(fl['file_blob']).decode()[:10]}...")
                            a3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}", help="دانلود")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- آپلود فایل (اصلاح شده خط ۱۲۵) ---
with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_sec_main")
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        c1, c2 = st.columns(2)
        with c1:
            s_p = st.selectbox("پروژه:", all_p['name'].tolist())
            p_id = all_p[all_p['name']==s_p]['id'].values[0]
            fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_id),))
            if not fs.empty:
                s_f = st.selectbox("پوشه:", fs['name'].tolist())
                f_id = fs[fs['name']==s_f]['id'].values[0]
                up_file = st.file_uploader("انتخاب فایل")
                if st.button("ثبت فایل نهایی") and up_file:
                    file_data = up_file.read()
                    c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                              (int(p_id), int(f_id), up_file.name, file_data))
                    conn.commit(); st.success("فایل با موفقیت ذخیره شد")

# --- تنظیمات سیستم ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات زیرساخت")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_setting")
    st.divider()
    cl, cr = st.columns(2)
    with cl:
        st.subheader("📍 مدیریت محل")
        ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
        s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="set_p")
        if s_p == "--- جدید ---":
            np = st.text_input("نام استان جدید:")
            if st.button("ثبت استان"):
                c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec))
                conn.commit(); st.rerun()
        else:
            p_id = ps[ps['name']==s_p]['id'].values[0]
            cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
            s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="set_c")
            if s_c == "--- جدید ---":
                nc = st.text_input("نام شهرستان:")
                if st.button("ثبت شهرستان"):
                    c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id)))
                    conn.commit(); st.rerun()
            else:
                c_id = cs[cs['name']==s_c]['id'].values[0]
                vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                s_v = st.selectbox("شهر/روستا:", ["--- جدید ---"] + vs['name'].tolist(), key="set_v")
                if s_v == "--- جدید ---":
                    nv = st.text_input("نام محل:"); t = st.selectbox("نوع:",["شهر","روستا"])
                    if st.button("ثبت محل"):
                        c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id)))
                        conn.commit(); st.rerun()
    with cr:
        st.subheader("🏗️ پروژه و پوشه")
        v_list = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
        if not v_list.empty:
            sv = st.selectbox("انتخاب محل:", v_list['name'].tolist(), key="set_pj_loc")
            pn = st.text_input("نام پروژه:"); cp = st.text_input("شرکت مسئول:"); cn = st.text_input("قرارداد:")
            if st.button("ثبت پروژه"):
                v_id = v_list[v_list['name']==sv]['id'].values[0]
                c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(v_id),pn,cp,cn,m_sec))
                conn.commit(); st.rerun()
        st.divider()
        all_projs = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
        if not all_projs.empty:
            spj = st.selectbox("پروژه برای پوشه:", all_projs['name'].tolist(), key="set_fld_pj")
            nf = st.text_input("نام پوشه جدید:")
            if st.button("ایجاد پوشه"):
                pid = all_projs[all_projs['name']==spj]['id'].values[0]
                c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec))
                conn.commit(); st.rerun()
