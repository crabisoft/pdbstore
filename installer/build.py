#!/usr/bin/env
"""
This file is able to create a self contained pdbstore executable that contains all it needs,
including the Python interpreter, so it wouldnt be necessary to have Python installed
in the system
It is important to install the dependencies and the project first with "pip install -e ."
which configures the project as "editable", that is, to run from the current source folder
After creating the executable, it can be pip uninstalled

$ pip install -e .
$ python installer/build.py

This has to run in the same platform that will be using the executable, pyinstaller does
not cross-build

The resulting executable can be put in the system PATH of the running machine
"""
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from zipfile import ZipFile

filescript_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if filescript_dir not in sys.path:
    sys.path.insert(0, filescript_dir)

from pdbstore import __version__  # noqa: E402 # pylint: disable=wrong-import-position
from pdbstore.typing import Any  # noqa: E402 # pylint: disable=wrong-import-position


def _check_build_result(dist_folder: str) -> str:
    # run the binary to test if working
    pdbstore_bin = os.path.join(dist_folder, "pdbstore")
    if platform.system() == "Windows":
        pdbstore_bin = pdbstore_bin + ".exe"
    retcode = os.system(f'"{pdbstore_bin}" --help 2>NULL')
    if retcode != 0:
        raise SystemError(f"{pdbstore_bin}: Binary not working")
    return pdbstore_bin


def _is_github_action() -> bool:
    return os.environ.get("GITHUB_ACTIONS", None) is not None


def _windows_rc_file(version: str) -> str:
    template = """# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers={version_tuple},
    prodvers={version_tuple},
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'000004b0',
        [StringStruct(u'Comments', u'This executable was created with pyinstaller'),
        StringStruct(u'CompanyName', u'CrabiSoft'),
        StringStruct(u'FileDescription', u'Manage symbol store'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'LegalCopyright', u'Copyright 2023 CrabiSoft'),
        StringStruct(u'ProductName', u'pdbstore'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [0, 1200])])
  ]
)"""
    if "-" in version:
        version, _ = version.split("-")
    version_tuple = tuple([int(v) for v in version.split(".")] + [0])
    return template.format(version=version, version_tuple=version_tuple)


def build_installer(source_folder: str, work_folder: str) -> str:
    """Build required executable"""
    if _is_github_action():
        # Install pyinstaller
        subprocess.call("pip install pyinstaller", shell=True)

    build_folder = os.path.join(work_folder, "_build")
    dist_folder = os.path.join(work_folder, "dist")
    command = "pyinstaller"
    exe_name = "pdbstore"

    def _on_rm_tree_error(*args: Any) -> None:
        print(f"Unable to remove old folder: {args[0]}")

    shutil.rmtree(build_folder, onerror=_on_rm_tree_error)

    if not os.path.exists(build_folder):
        os.makedirs(build_folder, exist_ok=True)

    main_script_path = os.path.join(source_folder, "pdbstore", "__main__.py")
    hidden = "--collect-submodules=pdbstore.cli.commands "

    if platform.system() == "Windows":
        win_ver_file = os.path.join(build_folder, "windows-version-file")
        ico_file_path = os.path.join(source_folder, "installer", "pdb.ico")
        content = _windows_rc_file(__version__)
        with open(win_ver_file, "wt", encoding="utf-8") as fpyins:
            fpyins.write(content)
        win_ver = f'--version-file "{win_ver_file}" -i "{ico_file_path}"'
    else:
        win_ver = ""

    templates_folder = os.path.join(source_folder, "pdbstore", "templates")
    dirs_info = next(os.walk(templates_folder))
    pkg_data = " --add-data ".join(
        [
            f"\"{os.path.join(dirs_info[0], d, '*.tmpl')}:pdbstore/templates/{d}\""
            for d in filter(lambda dc: not dc.endswith("__pycache__"), dirs_info[1])
        ]
    )

    env_pyinstaller = os.environ
    env_pyinstaller["PYTHONPATH"] = source_folder
    print(
        f"{command} -F -y -n {exe_name} -p {source_folder} --console "
        f"--workpath {build_folder} --distpath {dist_folder} "
        f"--add-data {pkg_data} "
        f"{main_script_path} {hidden} {win_ver} ",
    )
    subprocess.call(
        f"{command} -F -y -n {exe_name} -p {source_folder} --console "
        f"--workpath {build_folder} --distpath {dist_folder} "
        f"--add-data {pkg_data} "
        f"{main_script_path} {hidden} {win_ver} ",
        shell=True,
        env=env_pyinstaller,
    )

    # Build required executable
    exe_path = _check_build_result(dist_folder)
    if _is_github_action():
        # Create archive for release notes
        file_path = os.path.splitext(exe_path)[0]
        if platform.system() == "Windows":
            with ZipFile(file_path + "-win-64.zip", "w") as zip_file:
                zip_file.write(exe_path, arcname=os.path.basename(exe_path))
        else:
            with tarfile.open(file_path + "-linux-64.tar.gz", "w:gz") as tar_file:
                tar_file.add(exe_path, arcname=os.path.basename(exe_path))
    return os.path.abspath(os.path.join(dist_folder, "pdbstore"))


if __name__ == "__main__":
    script_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
    src_folder = os.path.dirname(script_dir)
    output_folder = build_installer(src_folder, script_dir)
    print(
        "\n**************  PDBStore executable created!  ******************\n"
        f"\nAppend this folder to your system PATH: '{output_folder}'\n"
        "Feel free to move the whole folder to another location.\n"
    )
