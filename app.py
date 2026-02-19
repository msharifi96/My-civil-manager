    with cl:
        st.subheader("📍 مدیریت محل پروژه")
        # اضافه کردن هر سه گزینه برای دسترسی کامل
        mode_loc = st.radio("عملیات محل:", ["افزودن محل جدید", "ویرایش نام محل", "حذف محل پروژه"], horizontal=True, key="loc_mode_final")
        
        if mode_loc == "افزودن محل جدید":
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="add_p_loc_new")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان جدید:", key="new_prov_name")
                if st.button("ثبت استان", key="btn_reg_prov"):
                    c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec)); conn.commit(); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="add_c_loc_new")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان:", key="new_city_name")
                    if st.button("ثبت شهرستان", key="btn_reg_city"):
                        c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id))); conn.commit(); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    s_v = st.selectbox("شهر/روستا:", ["--- جدید ---"] + vs['name'].tolist(), key="add_v_loc_new")
                    if s_v == "--- جدید ---":
                        nv = st.text_input("نام محل:", key="new_vill_name"); t = st.selectbox("نوع:",["شهر","روستا"], key="type_sel")
                        if st.button("ثبت محل", key="btn_reg_vill"):
                            c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id))); conn.commit(); st.rerun()
        
        elif mode_loc == "ویرایش نام محل":
            level_to_edit = st.selectbox("سطح مورد نظر برای ویرایش:", ["استان", "شهرستان", "شهر یا روستا"], key="lvl_edit_re")
            all_locs = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(level_to_edit, m_sec))
            if not all_locs.empty:
                target_loc = st.selectbox("انتخاب مورد:", all_locs['name'].tolist(), key="target_edit_re")
                new_name = st.text_input("نام جدید:", value=target_loc, key="name_edit_re")
                if st.button("✏️ اعمال تغییر نام", key="btn_do_edit_re", use_container_width=True):
                    c.execute("UPDATE locations SET name=? WHERE name=? AND level=? AND p_type=?", (new_name, target_loc, level_to_edit, m_sec))
                    conn.commit(); st.success("تغییر نام انجام شد"); st.rerun()
            else:
                st.info("موردی یافت نشد.")

        else: # حذف محل پروژه
            level_to_del = st.selectbox("سطح مورد نظر برای حذف:", ["استان", "شهرستان", "شهر یا روستا"], key="lvl_del_re")
            all_locs = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(level_to_del, m_sec))
            if not all_locs.empty:
                target_del = st.selectbox("انتخاب مورد برای حذف:", all_locs['name'].tolist(), key="target_del_re")
                with st.popover("⚠️ تایید حذف نهایی", use_container_width=True):
                    st.error(f"آیا مطمئن هستید که '{target_del}' حذف شود؟")
                    if st.button("بله، کاملاً مطمئنم", key="btn_do_del_re"):
                        c.execute("DELETE FROM locations WHERE name=? AND level=? AND p_type=?", (target_del, level_to_del, m_sec))
                        conn.commit(); st.rerun()
            else:
                st.info("موردی برای حذف نیست.")
