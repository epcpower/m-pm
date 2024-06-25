import alqtendpy.compileui
import pathlib


def compile_ui():
    print("compile_ui building UI in mpm")
    alqtendpy.compileui.compile_ui(
        directory_paths=[pathlib.Path(__file__).parent],
    )
