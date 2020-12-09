#!/usr/bin/python3.6
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import re
import sys
sys.path.append('/usr/lib64/fpemud-refsystem')
from fm_util import FmUtil
from fm_param import FmConst
from helper_pkg_merger import PkgMerger


# get packages versioned as "-9999"
pkgList = []
for fbasename in sorted(FmUtil.getFileList(FmConst.portageDbDir, 2, "d")):
    if FmUtil.repoIsSysFile(fbasename):
        continue
    if fbasename.split("/")[1].startswith("-MERGING"):
        continue
    m = re.fullmatch("(.*/.*)-9999+", fbasename)       # 9999 or more
    if m is None:
        continue
    pkgList.append(m.group(1))

# emerge package
PkgMerger().emergePkg("-1 --keep-going %s" % (" ".join(pkgList)))
