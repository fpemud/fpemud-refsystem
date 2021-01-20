#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob
import subprocess

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_extra_files()
{
        echo "/etc/portage"
        echo "/etc/portage/*"

        echo "/etc/profile.env"
        echo "/etc/csh.env"

        echo "/etc/ld.so.conf"

        echo "/var/log/emerge-fetch.log"
        echo "/var/log/emerge.log"
}
""")
    subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
