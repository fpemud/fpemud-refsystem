#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import sys
sys.path.append('/usr/lib64/fpemud-refsystem')
from fm_util import FmUtil
from fm_param import FmConst
from helper_boot_kernel import FkmKCacheUpdater
from helper_pkg_warehouse import PkgWarehouse
from helper_pkg_warehouse import EbuildRepositories
from helper_pkg_warehouse import EbuildOverlays
from helper_pkg_merger import PkgMerger


item = sys.argv[1]

if item == "sync-kcache":
    kcacheUpdater = FkmKCacheUpdater()
    kcacheUpdater.checkCache()
    kcacheUpdater.syncCache()
    sys.exit(0)

if item == "sync-repo":
    repoName = sys.argv[2]
    repoman = EbuildRepositories()
    repoman.syncRepository(repoName)
    sys.exit(0)

if item == "sync-ebuild2":
    FmUtil.gitPullOrClone(FmConst.ebuild2Dir, "https://github.com/fpemud/ebuild2")
    sys.exit(0)

if item == "sync-overlay":
    overlayName = sys.argv[2]
    pkgwh = PkgWarehouse()
    bFound = False
    if not bFound:
        for oname, ourl in pkgwh.getPreEnableOverlays().items():
            if oname == overlayName:
                vcsType, overlayUrl = pkgwh.layman.getOverlayVcsTypeAndUrl(oname)
                if ourl != overlayUrl:
                    bFound = True
                    break
    if not bFound:
        for oname, data in pkgwh.getPreEnablePackages().items():
            ourl, pkglist = data
            if oname == overlayName:
                vcsType, overlayUrl = pkgwh.layman.getOverlayVcsTypeAndUrl(oname)
                if ourl != overlayUrl:
                    bFound = True
                    break
    if bFound:
        print("WARNING: Overlay URL is not same with preconfigured data.")
    pkgwh.layman.syncOverlay(overlayName)
    sys.exit(0)

if item == "add-trusted-overlay":
    overlayName = sys.argv[2]
    overlayUrl = sys.argv[3]
    EbuildOverlays().addTrustedOverlay(overlayName, overlayUrl)
    sys.exit(0)

if item == "add-transient-overlay":
    overlayName = sys.argv[2]
    overlayUrl = sys.argv[3]
    EbuildOverlays().addTransientOverlay(overlayName, overlayUrl)
    sys.exit(0)

if item == "enable-overlay-package":
    overlayName = sys.argv[2]
    packageList = sys.argv[3:]
    layman = EbuildOverlays()
    for pkg in packageList:
        print("        - \"%s\"..." % (pkg))
        layman.enableOverlayPackage(overlayName, pkg, quiet=True)
    sys.exit(0)

if item == "refresh-package-related-stuff":
    pkgwh = PkgWarehouse()
    pkgwh.refreshPackageProvided()
    pkgwh.refreshTargetUseFlags()
    sys.exit(0)

if item == "touch-portage-tree":
    PkgMerger().touchPortageTree()
    sys.exit(0)

assert False
