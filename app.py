
import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from io import BytesIO

st.set_page_config(
    page_title="Healthcare Intelligence",
    page_icon="🏥",
    layout="wide"
)

# ==========================================
# 1. SAMPLE DATABASE
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
    st.session_state.hospitals = pd.DataFrame(
        SAMPLE_DATA, columns=COLUMNS
    )

# ==========================================
# 2. SIDEBAR
# ==========================================

st.sidebar.title("🏥 Healthcare Intelligence")
st.sidebar.caption("Hospital Data & Geospatial System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Hospital Mapping",
        "Database Management",
        "Analytics"
    ]
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
            if uploaded.name.endswith(".csv"):
                new_data = pd.read_csv(uploaded)
            else:
                new_data = pd.read_excel(uploaded)

            new_data.columns = new_data.columns.str.strip().str.lower()

            missing = set(COLUMNS) - set(new_data.columns)

            if missing:
                st.sidebar.error(
                    f"Missing columns: {', '.join(missing)}"
                )
            else:
                new_data = new_data[COLUMNS].copy()
                new_data["latitude"] = pd.to_numeric(
                    new_data["latitude"], errors="coerce"
                )
                new_data["longitude"] = pd.to_numeric(
                    new_data["longitude"], errors="coerce"
                )
                st.session_state.hospitals = new_data
                st.session_state.loaded_file = signature
                st.sidebar.success("Database loaded!")

        except Exception as e:
            st.sidebar.error(str(e))

df = st.session_state.hospitals.copy()

# ==========================================
# 3. COMMON FUNCTIONS
# ==========================================

def export_excel(data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Hospitals")
    return output.getvalue()

def get_filtered_data(data):
    st.sidebar.divider()
    st.sidebar.subheader("Interactive Filters")

    provinces = ["All"] + sorted(
        data["province"].dropna().unique().tolist()
    )
    statuses = ["All"] + sorted(
        data["lab_pa_status"].dropna().unique().tolist()
    )

    province = st.sidebar.selectbox(
        "Province", provinces
    )
    status = st.sidebar.selectbox(
        "Lab PA Status", statuses
    )

    result = data.copy()

    if province != "All":
        result = result[result["province"] == province]

    if status != "All":
        result = result[result["lab_pa_status"] == status]

    return result

# ==========================================
# 4. DASHBOARD
# ==========================================

if page == "Dashboard":

    st.title("Healthcare Intelligence Dashboard")
    st.caption("Hospital Database & Market Overview")

    total = len(df)
    available = (df["lab_pa_status"] == "Ada").sum()
    unavailable = (df["lab_pa_status"] == "Tidak ada").sum()
    unknown = (df["lab_pa_status"] == "Belum diketahui").sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Hospitals", total)
    c2.metric("Lab PA Available", available)
    c3.metric("Without Lab PA", unavailable)
    c4.metric("Need Verification", unknown)

    st.divider()

    left, right = st.columns([1.5, 1])

    with left:
        st.subheader("Hospital Distribution")

        valid = df.dropna(
            subset=["latitude", "longitude"]
        )

        if not valid.empty:
            colors = {
                "Ada": [22, 163, 74, 200],
                "Tidak ada": [220, 38, 38, 200],
                "Belum diketahui": [245, 158, 11, 200]
            }

            valid = valid.copy()
            valid["color"] = valid["lab_pa_status"].map(colors)

            view = pdk.ViewState(
                latitude=valid["latitude"].mean(),
                longitude=valid["longitude"].mean(),
                zoom=4
            )

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=valid,
                get_position="[longitude, latitude]",
                get_fill_color="color",
                get_radius=5000,
                pickable=True
            )

            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip={
                    "text": "{hospital_name}\n{city}, {province}\nLab PA: {lab_pa_status}"
                },
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
            )

            st.pydeck_chart(deck, use_container_width=True)

    with right:
        st.subheader("Lab PA Classification")

        pie = df["lab_pa_status"].value_counts().reset_index()
        pie.columns = ["Status", "Total"]

        fig = px.pie(
            pie,
            names="Status",
            values="Total",
            hole=0.45
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Hospital Database Preview")
    st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# 5. HOSPITAL MAPPING
# ==========================================

elif page == "Hospital Mapping":

    st.title("Hospital Geospatial Mapping")
    st.caption("Explore hospital locations across Indonesia")

    filtered = get_filtered_data(df)

    valid = filtered.dropna(
        subset=["latitude", "longitude"]
    ).copy()

    st.metric("Filtered Hospitals", len(filtered))

    if not valid.empty:

        colors = {
            "Ada": [22, 163, 74, 200],
            "Tidak ada": [220, 38, 38, 200],
            "Belum diketahui": [245, 158, 11, 200]
        }

        valid["color"] = valid["lab_pa_status"].map(colors)

        view = pdk.ViewState(
            latitude=valid["latitude"].mean(),
            longitude=valid["longitude"].mean(),
            zoom=5,
            pitch=0
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=valid,
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius=6000,
            pickable=True
        )

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={
                "text": "{hospital_name}\n{city}, {province}\nLab PA: {lab_pa_status}\nData: {data_status}"
            },
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
        )

        st.pydeck_chart(deck, use_container_width=True)

        st.caption(
            "Green: Lab PA available | Red: No Lab PA | Orange: Unknown"
        )

    else:
        st.warning("No valid coordinates available.")

    st.subheader("Filtered Hospital List")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    if not filtered.empty:
        selected = st.selectbox(
            "Select hospital for Google Maps",
            filtered["hospital_name"].tolist()
        )

        hospital = filtered[
            filtered["hospital_name"] == selected
        ].iloc[0]

        if pd.notna(hospital["latitude"]) and pd.notna(hospital["longitude"]):
            url = (
                "https://www.google.com/maps/search/?api=1&query="
                f"{hospital['latitude']},{hospital['longitude']}"
            )
            st.link_button("Open in Google Maps", url)

# ==========================================
# 6. DATABASE MANAGEMENT
# ==========================================

elif page == "Database Management":

    st.title("Hospital Database Management")
    st.caption("Add, edit, delete and export hospital records")

    st.info(
        "You can edit cells directly in the table. "
        "New rows and deleted rows are also supported."
    )

    edited = st.data_editor(
        st.session_state.hospitals,
        num_rows="dynamic",
        use_container_width=True,
        key="hospital_editor"
    )

    if st.button("Save Table Changes", type="primary"):
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
        lat = col1.number_input(
            "Latitude", value=0.0, format="%.6f"
        )
        lon = col2.number_input(
            "Longitude", value=0.0, format="%.6f"
        )

        lab = st.selectbox(
            "Lab PA Status",
            ["Ada", "Tidak ada", "Belum diketahui"]
        )

        verification = st.selectbox(
            "Data Status",
            ["Terverifikasi", "Perlu verifikasi"]
        )

        submitted = st.form_submit_button("Add Hospital")

        if submitted:
            if name and city and province:
                new_row = pd.DataFrame([[
                    name, city, province, lat, lon, lab, verification
                ]], columns=COLUMNS)

                st.session_state.hospitals = pd.concat(
                    [st.session_state.hospitals, new_row],
                    ignore_index=True
                )

                st.success("Hospital added!")
                st.rerun()
            else:
                st.error("Please complete hospital name, city and province.")

    st.divider()
    st.subheader("Download Database")

    current = st.session_state.hospitals

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
# 7. ANALYTICS
# ==========================================

elif page == "Analytics":

    st.title("Healthcare Market Analytics")
    st.caption("Explore hospital distribution and facility classification")

    filtered = get_filtered_data(df)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Lab PA Status")
        chart = filtered["lab_pa_status"].value_counts().reset_index()
        chart.columns = ["Status", "Count"]

        fig = px.pie(
            chart,
            names="Status",
            values="Count",
            hole=0.4
        )

        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Hospitals by Province")
        province_chart = (
            filtered.groupby("province")
            .size()
            .reset_index(name="Total")
            .sort_values("Total", ascending=True)
        )

        fig2 = px.bar(
            province_chart,
            x="Total",
            y="province",
            orientation="h",
            text="Total"
        )

        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Data Verification Status")

    verification = filtered["data_status"].value_counts().reset_index()
    verification.columns = ["Status", "Total"]

    fig3 = px.bar(
        verification,
        x="Status",
        y="Total",
        text="Total"
    )

    st.plotly_chart(fig3, use_container_width=True)

st.sidebar.divider()
st.sidebar.caption("Healthcare Intelligence | Prototype v1.0")
