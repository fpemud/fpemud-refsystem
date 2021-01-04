#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import sys
sys.path.append('/usr/lib64/fpemud-refsystem')
from helper_boot_kernel import FkmKCacheUpdater
from helper_pkg_merger import PkgMerger


item = sys.argv[1]

if item == "kernel":
    postfix = sys.argv[2]
    kcacheUpdater = FkmKCacheUpdater()
    kcacheUpdater.updateKernelCache(postfix)
    sys.exit(0)

if item == "firmware":
    version = sys.argv[2]
    kcacheUpdater = FkmKCacheUpdater()
    kcacheUpdater.updateFirmwareCache(version)
    sys.exit(0)

if item == "extra-firmware":
    name = sys.argv[2]
    kcacheUpdater = FkmKCacheUpdater()
    kcacheUpdater.updateExtraFirmwareCache(name)
    sys.exit(0)

if item == "wireless-regdb":
    ver = sys.argv[2]
    kcacheUpdater = FkmKCacheUpdater()
    kcacheUpdater.updateWirelessRegDbCache(ver)
    sys.exit(0)

if item == "tbs-driver":
    kcacheUpdater = FkmKCacheUpdater()
    kcacheUpdater.updateTbsDriverCache()
    sys.exit(0)

if item == "vbox-driver":
    kcacheUpdater = FkmKCacheUpdater()
    kcacheUpdater.updateVboxDriverCache()
    sys.exit(0)

if item == "distfiles":
    PkgMerger().fetchPkg("-uDN --with-bdeps=y @world")
    print("")
    sys.exit(0)

assert False
