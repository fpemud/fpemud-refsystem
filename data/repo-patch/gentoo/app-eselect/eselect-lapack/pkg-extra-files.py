#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob
import subprocess

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_extra_files()
{
	echo "/usr/lib64/liblapack.a"
	echo "/usr/lib64/liblapack.so"
	echo "/usr/lib64/liblapack.so.3"
	echo "/usr/lib64/pkgconfig/lapack.pc"
}
""")
    subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
