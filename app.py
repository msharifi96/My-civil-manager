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

# ۲. استایل و تراز راست‌چین
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .block-container { direction: rtl !important; text-align: right !important; font-family: 'Segoe UI', Tahoma, sans-serif; }
    h1, h2, h3, h4, h5, h6, label, .stMarkdown, p, span { text-align: right !important; direction: rtl !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl !important; display: flex !important; justify-content: flex-start !important; }
    div[data-testid="column"] { display: flex !important; align-items: center !important; }
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
                        c_name, c_btns = st.columns([4, 1.5])
                        with c_name: st.write(f"📄 {fl['file_name']}")
                        with c_btns:
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
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_setting_final")
    st.divider()
    cl, cr = st.columns(2)
    
    with cl:
        st.subheader("📍 مدیریت محل پروژه")
        mode_loc = st.radio("عملیات محل:", ["افزودن محل جدید", "ویرایش نام محل", "حذف محل پروژه"], horizontal=True, key="loc_ops")
        
        if mode_loc == "افزودن محل جدید":
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="add_p_final")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان جدید:", key="np_final")
                if st.button("ثبت استان", key="btn_p_final"):
                    c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec)); conn.commit(); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="add_c_final")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان:", key="nc_final")
                    if st.button("ثبت شهرستان", key="btn_c_final"):
                        c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id))); conn.commit(); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    s_v = st.selectbox("شهر/روستا:", ["--- جدید ---"] + vs['name'].tolist(), key="add_v_final")
                    if s_v == "--- جدید ---":
                        nv = st.text_input("نام محل:", key="nv_final"); t = st.selectbox("نوع:",["شهر","روستا"], key="tv_final")
                        if st.button("ثبت محل", key="btn_v_final"):
                            c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id))); conn.commit(); st.rerun()
        
        elif mode_loc == "ویرایش نام محل":
            lvl = st.selectbox("سطح ویرایش:", ["استان", "شهرستان", "شهر یا روستا"], key="lvl_ed")
            all_l = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(lvl, m_sec))
            if not all_l.empty:
                target = st.selectbox("انتخاب مورد:", all_l['name'].tolist(), key="tg_ed")
                new_n = st.text_input("نام جدید:", value=target, key="nn_ed")
                if st.button("✏️ اعمال تغییر نام", key="btn_ed", use_container_width=True):
                    c.execute("UPDATE locations SET name=? WHERE name=? AND level=? AND p_type=?", (new_n, target, lvl, m_sec))
                    conn.commit(); st.rerun()

        else: # حذف
            lvl = st.selectbox("سطح حذف:", ["استان", "شهرستان", "شهر یا روستا"], key="lvl_dl")
            all_l = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(lvl, m_sec))
            if not all_l.empty:
                target = st.selectbox("انتخاب برای حذف:", all_l['name'].tolist(), key="tg_dl")
                with st.popover("⚠️ تایید حذف نهایی", use_container_width=True):
                    if st.button("بله، حذف شود", key="btn_dl_final"):
                        c.execute("DELETE FROM locations WHERE name=? AND level=? AND p_type=?", (target, lvl, m_sec))
                        conn.commit(); st.rerun()

    with cr:
        st.subheader("🏗️ مدیریت پروژه")
        mode_pj = st.radio("عملیات:", ["افزودن پروژه", "ویرایش پروژه"], horizontal=True, key="pj_mode_f")
        all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
        
        if mode_pj == "افزودن پروژه":
            v_list = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
            if not v_list.empty:
                sv = st.selectbox("محل پروژه:", v_list['name'].tolist(), key="sv_pj")
                pn = st.text_input("نام پروژه:", key="pn_pj"); cp = st.text_input("شرکت:", key="cp_pj"); cn = st.text_input("قرارداد:", key="cn_pj")
                if st.button("ثبت پروژه", key="btn_pj"):
                    v_id = v_list[v_list['name']==sv]['id'].values[0]
                    c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(v_id),pn,cp,cn,m_sec)); conn.commit(); st.rerun()
            
            st.divider()
            if not all_p.empty:
                st.write("### 📁 ایجاد پوشه")
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                spj = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist(), key="spj_f")
                nf = st.text_input("نام پوشه:", key="nf_f")
                if st.button("ایجاد پوشه", key="btn_f"):
                    pid = all_p[all_p['disp']==spj]['id'].values[0]
                    c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec)); conn.commit(); st.rerun()
        else:
             if not all_p.empty:
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                edit_p = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist(), key="ed_pj_f")
                p_id = all_p[all_p['disp']==edit_p]['id'].values[0]
                p_data = all_p[all_p['id']==p_id].iloc[0]
                with st.expander("🛠️ ویرایش و حذف", expanded=True):
                    st.text_input("نام پروژه:", value=p_data['name'], key="ed_pn")
                    if st.button("💾 بروزرسانی", key=f"up_{p_id}"): st.success("بروز شد")
                    with st.popover("🗑️ حذف کامل"):
                        if st.button("تایید حذف", key=f"dl_pj_{p_id}"):
                            c.execute("DELETE FROM projects WHERE id=?", (int(p_id),)); conn.commit(); st.rerun()
