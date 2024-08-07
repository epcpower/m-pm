import pathlib

import click

import epyqlib.pm.parametermodel

import mpm.parameterstohierarchy
import mpm.project
import mpm.cantosym


def relative_path(target, reference):
    reference = pathlib.Path(reference)
    if reference.is_file():
        reference = reference.parents[0]

    return pathlib.Path(target).resolve().relative_to(reference.resolve())


@click.command()
@click.option("--project", "project_file", type=click.File(), required=True)
@click.option("--bcu-project", "bcu_project_file", type=click.File(), required=False)
@click.option("--sym", "sym_file", type=click.File("w"), required=True)
@click.option(
    "--hierarchy",
    "hierarchy_file",
    type=click.File("w"),
    required=True,
)
def cli(project_file, sym_file, hierarchy_file):
    project = mpm.project.load(project_file)
    bcu_project = mpm.project.load(bcu_project_file)

    (access_levels,) = project.models.parameters.root.nodes_by_filter(
        filter=(lambda node: isinstance(node, epyqlib.pm.parametermodel.AccessLevels)),
    )

    sym_builder = mpm.cantosym.builders.wrap(
        wrapped=project.models.can.root,
        access_levels=access_levels,
        parameter_uuid_finder=project.models.can.node_from_uuid,
        parameter_model=project.models.parameters,
    )

    hierarchy_builder = mpm.parameterstohierarchy.builders.wrap(
        wrapped=project.models.parameters.root,
        can_root=project.models.can.root,
    )

    sym = sym_builder.gen()
    hierarchy = hierarchy_builder.gen(indent=4)
    if hierarchy[-1] != "\n":
        hierarchy += "\n"

    sym_file.write(sym)
    hierarchy_file.write(hierarchy)
