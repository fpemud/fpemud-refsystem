#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class FmConst:

    libDir = "/usr/lib64/fpemud-refsystem"
    libInitrdDir = os.path.join(libDir, "initramfs")
    libexecDir = "/usr/libexec/fpemud-refsystem"
    dataDir = "/usr/share/fpemud-refsystem"
    dataKernelCfgRulesDir = os.path.join(dataDir, "kconfig-rules")

    defaultGentooMirror = "http://distfiles.gentoo.org"
    defaultRsyncMirror = "rsync://rsync.gentoo.org/gentoo-portage"
    defaultKernelMirror = "https://www.kernel.org/pub/linux/kernel"

    portageCfgDir = "/etc/portage"
    portageDataDir = "/var/lib/portage"
    portageCacheDir = "/var/cache/portage"
    portageDbDir = "/var/db/pkg"

    portageMirrorsFile = os.path.join(portageCfgDir, "mirrors")
    portageCfgMakeProfile = os.path.join(portageCfgDir, "make.profile")
    portageCfgMakeConf = os.path.join(portageCfgDir, "make.conf")
    portageCfgReposDir = os.path.join(portageCfgDir, "repos.conf")
    portageCfgMaskDir = os.path.join(portageCfgDir, "package.mask")
    portageCfgUnmaskDir = os.path.join(portageCfgDir, "package.unmask")
    portageCfgUseDir = os.path.join(portageCfgDir, "package.use")
    portageCfgEnvDir = os.path.join(portageCfgDir, "package.env")
    portageCfgAcceptKeywordsDir = os.path.join(portageCfgDir, "package.accept_keywords")
    portageCfgLicDir = os.path.join(portageCfgDir, "package.license")
    portageCfgEnvDataDir = os.path.join(portageCfgDir, "env")

    configArchiveDir = os.path.join(portageDataDir, "config-archive")

    ebuild2Dir = os.path.join(portageCacheDir, "ebuild2")
    repofilesDir = os.path.join(portageCacheDir, "repofiles")
    laymanfilesDir = os.path.join(portageCacheDir, "laymanfiles")
    distDir = os.path.join(portageCacheDir, "distfiles")
    kcacheDir = os.path.join(portageCacheDir, "kcache")
    archLinuxCacheDir = os.path.join(portageCacheDir, "archlinux")

    kernelMaskDir = os.path.join(portageCfgDir, "kernel.mask")
    kernelUseDir = os.path.join(portageCfgDir, "kernel.use")

    cfgDispatchConf = "/etc/dispatch-conf.conf"
    machineInfoFile = "/etc/machine-info"

    userDefaultPassword = "123456"

    buildServerDefaultPort = 2108
    buildServerConfFile = os.path.join(portageCfgDir, "build-server.conf")
    myCertFile = os.path.join(portageCfgDir, "cert.pem")
    myPrivKeyFile = os.path.join(portageCfgDir, "privkey.pem")

    # deprecated
    bootDir = "/boot"
    kernelInitCmd = "/usr/lib/systemd/systemd"


class SysParam:

    def __init__(self):
        super().__init__()

        self.singletonFile = "/run/sysman"
        self.tmpDir = "/tmp/sysman"
        self.tmpDirOnHdd = "/var" + self.tmpDir

        self.runMode = None             # "normal" | "prepare" | "setup"

        # business objects
        self.infoPrinter = None
        self.hwInfoGetter = None
        self.storageManager = None
        self.pkgManager = None
        self.logManager = None
        self.userManager = None
        self.sysChecker = None
        self.sysUpdater = None
        self.sysCleaner = None


class UsrParam:

    def __init__(self):
        super().__init__()

        self.tmpDir = "/tmp/usrman-%d" % (os.getuid())
        self.tmpDirOnHdd = "/var" + self.tmpDir

        # business objects
        self.infoPrinter = None
        self.checker = None
