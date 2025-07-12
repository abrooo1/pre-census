import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from ea_delineator import main as run_ea_process

st.title("Enumeration Area (EA) Delineation Tool")

st.markdown("""
Upload or select input files and define constraints to generate EAs.
This tool uses population raster and boundary data to create compact, surveyor-friendly EAs.
""")

# Input fields
population_raster = st.file_uploader("Upload Population Raster (GeoTIFF)", type=["tif"])
roads_shapefile = st.file_uploader("Upload Roads Shapefile (.shp)", type=["shp"])
rivers_shapefile = st.file_uploader("Upload Rivers Shapefile (.shp)", type=["shp"])
admin_shapefile = st.file_uploader("Upload Admin Boundaries (.shp)", type=["shp"])

max_population = st.slider("Max Population per EA", min_value=500, max_value=3000, value=750)
max_area_km2 = st.slider("Max Area per EA (km²)", min_value=1.0, max_value=20.0, value=9.0)

if st.button("Generate EAs"):
    if not all([population_raster, roads_shapefile, rivers_shapefile, admin_shapefile]):
        st.error("Please upload all required files.")
    else:
        # Save uploaded files temporarily
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)

        with open(os.path.join(data_dir, "population.tif"), "wb") as f:
            f.write(population_raster.read())
        with open(os.path.join(data_dir, "roads.shp"), "wb") as f:
            f.write(roads_shapefile.read())
        with open(os.path.join(data_dir, "rivers.shp"), "wb") as f:
            f.write(rivers_shapefile.read())
        with open(os.path.join(data_dir, "admin.shp"), "wb") as f:
            f.write(admin_shapefile.read())

        st.info("Running EA delineation process...")
        try:
            from io import StringIO
            import sys

            # Redirect stdout to capture logs
            old_stdout = sys.stdout
            redirected_output = StringIO()
            sys.stdout = redirected_output

            run_ea_process()  # Run the EA process

            sys.stdout = old_stdout

            st.success("EAs generated successfully!")

            # Load result
            eas_gdf = gpd.read_file("output/eas.shp")
            fig, ax = plt.subplots(figsize=(10, 6))
            eas_gdf.plot(ax=ax, column="population", legend=True, cmap="OrRd", edgecolor="black")
            st.pyplot(fig)

            # Provide download link
            st.download_button(
                label="Download EAs Shapefile",
                data=open("output/eas.shp", "rb").read(),
                file_name="eas.shp"
            )

        except Exception as e:
            st.error(f"Error during execution: {str(e)}")
            st.code(str(e))