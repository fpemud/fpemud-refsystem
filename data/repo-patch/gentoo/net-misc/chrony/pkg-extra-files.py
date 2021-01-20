#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob
import subprocess

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_extra_files()
{
        echo "/var/lib/chrony"
        echo "/var/lib/chrony/***"
        echo "/var/log/chrony"
        echo "/var/log/chrony/***"
}
""")
    subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
