#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob
import subprocess

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_extra_files()
{
        echo "/usr/bin/python-config"
        echo "/usr/bin/pydoc"
        echo "/usr/bin/idle"
        echo "/usr/bin/2to3"
        echo "/usr/bin/pythonw"
        echo "/usr/bin/python"
        echo "/usr/bin/python2"
        echo "/usr/bin/python3"
}
""")
    subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
