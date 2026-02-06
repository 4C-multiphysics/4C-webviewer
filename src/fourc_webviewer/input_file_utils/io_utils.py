"""Input/output utilities for 4C input files."""

import copy
import os
import re

from fourcipp.fourc_input import FourCInput
from loguru import logger

from fourc_webviewer.python_utils import flatten_list


def read_fourc_yaml_file(fourc_yaml_file):
    """Read in a given fourc yaml file. Validation is performed within the
    function.

    Args:
        fourc_yaml_file (str | Path): path to the fourc yaml file to be
        read.

    Returns:
        tuple: A tuple containing the following elements:
                - fourc_yaml_content (FourCInput): read-in file content.
                - fourc_yaml_lines (list): list of file lines.
                - fourc_yaml_size (int): file size.
                - fourc_yaml_last_modified (int): time stamp of the last
                  modification of the file.
                - status (bool): True if file was read-in and validated
                  correctly. If false, the other values are set to empty
                  objects of their type (or 0).
    """

    try:
        # load 4C yaml file
        fourc_yaml_content = FourCInput.from_4C_yaml(fourc_yaml_file)
        fourc_yaml_content.load_includes()

        # validate 4C yaml file
        fourc_yaml_content.validate()
    except Exception as exc:
        logger.error(exc)  # currently, we throw the exception as terminal output
        return (FourCInput({}), [], 0, 0, False)

    with open(fourc_yaml_file, "r") as input_file:
        fourc_yaml_lines = input_file.readlines()

    # get file size
    fourc_yaml_size = os.path.getsize(fourc_yaml_file)

    # get last modified time stamp
    fourc_yaml_last_modified = int(os.path.getmtime(fourc_yaml_file))

    return (
        fourc_yaml_content,
        fourc_yaml_lines,
        fourc_yaml_size,
        fourc_yaml_last_modified,
        True,
    )


def write_fourc_yaml_file(fourc_yaml_content, new_fourc_yaml_file):
    """Writes given content to a fourc yaml file upon validation.

    Args:
        fourc_yaml_content (FourCInput): content to be written to a new
        file.
        new_fourc_yaml_file (str | Path): path of the new file to write
        the content to.

    Returns:
        bool: status of the file writing process. True means that the
        file has been successfully written upon validation.
    """

    # validate content
    try:
        fourc_yaml_content.validate()
    except Exception as exc:
        logger.error(exc)  # currently, we throw the exception as terminal output
        return False

    # check if the output file suffix is supported
    if not str(new_fourc_yaml_file).endswith((".yaml", ".yml")):
        return False

    # dump content to the specified new file
    fourc_yaml_content.dump(input_file_path=new_fourc_yaml_file)

    return True


def find_linked_materials(material_id, material_items):
    """Find materials linked with a material number / id recursively based on
    given material specifiers (parameters which refer to other materials). This
    does NOT account for the cloning material map.

    Args:
        material_number (int): material number, e.g. 1 for "MAT 1".
        material_items (list): all material items in a list of dicts

    Returns:
        list: list containing the material indices in material_items corresponding to the found linked materials
    """

    # find the list item in material_items corresponding to the
    # specified material
    # index
    base_mat_item = None
    i = 0
    while i < len(material_items):
        if material_items[i]["MAT"] == material_id:
            base_mat_item = copy.deepcopy(material_items[i])
            break

        # increment index
        i += 1

    if base_mat_item is None:
        raise Exception(f"Could not find material id {material_id} in {material_items}")

    # get material parameters as a dict
    base_mat_item.pop("MAT")
    base_mat_params = next(iter(base_mat_item.values()))

    # search for the specifiers within the material_index line in material_items
    material_mat_specifiers = [
        spec_item
        for spec_item in mat_specifiers()
        if spec_item in base_mat_params.keys()
    ]

    if len(material_mat_specifiers) == 0:  # no further linked materials
        return [material_id]
    else:  # there are further linked materials
        list_of_material_item_numbers = [material_id]

        # for each of the found specifiers: find the values (equivalent
        # to material indices of the linked materials) and search within
        # them recursively
        for spec in material_mat_specifiers:
            if isinstance(base_mat_params[spec], list):
                list_of_material_item_numbers.append(
                    [
                        find_linked_materials(mat_id, material_items)
                        for mat_id in base_mat_params[spec]
                    ]
                )
            elif isinstance(base_mat_params[spec], int):
                list_of_material_item_numbers.append(
                    find_linked_materials(base_mat_params[spec], material_items)
                )
            else:
                raise Exception(
                    f"The data {base_mat_params[spec]} for spec {spec} of base material {base_mat_item} is neither list nor int! This should not be the case, since we want to get the linked material indices!"
                )

        return flatten_list(list_of_material_item_numbers)  # flatten the list of lists


def get_main_and_clustered_section_names(sections_list):
    """For given input file sections, determines all the main section names and
    clusters all sections according to them. Hereby, we look only at the
    general settings sections (we exclude functions, materials, boundary
    conditions and geometry).

    For example,
    SCALAR TRANSPORT DYNAMIC / SCALAR TRANSPORT DYNAMIC/STABILIZATION, SCALAR TRANSPORT DYNAMIC/S2I COUPLING
    are all clustered sections contained within the same main section SCALAR TRANSPORT DYNAMIC.

    Args:
        sections_list (list): list of all section names read from the input file.

    Returns:
        tuple:
            - main_section_names (list): list of the main section names [main_1, main_2, ....].
            - clustered_section_names (list): list of the clustered section names for each main category [[aux_1_1, aux_1_2,...], [aux_2_1, aux_2_2,...],...].
    """

    # create a copy of sections_list
    sections = sections_list.copy()

    # create arrays to be returned
    main_sections = []
    clustered_sections = []

    # loop through the sections (.dat file sections)
    while len(sections) > 0:
        # check if the section at the current index is "FUNCT<number>"
        if re.match("^FUNCT[0-9]+", sections[0]):  # yes
            # append the main section "FUNCTIONS"
            main_sections.append("FUNCTIONS")

            clustered_sections_to_be_added = []  # list of clustered sections to be added
            # add current element to clustered sections and remove it from sections
            clustered_sections_to_be_added.append(sections.pop(0))

            # go through the other elements and remove them
            j = 0
            while j < len(sections):
                if re.match("^FUNCT[0-9]+", sections[j]):
                    clustered_sections_to_be_added.append(sections.pop(j))
                else:
                    # increment j
                    j += 1

            # add the clustered sections
            clustered_sections.append(clustered_sections_to_be_added)
        else:  # no
            # check if element already in main sections -> SHOULD NEVER HAPPEN
            if sections[0].split("/")[0] in main_sections:
                raise Exception(
                    f"The item {sections[0]} is already in {main_sections}! There is a problem in the code!"
                )
            else:
                # get main category name to be added
                main_section_name = sections[0].split("/")[0]

                # add the main category
                main_sections.append(main_section_name)

                # add the current element to the list of clustered elements to be added
                clustered_sections_to_be_added = []
                clustered_sections_to_be_added.append(sections.pop(0))

                # go through the other elements and remove them
                j = 0
                while j < len(sections):
                    if sections[j].split("/")[0] == main_section_name:
                        clustered_sections_to_be_added.append(sections.pop(j))
                    else:
                        # increment j
                        j += 1

                # add the clustered sections
                clustered_sections.append(clustered_sections_to_be_added)

    return main_sections, clustered_sections


def mat_specifiers():
    """Get list of material parameter names which reference to other parameter
    IDs."""
    return [
        "MATIDSEL",
        "INELDEFGRADFACIDS",
        "PHASEIDS",
        "MATIDS",
        "MATID",
        "VISCOPLAST_LAW_ID",
        "FIBER_READER_ID",
        "STR_TENS_ID",
        "MATIDSCONST",
        "MATIDMIXTURERULE",
        "GROWTH_STRATEGY",
        "FIBER_MATERIAL_ID",
        "PRESTRESS_STRATEGY",
        "POROLAWID",
    ]


def create_file_object_for_browser(
    fourc_yaml_name, fourc_yaml_lines, fourc_yaml_size, fourc_yaml_last_modified
):
    """Creates a file object that can be utilized by the VFileInput object in
    the GUI toolbar.

    Args:
        fourc_yaml_name (str): stem of the input file.
        fourc_yaml_list (FourCInput): list of input file lines.
        fourc_yaml_size (int): size of the input file.
        fourc_yaml_last_modified (int): timestamp for the last
                                        modification of the input file.


    Returns:
        dict: file object dictionary mimicking the behavior utilized by file input objects in the browser.
    """

    # get file content from the read-in lines
    content = "\n".join(fourc_yaml_lines)

    # set file metadata
    fourc_yaml_type = "application/octet-stream"

    # mimic a file object and return it
    return {
        "name": fourc_yaml_name,
        "size": fourc_yaml_size,
        "type": fourc_yaml_type,
        "lastModified": fourc_yaml_last_modified,
        "content": content.encode("utf-8"),
        "_filter": ["content"],
    }


def get_master_and_linked_material_indices(materials_section):
    """Determine two lists: the master material indices (holding
    reference to all other linked material indices via material
    specifiers) and the linked material indices.

    Args:
        materials_section (list of dicts): materials section as read-in
                                           from the fourc yaml input
                                           file

    Returns:
        dict: output dict containing the master and linked material
        indices (list for each master material).
    """

    # get deepcopy of materials_section to not change it within the
    # function
    materials_section = copy.deepcopy(materials_section)

    # first set all material indices as master material indices -> we
    # will sort this out in the next step
    master_mat_indices = [mat_item["MAT"] for mat_item in materials_section]

    # check whether some of the master materials are actually related to others, and eliminate them from the master material index list
    linked_mat_indices = []  # list of linked material indices for each of the "master" materials: [<list of linked materials for "MASTER" 1>, <list of linked materials for "MASTER" 2>,... ]
    for master_mat_index in master_mat_indices:
        linked_mat_indices.append(
            find_linked_materials(
                master_mat_index,
                materials_section,
            )
        )

    # -> we go through the preliminary master_mat_indices list
    curr_master_list_ind = 0
    while curr_master_list_ind < len(master_mat_indices) - 1:
        # check the next items in master_mat_indices
        next_master_list_ind = curr_master_list_ind + 1
        while next_master_list_ind < len(master_mat_indices):
            # the master material with the larger number of linked materials becomes the master, and the other is eliminated from master_mat_indices
            if set(linked_mat_indices[next_master_list_ind]).issubset(
                set(linked_mat_indices[curr_master_list_ind])
            ):
                del master_mat_indices[next_master_list_ind]
                del linked_mat_indices[next_master_list_ind]
            # next_master_ind stays the same
            elif set(
                linked_mat_indices[curr_master_list_ind]
            ).issubset(
                set(linked_mat_indices[next_master_list_ind])
            ):  # this means that the current element is not truly a master -> has to be eliminated and we also break out of the for-loop
                del master_mat_indices[curr_master_list_ind]
                del linked_mat_indices[curr_master_list_ind]
                break  # curr_ind stays the same
            else:
                next_master_list_ind += 1
        else:
            curr_master_list_ind += 1

    return {
        "master_mat_indices": master_mat_indices,
        "linked_mat_indices": linked_mat_indices,
    }


def get_variable_data_by_name_in_funct_item(
    funct_section_item: dict, variable_name: str
):
    """Retrieves the entire dictionary for the variable called <variable_name>
    from the specified function section item, e.g. FUNCT1.

    Args:
        funct_section_item (dict): specified function item as a
            dictionary, adhereing to the structure utilized in the state
            variable funct_section.
        variable_name (str): name of the considered variable.
    Returns:
        dict: dictionary containing the information associated with the specified variable.
    """
    for k, v in funct_section_item.items():
        if "VARIABLE" in v and v["NAME"] == variable_name:
            return v
    return {}
