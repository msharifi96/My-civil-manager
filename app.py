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

# ایجاد جداول
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

# تابع رندر داشبورد
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

# آپلود فایل
with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_main")
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
        s_p_d = st.selectbox("پروژه:", all_p['disp'].tolist())
        p_id = all_p[all_p['disp']==s_p_d]['id'].values[0]
        fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_id),))
        if not fs.empty:
            s_f = st.selectbox("پوشه:", fs['name'].tolist())
            f_id = fs[fs['name']==s_f]['id'].values[0]
            up = st.file_uploader("انتخاب فایل")
            if st.button("ثبت فایل") and up:
                c.execute("INSERT INTO project_files (proj_id,folder_id,file_name,file_blob) VALUES (?,?,?,?)", (int(p_id), int(f_id), up.name, up.read()))
                conn.commit(); st.success("ذخیره شد")

# --- تنظیمات سیستم ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_set")
    st.divider()
    cl, cr = st.columns(2)
    
    # مدیریت محل پروژه
    with cl:
        st.subheader("📍 مدیریت محل پروژه")
        mode_l = st.radio("عملیات:", ["افزودن", "ویرایش", "حذف"], horizontal=True, key="l_op")
        
        if mode_l == "افزودن":
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="p_a")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان جدید:"); 
                if st.button("ثبت استان"):
                    c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec)); conn.commit(); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="c_a")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان جدید:"); 
                    if st.button("ثبت شهرستان"):
                        c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id))); conn.commit(); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    s_v = st.selectbox("محل:", ["--- جدید ---"] + vs['name'].tolist(), key="v_a")
                    if s_v == "--- جدید ---":
                        nv = st.text_input("نام محل:"); t = st.selectbox("نوع:",["شهر","روستا"])
                        if st.button("ثبت محل"):
                            c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id))); conn.commit(); st.rerun()
        
        elif mode_l == "ویرایش":
            lvl = st.selectbox("سطح ویرایش:", ["استان", "شهرستان", "شهر یا روستا"], key="l_e_v")
            all_l = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(lvl, m_sec))
            if not all_l.empty:
                tg = st.selectbox("انتخاب مورد:", all_l['name'].tolist(), key="l_e_t")
                nn = st.text_input("نام جدید:", value=tg)
                if st.button("ثبت ویرایش"):
                    c.execute("UPDATE locations SET name=? WHERE name=? AND level=? AND p_type=?", (nn, tg, lvl, m_sec))
                    conn.commit(); st.rerun()

        elif mode_l == "حذف":
            lvl = st.selectbox("سطح حذف:", ["استان", "شهرستان", "شهر یا روستا"], key="l_d_v")
            all_l = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(lvl, m_sec))
            if not all_l.empty:
                tg = st.selectbox("انتخاب برای حذف:", all_l['name'].tolist(), key="l_d_t")
                tid = all_l[all_l['name']==tg]['id'].values[0]
                with st.popover("⚠️ تایید حذف", use_container_width=True):
                    if st.button("حذف زنجیره‌ای"):
                        if lvl == "استان":
                            c_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(tid),)).fetchall()]
                            for cid in c_ids:
                                v_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(cid),)).fetchall()]
                                for vid in v_ids:
                                    c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                                    c.execute("DELETE FROM projects WHERE loc_id=?", (int(vid),))
                                    c.execute("DELETE FROM locations WHERE id=?", (int(vid),))
                                c.execute("DELETE FROM locations WHERE id=?", (int(cid),))
                        elif lvl == "شهرستان":
                            v_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(tid),)).fetchall()]
                            for vid in v_ids:
                                c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                                c.execute("DELETE FROM projects WHERE loc_id=?", (int(vid),))
                                c.execute("DELETE FROM locations WHERE id=?", (int(vid),))
                        else:
                            c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(tid),))
                            c.execute("DELETE FROM projects WHERE loc_id=?", (int(tid),))
                        c.execute("DELETE FROM locations WHERE id=?", (int(tid),))
                        conn.commit(); st.rerun()

    # مدیریت پروژه
    with cr:
        st.subheader("🏗️ مدیریت پروژه")
        mode_p = st.radio("عملیات:", ["افزودن", "ویرایش", "حذف"], horizontal=True, key="p_op")
        all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
        
        if mode_p == "افزودن":
            v_l = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
            if not v_l.empty:
                sv = st.selectbox("محل پروژه:", v_l['name'].tolist(), key="p_a_l")
                pn = st.text_input("نام پروژه:"); cp = st.text_input("شرکت:"); cn = st.text_input("قرارداد:")
                if st.button("ثبت پروژه"):
                    vid = v_l[v_l['name']==sv]['id'].values[0]
                    c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(vid),pn,cp,cn,m_sec)); conn.commit(); st.rerun()
            st.divider()
            if not all_p.empty:
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                spj = st.selectbox("انتخاب پروژه برای پوشه:", all_p['disp'].tolist(), key="p_a_f")
                nf = st.text_input("نام پوشه جدید:"); 
                if st.button("ایجاد پوشه"):
                    pid = all_p[all_p['disp']==spj]['id'].values[0]
                    c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec)); conn.commit(); st.rerun()
        
        elif mode_p == "ویرایش":
            if not all_p.empty:
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                tg = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist(), key="p_e_s")
                pid = all_p[all_p['disp']==tg]['id'].values[0]
                p_d = all_p[all_p['id']==pid].iloc[0]
                
                v_l = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
                cur_loc = v_l[v_l['id']==p_d['loc_id']]['name'].values[0] if p_d['loc_id'] in v_l['id'].values else v_l['name'].tolist()[0]
                
                new_l = st.selectbox("محل:", v_l['name'].tolist(), index=v_l['name'].tolist().index(cur_loc))
                new_pn = st.text_input("نام پروژه:", value=p_d['name'])
                new_cp = st.text_input("شرکت:", value=p_d['company'])
                new_cn = st.text_input("قرارداد:", value=p_d['contract_no'])
                
                if st.button("ثبت تغییرات پروژه"):
                    n_vid = v_l[v_l['name']==new_l]['id'].values[0]
                    c.execute("UPDATE projects SET loc_id=?, name=?, company=?, contract_no=? WHERE id=?", (int(n_vid), new_pn, new_cp, new_cn, int(pid)))
                    conn.commit(); st.rerun()

        elif mode_p == "حذف":
            if not all_p.empty:
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                tg = st.selectbox("پروژه جهت حذف:", all_p['disp'].tolist(), key="p_d_s")
                pid = all_p[all_p['disp']==tg]['id'].values[0]
                with st.popover("🗑️ تایید حذف نهایی", use_container_width=True):
                    if st.button("بله، حذف شود"):
                        c.execute("DELETE FROM projects WHERE id=?", (int(pid),)); c.execute("DELETE FROM project_files WHERE proj_id=?", (int(pid),))
                        conn.commit(); st.rerun()
