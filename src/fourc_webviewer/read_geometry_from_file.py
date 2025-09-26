"""I/O for Exodus II. This file is based on the meshio project see:

https://github.com/nschloe/meshio/blob/main/src/meshio/exodus/_exodus.py
"""

import re

import numpy as np
from meshio.__about__ import __version__
from meshio._common import warn
from meshio._exceptions import ReadError
from meshio._mesh import Mesh
import pyvista as pv
from fourcipp.fourc_input import FourCInput
from lnmmeshio import read, write
from lnmmeshio.meshio_to_discretization import mesh2Discretization
from lnmmeshio.discretization import (
    PointNodeset,
    LineNodeset,
    SurfaceNodeset,
    VolumeNodeset,
)
from lnmmeshio.fiber import Fiber
from pathlib import Path

exodus_to_meshio_type = {
    "SPHERE": "vertex",
    # curves
    "BEAM": "line",
    "BEAM2": "line",
    "BEAM3": "line3",
    "BAR2": "line",
    # surfaces
    "SHELL": "quad",
    "SHELL4": "quad",
    "SHELL8": "quad8",
    "SHELL9": "quad9",
    "QUAD": "quad",
    "QUAD4": "quad",
    "QUAD5": "quad5",
    "QUAD8": "quad8",
    "QUAD9": "quad9",
    #
    "TRI": "triangle",
    "TRIANGLE": "triangle",
    "TRI3": "triangle",
    "TRI6": "triangle6",
    "TRI7": "triangle7",
    # 'TRISHELL': 'triangle',
    # 'TRISHELL3': 'triangle',
    # 'TRISHELL6': 'triangle6',
    # 'TRISHELL7': 'triangle',
    #
    # volumes
    "HEX": "hexahedron",
    "HEXAHEDRON": "hexahedron",
    "HEX8": "hexahedron",
    "HEX9": "hexahedron9",
    "HEX20": "hexahedron20",
    "HEX27": "hexahedron27",
    #
    "TETRA": "tetra",
    "TETRA4": "tetra4",
    "TET4": "tetra4",
    "TETRA8": "tetra8",
    "TETRA10": "tetra10",
    "TETRA14": "tetra14",
    #
    "PYRAMID": "pyramid",
    "WEDGE": "wedge",
}
meshio_to_exodus_type = {v: k for k, v in exodus_to_meshio_type.items()}


def _categorize(names):
    """Check if there are any <name>R, <name>Z tuples or <name>X, <name>Y,
    <name>Z triplets in the point data. If yes, they belong together.

    Args:
        names (list):  list of data names
    Returns:
        list, list, list: lists of triplets; single, double, triple
    """
    # Check if there are any <name>R, <name>Z tuples or <name>X, <name>Y, <name>Z
    # triplets in the point data. If yes, they belong together.
    single = []
    double = []
    triple = []
    is_accounted_for = [False] * len(names)
    k = 0
    while True:
        if k == len(names):
            break
        if is_accounted_for[k]:
            k += 1
            continue
        name = names[k]
        if name[-1] == "X":
            i_x = k
            try:
                i_y = names.index(name[:-1] + "Y")
            except ValueError:
                i_y = None
            try:
                i_z = names.index(name[:-1] + "Z")
            except ValueError:
                i_z = None
            if i_y and i_z:
                triple.append((name[:-1], i_x, i_y, i_z))
                is_accounted_for[i_x] = True
                is_accounted_for[i_y] = True
                is_accounted_for[i_z] = True
            else:
                single.append((name, i_x))
                is_accounted_for[i_x] = True
        elif name[-2:] == "_R":
            i_r = k
            try:
                i_z = names.index(name[:-2] + "_Z")
            except ValueError:
                i_z = None
            if i_z:
                double.append((name[:-2], i_r, i_z))
                is_accounted_for[i_r] = True
                is_accounted_for[i_z] = True
            else:
                single.append((name, i_r))
                is_accounted_for[i_r] = True
        else:
            single.append((name, k))
            is_accounted_for[k] = True

        k += 1

    if not all(is_accounted_for):
        raise ReadError()
    return single, double, triple


def read_exodus(filename, use_set_names=False):  # noqa: C901
    """Reads a given exodus file.

    Args:
        filename (str | Path): file to be read.
        use_set_names (bool): should the set names for point and cell sets be utilized?

    Returns:
        meshio.Mesh: mesh object corresponding to the input exo file.
    """
    import netCDF4

    with netCDF4.Dataset(filename) as nc:
        # assert nc.version == np.float32(5.1)
        # assert nc.api_version == np.float32(5.1)
        # assert nc.floating_point_word_size == 8

        # assert b''.join(nc.variables['coor_names'][0]) == b'X'
        # assert b''.join(nc.variables['coor_names'][1]) == b'Y'
        # assert b''.join(nc.variables['coor_names'][2]) == b'Z'

        points = np.zeros((len(nc.dimensions["num_nodes"]), 3))
        point_data_names = []
        cell_data_names = []
        pd = {}
        cd = {}
        cells = []
        ns_names = []
        ns_ids = []
        eb_ids = []
        eb_names = []
        ns = []
        point_sets = {}
        info = []

        cell_sets = {}

        element_running_index = 0

        for key, value in nc.variables.items():
            if key == "info_records":
                value.set_auto_mask(False)
                for c in value[:]:
                    info += [b"".join(c).decode("UTF-8")]
            elif key == "qa_records":
                value.set_auto_mask(False)
                for val in value:
                    info += [b"".join(c).decode("UTF-8") for c in val[:]]
            elif key[:7] == "connect":
                meshio_type = exodus_to_meshio_type[value.elem_type.upper()]
                cell_sets[str(len(cell_sets) + 1)] = np.arange(
                    element_running_index, element_running_index + len(value[:])
                )
                cells.append((meshio_type, value[:] - 1))
                element_running_index += len(value[:])
            elif key == "coord":
                points = nc.variables["coord"][:].T
            elif key == "coordx":
                points[:, 0] = value[:]
            elif key == "coordy":
                points[:, 1] = value[:]
            elif key == "coordz":
                points[:, 2] = value[:]
            elif key == "name_nod_var":
                value.set_auto_mask(False)
                point_data_names = [b"".join(c).decode("UTF-8") for c in value[:]]
            elif key[:12] == "vals_nod_var":
                idx = 0 if len(key) == 12 else int(key[12:]) - 1
                value.set_auto_mask(False)
                # For now only take the first value
                pd[idx] = value[0]
                if len(value) > 1:
                    warn("Skipping some time data")
            elif key == "name_elem_var":
                value.set_auto_mask(False)
                cell_data_names = [b"".join(c).decode("UTF-8") for c in value[:]]
            elif key[:13] == "vals_elem_var":
                # eb: element block
                m = re.match("vals_elem_var(\\d+)?(?:eb(\\d+))?", key)
                idx = 0 if m.group(1) is None else int(m.group(1)) - 1
                block = 0 if m.group(2) is None else int(m.group(2)) - 1

                value.set_auto_mask(False)
                # For now only take the first value
                if idx not in cd:
                    cd[idx] = {}
                cd[idx][block] = value[0]

                if len(value) > 1:
                    warn("Skipping some time data")
            elif key == "ns_prop1":
                value.set_auto_mask(False)
                ns_ids = value[:]
            elif key == "ns_names":
                value.set_auto_mask(False)
                ns_names = [b"".join(c).decode("UTF-8") for c in value[:]]
            elif key == "eb_prop1":
                value.set_auto_mask(False)
                eb_ids = value[:]
            elif key == "eb_names":
                value.set_auto_mask(False)
                eb_names = [b"".join(c).decode("UTF-8") for c in value[:]]
            elif key.startswith("node_ns"):  # Expected keys: node_ns1, node_ns2
                ns.append(value[:] - 1)  # Exodus is 1-based

        # merge element block data; can't handle blocks yet
        for k, value in cd.items():
            cd[k] = np.concatenate(list(value.values()))

        # Check if there are any <name>R, <name>Z tuples or <name>X, <name>Y, <name>Z
        # triplets in the point data. If yes, they belong together.
        single, double, triple = _categorize(point_data_names)

        point_data = {}
        for name, idx in single:
            point_data[name] = pd[idx]
        for name, idx0, idx1 in double:
            point_data[name] = np.column_stack([pd[idx0], pd[idx1]])
        for name, idx0, idx1, idx2 in triple:
            point_data[name] = np.column_stack([pd[idx0], pd[idx1], pd[idx2]])

        cell_data = {}
        k = 0
        for _, cell in cells:
            n = len(cell)
            for name, data in zip(cell_data_names, cd.values()):
                if name not in cell_data:
                    cell_data[name] = []
                cell_data[name].append(data[k : k + n])
            k += n

    # write point and cell sets with correct ids
    point_sets = {str(id): dat.tolist() for id, dat in zip(ns_ids, ns)}
    cell_sets = {name: cell_set for name, cell_set in zip(eb_ids, cell_sets.values())}

    if use_set_names:
        point_sets = {name: dat for name, dat in zip(ns_names, ns)}
        cell_sets = {
            name: cell_set for name, cell_set in zip(eb_names, cell_sets.values())
        }

    return Mesh(
        points,
        cells,
        point_data=point_data,
        cell_data=cell_data,
        point_sets=point_sets,
        info=info,
        cell_sets=cell_sets,
    )


def check_for_geometry_files(fourc_yaml: FourCInput) -> list:
    """Checks the content of a fourc yaml file for referenced geometry files, e.g., contained within
    STRUCTURE GEOMETRY / FILE. Returns the identified file, whereby we previously verify whether all given files are the same file (required by 4C currently).

    Args:
        fourc_yaml(FourCInput): content of the fourc yaml file to be verified.
    Returns:
        list: list of file names (including extension) of files referenced in the fourc yaml file. If none where found, the list is empty.
    """

    keys_ending_with_geometry = [
        k for k in fourc_yaml.sections if k.endswith("GEOMETRY")
    ]
    # loop through keys and get the corresponding files
    geometry_files = []
    for k in keys_ending_with_geometry:
        if "FILE" not in fourc_yaml[k]:
            raise Exception("Specified geometry section, but without a FILE!")
        geometry_files.append(fourc_yaml[k]["FILE"])

    if not geometry_files:
        return []

    # currently, only a single file input is allowed for both 4C and the webviewer -> enfoprce uniqueness
    if len(set(geometry_files)) != 1:
        raise Exception(
            "Currently, 4C and the webviewer only allow for a single geometry file as input."
        )
    return [geometry_files[0]]


class FourCGeometry:
    def __init__(self, fourc_yaml_file: str | Path, temp_dir: str | Path):
        """Initialize geometry class based on the given input file.

        Args:
            fourc_yaml_file (str | Path): path to the yaml input
            temp_dir (str | Path): path to the yaml input
        """

        # read-in and save yaml file content
        self._fourc_yaml_file = fourc_yaml_file
        self._fourc_yaml = FourCInput.from_4C_yaml(input_file_path=fourc_yaml_file)

        # create vtu file based on the geometry type
        self._vtu_file_path = str(Path(temp_dir) / f"{Path(fourc_yaml_file).stem}.vtu")
        if self.geom_type == "exo":
            try:
                # read exodus mesh
                self._mesh_file = (
                    Path(fourc_yaml_file).parent
                    / self._fourc_yaml["STRUCTURE GEOMETRY"]["FILE"]
                )
                if not self._mesh_file.exists():
                    raise Exception(
                        f"The mesh file {self._mesh_file} does not exist for the fourc yaml file {fourc_yaml_file}"
                    )
                self._mesh_exo = read_exodus(
                    filename=self._mesh_file,
                    use_set_names=False,
                )
                # convert mesh to discretization preliminarily, without further info from the yaml file -> this is then added below
                self._dis = mesh2Discretization(mesh=self._mesh_exo)

                # enhance discretization with further information from the fourc yaml file
                self.enhance_exo_dis_with_fourc_yaml_info()

                # convert to vtu
                self.convert_dis_to_vtu()
            except Exception as exc:
                print(
                    exc
                )  # currently, we throw the conversion error as terminal output
                self._vtu_file_path = ""

        elif self.geom_type == "legacy":
            # convert yaml file to vtu file and return the path to the vtu file
            try:
                self._dis = read(str(fourc_yaml_file))
                self.convert_dis_to_vtu()
            except Exception as exc:  # if file conversion not successful
                print(
                    exc
                )  # currently, we throw the lnmmeshio conversion error as terminal output
                self._vtu_file_path = ""

    @property
    def geom_type(self) -> str:
        """Get geometry type for the given yaml input."""
        if check_for_geometry_files(fourc_yaml=self._fourc_yaml):
            return "exo"
        elif [k for k in self._fourc_yaml.sections if k.endswith("ELEMENTS")]:
            return "legacy"
        else:
            raise Exception(
                f"Cannot determine geometry type for the given input file {self._fourc_yaml_file} with sections {self._fourc_yaml.sections}"
            )

    @property
    def vtu_file_path(self):
        """Get the path to the converted vtu file."""
        return self._vtu_file_path

    @vtu_file_path.setter
    def vtu_file_path(self, value):
        """Set the path to the converted vtu file."""
        self._vtu_file_path = value

    def get_element_ids_of_block(self, element_block_id):
        """Get element ids of a given block (element block id is 1-based)."""
        return np.where(self._dis.cell_data["GROUP_ID"] == element_block_id - 1)[0]

    def get_all_nodes_in_element_block_exo(self, element_block_id: int):
        """Retrieve all unique node indices in a specified element block for Exodus geometry.
        Args:
            element_block_id (int): id of the element block to retrieve the nodes from
        Returns:
            ndarray: array of node indices within the specified element block.
        """

        # get cummulative element counts for each block
        cum_el_counts = np.cumsum([len(cs) for cs in self._mesh_exo.cells])

        # get all element ids in the considered cell set
        all_el_ids = self._mesh_exo.cell_sets[element_block_id]

        # declare array containing all node ids
        all_node_ids = []

        for el_id in all_el_ids:
            # get block index
            block_index = np.searchsorted(cum_el_counts, el_id, side="right")

            # get relative element id within the block
            if block_index == 0:
                rel_el_id = el_id
            else:
                rel_el_id = el_id - cum_el_counts[block_index - 1]

            # retrieve corresponding node ids
            all_node_ids.append(self._mesh_exo.cells[block_index].data[rel_el_id - 1])

        return np.unique(all_node_ids)

    def enhance_exo_dis_with_fourc_yaml_info(self):

        # --> read in nodeset info (pointnodesets, linenodesets, surfacenodesets, volumenodesets) based on the design sections specified in the yaml file
        # get all design sections
        all_design_sections = [
            {sec: val} for sec, val in self._fourc_yaml.items() if "DESIGN " in sec
        ]

        # loop through design sections, add point, surf, line, vol nodesets
        for dsect in all_design_sections:
            # get condition name
            dsect_name = next(iter(dsect))

            # check geometry type of condition
            geometry_type = ""
            if " POINT " in dsect_name:
                geometry_type = "point"
            elif " LINE " in dsect_name:
                geometry_type = "line"
            elif " SURF " in dsect_name:
                geometry_type = "surf"
            elif " VOL " in dsect_name:
                geometry_type = "vol"
            else:
                raise Exception(
                    "Cannot yet handle conditions without geometric references (POINT, LINE, SURF, VOL) in their condition names!"
                )

            # add the corresponding nodesets for each geometry type
            for entity in dsect[dsect_name]:
                # get entity number
                entity_number = entity["E"]

                # get entity type: must be available for exo integration!
                if "ENTITY_TYPE" not in entity.keys():
                    raise Exception(
                        f"The entity type is not provided for entity {entity_number} of {dsect_name}! For exodus files, this must be provided!"
                    )
                else:
                    entity_type = entity["ENTITY_TYPE"]
                    if entity_type == "legacy_id":
                        raise Exception(
                            "No support provided yet for entity type legacy_id when considering exodus files!"
                        )

                # get referenced nodes in the considered entity
                all_cond_nodes = []
                if entity_type == "node_set_id":
                    all_cond_nodes = np.array(
                        self._mesh_exo.point_sets[f"{entity_number}"]
                    )
                elif entity_type == "element_block_id":
                    all_cond_nodes = self.get_all_nodes_in_element_block_exo(
                        element_block_id=entity_number
                    )

                # add point sets
                if geometry_type == "point":
                    for cond_node_id, cond_node in enumerate(all_cond_nodes):
                        self._dis.nodes[cond_node].pointnodesets.append(
                            PointNodeset(id=str(entity_number))
                            # PointNodeset(id=len(dis_exo.nodes[cond_node].pointnodesets))
                        )
                elif geometry_type == "line":
                    for cond_node_id, cond_node in enumerate(all_cond_nodes):
                        self._dis.nodes[cond_node].linenodesets.append(
                            LineNodeset(id=str(entity_number))
                        )

                elif geometry_type == "surf":
                    for cond_node_id, cond_node in enumerate(all_cond_nodes):
                        self._dis.nodes[cond_node].surfacenodesets.append(
                            SurfaceNodeset(id=str(entity_number))
                        )

                elif geometry_type == "vol":
                    for cond_node_id, cond_node in enumerate(all_cond_nodes):
                        self._dis.nodes[cond_node].volumenodesets.append(
                            VolumeNodeset(id=str(entity_number))
                        )

        # -->  read-in element block info and add it to discretization
        # read * GEOMETRY sections
        all_geometry_section_names = [
            k for k in self._fourc_yaml.sections if k.endswith("GEOMETRY")
        ]
        if all_geometry_section_names:
            all_geometry_sections = [
                self._fourc_yaml[n] for n in all_geometry_section_names
            ]
        else:
            raise Exception(
                "At least 1 GEOMETRY section must be present when using the Exodus geometry format!"
            )
        # loop through geometry sections
        for geom_sect in all_geometry_sections:
            # loop through element blocks
            for eb_dict in geom_sect["ELEMENT_BLOCKS"]:
                # copy the dict to operate on it without affecting the section
                eb_dict_copy = eb_dict.copy()

                # read element block id
                eb_id = eb_dict_copy.pop("ID")

                # now read the field
                eb_field = next(iter(eb_dict_copy))
                eb_field_info = eb_dict_copy[eb_field]

                # read element type
                eb_ele_type = next(iter(eb_field_info))

                # read material
                eb_material = eb_field_info[eb_ele_type]["MAT"]

                # fiber reading implemented, but not verified just yet...
                eb_fibers = []
                if "FIBER1" in eb_field_info[eb_ele_type]:
                    eb_fibers.append({"FIBER1": eb_field_info[eb_ele_type]["FIBER1"]})
                if "FIBER2" in eb_field_info[eb_ele_type]:
                    eb_fibers.append({"FIBER2": eb_field_info[eb_ele_type]["FIBER2"]})
                if "FIBER3" in eb_field_info[eb_ele_type]:
                    eb_fibers.append({"FIBER3": eb_field_info[eb_ele_type]["FIBER3"]})

                # loop through block elements and append the obtained information
                for elements in self._dis.elements.values():
                    for ele in elements:
                        # verify whether we are in the right block
                        if ele.data["GROUP_ID"] == eb_id - 1:
                            # add material
                            ele.options["MAT"] = eb_material

                            # add fibers -> verify!
                            for eb_f in eb_fibers:
                                ele.fibers[next(iter(eb_f))] = Fiber(
                                    fib=np.array(eb_f[next(iter(eb_f))])
                                )

    def convert_dis_to_vtu(self, override=True):
        """Convert discretization to vtu.

        Args:
            override (bool, optional): Overwrite existing file. Defaults to True
        """

        self.prepare_dis_for_vtu_output()

        # write case file with lnmmeshio
        write(
            self.vtu_file_path,
            self._dis,
            file_format="vtu",
            override=override,
        )

    def prepare_dis_for_vtu_output(self):
        """Prepares discretization for vtu conversion by adding data contained within the yaml file (e.g. material id, design conditions) as nodal or element data."""
        self._dis.compute_ids(zero_based=False)

        # write node data
        for n in self._dis.nodes:
            # write node id
            n.data["node-id"] = n.id
            n.data["node-coords"] = n.coords

            # write fibers
            for name, f in n.fibers.items():
                n.data["node-" + name] = f.fiber

            # write dpoints
            for dp in n.pointnodesets:
                n.data["dpoint{0}".format(dp.id)] = 1.0

            # write dlines
            for dl in n.linenodesets:
                n.data["dline{0}".format(dl.id)] = 1.0

            # write dsurfs
            for ds in n.surfacenodesets:
                n.data["dsurf{0}".format(ds.id)] = 1.0

            # write dvols
            for dv in n.volumenodesets:
                n.data["dvol{0}".format(dv.id)] = 1.0

        # write element data
        for elements in self._dis.elements.values():
            for ele in elements:
                ele.data["element-id"] = ele.id

                # write mat
                if "MAT" in ele.options:
                    ele.data["element-material"] = int(ele.options["MAT"])

                # write fibers
                for name, f in ele.fibers.items():
                    ele.data["element-" + name] = f.fiber

    def __str__(self):
        """Print representation."""
        string = "4C Geometry"
        string += f"\n Geometry type: {self.geom_type}"
        string += f"\n Path to converted vtu: {self.vtu_file_path}"
        return string


temp_dir = "/home/dragos-ana/temp"

fourc_geom_exo = FourCGeometry(
    fourc_yaml_file="/home/dragos-ana/workspace/4C/tests/tutorials/tutorial_battery.4C.yaml",
    temp_dir=temp_dir,
)
print(fourc_geom_exo)


fourc_geom_legacy = FourCGeometry(
    fourc_yaml_file=Path(__file__).parents[1]
    / "fourc_webviewer_default_files/ssti_mono_3D_3hex8_elch_s2i_butlervolmerthermo_growthlaw.4C.yaml",
    temp_dir=temp_dir,
)
print(fourc_geom_legacy)


# current_default_file = Path()
# temp_vtu_path_current = convert_to_vtu(
#    fourc_yaml_file_path=current_default_file, temp_dir="/home/dragos-ana/temp"
# )
# pv_current = pv.read(filename=temp_vtu_path_current)
# print(pv_current.point_data)
# print(pv_current.cell_data)
