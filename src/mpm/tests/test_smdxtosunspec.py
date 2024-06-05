# import collections
import pathlib

import pytest
import sunspec.core.client

import mpm.smdxtosunspec


this = pathlib.Path(__file__).resolve()
here = this.parent


smdx_path = here / "sunspec"


@pytest.fixture
def fresh_pathlist():
    original_pathlist = sunspec.core.device.file_pathlist
    sunspec.core.device.file_pathlist = sunspec.core.util.PathList()

    yield sunspec.core.device.file_pathlist

    sunspec.core.device.file_pathlist = original_pathlist


def test_load():
    project = mpm.project.loadp(here / "project" / "project.pmp")

    parameter_model = project.models.parameters
    enumerations = parameter_model.list_selection_roots["enumerations"]
    sunspec_types = mpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations.append_child(sunspec_types)
    parameter_model.list_selection_roots["sunspec types"] = sunspec_types

    requested_models = [1, 17, 103, 65534]

    models = mpm.smdxtosunspec.import_models(
        *requested_models,
        parameter_model=project.models.parameters,
        paths=[smdx_path],
    )

    assert [model.id for model in models] == requested_models
