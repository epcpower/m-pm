import textwrap

import graham

import mpm.project

import pathlib

import epyqlib.pm

reference_string = textwrap.dedent(
    """\
{
    "_type": "project",
    "paths": {
        "_type": "models",
        "parameters": "parameters.json",
        "can": "can.json",
        "sunspec1": "sunspec1.json",
        "sunspec2": "sunspec2.json",
        "staticmodbus": "staticmodbus.json",
        "anomalies": "anomalies.json"
    }
}"""
)

reference_project = mpm.project.Project()
reference_project.paths.parameters = "parameters.json"
reference_project.paths.can = "can.json"
reference_project.paths.sunspec1 = "sunspec1.json"
reference_project.paths.sunspec2 = "sunspec2.json"
reference_project.paths.staticmodbus = "staticmodbus.json"
reference_project.paths.anomalies = "anomalies.json"


def test_save():
    assert reference_string == graham.dumps(reference_project, indent=4).data


def test_load():
    assert reference_project == (
        graham.schema(mpm.project.Project).loads(reference_string).data
    )


def test_model_iterable():
    model = mpm.project.Models()

    assert tuple(model) == (
        "parameters",
        "can",
        "sunspec1",
        "sunspec2",
        "staticmodbus",
        "anomalies",
    )


def test_model_set_all():
    model = mpm.project.Models()

    value = object()

    model.set_all(value)

    assert all(v is value for v in model.values())


def test_model_items():
    model = mpm.project.Models()

    expected = (
        ("parameters", None),
        ("can", None),
        ("sunspec1", None),
        ("sunspec2", None),
        ("staticmodbus", None),
        ("anomalies", None),
    )

    assert tuple(model.items()) == expected


def test_model_values():
    model = mpm.project.Models()

    for name in model:
        model[name] = name + "_"

    assert tuple(model.values()) == (
        "parameters_",
        "can_",
        "sunspec1_",
        "sunspec2_",
        "staticmodbus_",
        "anomalies_",
    )


def test_model_getitem():
    model = mpm.project.Models()

    values = []
    for name in model:
        values.append(model[name])

    assert values == [None] * 6


def test_model_proper_selection_roots():
    project = mpm.project.loadp(pathlib.Path(__file__).with_name("example_project.pmp"))

    expected = epyqlib.pm.parametermodel.types.list_selection_roots()

    assert set(project.models.parameters.list_selection_roots.keys()) == expected
