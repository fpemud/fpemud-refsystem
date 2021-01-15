
#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import subprocess

for fn in glob.glob("*.ebuild"):
	with open(fn, "a") as f:
		f.write("""
pkg_cruft_filter()
{
        echo "/var/lib/color"
        echo "/var/lib/color/*"
        echo "/var/lib/colord"
        echo "/var/lib/colord/*"
}
""")
	subprocess.run(["ebuild", fn, "manifest"], stdout=subprocess.DEVNULL)
