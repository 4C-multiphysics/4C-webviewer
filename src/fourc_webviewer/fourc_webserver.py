"""This module defines the FourCWebServer class, which manages the application
state, synchronizes server variables, and handles PyVista rendering for the 4C
web viewer."""

import copy
import re
import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv
from fourcipp import CONFIG
from trame.app import get_server
from trame.decorators import TrameApp, change, controller

import fourc_webviewer.pyvista_render as pv_render
from fourc_webviewer.gui_utils import create_gui
from fourc_webviewer.input_file_utils.fourc_yaml_file_visualization import (
    convert_to_vtu,
    function_plot_figure,
)
from fourc_webviewer.input_file_utils.io_utils import (
    create_file_object_for_browser,
    get_master_and_linked_material_indices,
    read_fourc_yaml_file,
    write_fourc_yaml_file,
)
from fourc_webviewer.python_utils import convert_string2number, find_value_recursively

# always set pyvista to plot off screen with Trame
pv.OFF_SCREEN = True


@TrameApp()
class FourCWebServer:
    """Trame webserver for FourC input files containing the server and its
    components (e.g., state, controller) along with other relevant server-only
    variables."""

    def __init__(
        self,
        fourc_yaml_file,
        page_title="4C Webviewer",
    ):
        """Constructor.

        Args:
            fourc_yaml_file (string|Path): path to the input fourc yaml file.
            page_title (string): page title appearing in the browser
            tab.
        """

        self.server = get_server()

        # declare server-side variable dict: variables which should not
        # be exposed to the client-side
        self._server_vars = {}

        # set basic webserver info
        self.state.trame__title = (
            page_title  # needs to be added to the state to be displayed in the browser
        )
        self._server_vars["render_count"] = {
            "change_selected_material": 0,
            "change_fourc_yaml_file": 0,
        }  # dict used to track whether the initial rendering was already performed in @change functions

        # create temporary directory
        self._server_vars["temp_dir_object"] = tempfile.TemporaryDirectory()

        # initialize state variables for the different modes and
        # statuses of the client (e.g. view mode versus edit mode,
        # read-in and export status, ...)
        self.init_mode_state_vars()

        # read basic fourc yaml file info and store either to state or
        # server vars
        (
            self._server_vars["fourc_yaml_content"],
            self._server_vars["fourc_yaml_lines"],
            self._server_vars["fourc_yaml_size"],
            self._server_vars["fourc_yaml_last_modified"],
            self._server_vars["fourc_yaml_read_in_status"],
        ) = read_fourc_yaml_file(fourc_yaml_file)

        if self._server_vars["fourc_yaml_read_in_status"]:
            self.state.read_in_status = self.state.all_read_in_statuses["success"]
        else:
            self.state.read_in_status = self.state.all_read_in_statuses[
                "validation_error"
            ]

        self._server_vars["fourc_yaml_name"] = Path(fourc_yaml_file).name
        self.state.fourc_yaml_file = create_file_object_for_browser(
            self._server_vars["fourc_yaml_name"],
            self._server_vars["fourc_yaml_lines"],
            self._server_vars["fourc_yaml_size"],
            self._server_vars["fourc_yaml_last_modified"],
        )

        # initialize state object
        self.init_state_and_server_vars()

        # convert file to vtu and create dedicated render objects
        self.state.vtu_path = convert_to_vtu(
            fourc_yaml_file,
            Path(self._server_vars["temp_dir_object"].name),
        )
        if self.state.vtu_path == "":
            self.state.read_in_status = self.state.all_read_in_statuses[
                "vtu_conversion_error"
            ]

        self.update_pyvista_render_objects(init_rendering=True)

        # create ui
        create_gui(self.server, self._server_vars["render_window"])

    @property
    def state(self):
        """Get state."""

        # self.state contains all the state variables to be shared between server and client
        return self.server.state

    @property
    def ctrl(self):
        """Get controller."""
        # self.ctrl contains all the control functions callable on both the Javascript client-side and the Python server (running on the Python server)
        return self.server.controller

    def init_state_and_server_vars(self):
        """Initialize state variables (reactive shared state) and server-side
        only variables, particularly the ones related to the fourc yaml
        content."""

        ### --- self.state VARIABLES FOR INPUT FILE CONTENT --- ###
        # name of the 4C yaml file
        self.state.fourc_yaml_name = self._server_vars["fourc_yaml_name"]
        # description as given in the TITLE section
        try:
            self.state.description = "\n".join(
                self._server_vars["fourc_yaml_content"]["TITLE"]
            )  # list of lines(strings): input file description
        except:  # the description is not always provided: then initialize empty string
            self.state.description = ""

        # path to the fourc yaml file to be exported after editing the
        # content via the GUI
        self.state.export_fourc_yaml_path = str(
            Path(self._server_vars["temp_dir_object"].name)
            / f"new_{self.state.fourc_yaml_file['name']}"
        )

        # get state variables of the general sections
        self.init_general_sections_state_and_server_vars()

        # create state variable for the section names (this
        # includes all relevant interactive sections, e.g., also the
        # materials, because we want to create a dropdown list from it)
        self.state.section_names = {
            k: {
                "subsections": list(v.keys()),
                "content_mode": self.state.all_content_modes["general_section"],
            }
            for k, v in self.state.general_sections.items()
        }

        # get state variables of the material section
        self.state.section_names["MATERIALS"] = {
            "subsections": ["OVERVIEW", "CLONING MATERIAL MAP"],
            "content_mode": self.state.all_content_modes["materials_section"],
        }
        self.init_materials_state_and_server_vars()

        # initialize the design condition state and server variables
        self.state.section_names["DESIGN CONDITIONS"] = {
            "subsections": ["DESIGN CONDITIONS"],
            "content_mode": self.state.all_content_modes["design_conditions_section"],
        }
        self.init_design_conditions_state_and_server_vars()

        # initialize the result description state and server variables
        self.state.section_names["RESULT DESCRIPTION"] = {
            "subsections": ["RESULT DESCRIPTION"],
            "content_mode": self.state.all_content_modes["result_description_section"],
        }
        self.init_result_description_state_and_server_vars()

        # initialize the function section state and server variables
        self.state.section_names["FUNCTIONS"] = {
            "subsections": ["FUNCTIONS"],
            "content_mode": self.state.all_content_modes["funct_section"],
        }
        self.init_funct_state_and_server_vars()

        # set initial section selection
        self.state.selected_main_section_name = list(self.state.section_names.keys())[0]
        self.state.selected_section_name = self.state.section_names[
            self.state.selected_main_section_name
        ]["subsections"][0]

        return

    def sync_server_vars_from_state(self):
        """Syncs the server variables containing the input file content based
        on the current state variables.

        We call this before exporting to a new input file.
        """

        # sync description
        self._server_vars["fourc_yaml_content"]["TITLE"] = self.state.description.split(
            "\n"
        )

        # sync all other sections
        self.sync_general_sections_from_state()
        self.sync_materials_sections_from_state()
        self.sync_design_conditions_sections_from_state()
        self.sync_result_description_section_from_state()
        self.sync_funct_section_from_state()

    def update_pyvista_render_objects(self, init_rendering=False):
        """Update/ initialize pyvista view objects (reader, thresholds, global
        COS, ...) for the rendered window. The saved vtu file path is hereby
        utilized.

        Args:
            init_rendering (bool): perform initialization tasks? (True:
            yes | False: no -> only updating)
        """

        # initialization tasks
        if init_rendering:
            # initialization: declare render window as a pyvista plotter
            self._server_vars["render_window"] = pv.Plotter()

        # get problem mesh
        self._server_vars["pv_mesh"] = pv.read(self.state.vtu_path)

        # get mesh of the selected material
        master_mat_ind = self.determine_master_mat_ind_for_current_selection()
        self._server_vars["pv_selected_material_mesh"] = self._server_vars[
            "pv_mesh"
        ].threshold(
            value=(master_mat_ind - 0.05, master_mat_ind + 0.05),
            scalars="element-material",
        )

        # get nodes of the selected condition geometry + entity
        self._server_vars["pv_selected_dc_geometry_entity"] = pv.PointSet(
            self._server_vars["pv_mesh"]
        ).threshold(
            value=1.0,
            scalars=f"d{self.state.selected_dc_geometry_type.lower()}{self.state.selected_dc_entity.replace('E', '')}",
            preference="point",
        )

        # get coords of node with prescribed result description
        self._server_vars["pv_selected_result_description_node_coords"] = (
            self._server_vars["pv_mesh"].points[
                self.state.result_description_section[
                    self.state.selected_result_description_id
                ]["PARAMETERS"]["NODE"]
                - 1,
                :,
            ]
        )

        # update plotter / rendering
        pv_render.update_pv_plotter(
            self._server_vars["render_window"],
            self._server_vars["pv_mesh"],
            self._server_vars["pv_selected_material_mesh"],
            self._server_vars["pv_selected_dc_geometry_entity"],
            self._server_vars["pv_selected_result_description_node_coords"],
        )

    def init_general_sections_state_and_server_vars(self):
        """Get the general sections and cluster them into subsections. For
        example, SCALAR TRANSPORT DYNAMIC / SCALAR TRANSPORT
        DYNAMIC/STABILIZATION, SCALAR TRANSPORT DYNAMIC/S2I COUPLING are all
        subsections contained within the same main section SCALAR TRANSPORT
        DYNAMIC. Then we add dedicated state and server variables.

        NOTE: we only look at the general setting sections. Hence, we
        exclude the sections related to:
            - title (containing the file description),
            - materials,
            - functions,
            - boundary conditions,
            - result description
            - geometry,
        which are handled separately. For the solvers, we take the
        approach to add them up to the main section SOLVERS.
        """

        self.state.json_schema = CONFIG["json_schema"]

        # define substrings of section names to exclude
        substr_to_exclude = ["DESIGN", "TOPOLOGY", "ELEMENTS", "NODE", "FUNCT"]
        # define full section names to exclude
        sect_to_exclude = [
            "MATERIALS",
            "TITLE",
            "CLONING MATERIAL MAP",
            "RESULT DESCRIPTION",
        ]

        # loop through input file sections
        self.state.general_sections = {}
        for section_name, section_data in self._server_vars[
            "fourc_yaml_content"
        ].sections.items():
            if (
                not any(substr in section_name for substr in substr_to_exclude)
                and not section_name in sect_to_exclude
            ):  # account for sections to be excluded as defined above
                # check if the current section is "SOLVER<number>"
                if re.match("^SOLVER [0-9]+", section_name):  # yes
                    # if the main section "SOLVERS" is not already saved,
                    # create dedicated key
                    if "SOLVERS" not in self.state.general_sections.keys():
                        self.state.general_sections["SOLVERS"] = {}

                    # add function subsection
                    self.state.general_sections["SOLVERS"][section_name] = section_data

                # general, no-solver section
                else:
                    # get main section name
                    main_section_name = section_name.split("/")[0]

                    # if the main section is not already saved, create dedicated key
                    if main_section_name not in self.state.general_sections.keys():
                        self.state.general_sections[main_section_name] = {}

                    # add subsection
                    self.state.general_sections[main_section_name][section_name] = (
                        section_data
                    )

    def sync_general_sections_from_state(self):
        """Syncs the server-side general sections based on the current values
        of the dedicated state variables."""

        # copy the current general sections state variables
        copy_general_sections = self.state.general_sections

        # loop through main sections
        for main_section_data in copy_general_sections.values():
            # loop through sections and add to our server side yaml
            # content
            for section, section_data in main_section_data.items():
                self._server_vars["fourc_yaml_content"][section] = section_data

    def init_materials_state_and_server_vars(self):
        """Initialize state and server-side variables related to the MATERIALS
        section and the CLONING MATERIAL MAP."""

        # get the materials (used only as a reference for CLONING_MATERIAL_MAP -> source)
        materials_section = copy.deepcopy(
            self._server_vars["fourc_yaml_content"]["MATERIALS"]
        )

        # get the cloning material map state variables
        self.state.cloning_material_map_section = {}
        try:  # if the categories contain "CLONING MATERIAL MAP"
            cloning_material_map_section = copy.deepcopy(
                self._server_vars["fourc_yaml_content"]["CLONING MATERIAL MAP"]
            )

            # we keep the cloning material map in the same structure in
            # our state
            self.state.cloning_material_map_section = cloning_material_map_section

        except:
            pass

        # get the material state variable
        self.state.materials_section = {}
        for material in materials_section:
            # material name: "MAT 1" as the key
            material_name = f"MAT {material['MAT']}"

            # material type: "MAT_InelasticDefgradGrowth"
            material_type = f"{list(material.keys())[1]}"

            # material parameters
            material_params = material[material_type]

            # add item to materials section
            self.state.materials_section[material_name] = {
                "TYPE": material_type,
                "PARAMETERS": material_params,
            }

        # get master material indices and the linked material indices
        # related to them
        material_indices = get_master_and_linked_material_indices(materials_section)

        # loop through material section and get the state variables into
        # their dedicated lists
        for mat_item_key, mat_item_val in self.state.materials_section.items():
            # get material id from material name
            mat_name = mat_item_key
            mat_id = int(mat_name.replace("MAT", "").strip())

            # add custom key, value pair  to the material item, to track
            # the linked material indices and the master material index
            mat_item_val["RELATIONSHIPS"] = {
                "LINKED MATERIALS": [],
                "MASTER MATERIAL": -1,
            }

            # get indices of the linked materials
            found_linked_mat_indices = False
            for index_of_item, linked_material_indices_item in enumerate(
                material_indices["linked_mat_indices"]
            ):
                if mat_id in linked_material_indices_item:
                    # add linked material indices
                    mat_item_val["RELATIONSHIPS"]["LINKED MATERIALS"] = (
                        linked_material_indices_item
                    )

                    # add master material index
                    mat_item_val["RELATIONSHIPS"]["MASTER MATERIAL"] = material_indices[
                        "master_mat_indices"
                    ][index_of_item]

                    found_linked_mat_indices = True
                    break
            if not found_linked_mat_indices:
                raise Exception(
                    f"Did not find linked material indices for MAT {self.state.materials_section[mat_name]['MAT']}"
                )

        # set user selection variables
        self.state.selected_material = next(iter(self.state.materials_section), None)
        if self.state.selected_material in self.state.materials_section:
            self.state.selected_material_param = next(
                iter(
                    self.state.materials_section[self.state.selected_material][
                        "PARAMETERS"
                    ]
                ),
                None,
            )

    def sync_materials_sections_from_state(self):
        """Syncs the server-side materials (and cloning material map) sections
        based on the current values of the relevant materials state
        variables."""

        # deep copy the current state variables
        copy_materials_section = copy.deepcopy(self.state.materials_section)
        copy_cloning_material_map_section = copy.deepcopy(
            self.state.cloning_material_map_section
        )

        # go through the material items and remove the quantities added
        # within the init_ routine, but which are not present in the
        # fourc yaml file
        new_materials_section = []
        for mat_item_key, mat_item_val in copy_materials_section.items():
            # get material id from material name
            mat_name = mat_item_key
            mat_id = int(mat_name.replace("MAT", "").strip())

            # get material type
            mat_type = mat_item_val["TYPE"]

            # now rewrite MATERIALS to the original structure
            new_materials_section.append(
                {"MAT": mat_id, f"{mat_type}": mat_item_val["PARAMETERS"]}
            )

        # set the new cloning material map section
        new_cloning_material_map_section = copy_cloning_material_map_section

        # write to server-side content
        self._server_vars["fourc_yaml_content"]["MATERIALS"] = new_materials_section
        if new_cloning_material_map_section:
            self._server_vars["fourc_yaml_content"]["CLONING MATERIAL MAP"] = (
                new_cloning_material_map_section
            )

    def init_design_conditions_state_and_server_vars(self):
        """Initialize the state and server variables for the design condition
        sections."""

        # get all sections starting with "DESIGN" into a dict: these are
        # our design condition items
        design_condition_items = copy.deepcopy(
            {
                k: v
                for k, v in self._server_vars["fourc_yaml_content"].items()
                if k.startswith("DESIGN ")
            }
        )

        # set geometry types for the design condition
        all_dc_geometries = ["POINT", "LINE", "SURF", "VOL"]

        # loop through the items, and create dict of the structure:
        #   geometry (point, line, surf, vol)
        #       --> entity (e.g. E1)
        #           --> type (e.g. Dirichlet, S2I kinetics, ...)
        #               --> design condition specification (data)
        self.state.dc_sections = {}
        for dc_type, dc_data_all_entities in design_condition_items.items():
            # get geometry type and add it to dictionary if it is not present
            dc_type_components = dc_type.split()
            possible_geometry_types = [
                v for v in dc_type_components if v in all_dc_geometries
            ]
            if not possible_geometry_types:
                raise Exception(f"Did not find geometry type for {dc_type}")
            elif len(possible_geometry_types) > 1:
                raise Exception(
                    f"Found {possible_geometry_types} as possible geometry types for {dc_type}! We should only have one type!"
                )
            else:
                geometry_type = possible_geometry_types[0]
                if geometry_type not in self.state.dc_sections.keys():
                    self.state.dc_sections[geometry_type] = {}

            # loop through conditions for the determined geometry
            for specific_bc in dc_data_all_entities:
                # get entity
                specific_dc_entity = specific_bc["E"]

                # add entity to the geometry type if it is not already present
                if (
                    f"E{specific_dc_entity}"
                    not in self.state.dc_sections[geometry_type].keys()
                ):
                    self.state.dc_sections[geometry_type][f"E{specific_dc_entity}"] = {}

                # append entity data (key = full type name)
                self.state.dc_sections[geometry_type][f"E{specific_dc_entity}"][
                    dc_type
                ] = {k: v for k, v in specific_bc.items() if k != "E"}

        # sort entities for each geometry alphabetically
        for geometry_type, geometry_type_data in self.state.dc_sections.items():
            self.state.dc_sections[geometry_type] = dict(
                sorted(self.state.dc_sections[geometry_type].items())
            )
        # sort geometries from point to vol
        copy_dc_sections = copy.deepcopy(self.state.dc_sections)
        self.state.dc_sections = {
            dict_key: copy_dc_sections[dict_key]
            for dict_key in all_dc_geometries
            if dict_key in copy_dc_sections
        }

        # set user selection variables
        self.state.selected_dc_geometry_type = next(iter(self.state.dc_sections), None)
        if self.state.selected_dc_geometry_type in self.state.dc_sections:
            self.state.selected_dc_entity = next(
                iter(self.state.dc_sections[self.state.selected_dc_geometry_type]), None
            )
            if (
                self.state.selected_dc_entity
                in self.state.dc_sections[self.state.selected_dc_geometry_type]
            ):
                self.state.selected_dc_condition = next(
                    iter(
                        self.state.dc_sections[self.state.selected_dc_geometry_type][
                            self.state.selected_dc_entity
                        ]
                    ),
                    None,
                )

    def sync_design_conditions_sections_from_state(self):
        """Syncs the server-side design sections based on the current values of
        the dedicated state variables."""

        # loop through geometry types
        new_dc_sections = {}
        for geometry_type, geometry_type_data in self.state.dc_sections.items():
            # loop through entity indices
            for entity, entity_data in geometry_type_data.items():
                # loop through design condition types
                for dc_type, dc_data in entity_data.items():
                    # check whether the design condition type is
                    # already added to the output
                    if dc_type not in new_dc_sections.keys():
                        new_dc_sections[dc_type] = []

                    # add entity along with its data
                    new_dc_sections[dc_type].append(
                        {"E": int(entity.replace("E", "")), **dc_data}
                    )

        # remove design condition sections from server side fourc yaml
        # content and then replace with the new, determined sections
        for section_name, section_data in self._server_vars[
            "fourc_yaml_content"
        ].sections.items():
            if section_name.startswith("DESIGN "):
                self._server_vars["fourc_yaml_content"].pop(section_name)
        self._server_vars["fourc_yaml_content"].combine_sections(new_dc_sections)

    def init_result_description_state_and_server_vars(self):
        """Initialize the state and server variables for the result description
        section."""

        # get result description section
        result_description_section = copy.deepcopy(
            self._server_vars["fourc_yaml_content"]["RESULT DESCRIPTION"]
        )

        # initialize empty dict as the result description section
        self.state.result_description_section = {}
        # loop through the read-in list:
        for result_description_index, result_description_item in enumerate(
            result_description_section
        ):
            # get field
            field = next(iter(result_description_item))

            # get corresponding parameter dict
            params = result_description_item[field]

            # create an identifier for this description item
            id = f"Check {result_description_index + 1}"

            # create list element to be added to the state
            self.state.result_description_section[id] = {
                "FIELD": field,
                "PARAMETERS": params,
            }

        # set user selection variables
        self.state.selected_result_description_id = next(
            iter(self.state.result_description_section), None
        )  # set the selected result description by id
        if (
            self.state.selected_result_description_id
            in self.state.result_description_section
        ):
            self.state.selected_result_description_param = next(
                iter(
                    self.state.result_description_section[
                        self.state.selected_result_description_id
                    ]["PARAMETERS"]
                ),
                None,
            )

    def sync_result_description_section_from_state(self):
        """Syncs the server-side result description section based on the
        current values of the dedicated state variables."""

        # initialize empty list as the result description section
        copy_result_description_section = copy.deepcopy(
            self.state.result_description_section
        )
        new_result_description_section = []
        # loop through the read-in list:
        for (
            result_description_id,
            result_description_item,
        ) in copy_result_description_section.items():
            # get field
            field = result_description_item["FIELD"]

            # get corresponding parameter dict
            params = result_description_item["PARAMETERS"]

            # get item in the yaml file structure
            new_result_description_section.append({field: params})

        # set result description section on the server
        self._server_vars["fourc_yaml_content"]["RESULT DESCRIPTION"] = (
            new_result_description_section
        )

    def init_funct_state_and_server_vars(self):
        """Initialize the state and server variables for the function
        sections."""

        # get all sections starting with "FUNCT" into a dict: these are
        # our function items
        funct_items = copy.deepcopy(
            {
                k: v
                for k, v in self._server_vars["fourc_yaml_content"].items()
                if k.startswith("FUNCT")
            }
        )

        # go through the dictionary and determine whether we can
        # visualize the function currently or not
        self.state.funct_section = {}
        for funct_name, funct_data in funct_items.items():
            # CURRENTLY: we only support the functional data to have the
            # keys 'SYMBOLIC_FUNCTION_OF_SPACE_TIME' (and) 'COMPONENT'.
            # If 'COMPONENT' is not provided, we add 'COMPONENT': 0 to
            # the dictionary

            # check if the function data contains only one component
            # with the type 'SYMBOLIC_FUNCTION_OF_SPACE_TIME' as the
            # single component key -> in this case, we append
            # 'COMPONENT': 0
            if len(funct_data) == 1 and set(funct_data[0].keys()) == {
                "SYMBOLIC_FUNCTION_OF_SPACE_TIME",
            }:
                funct_data[0]["COMPONENT"] = 0
                funct_data[0] = {
                    k: funct_data[0][k]
                    for k in [
                        "COMPONENT",
                        "SYMBOLIC_FUNCTION_OF_SPACE_TIME",
                    ]
                }

            # initialize the space for the current function within our
            # state variable (and the server variable)
            self.state.funct_section[funct_name] = {}

            # go through component data and check whether the function
            # component is currently visualizable...
            for component_index, component_data in enumerate(funct_data):
                if not all(
                    [
                        (
                            component_key
                            in ["COMPONENT", "SYMBOLIC_FUNCTION_OF_SPACE_TIME"]
                        )
                        for component_key in component_data.keys()
                    ]
                ):
                    funct_items[funct_name][component_index]["VISUALIZATION"] = False
                else:
                    funct_items[funct_name][component_index]["VISUALIZATION"] = True

                # append the component to our state variable
                self.state.funct_section[funct_name][f"Item {component_index + 1}"] = {
                    k: v for k, v in component_data.items() if k != "PARSED_FUNCT"
                }

        # set user selection variables
        self.state.selected_funct = next(
            iter(self.state.funct_section), None
        )  # selected function
        if self.state.selected_funct in self.state.funct_section:
            self.state.selected_funct_item = next(
                iter(self.state.funct_section[self.state.selected_funct]), None
            )  # selected item of the selected function
        self.state.funct_plot = {}
        self.state.funct_plot["max_time"] = (
            find_value_recursively(
                self._server_vars["fourc_yaml_content"].sections,
                "MAXTIME",  # we try to find the specified max time within the input file as the initial value
            )
            or 100
        )
        self.state.funct_plot["x_val"] = 0  # current value of x for the function plot
        self.state.funct_plot["y_val"] = 0  # current value of y for the function plot
        self.state.funct_plot["z_val"] = 0  # current value of z for the function plot
        self.state.funct_plot["input_precision"] = (
            6  # precision for the user input of the values defined above: x, y, z and t_max
        )

    def sync_funct_section_from_state(self):
        """Syncs the server-side functions section based on the current values
        of the dedicated state variables."""

        # copy state function sections and create new object to set our
        # server variables to, afterwards
        copy_funct_section = self.state.funct_section
        # loop through functions
        for funct_name, funct_data in copy_funct_section.items():
            # clear current function section or add new function
            self._server_vars["fourc_yaml_content"][funct_name] = []

            # loop through components
            for component_name, component_data in funct_data.items():
                self._server_vars["fourc_yaml_content"][funct_name].append(
                    {k: v for k, v in component_data.items() if k != "VISUALIZATION"}
                )

    def init_mode_state_vars(self):
        """Initialize state variables related to mode changes (edit mode, view
        mode) and statuses (e.g. read-in status)."""
        # initialize the read-in status and its possible choices
        self.state.all_read_in_statuses = {
            "success": "SUCCESS",  # successful read-in of the file
            "validation_error": "VALIDATION_ERROR",  # error during the reading of the input file (validation)
            "vtu_conversion_error": "VTU_CONVERSION_ERROR",  # error during the conversion of the geometry within the input file to vtu
        }
        self.state.read_in_status = self.state.all_read_in_statuses["success"]

        # initialize the edit mode toggle value: first on view mode
        self.state.all_edit_modes = {
            "view_mode": "VIEW MODE",
            "edit_mode": "EDIT MODE",
        }
        self.state.edit_mode = self.state.all_edit_modes["view_mode"]

        # initialize the content modes for the different sections
        # update the content mode
        self.state.all_content_modes = {
            "general_section": "general_section",
            "materials_section": "materials_section",
            "design_conditions_section": "design_conditions_section",
            "result_description_section": "result_description_section",
            "funct_section": "funct_section",
        }

        # initialize info mode value: False (bottom sheet with infos is not displayed until "INFO" button is pressed, and INFO_MODE is then set to True)
        self.state.info_mode = False

        # initialize export mode value: False (bottom sheet with export settings is not displayed until "EXPORT" button is pressed, and EXPORT_MODE is then set to True)
        self.state.export_mode = False

        # initialize the export status and its possible choices
        self.state.all_export_statuses = {
            "info": "INFO",
            "success": "SUCCESS",
            "error": "ERROR",
        }

        # INFO: button was not yet clicked, SUCCESS: export was successful, ERROR: there was an error after trying to export
        self.state.export_status = self.state.all_export_statuses["info"]

    """------------------- State change functions -------------------"""

    #################################################
    # INPUT FILE CHANGE #################################
    ################################################
    @change("fourc_yaml_file")
    def change_fourc_yaml_file(self, fourc_yaml_file, **kwargs):
        """Reaction to change of state.fourc_yaml_file."""

        # create temporary fourc yaml file from the content of the given file
        temp_fourc_yaml_file = Path(
            self._server_vars["temp_dir_object"].name, fourc_yaml_file["name"]
        )
        with open(temp_fourc_yaml_file, "w") as f:
            f.writelines(fourc_yaml_file["content"].decode("utf-8"))

        # read content, lines and other details of the given file
        (
            self._server_vars["fourc_yaml_content"],
            self._server_vars["fourc_yaml_lines"],
            self._server_vars["fourc_yaml_size"],
            self._server_vars["fourc_yaml_last_modified"],
            self._server_vars["fourc_yaml_read_in_status"],
        ) = read_fourc_yaml_file(temp_fourc_yaml_file)

        self._server_vars["fourc_yaml_name"] = Path(temp_fourc_yaml_file).name

        # set vtu file path empty to make the convert button visible
        # (only if the function was not run yet, i.e., after the
        # initial rendering)
        self._server_vars["render_count"]["change_fourc_yaml_file"] += 1
        if self._server_vars["render_count"]["change_fourc_yaml_file"] > 1:
            self.state.vtu_path = ""

    @change("export_fourc_yaml_path")
    def change_export_fourc_yaml_path(self, export_fourc_yaml_path, **kwargs):
        """Reaction to change of state.export_fourc_yaml_path."""
        # set the export status to info
        self.state.export_status = self.state.all_export_statuses["info"]

    #################################################
    # SELECTION CHANGES #################################
    ################################################
    @change("selected_main_section_name")
    def change_selected_main_section_name(self, selected_main_section_name, **kwargs):
        """Reaction to change of state.selected_main_section_name."""
        # set selected section name to the first one within the selected
        # main section
        self.state.selected_section_name = self.state.section_names[
            selected_main_section_name
        ]["subsections"][0]

    @change("selected_material")
    def change_selected_material(self, selected_material, **kwargs):
        """Reaction to change of state.selected_material."""
        # we need to select the material region based on the newly selected
        # material (if we are not in an initial rendering scenario)
        if self._server_vars["render_count"]["change_selected_material"] > 0:
            # first get the master material id
            master_mat_id = self.determine_master_mat_ind_for_current_selection()

            # update plotter / render objects
            self.update_pyvista_render_objects()

            # update the pyvista local view
            self.ctrl.view_update()

            # set the material parameter selector to the first parameter
            # of the currently selected material
            if self.state.materials_section[selected_material]["PARAMETERS"]:
                self.state.selected_material_param = next(
                    iter(self.state.materials_section[selected_material]["PARAMETERS"])
                )
        else:
            # increment render counter
            self._server_vars["render_count"]["change_selected_material"] += 1

    @change("selected_dc_geometry_type")
    def change_selected_dc_geometry_type(self, selected_dc_geometry_type, **kwargs):
        """Reaction to change of state.selected_dc_geometry_type."""
        # change entity to the first of the selected geometry
        self.state.selected_dc_entity = next(
            iter(self.state.dc_sections[selected_dc_geometry_type])
        )

        # change selected condition for the geometry-entity combination
        self.state.selected_dc_condition = next(
            iter(
                self.state.dc_sections[selected_dc_geometry_type][
                    self.state.selected_dc_entity
                ]
            )
        )

        # update plotter / render objects
        self.update_pyvista_render_objects()

        # update the pyvista local view
        self.ctrl.view_update()

    @change("selected_dc_entity")
    def change_selected_dc_entity(self, selected_dc_entity, **kwargs):
        """Reaction to change of state.selected_dc_entity."""
        # change selected condition for the geometry-entity combination
        self.state.selected_dc_condition = next(
            iter(
                self.state.dc_sections[self.state.selected_dc_geometry_type][
                    self.state.selected_dc_entity
                ]
            )
        )

        # update plotter / render objects
        self.update_pyvista_render_objects()

        # update the pyvista local view
        self.ctrl.view_update()

    @change("selected_result_description_id")
    def change_selected_result_description_id(
        self, selected_result_description_id, **kwargs
    ):
        """Reaction to change of state.selected_result_description_id."""
        # update plotter / render objects
        self.update_pyvista_render_objects()

        # update the pyvista local view
        self.ctrl.view_update()

    @change("selected_funct")
    def change_selected_funct(self, selected_funct, **kwargs):
        """Reaction to change of state.selected_funct."""
        # set the selected funct item to the first within the newly
        # selected funct
        self.state.selected_funct_item = next(
            iter(self.state.funct_section[selected_funct])
        )

        # update plotly figure
        if self.state.funct_section[selected_funct][self.state.selected_funct_item][
            "VISUALIZATION"
        ]:
            self.server.controller.figure_update(function_plot_figure(self.state))

    @change("selected_funct_item")
    def change_selected_funct_item(self, selected_funct_item, **kwargs):
        """Reaction to change of state.selected_funct_item."""
        # update plotly figure
        if self.state.funct_section[self.state.selected_funct][
            self.state.selected_funct_item
        ]["VISUALIZATION"]:
            self.server.controller.figure_update(function_plot_figure(self.state))

    #################################################
    # FUNCTION CHANGES #################################
    ################################################
    @change("funct_plot")
    def change_funct_plot(self, funct_plot, **kwargs):
        """Reaction to change of state.funct_plot."""
        # update plotly figure
        if self.state.funct_section[self.state.selected_funct][
            self.state.selected_funct_item
        ]["VISUALIZATION"]:
            self.server.controller.figure_update(function_plot_figure(self.state))

    @change("funct_section")
    def change_funct_section(self, funct_section, **kwargs):
        """Reaction to change of state.funct_section."""
        # update plotly figure
        if self.state.funct_section[self.state.selected_funct][
            self.state.selected_funct_item
        ]["VISUALIZATION"]:
            self.server.controller.figure_update(function_plot_figure(self.state))

    #################################################
    # MODE CHANGES #################################
    ################################################
    @change("edit_mode")
    def change_edit_mode(self, edit_mode, **kwargs):
        """Reaction to change of state.edit_mode."""
        # cast entered string values from VTextField (edit mode) to
        # numbers
        if (
            edit_mode == self.state.all_edit_modes["view_mode"]
        ):  # after edit mode we are again in view mode
            self.convert_string2num_all_sections()

            # for now we don't convert the function section, because it
            # works itself with strings, e.g.
            # 'SYMBOLIC_FUNCTION_OF_SPACE_TIME' is a string even if it
            # contains a single number. But maybe this will be
            # relevant at some point in time...
            # self.state.funct_section = convert_string2number(self.state.funct_section)

    @change("export_mode")
    def change_export_mode(self, export_mode, **kwargs):
        """Reaction to change of state.export_mode."""
        # revert export status to "INFO"
        self.state.export_status = self.state.all_export_statuses["info"]
        self.convert_string2num_all_sections()

    """------------------- Controller functions -------------------"""

    @controller.set("click_info_button")
    def click_info_button(self, **kwargs):
        """Toggles the info mode, which displays a bottom sheet containing file
        name and simulation description."""
        self.state.info_mode = not self.state.info_mode

    @controller.set("click_export_button")
    def click_export_button(self, **kwargs):
        """Toggles the export mode, which displays a bottom sheet with export
        settings."""
        self.state.export_mode = not self.state.export_mode

    @controller.set("click_convert_button")
    def click_convert_button(self, **kwargs):
        """Convert the given fourc yaml file to vtu and run the state
        initialization routines."""

        # create temporary fourc yaml file from the content of the given file
        temp_fourc_yaml_file = Path(
            self._server_vars["temp_dir_object"].name,
            self.state.fourc_yaml_file["name"],
        )

        with open(temp_fourc_yaml_file, "w") as f:
            f.write(self.state.fourc_yaml_file["content"].decode("utf-8"))

        if self._server_vars["fourc_yaml_read_in_status"]:
            self.state.read_in_status = self.state.all_read_in_statuses["success"]

            # initialize state object
            self.init_state_and_server_vars()

            # convert to vtu
            self.state.vtu_path = convert_to_vtu(
                temp_fourc_yaml_file,
                Path(self._server_vars["temp_dir_object"].name),
            )

            # catch eventual conversion error
            if self.state.vtu_path == "":
                self.state.read_in_status = self.state.all_read_in_statuses[
                    "vtu_conversion_error"
                ]
            else:
                # reset view
                self.update_pyvista_render_objects()
                self._server_vars["render_window"].reset_camera()
                self.ctrl.view_reset_camera()
                self.ctrl.view_update()

        else:
            self.state.read_in_status = self.state.all_read_in_statuses[
                "validation_error"
            ]

    @controller.set("click_save_button")
    def click_save_button(self, **kwargs):
        """Save the current content to a new fourc_yaml content."""
        # sync server-side variables
        self.sync_server_vars_from_state()

        # dump content to the defined export file
        self._server_vars["fourc_yaml_file_write_status"] = write_fourc_yaml_file(
            self._server_vars["fourc_yaml_content"], self.state.export_fourc_yaml_path
        )

        # check write status
        if self._server_vars["fourc_yaml_file_write_status"]:
            self.state.export_status = self.state.all_export_statuses["success"]
        else:
            self.state.export_status = self.state.all_export_statuses["error"]

    """ --- Other helper functions"""

    def convert_string2num_all_sections(self):
        """Converts string to num wherever possible for all considered
        sections."""
        self.state.general_sections = convert_string2number(self.state.general_sections)
        self.state.materials_section = convert_string2number(
            self.state.materials_section
        )
        self.state.dc_sections = convert_string2number(self.state.dc_sections)
        self.state.result_description_section = convert_string2number(
            self.state.result_description_section
        )

    def determine_master_mat_ind_for_current_selection(self):
        """Determines the real master/source material of the currently selected
        material. Accounts for CLONING MATERIAL MAP by going one step further
        and checking for the real source material recursively (important in
        multi-field problem settings, e.g., in SSTI, the procedure finds the
        structural material).

        Returns:
            int: id of the real master material of the currently
                selected material.
        """
        # get id of the master material
        master_mat_id = self.state.materials_section[self.state.selected_material][
            "RELATIONSHIPS"
        ]["MASTER MATERIAL"]

        # it could now be that the master material is a TARGET material
        # during cloning material map (and its master might be also a
        # target...) -> in that case we need to get the real
        # SOURCE material as the master material
        if self.state.cloning_material_map_section:
            # get list of target materials
            tar_mat_list = np.array(
                [
                    cmm_item["TAR_MAT"]
                    for cmm_item in self.state.cloning_material_map_section
                ]
            )

            # get index of the first match
            matches = np.where(tar_mat_list == master_mat_id)[0]

            # get the real master / source material recursively
            while matches.size > 0:
                master_mat_id = self.state.cloning_material_map_section[matches[0]][
                    "SRC_MAT"
                ]
                matches = np.where(tar_mat_list == master_mat_id)[0]

        return master_mat_id

    def cleanup(self):
        """Perform cleanup tasks for the webserver."""
        self._server_vars["temp_dir_object"].cleanup()
