#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob
import subprocess

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_extra_files()
{
        echo "[var]"
        echo "/var/lib/sddm"
        echo "/var/lib/sddm/***"

        echo "[home]"
        echo "~/.local/share/sddm"
        echo "~/.local/share/sddm/***"
}
""")
    subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
