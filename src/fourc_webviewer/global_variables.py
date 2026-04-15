"""Contains global variables to be used in several files."""

# geometry types for the design conditions
ALL_DC_GEOMETRIES = {
    "POINT": ["POINT", "NODE"],
    "LINE": ["LINE"],
    "SURF": ["SURF", "SURFACE"],
    "VOL": ["VOL", "VOLUME"],
}

# factor which scales the spheres used to represent nodal design conditions and result descriptions with respect to the problem length scale
PV_SPHERE_FRAC_SCALE = 1.0 / 75.0

# enabled suffixes for geometry files
EXODUS_FILE_SUFFIXES = [".exo", ".e"]
VTU_FILE_SUFFIXES = [".vtu"]
SUPPORTED_GEOMETRY_FORMATS = EXODUS_FILE_SUFFIXES + VTU_FILE_SUFFIXES

# Fraction of the problem length scale used to size the visualized slice planes.
PV_SLICE_PLANE_SIZE_FRAC = 0.8
