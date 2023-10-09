import codecs
import os
import re
from typing import Any

from nbconvert import HTMLExporter
import nbconvert
from nbconvert.preprocessors import ExecutePreprocessor
import nbformat


def check_placeholders(nb: nbformat.NotebookNode) -> None:
    """
    Checks that all placeholders in a notebook have been filled.
    """
    for i, cell in enumerate(nb["cells"]):
        if cell["source"].startswith(f"# @ PLACEHOLDER<"):
            re_res = re.search(r"# @ PLACEHOLDER<(.*)>", cell["source"])
            extra_info = f", key: '{re_res.groups()[0]}'" if re_res is not None else ""
            raise ValueError(f"Unfilled placeholder in cell {i}{extra_info}")


def fill_placeholders(nb: nbformat.NotebookNode, fills: dict, add_autofilled_flag=False) -> None:
    """
    Replace placeholders in a notebook.

    Allows putting anything in the placeholder cell but the fill must be a string
    """
    for i, cell in enumerate(nb["cells"]):
        if cell["source"].startswith(f"# @ PLACEHOLDER<"):
            # get key inside placeholder
            re_res = re.search(r"# @ PLACEHOLDER<(.*)>", cell["source"])

            # if key is not raise error
            if re_res is None:
                raise ValueError(f"Invalid or missing template key in cell {i}")

            # get actual key string
            key = re_res.groups()[0]

            # fill cell
            if key not in fills:
                raise KeyError(f"Missing key '{key}' for cell {i} in provided dict")

            if add_autofilled_flag:
                cell["source"] = "# @ AUTOFILLED<{key}>\n" + fills[key]
            else:
                cell["source"] = fills[key]

    # check if all placeholders have been filled
    check_placeholders(nb)


def fill(**kwargs) -> str:
    """
    Prepares a fill for a placeholder in a notebook with variables declarations.
    """
    def surround(s: str):
        # TODO add escaping
        return f"'{s}'"

    return "\n".join([f"{k} = {v if not isinstance(v, str) else surround(v)}" for k, v in kwargs.items()])


def _export_last_cell(notebook_path: str) -> None:
    """
    Export last cell from a notebook to html.

    Something I needed but you probably don't
    """
    html_path = notebook_path.replace(".ipynb", ".html")

    if os.path.exists(html_path):
        print(f"HTML output already exists at {html_path}, skipping.")
        return

    print(f"Exporting '{notebook_path}' last cell to '{html_path}'…")
    nb = nbformat.read(notebook_path, as_version=4)

    cell = {"source": ""}
    i = 1
    while cell["source"] == "":
        cell = nb["cells"][-i]
        i += 1

    nb["cells"] = [cell]

    exporter = HTMLExporter()
    output, _ = exporter.from_notebook_node(nb)
    codecs.open(html_path, "w", encoding="utf-8").write(output)


def fill_n_run(
    template_path: str,
    fills: dict[str, str],
    add_autofilled_flag=False,
    **kwargs,
) -> nbformat.NotebookNode:
    # Open template
    with open(template_path) as template_file:
        nb = nbformat.read(template_file, as_version=4)

    # fill placeholders
    fill_placeholders(nb, fills, add_autofilled_flag=add_autofilled_flag)

    # run notebook
    ep = ExecutePreprocessor(timeout=None, allow_error=True, **kwargs)
    ep.preprocess(nb, {"metadata": {"path": "./"}})

    return nb


def frs(
    template_path: str,
    out_path: str,
    fills: dict[str, str],
    **kwargs
):
    """
    Fill, Run and Save.
    """
    nb = fill_n_run(template_path, fills, **kwargs)
    # save outputs
    with open(out_path, "w", encoding="utf-8") as out_file:
        nbformat.write(nb, out_file)


def fre(
    template_path: str,
    exporter: nbconvert.Exporter,
    fills: dict[str, str],
    **kwargs
) -> Any:
    """
    Fill, Run and Export.
    """
    nb = fill_n_run(template_path, fills, **kwargs)
    output, _ = exporter.from_notebook_node(nb)
    return output



if __name__ == "__main__":
    output = fre(
        "./Example_template.ipynb",
        nbconvert.exporters.HTMLExporter(),
        {
            "values": fill(
                value="another value",
                intvalue=300,
            ),
            "md": "**Some markdown** for a markdown cell",
        },
        kernel_name = "mykernel"
    )
    codecs.open("test.html", "w", encoding="utf-8").write(output)
