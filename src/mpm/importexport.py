import itertools
import math
import os
import pathlib
import subprocess
import typing

import attr
import graham
import uuid

import mpm.cantosym
import mpm.cantoxlsx
import mpm.canmodel
import mpm.importexportdialog
import mpm.parameterstohierarchy
import mpm.parameterstosil
import mpm.project
import mpm.smdxtosunspec
import mpm.sunspecmodel
import mpm.symtoproject
import mpm.anomaliestoc
import mpm.anomaliestoxlsx
import epyqlib.attrsmodel
import epyqlib.pm.parametermodel


def full_import(paths):
    with open(paths.can, "rb") as sym, open(paths.hierarchy) as hierarchy:
        parameters_root, can_root, sunspec_root = mpm.symtoproject.load_can_file(
            can_file=sym,
            file_type=str(pathlib.Path(sym.name).suffix[1:]),
            parameter_hierarchy_file=hierarchy,
        )

    project = mpm.project.Project()

    project.models.parameters = epyqlib.attrsmodel.Model(
        root=parameters_root,
        columns=epyqlib.pm.parametermodel.columns,
    )
    project.models.can = epyqlib.attrsmodel.Model(
        root=can_root,
        columns=mpm.canmodel.columns,
    )
    project.models.sunspec = epyqlib.attrsmodel.Model(
        root=sunspec_root,
        columns=mpm.sunspecmodel.columns,
    )

    mpm.project._post_load(project)

    # TODO: backmatching
    mpm.symtoproject.go_add_tables(
        parameters_root=project.models.parameters.root,
        can_root=project.models.can.root,
    )

    sunspec_types = mpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations = project.models.parameters.list_selection_roots["enumerations"]
    enumerations.append_child(sunspec_types)

    project.models.update_enumeration_roots()

    sunspec_models = []
    prefix = "smdx_"
    suffix = ".xml"
    for smdx_path in paths.smdx:
        models = mpm.smdxtosunspec.import_models(
            int(smdx_path.name[len(prefix) : -len(suffix)]),
            parameter_model=project.models.parameters,
            paths=[smdx_path.parent],
        )
        sunspec_models.extend(models)

    for sunspec_model in sunspec_models:
        project.models.sunspec.root.append_child(sunspec_model)

    points = (
        (model, block, point)
        for model in project.models.sunspec.root.children
        for block in model.children
        for point in block.children
    )

    get_set = mpm.smdxtosunspec.import_get_set(paths.sunspec1_spreadsheet)

    for model, block, point in points:
        parameter = project.models.sunspec.node_from_uuid(
            point.parameter_uuid,
        )
        for direction in ("get", "set"):
            key = mpm.smdxtosunspec.GetSetKey(
                model=model.id,
                name=parameter.abbreviation,
                get_set=direction,
            )
            accessor = get_set.get(key)
            if accessor is not None:
                setattr(point, direction, accessor)

    project.paths["parameters"] = "parameters.json"
    project.paths["can"] = "can.json"
    project.paths["sunspec1"] = "sunspec1.json"
    project.paths["sunspec2"] = "sunspec2.json"
    project.paths["staticmodbus"] = "staticmodbus.json"
    project.paths["anomalies"] = "anomalies.json"

    return project


def merge_parameter_models(tcu, bcu, unit, param_offset, enum_offset):
    def spoof_uuid(node, payload):
        node.uuid = uuid.UUID(int=(node.uuid.int + param_offset))
        if isinstance(node, epyqlib.pm.parametermodel.Parameter):
            if node.enumeration_uuid is not None:
                node.enumeration_uuid = uuid.UUID(
                    int=(node.enumeration_uuid.int + enum_offset)
                )

    for bcu_child in bcu.children:
        if bcu_child.name == "Parameters":
            for tcu_child in tcu.children:
                # BCU parameters are added under the Parameter group as a subgroup
                if tcu_child.name == "Parameters":
                    bcu_child.name = "BCU{}_".format(unit) + bcu_child.name
                    bcu_child.traverse(
                        call_this=spoof_uuid, payload=None, internal_nodes=True
                    )
                    tcu_child.append_child(bcu_child)
                    break

        elif bcu_child.name == "Enumerations" and unit == 1:
            for tcu_child in tcu.children:
                # Enumerations are merged under the same group
                if tcu_child.name == "Enumerations":
                    for enum in bcu_child.children:
                        enum.name = "BCU_" + enum.name
                        enum.uuid = uuid.UUID(int=(enum.uuid.int + enum_offset))
                        tcu_child.append_child(enum)
                    break

        elif "Other" in bcu_child.name:
            # Others are added under Root as subgroups
            bcu_child.name = "BCU{}_".format(unit) + bcu_child.name
            bcu_child.traverse(call_this=spoof_uuid, payload=None, internal_nodes=True)
            tcu.append_child(bcu_child)


def merge_can_models(tcu, bcu, unit, param_offset, enum_offset):
    def spoof_uuid(node, payload):
        if isinstance(node, mpm.canmodel.Signal):
            node.parameter_uuid = uuid.UUID(
                int=(node.parameter_uuid.int + param_offset)
            )
            if node.enumeration_uuid is not None:
                node.enumeration_uuid = uuid.UUID(
                    int=(node.enumeration_uuid.int + enum_offset)
                )

    for bcu_msg in bcu.children:
        if bcu_msg.name == "ParameterQuery":

            # Find destination ParameterQuery
            dest_param_query = None
            for tcu_msg in tcu.children:
                if tcu_msg.name == "ParameterQuery":
                    dest_param_query = tcu_msg
                    break

            # Append Multiplexers from source under it
            # Shift identifiers and add "BCU_" prefix to avoid conflicts
            for bcu_msg_child in bcu_msg.children:
                if isinstance(bcu_msg_child, mpm.canmodel.Multiplexer):
                    bcu_msg_child.name = "BCU{}_".format(unit) + bcu_msg_child.name
                    bcu_msg_child.identifier += param_offset
                    bcu_msg_child.uuid = uuid.UUID(
                        int=(bcu_msg_child.uuid.int + param_offset)
                    )
                    bcu_msg_child.traverse(
                        call_this=spoof_uuid, payload=None, internal_nodes=False
                    )
                    for bcu_msg_mux_sig in bcu_msg_child.path_children:
                        bcu_msg_mux_sig.parameter_uuid = uuid.UUID(
                            int=(bcu_msg_mux_sig.parameter_uuid.int + param_offset)
                        )

                    dest_param_query.append_child(bcu_msg_child)


def can_hierarchy_export(
    project,
    bcu_projects,
    paths,
) -> None:
    """
    Exports parameter hierarchy and CAN symbol files
    """

    # If BCU project is included, add its contents to CAN and Parameter models
    if bcu_projects:
        # Before merging BCU and TCU models, export the TCU sym file without BCU parameters
        no_bcu_symfile = paths.can.with_name(
            paths.can.stem + "_NO_BCU" + paths.can.suffix
        )
        mpm.cantosym.export(
            path=no_bcu_symfile,
            can_model=project.models.can,
            parameters_model=project.models.parameters,
        )

        unit = 1
        param_offset = 2000
        enum_offset = param_offset

        for bcu_project in bcu_projects:
            # Merge BCU parameters and CAN definitions into TCU models
            merge_parameter_models(
                project.models.parameters.root,
                bcu_project.models.parameters.root,
                unit,
                param_offset,
                enum_offset,
            )
            merge_can_models(
                project.models.can.root,
                bcu_project.models.can.root,
                unit,
                param_offset,
                enum_offset,
            )

            unit += 1
            param_offset += 1000

    # Use extended models with BCU parameter info when exporing sym and
    # parameter hierarchies
    mpm.cantosym.export(
        path=paths.can,
        can_model=project.models.can,
        parameters_model=project.models.parameters,
    )

    mpm.parameterstohierarchy.export(
        path=paths.hierarchy,
        can_model=project.models.can,
        parameters_model=project.models.parameters,
    )


def interface_code_export(
    project,
    paths,
    skip_output=False,
    include_uuid_in_item=False,
):
    """
    Exports interface code
    """

    mpm.anomaliestoc.export(
        h_path=paths.anomalies_h,
        anomaly_model=project.models.anomalies,
        parameters_model=project.models.parameters,
    )

    mpm.anomaliestoxlsx.export(
        path=paths.anomalies_spreadsheet,
        anomaly_model=project.models.anomalies,
        parameters_model=project.models.parameters,
        skip_output=False,
    )


def full_export(
    project,
    bcu_projects,
    paths,
    target_directory,
    first_time=False,
    skip_output=False,
    include_uuid_in_item=False,
):
    can_hierarchy_export(project, bcu_projects, paths)
    interface_code_export(project, paths, skip_output, include_uuid_in_item)


def modification_time_or(path, alternative):
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return alternative


def get_sunspec_models(path):
    root_schema = graham.schema(mpm.sunspecmodel.Root)
    raw = path.read_bytes()
    root = root_schema.loads(raw).data

    return tuple(
        child.id for child in root.children if isinstance(child, mpm.sunspecmodel.Model)
    )


def is_stale(project, paths, skip_sunspec=False):
    loaded_project = mpm.project.loadp(project, post_load=False)

    source_paths = (
        project,
        *(project.parent / path for path in attr.astuple(loaded_project.paths)),
    )

    source_modification_time = max(path.stat().st_mtime for path in source_paths)

    if skip_sunspec:
        sunspec1_models = []
        sunspec2_models = []
    else:
        sunspec1_models = get_sunspec_models(
            project.parent / loaded_project.paths.sunspec1,
        )
        sunspec2_models = get_sunspec_models(
            project.parent / loaded_project.paths.sunspec2,
        )

    smdx1 = tuple(
        paths.sunspec_c / f"smdx1_{model:05}.xml" for model in sunspec1_models
    )
    smdx2 = tuple(
        paths.sunspec_c / f"smdx2_{model:05}.xml" for model in sunspec2_models
    )

    sunspec1_c_h = tuple(
        paths.sunspec_c / f"sunspec1InterfaceGen{model}.{extension}"
        for model, extension in itertools.product(sunspec1_models, ("c", "h"))
    )
    sunspec2_c_h = tuple(
        paths.sunspec_c / f"sunspec2InterfaceGen{model}.{extension}"
        for model, extension in itertools.product(sunspec2_models, ("c", "h"))
    )

    sil_c_h = (paths.sil_c, paths.sil_c.with_suffix(".h"))

    destination_paths = [
        paths.can,
        paths.hierarchy,
        *paths.smdx,
        paths.sunspec1_spreadsheet,
        paths.sunspec2_spreadsheet,
        paths.sunspec1_spreadsheet_user,
        paths.sunspec2_spreadsheet_user,
        *smdx1,
        *smdx2,
        *sunspec1_c_h,
        *sunspec2_c_h,
        paths.sunspec1_tables_c,
        paths.sunspec2_tables_c,
        *sil_c_h,
    ]

    destination_modification_time = min(
        modification_time_or(path=path, alternative=-math.inf)
        for path in destination_paths
    )

    destination_newer_by = destination_modification_time - source_modification_time

    return destination_newer_by < 1


def generate_docs(
    project: mpm.project.Project,
    paths: mpm.importexportdialog.ImportPaths,
    pmvs_path: pathlib.Path,
    generate_formatted_output: bool,
    product_specific_defaults: typing.List[str],
) -> None:
    """
    Generate the CAN model parameter data documentation.

    Args:
        project: PM project (pmp)
        paths: import/export dialog paths
        pmvs_path: PMVS output path
        generate_formatted_output: generate formatted output (takes a long time)

    Returns:

    """
    mpm.cantoxlsx.export(
        path=paths.spreadsheet_can,
        can_model=project.models.can,
        pmvs_path=pmvs_path,
    )

    if generate_formatted_output:
        mpm.cantoxlsx.format_for_manual(
            input_path=paths.spreadsheet_can,
            parameters_model=project.models.parameters,
            product_specific_defaults=product_specific_defaults,
        )
