#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob
import pathlib
import subprocess

bProcessed = False
for fn in glob.glob("*.ebuild"):
    buf = pathlib.Path(fn).read_text()
    if "python3_7" in buf:
        with open(fn, "w") as f:
            f.write(buf.replace("python3_7", "python3_{7,8,9}"))
        subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
        bProcessed = True

if not bProcessed:
    print("outdated")
