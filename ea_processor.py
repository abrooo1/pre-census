import geopandas as gpd
import rasterio
from rasterio import features
import numpy as np
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from skimage.util import view_as_blocks


def load_boundaries(roads_path=None, rivers_path=None, settlements_path=None):
    """Load optional boundary layers."""
    boundaries = []

    if roads_path:
        boundaries.append(gpd.read_file(roads_path).to_crs(epsg=3857))
    if rivers_path:
        boundaries.append(gpd.read_file(rivers_path).to_crs(epsg=3857))
    if settlements_path:
        boundaries.append(gpd.read_file(settlements_path).to_crs(epsg=3857))

    if not boundaries:
        return None

    combined = boundaries[0]
    for layer in boundaries[1:]:
        combined = gpd.overlay(combined, layer, how='union')

    return combined


def rasterize_population(pop_raster_path):
    """Convert population GeoTIFF to polygons."""
    with rasterio.open(pop_raster_path) as src:
        image = src.read(1)
        transform = src.transform
        crs = src.crs

    shapes = list(features.shapes(image, transform=transform))
    polygons = []
    for geom, value in shapes:
        if value > 0:
            polygons.append({
                'geometry': shape(geom),
                'population': float(value)
            })

    return gpd.GeoDataFrame(polygons, crs=crs).to_crs(epsg=3857)


def split_by_boundaries(pop_gdf, boundary_gdf):
    """Split population units by visible boundaries."""
    if boundary_gdf is None:
        return pop_gdf.assign(area_km2=lambda x: x.geometry.area / 1e6)

    split_units = gpd.overlay(pop_gdf, boundary_gdf, how='intersection')
    split_units['area_km2'] = split_units.geometry.area / 1e6
    return split_units


def quadtree_split(geometry, max_area_km2, max_pop, pop_density_gdf):
    """Split large area using quadtree decomposition."""
    minx, miny, maxx, maxy = geometry.bounds
    width = maxx - minx
    height = maxy - miny

    if geometry.area / 1e6 <= max_area_km2:
        return [geometry]

    children = []
    half_width = width / 2
    half_height = height / 2

    # Create four quadrants
    quads = [
        Polygon([(minx, miny), (minx + half_width, miny), (minx + half_width, miny + half_height), (minx, miny + half_height)]),
        Polygon([(minx + half_width, miny), (maxx, miny), (maxx, miny + half_height), (minx + half_width, miny + half_height)]),
        Polygon([(minx, miny + half_height), (minx + half_width, miny + half_height), (minx + half_width, maxy), (minx, maxy)]),
        Polygon([(minx + half_width, miny + half_height), (maxx, miny + half_height), (maxx, maxy), (minx + half_width, maxy)])
    ]

    for quad in quads:
        if not geometry.contains(quad.centroid):
            continue

        clipped_quad = quad.intersection(geometry)
        if clipped_quad.is_empty:
            continue

        quad_pop = sum(pop_density_gdf[
            pop_density_gdf.geometry.within(clipped_quad)].population)

        if quad_pop > max_pop or clipped_quad.area / 1e6 > max_area_km2:
            children.extend(quadtree_split(clipped_quad, max_area_km2, max_pop, pop_density_gdf))
        else:
            children.append(clipped_quad)

    return children


def merge_units(units_gdf, max_pop=750, max_area=9.0):
    """Merge small units into EAs based on constraints."""
    merged = []
    current_geom = None
    current_pop = 0
    current_area = 0

    for _, row in units_gdf.iterrows():
        if (current_pop + row.population > max_pop) or \
           (current_area + row.area_km2 > max_area):

            if current_geom:
                merged.append({'geometry': current_geom, 'population': current_pop, 'area_km2': current_area})
                current_geom = None
                current_pop = 0
                current_area = 0

        if current_geom is None:
            current_geom = row.geometry
            current_pop = row.population
            current_area = row.area_km2
        else:
            try:
                current_geom = current_geom.union(row.geometry)
            except:
                continue
            current_pop += row.population
            current_area += row.area_km2

    if current_geom:
        merged.append({'geometry': current_geom, 'population': current_pop, 'area_km2': current_area})

    return gpd.GeoDataFrame(merged, crs=units_gdf.crs)


def generate_eas(admin_path, pop_raster_path,
                  max_pop=750, max_area=9.0,
                  roads_path=None, rivers_path=None, settlements_path=None):
    """Main function to generate EAs."""
    print("Loading admin boundary...")
    admin_gdf = gpd.read_file(admin_path).to_crs(epsg=3857)

    print("Rasterizing population...")
    pop_gdf = rasterize_population(pop_raster_path)

    print("Loading optional boundary layers...")
    boundary_gdf = load_boundaries(roads_path, rivers_path, settlements_path)

    print("Splitting by boundaries...")
    split_units = split_by_boundaries(pop_gdf, boundary_gdf)

    print("Merging units into EAs...")
    eas_gdf = merge_units(split_units, max_pop=max_pop, max_area=max_area)

    print("Running quadtree on sparse areas...")
    sparse_areas = []
    for idx, row in eas_gdf.iterrows():
        if row.population < max_pop * 0.3 or row.area_km2 < max_area * 0.3:
            quads = quadtree_split(row.geometry, max_area, max_pop, pop_gdf)
            for q in quads:
                q_pop = sum(pop_gdf[pop_gdf.geometry.within(q)].population)
                sparse_areas.append({'geometry': q, 'population': q_pop, 'area_km2': q.area / 1e6})

    if sparse_areas:
        sparse_gdf = gpd.GeoDataFrame(sparse_areas, crs=eas_gdf.crs)
        eas_gdf = gpd.GeoDataFrame(pd.concat([eas_gdf, sparse_gdf], ignore_index=True))

    return eas_gdf