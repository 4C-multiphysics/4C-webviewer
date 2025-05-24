"""Tests related to pyvista plotting."""

import tempfile
from pathlib import Path

import pytest
import pyvista as pv
from pyvista.trame.ui import plotter_ui
from trame.app import get_server
from trame.app.file_upload import ClientFile
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3


@pytest.mark.gui
def test_pyvista_trame_popup():
    """Test pyvista trame combination."""
    pv.OFF_SCREEN = True

    server = get_server()
    ctrl = server.controller

    pl = pv.Plotter()

    @server.state.change("file_exchange")
    def handle(file_exchange, **kwargs) -> None:
        """Reaction to file exchange."""
        if file_exchange:
            file = ClientFile(file_exchange[0])
            if file.content:
                pl.remove_actor("mesh")
                bytes = file.content  # noqa: A001
                with tempfile.NamedTemporaryFile(suffix=file.name) as path:
                    with Path(path.name).open("wb") as f:
                        f.write(bytes)
                    ds = pv.read(path.name).extract_surface()
                pl.add_mesh(ds, name="mesh")
                pl.reset_camera()
        else:
            pl.clear_actors()
            pl.reset_camera()

    with SinglePageLayout(server) as layout:
        with layout.toolbar:
            vuetify3.VSpacer()
            vuetify3.VFileInput(
                multiple=False,
                show_size=True,
                small_chips=True,
                truncate_length=25,
                v_model=("file_exchange", None),
                density="compact",
                hide_details=True,
                style="max-width: 300px;",
            )
            vuetify3.VProgressLinear(
                indeterminate=True, absolute=True, bottom=True, active=("trame__busy",)
            )

            with layout.content:  # noqa: SIM117
                with vuetify3.VContainer(
                    fluid=True, classes="pa-0 fill-height", style="position: relative;"
                ):
                    view = plotter_ui(pl)
                    ctrl.view_update = view.update
    # Show UI
    server.start(open_browser=False)
