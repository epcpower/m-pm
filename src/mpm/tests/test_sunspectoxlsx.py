import csv
import pathlib

import mpm.mpm_helper
import mpm.project
import mpm.smdxtosunspec
import mpm.sunspectoxlsx


this = pathlib.Path(__file__).resolve()
here = this.parent


smdx_path = here / "sunspec"


def test_x():
    project = mpm.project.loadp(here / "project" / "project.pmp")

    attrs_model = project.models.sunspec1
    parameter_model = project.models.parameters

    enumerations = parameter_model.list_selection_roots["enumerations"]
    sunspec_types = mpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations.append_child(sunspec_types)
    parameter_model.list_selection_roots["sunspec types"] = sunspec_types

    requested_models = [1, 17, 103, 65534]
    sunspec_models = mpm.smdxtosunspec.import_models(
        *requested_models,
        parameter_model=parameter_model,
        paths=[smdx_path],
    )

    for sunspec_model in sunspec_models:
        attrs_model.root.append_child(sunspec_model)

    points = (
        (model, block, point)
        for model in attrs_model.root.children
        if isinstance(model, mpm.sunspecmodel.Model)
        for block in model.children
        for point in block.children
    )

    get_set = mpm.smdxtosunspec.import_get_set(
        smdx_path / "MODBUS_SunSpec-EPC.xlsx",
    )

    for model, block, point in points:
        parameter = attrs_model.node_from_uuid(point.parameter_uuid)
        for direction in ("get", "set"):
            key = mpm.smdxtosunspec.GetSetKey(
                model=model.id,
                name=parameter.abbreviation,
                get_set=direction,
            )
            accessor = get_set.get(key)
            if accessor is not None:
                setattr(point, direction, accessor)

    project.filename = here / "project_with_sunspec" / "project.pmp"
    project.paths["sunspec1"] = "sunspec1.json"
    project.paths["sunspec2"] = "sunspec2.json"
    project.filename.parent.mkdir(parents=True, exist_ok=True)
    project.save()

    builder = mpm.sunspectoxlsx.builders.wrap(
        wrapped=attrs_model.root,
        parameter_uuid_finder=attrs_model.node_from_uuid,
        parameter_model=project.models.parameters,
        column_filter=mpm.mpm_helper.attr_fill(mpm.sunspectoxlsx.Fields, True),
        sunspec_id=mpm.mpm_helper.SunSpecSection.SUNSPEC_ONE,
    )

    workbook = builder.gen()

    assert workbook.sheetnames == [
        "License Agreement",
        "Summary",
        "Index",
        "1",
        "17",
        "103",
        "65534",
    ]

    workbook.save("test_sunspectoxlsx.xlsx")

    with open("test_sunspectoxlsx.csv", "w", newline="") as file:
        writer = csv.writer(file)

        for sheet in workbook.worksheets:
            for row in sheet.rows:
                writer.writerow(cell.value for cell in row)
