#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import subprocess

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_cruft_filter()
{
        echo "/var/lib/sddm"
}

pkg_cruft_filter_user()
{
        echo ".local/share/sddm"
        echo ".local/share/sddm/*"
}
""")
    subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
