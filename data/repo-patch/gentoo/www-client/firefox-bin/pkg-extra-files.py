#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob
import subprocess

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_extra_files()
{
        echo "~/.mozilla/firefox"
        echo "~/.mozilla/firefox/***"
        echo "~/.cache/mozilla/firefox"
        echo "~/.cache/mozilla/firefox/***"
}
""")
    subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
