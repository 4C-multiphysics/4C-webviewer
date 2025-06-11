"""Specifies the GUI layout."""

import plotly
from pyvista.trame.ui import plotter_ui

from fourc_webviewer.input_file_utils.fourc_yaml_file_visualization import (
    function_plot_figure,
)

CLIENT_TYPE = "vue3"
if CLIENT_TYPE == "vue2":
    from trame.ui.vuetify2 import SinglePageWithDrawerLayout
    from trame.widgets import vuetify2 as vuetify
    from trame_vuetify.widgets.vuetify import HtmlElement
else:
    from trame.ui.vuetify3 import SinglePageWithDrawerLayout
    from trame.widgets import vuetify3 as vuetify
    from trame_vuetify.widgets.vuetify3 import HtmlElement
from trame.widgets import html, plotly


class VFileInput(HtmlElement):
    """Custom VFileInput element, since the one provided by trame does not
    currently support all relevant attributes, such as e.g. 'accept'."""

    def __init__(self, children=None, **kwargs):
        """Initialize custom VFileInput element."""
        super().__init__("v-file-input", children, **kwargs)
        self._attr_names += [
            "accept",
            "append_icon",
            "append_outer_icon",
            "autofocus",
            "background_color",
            "chips",
            "clear_icon",
            "clearable",
            "color",
            "counter",
            "counter_size_string",
            "counter_string",
            "counter_value",  # JS functions unimplemented
            "dark",
            "dense",
            "disabled",
            "error",
            "error_count",
            "error_messages",
            "filled",
            "flat",
            "full_width",
            "height",
            "hide_details",
            "hide_input",
            "hide_spin_buttons",
            "hint",
            "id",
            "label",
            "light",
            "loader_height",
            "loading",
            "messages",
            "multiple",
            "outlined",
            "persistent_hint",
            "persistent_placeholder",
            "placeholder",
            "prefix",
            "prepend_icon",
            "prepend_inner_icon",
            "reverse",
            "rounded",
            "rules",
            "shaped",
            "show_size",
            "single_line",
            "small_chips",
            "solo",
            "solo_inverted",
            "success",
            "success_messages",
            "suffix",
            "truncate_length",
            "type",
            "validate_on_blur",
            "value",
        ]
        self._event_names += [
            "blur",
            "change",
            "click",
            ("click_append", "click:append"),
            ("click_append_outer", "click:append-outer"),
            ("click_clear", "click:clear"),
            ("click_prepend", "click:prepend"),
            ("click_prepend_inner", "click:prepend-inner"),
            "focus",
            "input",
            "keydown",
            "mousedown",
            "mouseup",
            ("update_error", "update:error"),
        ]


def _toolbar(server_controller):
    """Toolbar layout."""

    html.Img(
        src="https://raw.githubusercontent.com/4C-multiphysics/4C-webviewer/refs/heads/main/images/4C-logo/negative-white/4C-logo-landscape_negative.svg",
        alt="4C Logo",
        style="height: 50px; width: auto; filter: invert(1); padding-left: 20px; padding-right: 10px;",
        class_="me-2",
    )

    with vuetify.VTooltip(location="top"):
        with html.Template(v_slot_activator="{ props }"):
            with vuetify.VBtn(
                tag="a",
                v_bind="{...props, target: '_blank'}",
                v_tooltip="4C Documentation",
                href="https://4c-multiphysics.github.io/4C/documentation/index.html",
                icon=True,
                rel="noopener noreferrer",
            ):
                vuetify.VIcon(
                    "mdi-book-open-blank-variant-outline",
                    size=36,
                    color="#666",
                )
        html.Span("4C Documentation")

    vuetify.VSpacer()

    vuetify.VToolbarTitle(
        "4C Webviewer",
        tag="h1",
        shrink=True,
        class_="mx-4",
        style="font-weight: 500; padding-right: 10px;",
    )

    vuetify.VFileInput(
        label="Input file",
        v_model=("fourc_yaml_file",),
        update_modelValue="flushState('fourc_yaml_file')",
        accept=".yaml,.yml",
    )
    vuetify.VBtn(
        text="CONVERT",
        v_if=("vtu_path == ''",),
        click=server_controller.click_convert_button,
    )
    vuetify.VBtn(
        text="INFO",
        outlined=True,
        color="red",
        v_if=("vtu_path != ''",),
        click=server_controller.click_info_button,
    )
    vuetify.VBtn(
        text="EXPORT",
        outlined=True,
        color="blue",
        v_if=("vtu_path != ''",),
        click=server_controller.click_export_button,
    )
    with vuetify.VBtn(icon=True, click=server_controller.view_reset_camera):
        vuetify.VIcon("mdi-crop-free")


def _bottom_sheet_info():
    """Bottom sheet layout (INFO mode)."""
    with vuetify.VBottomSheet(v_model=("info_mode",), inset=True):
        with vuetify.VCard(
            classes="text-center",
            height=500,
        ):
            with vuetify.VCardText():
                html.H2(
                    v_text=("fourc_yaml_name",),
                    v_if=("edit_mode == all_edit_modes['view_mode']",),
                    classes="mb-5",
                )
                html.H3(
                    "File name",
                    v_if=("edit_mode == all_edit_modes['edit_mode']",),
                    classes="text-left",
                )
                vuetify.VTextField(
                    v_model=("fourc_yaml_name",),
                    v_if=("edit_mode == all_edit_modes['edit_mode']",),
                    dense=True,
                    hide_details=True,
                )
                html.H3("Description", classes="text-left")
                html.P(
                    v_for=(r"item in description.split('\n')",),
                    v_text=("item",),
                    v_if=("edit_mode == all_edit_modes['view_mode']",),
                    classes="ml-5 text-left",
                )
                vuetify.VTextarea(
                    v_model=("description",),
                    rows=17,  # default height of the element
                    v_if=("edit_mode == all_edit_modes['edit_mode']",),
                    classes="ml-5 text-left",
                )


def _bottom_sheet_export(server_controller):
    """Bottom sheet layout (EXPORT mode)."""
    with vuetify.VBottomSheet(v_model=("export_mode",), inset=True):
        with vuetify.VCard(classes="text-center", height=250, title="Export"):
            with vuetify.VCardText():
                vuetify.VTextField(
                    label="Export input file",
                    v_model=("export_fourc_yaml_path",),
                    dense=True,
                    hide_details=True,
                )
                vuetify.VAlert(
                    title="Click on <SAVE> to export the input file under the entered path",
                    type="info",
                    v_if=("export_status == all_export_statuses['info']",),
                    classes="h-50",
                )
                vuetify.VAlert(
                    title="Your file was exported correctly!",
                    type="success",
                    v_if=("export_status == all_export_statuses['success']",),
                    classes="h-50",
                )
                vuetify.VAlert(
                    title="There was a problem while trying to export! Further details are provided in the terminal output...",
                    type="error",
                    v_if=("export_status == all_export_statuses['error']",),
                    classes="h-50",
                )
        vuetify.VBtn(
            text="SAVE", color="primary", click=server_controller.click_save_button
        )


def _sections_dropdown():
    """Section dropdown layout."""
    vuetify.VSelect(
        v_model=("selected_main_section_name",),
        items=("Object.keys(section_names)",),
    )
    vuetify.VSelect(
        v_if=("section_names[selected_main_section_name]['subsections'].length>1"),
        v_model=("selected_section_name",),
        items=("section_names[selected_main_section_name]['subsections']",),
    )


def _functions_panel(server):
    """Functions panel layout."""
    with html.Div(
        v_if=(
            "section_names[selected_main_section_name]['content_mode'] == all_content_modes['funct_section']"
        ),
    ):
        # select functions via dropdown
        vuetify.VSelect(
            v_model=("selected_funct",),
            items=("Object.keys(funct_section)",),
        )
        # select function items via dropdown
        vuetify.VSelect(
            v_if=("Object.keys(funct_section[selected_funct]).length > 0",),
            v_model=("selected_funct_item",),
            items=("Object.keys(funct_section[selected_funct])",),
        )
        with html.Div(
            v_if=(
                "funct_section[selected_funct][selected_funct_item]['VISUALIZATION']",
            ),
        ):
            ## show function component
            with html.Div(
                classes="d-flex align-center ga-3 mb-5 pl-5 w-full",
            ):
                ### --> see fourc_webserver specification on which function visualizations are currently supported
                html.Span("COMPONENT: ", classes="text-h6")
                html.Span(
                    v_text=(
                        "funct_section[selected_funct][selected_funct_item]['COMPONENT']",
                    ),
                )
            ## show function string
            with html.Div(
                classes="d-flex align-center ga-3 mb-5 pl-5 w-full",
            ):
                ### --> see fourc_webserver specification on which function visualizations are currently supported
                html.Span("FUNCTION: ", classes="text-h6")
                # view mode: text
                html.Span(
                    v_if=("edit_mode == all_edit_modes['view_mode']",),
                    v_text=(
                        "funct_section[selected_funct][selected_funct_item]['SYMBOLIC_FUNCTION_OF_SPACE_TIME']",
                    ),
                )
                # edit mode: text field
                vuetify.VTextField(
                    v_model=(
                        "funct_section[selected_funct][selected_funct_item]['SYMBOLIC_FUNCTION_OF_SPACE_TIME']",
                    ),
                    update_modelValue="flushState('funct_section')",
                    v_if=("edit_mode == all_edit_modes['edit_mode']",),
                    dense=True,
                    hide_details=True,
                )
            # next components: only in view mode
            with html.Div(
                v_if=("edit_mode == all_edit_modes['view_mode']",),
            ):
                # divider for optical separation
                vuetify.VDivider(
                    thickness="20",
                )

                # numeric edit fields for the t_max,x,y,z values
                with vuetify.VTable(classes="mx-3"):
                    with html.Thead():
                        with html.Tr():
                            html.Th(
                                "Variable",
                                classes="text-left font-weight-bold",
                            )
                            html.Th(
                                "Value",
                                classes="text-left font-weight-bold",
                            )
                    with html.Tbody():
                        with html.Tr():
                            html.Td(
                                "t_max",
                                classes="text-left font-weight-bold",
                            )
                            with html.Td(
                                classes="text-center-md",
                            ):
                                vuetify.VNumberInput(
                                    precision=("funct_plot['input_precision']",),
                                    v_model=("funct_plot['max_time']",),
                                    update_modelValue="flushState('funct_plot')",
                                    dense=True,
                                    hide_details=True,
                                )
                        with html.Tr():
                            html.Td(
                                "x",
                                classes="text-left font-weight-bold",
                            )
                            with html.Td(
                                classes="text-center-md",
                            ):
                                vuetify.VNumberInput(
                                    precision=("funct_plot['input_precision']",),
                                    v_model=("funct_plot['x_val']",),
                                    update_modelValue="flushState('funct_plot')",
                                    classes="bg-gray",
                                    dense=True,
                                    hide_details=True,
                                )
                        with html.Tr():
                            html.Td(
                                "y",
                                classes="text-left font-weight-bold",
                            )
                            with html.Td(
                                classes="text-center-md",
                            ):
                                vuetify.VNumberInput(
                                    precision=("funct_plot['input_precision']",),
                                    v_model=("funct_plot['y_val']",),
                                    update_modelValue="flushState('funct_plot')",
                                    dense=True,
                                    hide_details=True,
                                )
                        with html.Tr():
                            html.Td(
                                "z",
                                classes="text-left font-weight-bold",
                            )
                            with html.Td(
                                classes="text-center-md",
                            ):
                                vuetify.VNumberInput(
                                    precision=("funct_plot['input_precision']",),
                                    v_model=("funct_plot['z_val']",),
                                    update_modelValue="flushState('funct_plot')",
                                    dense=True,
                                    hide_details=True,
                                )

                # plots of the components
                with vuetify.VContainer(
                    # v_if=(
                    #    "Object.values(funct_plot).every(val => val !== null && val !== undefined && val !== '')"
                    # ) # --> this way we could make the plot disappear if no
                    #   value is given for one of the parameters -> but then the
                    #   view is reset and we have to scroll down again to
                    #   see the function...
                ):
                    figure = plotly.Figure(
                        display_logo=False,
                        display_mode_bar="true",
                    )
                    server.controller.figure_update = figure.update
                    server.controller.figure_update(function_plot_figure(server.state))

        # here we define the GUI output of the non-visualizable function components
        with html.Div(
            v_if=(
                "!funct_section[selected_funct][selected_funct_item]['VISUALIZATION']",
            ),
            classes="ml-10",
        ):
            with html.Div(
                v_for=(
                    "[param_key, param_val] of Object.entries(funct_section[selected_funct][selected_funct_item])",
                ),
                classes="d-flex align-center ga-3 mb-5 pl-5 w-full",
            ):
                html.P(
                    v_if=("param_key != 'VISUALIZATION'",),
                    v_text=("param_key"),
                    classes="text-h6",
                )
                html.P(v_if=("param_key != 'VISUALIZATION'",), v_text=("param_val"))
            html.P(
                "This type of function component cannot be currently visualized...",
                classes="font-italic",
            )


def _prop_value_table():
    """Table (property - value) layout (for general sections)."""
    with vuetify.VTable(
        v_if=(
            "section_names[selected_main_section_name]['content_mode'] == all_content_modes['general_section']",
        ),
    ):
        with html.Thead():
            with html.Tr():
                html.Th(
                    "Property",
                    classes="text-center font-weight-bold",
                )
                html.Th(
                    "Value",
                    classes="text-center font-weight-bold",
                )

        with html.Tbody():
            with html.Tr(
                v_if=(
                    "general_sections[selected_main_section_name] && general_sections[selected_main_section_name][selected_section_name] && Object.keys(general_sections[selected_main_section_name][selected_section_name]).length >= 1",
                ),
                v_for=(
                    "[item_key, item_val] of Object.entries(general_sections[selected_main_section_name]?.[selected_section_name] || {})",
                ),
                key="item_key",
            ):
                with html.Td(classes="text-center"):
                    with vuetify.VTooltip(location="bottom"):
                        with html.Template(v_slot_activator="{ props }"):
                            html.P(v_text=("item_key",), v_bind="props")
                        html.P(
                            v_text=(
                                "json_schema['properties']?.[selected_section_name]?.['properties']?.[item_key]?.['description'] || 'no description'",
                            ),
                            v_if=(
                                "json_schema['properties']?.[selected_section_name]?.['properties']?.[item_key]?.['description']",
                            ),
                            style="max-width: 450px;",
                        )
                html.Td(
                    v_if="edit_mode == all_edit_modes['view_mode']",
                    v_text=("item_val",),
                    classes="text-center w-50",
                )
                with html.Td(
                    v_if="edit_mode == all_edit_modes['edit_mode']",
                    classes="text-center w-50",
                ):
                    vuetify.VTextField(
                        v_model=(
                            "general_sections[selected_main_section_name][selected_section_name][item_key]",  # binding item_val directly does not work, since Object.entries(...) creates copies for the mutable objects
                        ),
                        update_modelValue="flushState('general_sections')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                        classes="w-80",
                        dense=True,
                        hide_details=True,
                    )


def _materials_panel():
    """Materials panel layout."""
    with html.Div(
        v_if=(
            "section_names[selected_main_section_name]['content_mode'] == all_content_modes['materials_section']"
        ),
    ):
        ##################################
        # MATERIALS OVERVIEW #############
        ##################################
        with html.Div(
            v_if=(
                "selected_section_name == section_names['MATERIALS']['subsections'][0]",
            ),
        ):
            # select materials via dropdown
            vuetify.VSelect(
                v_model=("selected_material",),
                items=("Object.keys(materials_section)",),
            )
            # show material type
            with html.Div(classes="d-flex align-center ga-3 mb-1 pl-5 w-full"):
                html.Span("TYPE: ", classes="text-h6")
                # view mode: text
                html.Span(
                    v_if=("edit_mode ==  all_edit_modes['view_mode']",),
                    v_text=("materials_section[selected_material]['TYPE']",),
                )
                with html.Div(
                    v_if=("edit_mode ==  all_edit_modes['edit_mode']",),
                    classes="flex-fill",
                ):
                    vuetify.VTextField(
                        v_model=(
                            "materials_section[selected_material]['TYPE']",  # binding item_val directly does not work, since Object.entries(...) creates copies for the mutable objects
                        ),
                        update_modelValue="flushState('materials_section')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                        classes="mx-10",
                        dense=True,
                        hide_details=True,
                    )
            html.P(
                classes="ga-3 mb-5 pl-5 pr-5 w-full",
                v_if=("edit_mode ==  all_edit_modes['view_mode']",),
                v_text=(
                    "json_schema?.properties?.MATERIALS?.items?.oneOf?"
                    ".find(v => v.properties?.[materials_section[selected_material]?.TYPE])?.properties?"
                    ".[materials_section[selected_material]?.TYPE]?.description || 'Error on material description'",
                ),
                style="color: #999;",
            )

            # show relationships to other materials (linked materials
            # and master material) -> only in view mode

            with html.Div(
                v_if=("edit_mode ==  all_edit_modes['view_mode']",),
            ):
                html.P("RELATIONSHIPS: ", classes="text-h6 pl-5 mb-2")
                with html.Div(
                    classes="d-flex justify-start align-center ga-3 mb-2 pl-8"
                ):
                    html.Span("LINKED MATERIALS: ")
                    html.Span(
                        v_text=(
                            "materials_section[selected_material]['RELATIONSHIPS']['LINKED MATERIALS']",
                        ),
                        classes="",
                    )
                with html.Div(
                    classes="d-flex justify-start align-center ga-3 mb-5 pl-8"
                ):
                    html.Span("MASTER MATERIAL: ")
                    html.Span(
                        v_text=(
                            "materials_section[selected_material]['RELATIONSHIPS']['MASTER MATERIAL']",
                        ),
                        classes="",
                    )
            # show material parameters (as a table with different
            # view<->edit mode structures)
            html.P("PARAMETERS: ", classes="text-h6 pl-5 mb-1")
            # show table of parameters in view mode
            with vuetify.VTable(
                v_if=("edit_mode ==  all_edit_modes['view_mode']",), classes="mx-3"
            ):
                with html.Thead():
                    with html.Tr():
                        html.Th(
                            "Property",
                            classes="text-center font-weight-bold",
                        )
                        html.Th(
                            "Value",
                            classes="text-center font-weight-bold",
                            style="width: 50%;",
                        )
                with html.Tbody():
                    with html.Tr(
                        v_for=(
                            "[param_key, param_val] of Object.entries(materials_section[selected_material]?.['PARAMETERS'] || {})",
                        ),
                        classes="text-center",
                    ):
                        with html.Td(classes="text-center"):
                            with vuetify.VTooltip(location="bottom"):
                                with html.Template(v_slot_activator="{ props }"):
                                    html.P(v_text=("param_key",), v_bind="props")
                                html.P(
                                    v_text=(
                                        "json_schema?.properties?.MATERIALS?.items?.oneOf?"
                                        ".find(v => v.properties?.[materials_section[selected_material]?.TYPE])?"
                                        ".properties?.[materials_section[selected_material]?.TYPE]?.properties?"
                                        ".[param_key]?.description || 'Error on parameter description'",
                                    ),
                                    style="max-width: 450px;",
                                )
                        html.Td(
                            v_text=("param_val",),
                        )
            with html.Div(
                v_if=(
                    "edit_mode ==  all_edit_modes['edit_mode'] && Object.keys(materials_section[selected_material]['PARAMETERS']).length > 0",
                ),
                classes="pl-8",
            ):
                vuetify.VSelect(
                    v_model=("selected_material_param",),
                    items=(
                        "Object.keys(materials_section[selected_material]['PARAMETERS'])",
                    ),
                    classes="mx-10",
                )
                # if parameter is single value (as opposed to list or
                # dict) -> VTextField
                vuetify.VTextField(
                    v_if=(
                        "materials_section[selected_material]['PARAMETERS'][selected_material_param]!== null && typeof materials_section[selected_material]['PARAMETERS'][selected_material_param] !== 'object' && !Array.isArray(materials_section[selected_material]['PARAMETERS'][selected_material_param])",
                    ),
                    v_model=(
                        "materials_section[selected_material]['PARAMETERS'][selected_material_param]",  # binding item_val directly does not work, since Object.entries(...) creates copies for the mutable objects
                    ),
                    update_modelValue="flushState('materials_section')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                    classes="mx-10",
                    dense=True,
                    hide_details=True,
                )
                # if parameter is list -> VTextField
                with vuetify.VList(
                    v_if=(
                        "materials_section[selected_material]['PARAMETERS'][selected_material_param]!== null && Array.isArray(materials_section[selected_material]['PARAMETERS'][selected_material_param])"
                    ),
                ):
                    with html.Div(
                        v_for=(
                            "(param_item, param_index) in materials_section[selected_material]?.PARAMETERS?.[selected_material_param]",
                        ),
                        key="param_index",
                        classes="d-flex align-center",
                    ):
                        vuetify.VIcon(
                            "mdi-circle-medium",
                            color="primary",
                            classes="mr-2",
                        )
                        vuetify.VTextField(
                            v_model=(
                                "materials_section[selected_material]['PARAMETERS'][selected_material_param][param_index]",
                            ),
                            dense=True,
                            hide_details=True,
                            update_modelValue="flushState('materials_section')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                            classes="mx-10",
                        )
                # show table of modifiable dict parameters if material
                # parameter is a dict
                with vuetify.VTable(
                    v_if=(
                        "materials_section[selected_material]['PARAMETERS'][selected_material_param]!== null && typeof materials_section[selected_material]['PARAMETERS'][selected_material_param] === 'object' && !Array.isArray(materials_section[selected_material]['PARAMETERS'][selected_material_param])"
                    ),
                    classes="mx-3",
                ):
                    with html.Thead():
                        with html.Tr():
                            html.Th(
                                "Property",
                                classes="text-center font-weight-bold",
                            )
                            html.Th(
                                "Value",
                                classes="text-center font-weight-bold",
                            )
                    with html.Tbody():
                        with html.Tr(
                            v_for=(
                                "[param_key, param_val] of Object.entries(materials_section[selected_material]['PARAMETERS']?.[selected_material_param] || {})",
                            ),
                            classes="text-center",
                        ):
                            html.Td(v_text=("param_key",))
                            # if parameter of material parameter is
                            # single-value: we show a modifiable
                            # text field
                            with html.Td(
                                v_if=(
                                    "materials_section[selected_material]['PARAMETERS'][selected_material_param][param_key]!== null && typeof materials_section[selected_material]['PARAMETERS'][selected_material_param][param_key] !== 'object' && !Array.isArray(materials_section[selected_material]['PARAMETERS'][selected_material_param][param_key])",
                                )
                            ):
                                vuetify.VTextField(
                                    v_model=(
                                        "materials_section[selected_material]['PARAMETERS'][selected_material_param][param_key]",
                                    ),
                                    update_modelValue="flushState('materials_section')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                                    classes="mx-10",
                                )
                            # else if parameter of material parameter is
                            # list | dict -> we don't make it modifiable (currently)
                            html.Td(
                                v_if=(
                                    "Array.isArray(materials_section[selected_material]['PARAMETERS'][selected_material_param][param_key]) || typeof materials_section[selected_material]['PARAMETERS'][selected_material_param][param_key] == 'object'",
                                ),
                                v_text=(
                                    "materials_section[selected_material]['PARAMETERS'][selected_material_param][param_key]",
                                ),
                            )
        ##################################
        # CLONING MATERIAL MAP #############
        ##################################
        with html.Div(
            v_if=(
                "selected_section_name == section_names['MATERIALS']['subsections'][1] && cloning_material_map_section.length>0",
            ),
        ):
            ##################################################
            # View Mode == Edit Mode (currently) #############
            ##################################################
            with html.Div():
                # show table of cloning material map items
                with vuetify.VTable(classes="mx-3"):
                    with html.Thead():
                        with html.Tr():
                            html.Th(
                                "SOURCE FIELD",
                                classes="text-center font-weight-bold",
                            )
                            html.Th(
                                "SOURCE MATERIAL",
                                classes="text-center font-weight-bold",
                            )
                            html.Th(
                                "TARGET FIELD",
                                classes="text-center font-weight-bold",
                            )
                            html.Th(
                                "TARGET MATERIAL",
                                classes="text-center font-weight-bold",
                            )
                    with html.Tbody():
                        with html.Tr(
                            v_for=("item in cloning_material_map_section"),
                        ):
                            html.Td(
                                v_text=("item['SRC_FIELD']",),
                                classes="text-center",
                            )
                            html.Td(
                                v_text=("item['SRC_MAT']",),
                                classes="text-center",
                            )
                            html.Td(
                                v_text=("item['TAR_FIELD']",),
                                classes="text-center",
                            )
                            html.Td(
                                v_text=("item['TAR_MAT']",),
                                classes="text-center",
                            )


def _design_conditions_panel():
    """Layout for the design conditions panel."""
    with html.Div(
        v_if=(
            "section_names[selected_main_section_name]['content_mode'] == all_content_modes['design_conditions_section']"
        ),
    ):
        # dropdown for geometries: POINT, LINE, SURF, VOL
        vuetify.VSelect(
            v_if=("Object.keys(dc_sections).length > 0",),
            v_model=("selected_dc_geometry_type",),
            items=("Object.keys(dc_sections)",),
        )
        # dropdown for entities
        vuetify.VSelect(
            v_if=(
                "Object.keys(dc_sections).length > 0 && Object.keys(dc_sections[selected_dc_geometry_type]).length > 0",
            ),
            v_model=("selected_dc_entity",),
            items=("Object.keys(dc_sections[selected_dc_geometry_type])",),
        )
        with html.Div(
            v_if=(
                "Object.keys(dc_sections).length > 0 && Object.keys(dc_sections[selected_dc_geometry_type]).length > 0",
            ),
        ):
            # view mode: show table of property - value
            with vuetify.VTable(
                v_if=(
                    "Object.keys(dc_sections).length > 0 && Object.keys(dc_sections[selected_dc_geometry_type]).length > 0 && edit_mode == all_edit_modes['view_mode']",
                ),
                classes="mx-3",
            ):
                with html.Thead():
                    with html.Tr():
                        html.Th(
                            "CONDITION TYPE",
                            classes="text-center font-weight-bold",
                        )
                        html.Th(
                            "SETTINGS",
                            classes="text-center font-weight-bold",
                        )
                with html.Tbody():
                    with html.Tr(
                        v_for=(
                            "[item_key, item_val] of Object.entries(dc_sections[selected_dc_geometry_type]?.[selected_dc_entity] || {})"
                        ),
                    ):
                        html.Td(
                            v_text=("item_key",),
                            classes="text-center",
                        )
                        html.Td(
                            v_text=("item_val",),
                            classes="text-center",
                        )

            # edit mode: add selector for conditions and display the setting
            # items in a property - value table
            with html.Div(v_if=("edit_mode == all_edit_modes['edit_mode']",)):
                vuetify.VSelect(
                    v_model=("selected_dc_condition",),
                    items=(
                        "Object.keys(dc_sections[selected_dc_geometry_type][selected_dc_entity])",
                    ),
                )
                with vuetify.VTable(classes="mx-3"):
                    with html.Thead():
                        with html.Tr():
                            html.Th(
                                "Property",
                                classes="text-center font-weight-bold",
                            )
                            html.Th(
                                "Value",
                                classes="text-center font-weight-bold",
                            )
                    with html.Tbody():
                        with html.Tr(
                            v_for=(
                                "[item_key, item_val] of Object.entries(dc_sections[selected_dc_geometry_type][selected_dc_entity][selected_dc_condition])"
                            ),
                        ):
                            html.Td(
                                v_text=("item_key",),
                                classes="text-center",
                            )
                            # single values (!= dict and != list): show
                            # modifiable text field
                            with html.Td(
                                v_if=(
                                    "item_val !== null && !Array.isArray(item_val) && typeof item_val !== 'object'"
                                ),
                                classes="text-center",
                            ):
                                vuetify.VTextField(
                                    v_model=(
                                        "dc_sections[selected_dc_geometry_type][selected_dc_entity][selected_dc_condition][item_key]",
                                    ),
                                    update_modelValue="flushState('dc_sections')",
                                    classes="mx-10",
                                    dense=True,
                                    hide_details=True,
                                )
                            # for lists within condition parameters: show
                            # list of modifiable text fields
                            # modifiable text field
                            with html.Td(
                                v_if=("item_val !== null && Array.isArray(item_val) "),
                                classes="text-center",
                            ):
                                with vuetify.VList():
                                    with html.Div(
                                        v_for=(
                                            "(param_item, param_index) in item_val",
                                        ),
                                        key="param_index",
                                        classes="d-flex align-center",
                                    ):
                                        vuetify.VIcon(
                                            "mdi-circle-small",
                                            color="primary",
                                            classes="mr-2",
                                        )
                                        vuetify.VTextField(
                                            v_model=(
                                                "dc_sections[selected_dc_geometry_type][selected_dc_entity][selected_dc_condition][item_key][param_index]",
                                            ),
                                            dense=True,
                                            hide_details=True,
                                            update_modelValue="flushState('dc_sections')",
                                            classes="mx-10",
                                        )


def _result_description_panel():
    """Layout for the result description panel."""
    with html.Div(
        v_if=(
            "section_names[selected_main_section_name]['content_mode'] == all_content_modes['result_description_section']",
        ),
    ):
        with html.Div(
            v_if=("Object.keys(result_description_section).length > 0",),
        ):
            # dropdown for indices
            vuetify.VSelect(
                v_model=("selected_result_description_id",),
                items=("Object.keys(result_description_section)",),
            )

            # visualization of the field
            with html.Div(classes="d-flex align-center ga-3 mb-5 pl-5 w-full"):
                html.Span("FIELD: ", classes="text-h6")
                # view mode: text
                html.Span(
                    v_if=("edit_mode ==  all_edit_modes['view_mode']",),
                    v_text=(
                        "result_description_section[selected_result_description_id]['FIELD']",
                    ),
                )
                with html.Div(
                    v_if=("edit_mode ==  all_edit_modes['edit_mode']",),
                    classes="flex-fill",
                ):
                    vuetify.VTextField(
                        v_model=(
                            "result_description_section[selected_result_description_id]['FIELD']",  # binding item_val directly does not work, since Object.entries(...) creates copies for the mutable objects
                        ),
                        update_modelValue="flushState('result_description_section')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                        classes="mx-10",
                        dense=True,
                        hide_details=True,
                    )

            # show result description parameters (as a table with different
            # view<->edit mode structures)
            html.P("PARAMETERS: ", classes="text-h6 pl-5 mb-1")
            # show table of parameters in view mode
            with vuetify.VTable(
                v_if=("edit_mode ==  all_edit_modes['view_mode']",), classes="mx-3"
            ):
                with html.Thead():
                    with html.Tr():
                        html.Th(
                            "Property",
                            classes="text-center font-weight-bold",
                        )
                        html.Th(
                            "Value",
                            classes="text-center font-weight-bold",
                        )
                with html.Tbody():
                    with html.Tr(
                        v_for=(
                            "[param_key, param_val] of Object.entries(result_description_section[selected_result_description_id]?.['PARAMETERS'] || {})",
                        ),
                        classes="text-center",
                    ):
                        html.Td(v_text=("param_key",))
                        html.Td(
                            v_if=("edit_mode ==  all_edit_modes['view_mode']",),
                            v_text=("param_val",),
                        )

        with html.Div(
            v_if=(
                "edit_mode ==  all_edit_modes['edit_mode'] && Object.keys(result_description_section[selected_result_description_id]).length > 0",
            ),
            classes="pl-8",
        ):
            vuetify.VSelect(
                v_model=("selected_result_description_param",),
                items=(
                    "Object.keys(result_description_section[selected_result_description_id]['PARAMETERS'])",
                ),
                classes="mx-10",
            )
            # if parameter is single value (as opposed to list or
            # dict) -> VTextField
            vuetify.VTextField(
                v_if=(
                    "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param]!== null && typeof result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param] !== 'object' && !Array.isArray(result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param])",
                ),
                v_model=(
                    "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param]",
                ),
                update_modelValue="flushState('result_description_section')",
                classes="mx-10",
                dense=True,
                hide_details=True,
            )
            # if parameter is list -> VTextField
            with vuetify.VList(
                v_if=(
                    "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param]!== null && Array.isArray(result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param])"
                ),
            ):
                with html.Div(
                    v_for=(
                        "(param_item, param_index) in result_description_section[selected_result_description_id]?.PARAMETERS?.[selected_result_description_param]",
                    ),
                    key="param_index",
                    classes="d-flex align-center",
                ):
                    vuetify.VIcon(
                        "mdi-circle-medium",
                        color="primary",
                        classes="mr-2",
                    )
                    vuetify.VTextField(
                        v_model=(
                            "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_index]",
                        ),
                        dense=True,
                        hide_details=True,
                        update_modelValue="flushState('result_description_section')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                        classes="mx-10",
                    )
            # show table of modifiable dict parameters if material
            # parameter is a dict
            with vuetify.VTable(
                v_if=(
                    "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param]!== null && typeof result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param] === 'object' && !Array.isArray(result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param])"
                ),
                classes="mx-3",
            ):
                with html.Thead():
                    with html.Tr():
                        html.Th(
                            "Property",
                            classes="text-center font-weight-bold",
                        )
                        html.Th(
                            "Value",
                            classes="text-center font-weight-bold",
                        )
                with html.Tbody():
                    with html.Tr(
                        v_for=(
                            "[param_key, param_val] of Object.entries(result_description_section[selected_result_description_id]['PARAMETERS']?.[selected_result_description_param] || {})",
                        ),
                        classes="text-center",
                    ):
                        html.Td(v_text=("param_key",))
                        # if parameter of material parameter is
                        # single-value: we show a modifiable
                        # text field
                        with html.Td(
                            v_if=(
                                "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_key]!== null && typeof result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_key] !== 'object' && !Array.isArray(result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_key])",
                            )
                        ):
                            vuetify.VTextField(
                                v_model=(
                                    "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_key]",
                                ),
                                update_modelValue="flushState('result_description_section')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                                classes="mx-10",
                            )
                        # else if parameter of material parameter is
                        # list | dict -> we don't make it modifiable (currently)
                        html.Td(
                            v_if=(
                                "Array.isArray(result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_key]) || typeof result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_key] == 'object'",
                            ),
                            v_text=(
                                "result_description_section[selected_result_description_id]['PARAMETERS'][selected_result_description_param][param_key]",
                            ),
                        )


def create_gui(server, render_window):
    """Creates the graphical user interface based on the defined layout
    elements."""
    with SinglePageWithDrawerLayout(server) as layout:
        layout.title.hide()

        with layout.toolbar as toolbar:
            toolbar.height = 100
            _toolbar(server.controller)

        with html.Div(v_if=("vtu_path != ''",)):
            _bottom_sheet_info()
            _bottom_sheet_export(server.controller)

        with layout.drawer as drawer:
            drawer.width = 800
            with html.Div(v_if=("vtu_path != ''",)):
                # EDIT MODE switch
                vuetify.VSwitch(
                    v_model=("edit_mode", "all_edit_modes['view_mode']"),
                    label=("edit_mode", "VIEW"),
                    true_value=("all_edit_modes['edit_mode']",),
                    false_value=("all_edit_modes['view_mode']",),
                    color="primary",
                    inset=True,
                    classes="ml-5",
                )

                # Further elements with conditional rendering (see above)
                _sections_dropdown()
                _prop_value_table()
                _materials_panel()
                _functions_panel(server)
                _design_conditions_panel()
                _result_description_panel()
            with html.Div(classes="flex-column justify-start"):
                vuetify.VCard(
                    title="No input file content available",
                    v_if=("vtu_path == ''",),
                    classes="text-center",
                    height="100%",
                )
                vuetify.VAlert(
                    title="There was a problem while trying to validate your input! Further details are provided in the terminal output...",
                    type="error",
                    v_if=(
                        "read_in_status == all_read_in_statuses['validation_error']",
                    ),
                    classes="mt-1",
                )
                vuetify.VAlert(
                    title="There was a problem while trying to convert the input file to vtu (using lnmmeshio)! Further details are provided in the terminal output...",
                    type="error",
                    v_if=(
                        "read_in_status == all_read_in_statuses['vtu_conversion_error']",
                    ),
                    classes="mt-1",
                )

        with layout.content:
            with vuetify.VContainer(
                fluid="true", classes="pa-0 fill-height", v_if=("vtu_path != ''",)
            ):
                # html_view = vtk.VtkRemoteView(render_window)
                html_view = plotter_ui(render_window)
                server.controller.view_update = (
                    html_view.update
                )  # update function for the vtk figure
                server.controller.view_reset_camera = html_view.reset_camera
                server.controller.on_server_ready.add(html_view.update)
                server.controller.on_server_ready.add(html_view.reset_camera)
