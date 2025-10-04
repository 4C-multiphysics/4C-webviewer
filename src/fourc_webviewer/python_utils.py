"""Module for python utils."""

import re

from fourcipp import CONFIG


def flatten_list(input_list):
    """Flattens a given (multi-level) list into a single list.

    Args:
        input_list (list): list to be flattened.

    Returns:
        list: flattened list.
    """

    output_list = []

    for input_list_item in input_list:
        if isinstance(input_list_item, list):
            output_list.extend(flatten_list(input_list_item))
        else:
            output_list.append(input_list_item)

    return output_list


def find_value_recursively(input_dict, target_key):
    """Finds the value for a specified key within a nested dict recursively.
    Helpful when going through the sections of the input fourc yaml file.

    Args:
        input_dict (dict): input dict to be scanned for the target key
        target_key (string): target key to search for

    Returns:
        any | None: value of the specific target key
    """
    if isinstance(input_dict, dict):
        for key, value in input_dict.items():
            if key == target_key:
                return value
            result = find_value_recursively(value, target_key)
            if result is not None:
                return result
    elif isinstance(input_dict, list):
        for item in input_dict:
            result = find_value_recursively(item, target_key)
            if result is not None:
                return result
    return None


def get_by_path(dct, path):
    """Retrieve the value at the nested path from dct.

    Raises KeyError if any key is missing.
    """
    current = dct
    for key in path:
        current = current[key]
    return current


def dict_leaves_to_number_if_schema(value, schema_path=[]):
    """Convert all leaves of a dict to numbers if possible."""
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = dict_leaves_to_number_if_schema(
                v, schema_path + ["properties", k]
            )
        return value
    if isinstance(value, str) and get_by_path(
        CONFIG.fourc_json_schema, schema_path + ["type"]
    ) in ["number", "integer"]:
        return smart_string2number_cast(value)
    return value


def dict_number_leaves_to_string(value):
    """Convert all leaves of a dict to numbers if possible."""
    if isinstance(value, bool):
        return value  # isinstance(True, int) is True
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = dict_number_leaves_to_string(v)
        return value
    if isinstance(value, int) or isinstance(value, float):
        return str(value)
    return value


def parse_validation_error_text(text):
    """Parse a ValidationError message string (with multiple "- Parameter in
    [...]" blocks) into a nested dict.

    Args:
        text (str): <fill in your definition>
    Returns:
        dict: <fill in your definition>
    """
    error_dict = {}
    # Match "- Parameter in [...]" blocks up until the next one or end of string
    block_re = re.compile(
        r"- Parameter in (?P<path>(?:\[[^\]]+\])+)\n"
        r"(?P<body>.*?)(?=(?:- Parameter in )|\Z)",
        re.DOTALL,
    )
    for m in block_re.finditer(text):
        path_str = m.group("path")
        body = m.group("body")

        # extract the Error: line
        err_m = re.search(r"Error:\s*(.+)", body)
        if not err_m:
            continue
        err_msg = err_m.group(1).strip()

        keys = re.findall(r'\["([^"]+)"\]', path_str)

        # walk/create nested dicts, then assign the message at the leaf
        cur = error_dict
        for key in keys[:-1]:
            cur = cur.setdefault(key, {})
        cur[keys[-1]] = err_msg

    return error_dict


def smart_string2number_cast(input_string):
    """Casts an input_string to float / int if possible. Helpful when dealing
    with automatic to-string conversions from vuetify.VTextField input
    elements.

    Args:
        input_string (str): input string to be converted.
    Returns:
        int | float | str | object: converted value.
    """
    # otherwise boolean values are converted to 0/1
    if not isinstance(input_string, str):
        return input_string
    try:
        # first convert to float
        input_float = float(input_string)
        if input_float.is_integer():
            return int(input_float)
        return input_float
    except (ValueError, TypeError):
        return input_string  # if conversion fails: return original string


def convert_string2number(input_element):
    """Recursively converts strings to int/float where possible in nested lists
    or dictionaries.

    Args:
        input_element (str | list | dict): Input to be converted.

    Returns:
        int | float | str | list | dict: Converted structure with numeric strings cast.
    """
    if isinstance(input_element, list):
        return [convert_string2number(el) for el in input_element]
    elif isinstance(input_element, dict):
        return {k: convert_string2number(v) for k, v in input_element.items()}
    else:
        return smart_string2number_cast(input_element)
