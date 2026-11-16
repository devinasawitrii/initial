import streamlit as st
import pandas as pd
import plotly.express as px
import folium
import streamlit.components.v1 as components
from folium.plugins import MarkerCluster
from io import BytesIO

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Healthcare Intelligence",
    page_icon="🏥",
    layout="wide"
)

# ==========================================
# 2. SAMPLE DATABASE
# ==========================================
SAMPLE_DATA = [
    ["RS Contoh Bekasi", "Bekasi", "Jawa Barat", -6.2383, 106.9756, "Ada", "Terverifikasi"],
    ["RS Contoh Bandung", "Bandung", "Jawa Barat", -6.9175, 107.6191, "Ada", "Terverifikasi"],
    ["RS Contoh Karawang", "Karawang", "Jawa Barat", -6.3050, 107.3000, "Tidak ada", "Terverifikasi"],
    ["RS Contoh Bogor", "Bogor", "Jawa Barat", -6.5971, 106.8060, "Belum diketahui", "Perlu verifikasi"],
    ["RS Contoh Semarang", "Semarang", "Jawa Tengah", -6.9667, 110.4167, "Ada", "Terverifikasi"],
    ["RS Contoh Solo", "Surakarta", "Jawa Tengah", -7.5666, 110.8167, "Tidak ada", "Terverifikasi"],
    ["RS Contoh Yogyakarta", "Yogyakarta", "DI Yogyakarta", -7.7956, 110.3695, "Ada", "Terverifikasi"],
    ["RS Contoh Surabaya", "Surabaya", "Jawa Timur", -7.2575, 112.7521, "Ada", "Terverifikasi"],
    ["RS Contoh Malang", "Malang", "Jawa Timur", -7.9666, 112.6326, "Belum diketahui", "Perlu verifikasi"],
    ["RS Contoh Tangerang", "Tangerang", "Banten", -6.1783, 106.6319, "Tidak ada", "Terverifikasi"],
    ["RS Contoh Jakarta", "Jakarta", "DKI Jakarta", -6.2088, 106.8456, "Ada", "Terverifikasi"],
    ["RS Contoh Medan", "Medan", "Sumatera Utara", 3.5952, 98.6722, "Tidak ada", "Terverifikasi"],
    ["RS Contoh Makassar", "Makassar", "Sulawesi Selatan", -5.1477, 119.4327, "Ada", "Terverifikasi"],
    ["RS Contoh Denpasar", "Denpasar", "Bali", -8.6705, 115.2126, "Belum diketahui", "Perlu verifikasi"],
    ["RS Contoh Pontianak", "Pontianak", "Kalimantan Barat", -0.0263, 109.3425, "Tidak ada", "Terverifikasi"]
]

COLUMNS = [
    "hospital_name", "city", "province",
    "latitude", "longitude",
    "lab_pa_status", "data_status"
]

if "hospitals" not in st.session_state:
    st.session_state.hospitals = pd.DataFrame(SAMPLE_DATA, columns=COLUMNS)

# ==========================================
# 3. SIDEBAR & DATA IMPORT
# ==========================================
st.sidebar.title("🏥 Healthcare Intelligence")
st.sidebar.caption("Hospital Data & Geospatial System")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Hospital Mapping", "Database Management", "Analytics"]
)

st.sidebar.divider()
st.sidebar.subheader("Import Database")
uploaded = st.sidebar.file_uploader(
    "Upload CSV / Excel",
    type=["csv", "xlsx"]
)

if uploaded is not None:
    signature = (uploaded.name, uploaded.size)
    if st.session_state.get("loaded_file") != signature:
        try:
            if uploaded.name.lower().endswith(".csv"):
                new_data = pd.read_csv(uploaded)
            else:
                new_data = pd.read_excel(uploaded)

            new_data.columns = new_data.columns.astype(str).str.strip().str.lower()
            missing = set(COLUMNS) - set(new_data.columns)

            if missing:
                st.sidebar.error(
                    "Kolom wajib belum tersedia: " + ", ".join(sorted(missing))
                )
            else:
                new_data = new_data[COLUMNS].copy()
                new_data["latitude"] = pd.to_numeric(new_data["latitude"], errors="coerce")
                new_data["longitude"] = pd.to_numeric(new_data["longitude"], errors="coerce")
                new_data["lab_pa_status"] = new_data["lab_pa_status"].fillna("Belum diketahui")
                new_data["data_status"] = new_data["data_status"].fillna("Perlu verifikasi")
                st.session_state.hospitals = new_data
                st.session_state.loaded_file = signature
                st.sidebar.success("Database berhasil dimuat!")
        except Exception as e:
            st.sidebar.error(f"Gagal membaca file: {e}")

# Always use a fresh copy of the latest session data
_df = st.session_state.hospitals.copy()
_df["latitude"] = pd.to_numeric(_df["latitude"], errors="coerce")
_df["longitude"] = pd.to_numeric(_df["longitude"], errors="coerce")

# ==========================================
# 4. COMMON FUNCTIONS
# ==========================================
def export_excel(data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Hospitals")
    return output.getvalue()


def get_filtered_data(data):
    st.sidebar.divider()
    st.sidebar.subheader("Interactive Filters")

    provinces = ["All"] + sorted(data["province"].dropna().astype(str).unique().tolist())
    statuses = ["All"] + sorted(data["lab_pa_status"].dropna().astype(str).unique().tolist())

    province = st.sidebar.selectbox("Province", provinces)
    status = st.sidebar.selectbox("Lab PA Status", statuses)

    result = data.copy()
    if province != "All":
        result = result[result["province"] == province]
    if status != "All":
        result = result[result["lab_pa_status"] == status]
    return result


def render_esri_map(data, height=600, zoom_start=5):
    """Render hospital markers on Esri World Street Map using Folium."""
    valid = data.copy()
    valid["latitude"] = pd.to_numeric(valid["latitude"], errors="coerce")
    valid["longitude"] = pd.to_numeric(valid["longitude"], errors="coerce")
    valid = valid.dropna(subset=["latitude", "longitude"])

    # Remove coordinates outside valid latitude/longitude ranges
    valid = valid[
        valid["latitude"].between(-90, 90)
        & valid["longitude"].between(-180, 180)
    ]

    if valid.empty:
        st.warning("Belum ada data koordinat yang valid untuk ditampilkan di peta.")
        return

    center = [valid["latitude"].mean(), valid["longitude"].mean()]
    esri_tiles = (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
    )

    map_object = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles=esri_tiles,
        attr="Tiles © Esri"
    )

    cluster = MarkerCluster(name="Hospital Locations").add_to(map_object)
    marker_colors = {
        "Ada": "green",
        "Tidak ada": "red",
        "Belum diketahui": "orange"
    }

    for _, row in valid.iterrows():
        status = str(row.get("lab_pa_status", "Belum diketahui"))
        marker_color = marker_colors.get(status, "blue")
        hospital_name = str(row.get("hospital_name", "Hospital"))
        city = str(row.get("city", ""))
        province = str(row.get("province", ""))
        data_status = str(row.get("data_status", ""))

        popup_html = f"""
        <div style="width:220px">
            <b>{hospital_name}</b><br>
            {city}, {province}<br>
            <b>Lab PA:</b> {status}<br>
            <b>Data:</b> {data_status}
        </div>
        """

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            tooltip=hospital_name,
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=marker_color, icon="plus-sign", prefix="glyphicon")
        ).add_to(cluster)

    folium.LayerControl().add_to(map_object)
    components.html(map_object.get_root().render(), height=height, scrolling=True)


def render_status_pie(data, hole=0.45):
    chart_data = data["lab_pa_status"].fillna("Belum diketahui").value_counts().reset_index()
    chart_data.columns = ["Status", "Total"]
    if chart_data.empty:
        st.info("Belum ada data untuk ditampilkan.")
        return
    fig = px.pie(chart_data, names="Status", values="Total", hole=hole)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. DASHBOARD
# ==========================================
if page == "Dashboard":
    st.title("Healthcare Intelligence Dashboard")
    st.caption("Hospital Database & Market Overview")

    total = len(_df)
    available = (_df["lab_pa_status"] == "Ada").sum()
    unavailable = (_df["lab_pa_status"] == "Tidak ada").sum()
    unknown = (_df["lab_pa_status"] == "Belum diketahui").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Hospitals", total)
    c2.metric("Lab PA Available", int(available))
    c3.metric("Without Lab PA", int(unavailable))
    c4.metric("Need Verification", int(unknown))

    st.divider()
    left, right = st.columns([1.5, 1])

    with left:
        st.subheader("Hospital Distribution")
        render_esri_map(_df, height=550, zoom_start=5)

    with right:
        st.subheader("Lab PA Classification")
        render_status_pie(_df)

    st.subheader("Hospital Database Preview")
    st.dataframe(_df, use_container_width=True, hide_index=True)

# ==========================================
# 6. HOSPITAL MAPPING
# ==========================================
elif page == "Hospital Mapping":
    st.title("Hospital Geospatial Mapping")
    st.caption("Explore hospital locations across Indonesia")

    filtered = get_filtered_data(_df)
    st.metric("Filtered Hospitals", len(filtered))

    render_esri_map(filtered, height=650, zoom_start=5)
    st.caption("Green: Lab PA available | Red: No Lab PA | Orange: Unknown")

    st.subheader("Filtered Hospital List")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    if not filtered.empty:
        selected = st.selectbox(
            "Select hospital for Google Maps",
            filtered["hospital_name"].astype(str).tolist()
        )
        hospital = filtered[filtered["hospital_name"].astype(str) == selected].iloc[0]

        if pd.notna(hospital["latitude"]) and pd.notna(hospital["longitude"]):
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
