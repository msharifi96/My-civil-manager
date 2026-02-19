import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
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
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل راست‌چین
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .block-container { direction: rtl !important; text-align: right !important; font-family: 'Segoe UI', Tahoma, sans-serif; }
    h1, h2, h3, h4, h5, h6, label, .stMarkdown, p, span { text-align: right !important; direction: rtl !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl !important; display: flex !important; justify-content: flex-start !important; }
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
                        c_n, c_b = st.columns([4, 1.5])
                        with c_n: st.write(f"📄 {fl['file_name']}")
                        with c_b:
                            a1, a2, a3 = st.columns([1, 1, 1])
                            if a1.button("🗑️", key=f"del_f_{fl['id']}"):
                                c.execute("DELETE FROM project_files WHERE id=?", (int(fl['id']),)); conn.commit(); st.rerun()
                            if a2.button("🔗", key=f"lnk_{fl['id']}"):
                                st.toast("لینک کپی شد"); st.code(f"data:file;base64,{base64.b64encode(fl['file_blob']).decode()[:10]}...")
                            a3.download_button("💾", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- تنظیمات سیستم ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_set_main")
    st.divider()
    cl, cr = st.columns(2)
    
    with cl:
        st.subheader("📍 مدیریت محل پروژه")
        mode_l = st.radio("عملیات:", ["افزودن", "ویرایش", "حذف"], horizontal=True, key="l_op_final")
        
        if mode_l == "افزودن":
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="p_add_sel")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان:", value="", placeholder="نام استان جدید...", key="in_p_a") 
                if st.button("ثبت استان"):
                    if np: c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec)); conn.commit(); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="c_add_sel")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان:", value="", placeholder="نام شهرستان جدید...", key="in_c_a") 
                    if st.button("ثبت شهرستان"):
                        if nc: c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id))); conn.commit(); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    s_v = st.selectbox("محل:", ["--- جدید ---"] + vs['name'].tolist(), key="v_add_sel")
                    if s_v == "--- جدید ---":
                        nv = st.text_input("نام محل:", value="", placeholder="نام شهر یا روستا...", key="in_v_a")
                        t = st.selectbox("نوع:",["شهر","روستا"])
                        if st.button("ثبت محل"):
                            if nv: c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id))); conn.commit(); st.rerun()
        # بخش ویرایش و حذف محل طبق کد قبلی باقی می‌ماند...

    with cr:
        st.subheader("🏗️ مدیریت پروژه")
        mode_p = st.radio("عملیات:", ["افزودن", "ویرایش", "حذف"], horizontal=True, key="p_op_final")
        all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
        
        if mode_p == "افزودن":
            v_l = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
            if not v_l.empty:
                sv = st.selectbox("محل پروژه:", v_l['name'].tolist(), key="p_add_loc")
                pn = st.text_input("نام پروژه:", value="", placeholder="نام پروژه جدید...", key="in_p_n_a")
                cp = st.text_input("شرکت:", value="", placeholder="نام شرکت...", key="in_p_c_a")
                cn = st.text_input("قرارداد:", value="", placeholder="شماره قرارداد...", key="in_p_cont_a")
                if st.button("ثبت پروژه"):
                    vid = v_l[v_l['name']==sv]['id'].values[0]
                    c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(vid),pn,cp,cn,m_sec)); conn.commit(); st.rerun()
            
            st.markdown("---")
            # --- بازگشت بخش ایجاد پوشه ---
            if not all_p.empty:
                st.write("### 📁 ایجاد پوشه")
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                spj = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist(), key="p_folder_sel")
                nf = st.text_input("نام پوشه:", value="", placeholder="مثلاً: نقشه‌ها، صورت‌جلسات...", key="in_f_n_a") 
                if st.button("ثبت پوشه جدید"):
                    if nf:
                        pid = all_p[all_p['disp']==spj]['id'].values[0]
                        c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec))
                        conn.commit(); st.success("پوشه ایجاد شد"); st.rerun()
        
        elif mode_p == "ویرایش":
            # بخش ویرایش طبق کد قبلی...
            if not all_p.empty:
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                tg = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist(), key="p_edit_sel")
                pid = all_p[all_p['disp']==tg]['id'].values[0]
                p_d = all_p[all_p['id']==pid].iloc[0]
                v_l = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
                cur_l = v_l[v_l['id']==p_d['loc_id']]['name'].values[0] if p_d['loc_id'] in v_l['id'].values else v_l['name'].tolist()[0]
                new_l = st.selectbox("محل:", v_l['name'].tolist(), index=v_l['name'].tolist().index(cur_l))
                new_pn = st.text_input("نام پروژه:", value="", placeholder=f"فعلی: {p_d['name']}", key="in_p_n_e")
                new_cp = st.text_input("شرکت:", value="", placeholder=f"فعلی: {p_d['company']}", key="in_p_c_e")
                new_cn = st.text_input("قرارداد:", value="", placeholder=f"فعلی: {p_d['contract_no']}", key="in_p_cont_e")
                if st.button("ثبت تغییرات پروژه"):
                    n_vid = v_l[v_l['name']==new_l]['id'].values[0]
                    f_pn = new_pn if new_pn else p_d['name']
                    f_cp = new_cp if new_cp else p_d['company']
                    f_cn = new_cn if new_cn else p_d['contract_no']
                    c.execute("UPDATE projects SET loc_id=?, name=?, company=?, contract_no=? WHERE id=?", (int(n_vid), f_pn, f_cp, f_cn, int(pid)))
                    conn.commit(); st.rerun()

        elif mode_p == "حذف":
            # بخش حذف طبق کد قبلی...
            if not all_p.empty:
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                tg = st.selectbox("پروژه جهت حذف:", all_p['disp'].tolist(), key="p_del_sel")
                pid = all_p[all_p['disp']==tg]['id'].values[0]
                with st.popover("🗑️ تایید حذف پروژه", use_container_width=True):
                    if st.button("حذف قطعی"):
                        c.execute("DELETE FROM project_files WHERE proj_id=?"); c.execute("DELETE FROM project_folders WHERE proj_id=?"); c.execute("DELETE FROM projects WHERE id=?", (int(pid),))
                        conn.commit(); st.rerun()
