# --- بخش مربوط به حذف محل پروژه با قابلیت حذف زنجیره‌ای زیرمجموعه‌ها ---

else: # عملیات حذف محل پروژه
    lvl = st.selectbox("سطح حذف:", ["استان", "شهرستان", "شهر یا روستا"], key="lvl_dl")
    all_l = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(lvl, m_sec))
    
    if not all_l.empty:
        target = st.selectbox("انتخاب برای حذف:", all_l['name'].tolist(), key="tg_dl")
        target_id = all_l[all_l['name'] == target]['id'].values[0]
        
        with st.popover("⚠️ تایید حذف نهایی", use_container_width=True):
            st.error(f"هشدار: با حذف '{target}'، تمام زیرمجموعه‌ها، پروژه‌ها و فایل‌های مربوط به آن نیز حذف خواهند شد!")
            if st.button("بله، همه موارد حذف شوند", key="btn_dl_final"):
                
                if lvl == "استان":
                    # ۱. پیدا کردن تمام شهرستان‌های این استان
                    c_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(target_id),)).fetchall()]
                    for cid in c_ids:
                        # ۲. پیدا کردن تمام شهرهای این شهرستان‌ها
                        v_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(cid),)).fetchall()]
                        for vid in v_ids:
                            # ۳. حذف فایل‌ها، پوشه‌ها و پروژه‌های هر شهر
                            c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                            c.execute("DELETE FROM project_folders WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                            c.execute("DELETE FROM projects WHERE loc_id=?", (int(vid),))
                            c.execute("DELETE FROM locations WHERE id=?", (int(vid),))
                        c.execute("DELETE FROM locations WHERE id=?", (int(cid),))
                    # ۴. حذف خود استان
                    c.execute("DELETE FROM locations WHERE id=?", (int(target_id),))

                elif lvl == "شهرستان":
                    v_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(target_id),)).fetchall()]
                    for vid in v_ids:
                        c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                        c.execute("DELETE FROM project_folders WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                        c.execute("DELETE FROM projects WHERE loc_id=?", (int(vid),))
                        c.execute("DELETE FROM locations WHERE id=?", (int(vid),))
                    c.execute("DELETE FROM locations WHERE id=?", (int(target_id),))

                elif lvl == "شهر یا روستا":
                    c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(target_id),))
                    c.execute("DELETE FROM project_folders WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(target_id),))
                    c.execute("DELETE FROM projects WHERE loc_id=?", (int(target_id),))
                    c.execute("DELETE FROM locations WHERE id=?", (int(target_id),))

                conn.commit()
                st.success(f"'{target}' و تمامی زیرمجموعه‌های آن با موفقیت حذف شدند.")
                st.rerun()
