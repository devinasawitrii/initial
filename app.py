            google_maps_url = (
                "https://www.google.com/maps/search/?api=1&query="
                f"{hospital['latitude']},{hospital['longitude']}"
            )
        else:
            search_text = f"{hospital['hospital_name']} {hospital['city']} {hospital['province']}"
            google_maps_url = "https://www.google.com/maps/search/?api=1&query=" + search_text.replace(" ", "+")

        st.link_button("Open in Google Maps", google_maps_url)

# ==========================================
# 7. DATABASE MANAGEMENT
# ==========================================
elif page == "Database Management":
    st.title("Hospital Database Management")
    st.caption("Add, edit, delete and export hospital records")

    st.info(
        "Edit data langsung di tabel. Kamu juga bisa menambah baris baru "
        "atau menghapus baris yang sudah ada. Klik Save Table Changes untuk menyimpan."
    )

    edited = st.data_editor(
        st.session_state.hospitals,
        num_rows="dynamic",
        use_container_width=True,
        key="hospital_editor"
    )

    if st.button("Save Table Changes", type="primary"):
        edited["latitude"] = pd.to_numeric(edited["latitude"], errors="coerce")
        edited["longitude"] = pd.to_numeric(edited["longitude"], errors="coerce")
        st.session_state.hospitals = edited.copy()
        st.success("Changes saved for this session!")
        st.rerun()

    st.divider()
    st.subheader("Add New Hospital")

    with st.form("add_hospital"):
        name = st.text_input("Hospital Name")
        city = st.text_input("City")
        province = st.text_input("Province")

        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=0.0, format="%.6f")
        lon = col2.number_input("Longitude", value=0.0, format="%.6f")

        lab = st.selectbox("Lab PA Status", ["Ada", "Tidak ada", "Belum diketahui"])
        verification = st.selectbox("Data Status", ["Terverifikasi", "Perlu verifikasi"])
        submitted = st.form_submit_button("Add Hospital")

        if submitted:
            if name.strip() and city.strip() and province.strip():
                new_row = pd.DataFrame([[
                    name.strip(), city.strip(), province.strip(), lat, lon, lab, verification
                ]], columns=COLUMNS)
                st.session_state.hospitals = pd.concat(
                    [st.session_state.hospitals, new_row], ignore_index=True
                )
                st.success("Hospital added!")
                st.rerun()
            else:
                st.error("Please complete hospital name, city and province.")

    st.divider()
    st.subheader("Download Database")
    current = st.session_state.hospitals.copy()
    col1, col2 = st.columns(2)

    col1.download_button(
        "Download CSV",
        data=current.to_csv(index=False).encode("utf-8-sig"),
        file_name="hospital_database.csv",
        mime="text/csv"
    )
    col2.download_button(
        "Download Excel",
        data=export_excel(current),
        file_name="hospital_database.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ==========================================
# 8. ANALYTICS
# ==========================================
elif page == "Analytics":
    st.title("Healthcare Market Analytics")
    st.caption("Explore hospital distribution and facility classification")

    filtered = get_filtered_data(_df)
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Lab PA Status")
        render_status_pie(filtered, hole=0.4)

    with c2:
        st.subheader("Hospitals by Province")
        province_chart = (
            filtered.groupby("province")
            .size()
            .reset_index(name="Total")
            .sort_values("Total", ascending=True)
        )
        if province_chart.empty:
            st.info("Belum ada data untuk ditampilkan.")
        else:
            fig2 = px.bar(
                province_chart,
                x="Total",
                y="province",
                orientation="h",
                text="Total"
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Data Verification Status")
    verification = filtered["data_status"].fillna("Perlu verifikasi").value_counts().reset_index()
    verification.columns = ["Status", "Total"]
    if verification.empty:
        st.info("Belum ada data untuk ditampilkan.")
    else:
        fig3 = px.bar(verification, x="Status", y="Total", text="Total")
        st.plotly_chart(fig3, use_container_width=True)

st.sidebar.divider()
st.sidebar.caption("Healthcare Intelligence | Prototype v1.0")
