#!/usr/bin/python3.6
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import pwd
import grp
import glob
import stat
import time
import ntplib
import struct
import shutil
import fnmatch
import portage
import filecmp
import strict_pgs
from fm_util import FmUtil
from fm_util import TmpMount
from fm_param import FmConst
from helper_pkg_warehouse import PkgWarehouse
from helper_pkg_warehouse import Ebuild2Dir
from helper_pkg_warehouse import RepositoryCheckError
from helper_pkg_warehouse import OverlayCheckError
from helper_pkg_warehouse import Ebuild2CheckError
from sys_storage_manager import FmStorageLayoutBiosSimple
from sys_storage_manager import FmStorageLayoutBiosLvm
from sys_storage_manager import FmStorageLayoutEfiSimple
from sys_storage_manager import FmStorageLayoutEfiLvm
from sys_storage_manager import FmStorageLayoutEfiBcacheLvm
from sys_storage_manager import FmStorageLayoutNonStandard
from sys_storage_manager import FmStorageLayoutEmpty


# TODO:
# 1. partition 4k align check
# 2. disk 2048 reserve check
# 3. ssd io scheduler check
# 7. systemd unit files reference not-exist service or target file
# 8. check mount option for boot device
# 9. should not have uid/gid without name


class FmSysChecker:

    def __init__(self, param):
        self.param = param
        self.infoPrinter = self.param.infoPrinter
        self.pkgwh = PkgWarehouse()
        self.bAutoFix = False

    def doPostCheck(self):
        # do Power On Self Test check
        self._checkMachineInfo()
        self._checkPortageDataDir()
        self._checkPortageCacheDir()
        self._checkPortageCfgMakeProfile()
        self._checkPortageMakeConf()
        self._checkPortageCfgDir()
        self._checkRepositories(bFullCheck=False)
        self._checkOverlays(bFullCheck=False)

    def doSysCheck(self, bAutoFix, deepCheck):
        self.bAutoFix = bAutoFix

        self.infoPrinter.printInfo(">> Check hardware...")
        self.infoPrinter.incIndent()
        self._checkHardware(deepCheck)
        self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Check storage layout...")
        self.infoPrinter.incIndent()
        self._checkItemStorageLayout()
        self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Check operating system...")
        self.infoPrinter.incIndent()
        try:
            self.infoPrinter.printInfo("- Check system files...")
            self.infoPrinter.incIndent()
            try:
                self._checkMachineInfo()
                self._checkPureSystemFiles()
                self._checkHostsFile()
                self._checkPamCfgFiles()
                self._checkLmSensorsCfgFiles()
                self._checkEtcUdevRuleFiles()
                self._checkServiceFiles()
                # self._checkFirmware()
                self._checkHomeDir()
            finally:
                self.infoPrinter.decIndent()

            self.infoPrinter.printInfo("- Check %s directory..." % (FmConst.portageDataDir))
            self.infoPrinter.incIndent()
            try:
                self._checkPortageDataDir()
            finally:
                self.infoPrinter.decIndent()

            self.infoPrinter.printInfo("- Check %s directory..." % (FmConst.portageCacheDir))
            self.infoPrinter.incIndent()
            try:
                self._checkPortageCacheDir()
            finally:
                self.infoPrinter.decIndent()

            self.infoPrinter.printInfo("- Check %s directory..." % (FmConst.portageCfgDir))
            self.infoPrinter.incIndent()
            try:
                self._checkPortageCfgMakeProfile()
                self._checkPortageCfgDir()
                self._checkPortageMakeConf()
                self._checkPortageCfgReposDir()
                self._checkPortageCfgMaskDir()
                self._checkPortageCfgUnmaskDir()
                self._checkPortageCfgUseDir()
                self._checkPortageCfgAcceptKeywordDir()
                self._checkPortageCfgLicDir()
                self._checkPortageCfgEnvDir()
                self._checkPortageCfgProvidedFile()
                self._checkKernelMaskDir()
                self._checkKernelUseDir()
                self._checkCfgDispatchConfFile()
            finally:
                self.infoPrinter.decIndent()

            self.infoPrinter.printInfo("- Check system configuration...")
            self.infoPrinter.incIndent()
            try:
                self._checkSystemLocale()
                # self._checkSystemServices()       # FIXME: seems not that simple
                self._checkSystemTime()
            finally:
                self.infoPrinter.decIndent()
        finally:
            self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Check package repositoryies & overlays...")
        self.infoPrinter.incIndent()
        try:
            self._checkPkgWarehouse()
            self._checkRepositories()
            self._checkOverlays()
            self._checkEbuild2Dir()
        finally:
            self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Check users and groups...")
        self.infoPrinter.incIndent()
        try:
            self._checkUsersAndGroups()
        finally:
            self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Do per-package check...")
        self.infoPrinter.incIndent()
        try:
            for pkgNameVer in sorted(FmUtil.getFileList(FmConst.portageDbDir, 2, "d")):
                if FmUtil.repoIsSysFile(pkgNameVer):
                    continue
                if pkgNameVer.split("/")[1].startswith("-MERGING"):
                    continue
                self.infoPrinter.startPrintByError()
                self.infoPrinter.printInfo("- Package %s:" % (pkgNameVer))
                self.infoPrinter.incIndent()
                try:
                    self._checkPackageContentFile(pkgNameVer)
                    self._checkPackageFileScope(pkgNameVer)
                    self._checkPakcageMd5(pkgNameVer)
                    self._checkPkgEbuild2(pkgNameVer)
                finally:
                    self.infoPrinter.decIndent()
                    self.infoPrinter.endPrintByError()
        finally:
            self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Find system cruft files...")
        self.infoPrinter.incIndent()
        try:
            self._checkItemSystemCruft()
        finally:
            self.infoPrinter.decIndent()

    def _checkHardware(self, deepCheck):
        tlist = FmUtil.getDevPathListForFixedHdd()
        if len(tlist) == 0:
            self.infoPrinter.printError("No hard disk?!")
            return

        # hardware check
        if not deepCheck:
            for hdd in tlist:
                self.infoPrinter.printInfo("- Doing basic hardware check for %s(%s)" % (hdd, FmUtil.getBlkDevModel(hdd)))
                self.infoPrinter.incIndent()
                rc, out = FmUtil.cmdCallWithRetCode("/usr/sbin/smartctl", "-H", hdd)
                if re.search("failure", out, re.I) is not None:
                    self.infoPrinter.printError("HDD health check failed! Run \"smartctl -H %s\" to do future inspection!" % (hdd))
                self.infoPrinter.decIndent()
        else:
            self.infoPrinter.printInfo("- Starting extensive hardware test for %s(%s)" % (hdd, FmUtil.getBlkDevModel(hdd)))
            self.infoPrinter.incIndent()
            tlist2 = list(tlist)
            for hdd in tlist:
                try:
                    rc, out = FmUtil.cmdCallWithRetCode("/usr/sbin/smartctl", "-t", "long", hdd)
                    if rc == 0:
                        m = re.search("Please wait ([0-9]+) minutes for test to complete\\.", out, re.M)
                        if m is None:
                            raise Exception("")
                        self.infoPrinter.printInfo("Test on %s(%s) started, %s minutes needed." % (hdd, FmUtil.getBlkDevModel(hdd), m.group(1)))
                    elif rc == 4:
                        self.infoPrinter.printInfo("Test on %s(%s) started. Why it is already in progress?" % (hdd, FmUtil.getBlkDevModel(hdd)))
                    else:
                        raise Exception("")
                except:
                    self.infoPrinter.printError("Failed to start test on %s(%s)!" % (hdd, FmUtil.getBlkDevModel(hdd)))
                    FmUtil.cmdCallIgnoreResult("/usr/sbin/smartctl", "-X", hdd)
                    tlist2.remove(hdd)
            self.infoPrinter.decIndent()

            try:
                self.infoPrinter.printInfo("- Waiting...")
                self.infoPrinter.incIndent()
                last_progress = 0
                while tlist2 != []:
                    time.sleep(60 * 5)
                    min_progress = None
                    for hdd in list(tlist2):
                        out = FmUtil.cmdCall("/usr/sbin/smartctl", "-l", "selftest", hdd)
                        if re.search("# 1\\s+Extended offline\\s+Completed without error\\s+.*", out, re.M) is not None:
                            self.infoPrinter.printInfo("Test on %s finished." % (hdd))
                            tlist2.remove(hdd)
                            continue
                        m = re.search("# 1\\s+Extended offline\\s+Self-test routine in progress\\s+([0-9]+)%.*", out, re.M)
                        if m is None:
                            self.infoPrinter.printInfo("Test on %s failed. Run \"smartctl -l selftest %s\" to do future inspection." % (hdd, hdd))
                            tlist2.remove(hdd)
                            continue
                        if min_progress is None:
                            min_progress = 100
                        min_progress = min(min_progress, 100 - int(m.group(1)))
                    if min_progress is not None and min_progress > last_progress:
                        self.infoPrinter.printInfo("Test progress: %d%%" % (min_progress))
                        last_progress = min_progress
                self.infoPrinter.decIndent()
            finally:
                for hdd in tlist2:
                    FmUtil.cmdCallIgnoreResult("/usr/sbin/smartctl", "-X", hdd)

    def _checkItemStorageLayout(self):
        tlist = FmUtil.getDevPathListForFixedHdd()
        if len(tlist) == 0:
            self.infoPrinter.printError("No hard disk?!")
            return

        layout = self.param.storageManager.getStorageLayout()

        # partition table check
        obj = _DiskPartitionTableChecker()
        for hdd in tlist:
            self.infoPrinter.printInfo("- Checking partition table for %s(%s)" % (hdd, FmUtil.getBlkDevModel(hdd)))
            self.infoPrinter.incIndent()
            try:
                obj.checkDisk(hdd)
            except _DiskPartitionTableCheckerFailure as e:
                self.infoPrinter.printError(e.message)
            if len(glob.glob(hdd + "*")) == 1:
                self.infoPrinter.printError("Harddisk %s has no partition." % (hdd))
            self.infoPrinter.decIndent()

        # storage layout check
        self.infoPrinter.printInfo("- Checking storage layout")
        self.infoPrinter.incIndent()
        if True:
            if isinstance(layout, FmStorageLayoutBiosSimple):
                pass
            elif isinstance(layout, FmStorageLayoutBiosLvm):
                pass
            elif isinstance(layout, FmStorageLayoutEfiSimple):
                pass
            elif isinstance(layout, FmStorageLayoutEfiLvm):
                pass
            elif isinstance(layout, FmStorageLayoutEfiBcacheLvm):
                if layout.ssd is None:
                    self.infoPrinter.printError("Storage layout \"%s\" should have a cache device." % (layout.name))
                else:
                    if layout.ssdSwapParti is None:
                        self.infoPrinter.printError("Storage layout \"%s\" should have a cache device with a swap partition." % (layout.name))
                for fn in glob.glob("/sys/block/bcache*"):
                    with open(os.path.join(fn, "bcache", "cache_mode"), "r") as f:
                        m = re.search("\\[(.*)\\]", f.read())
                        if m is None or m.group(1) != "writeback":
                            self.infoPrinter.printError("BCACHE device %s should be configured as writeback mode." % (os.path.basename(fn)))
            elif isinstance(layout, FmStorageLayoutNonStandard):
                self.infoPrinter.printError("Non-standard storage layout (which is bad) detected.")
                self.infoPrinter.printError("Closest storage layout is \"%s\", but %s" % (layout.closestLayoutName, layout.message))
            elif isinstance(layout, FmStorageLayoutEmpty):
                self.infoPrinter.printError("Empty storage layout (which is unusable) detected.")
            else:
                if not layout.isReady():
                    self.infoPrinter.printError("Storage layout \"%s\" detected, but is in not-ready state." % (layout.name))
                else:
                    if isinstance(layout, FmStorageLayoutEfiBcacheLvm) and layout.ssd is None:
                        self.infoPrinter.printError("Storage layout is \"%s\", but without a SSD device." % (FmStorageLayoutEfiBcacheLvm.name))
        self.infoPrinter.decIndent()

        # check mount point
        self.infoPrinter.printInfo("- Checking mount point")
        self.infoPrinter.incIndent()
        if True:
            # check root device
            if layout.getRootDev() is not None:
                if FmUtil.getMountDeviceForPath("/") != layout.getRootDev():
                    self.infoPrinter.printError("Directory / should be mounted to root device %s." % (layout.getRootDev()))

            # check boot device
            if layout.getBootDev() is not None:
                if FmUtil.getMountDeviceForPath("/boot") != layout.getBootDev():
                    self.infoPrinter.printError("Directory /boot should be mounted to boot device %s." % (layout.getBootDev()))
            else:
                if FmUtil.isMountPoint("/boot"):
                    self.infoPrinter.printError("Directory /boot should not be mounted!")
        self.infoPrinter.decIndent()

        # check swap
        self.infoPrinter.printInfo("- Checking swap")
        self.infoPrinter.incIndent()
        if True:
            dirname = "/etc/systemd/system"
            if isinstance(layout, (FmStorageLayoutBiosSimple, FmStorageLayoutEfiSimple)):
                swapFileOrDev = layout.swapFile
            elif isinstance(layout, (FmStorageLayoutBiosLvm, FmStorageLayoutEfiLvm)):
                swapFileOrDev = layout.lvmSwapLv
            elif isinstance(layout, FmStorageLayoutEfiBcacheLvm):
                swapFileOrDev = layout.ssdSwapParti
            else:
                swapFileOrDev = None

            # swap service should only exist in /etc
            for td in ["/usr/lib/systemd/system", "/lib/systemd/system"]:
                if os.path.exists(td):
                    for sname in FmUtil.systemdFindAllSwapServicesInDirectory(td):
                        self.infoPrinter.printError("Swap service \"%s\" should not exist." % (os.path.join(td, sname)))

            # only standard swap service should exist
            for sname in FmUtil.systemdFindAllSwapServicesInDirectory(dirname):
                if swapFileOrDev is not None and sname == FmUtil.path2SwapServiceName(swapFileOrDev):
                    continue
                self.infoPrinter.printError("Swap service \"%s\" should not exist." % (os.path.join(dirname, sname)))

            # swap should be enabled
            while True:
                if swapFileOrDev is None:
                    if isinstance(layout, (FmStorageLayoutBiosSimple, FmStorageLayoutEfiSimple, FmStorageLayoutBiosLvm, FmStorageLayoutEfiLvm, FmStorageLayoutEfiBcacheLvm)):
                        self.infoPrinter.printError("Swap is not enabled.")
                        break
                serviceName = FmUtil.systemdFindSwapServiceInDirectory(dirname, swapFileOrDev)
                if serviceName is None:
                    self.infoPrinter.printError("Swap is not enabled.")
                    break
                if self.param.runMode == "normal":
                    if not FmUtil.systemdIsServiceEnabled(serviceName):
                        self.infoPrinter.printError("Swap is not enabled.")
                        break
                break
        self.infoPrinter.decIndent()

        # file system check
        # self.infoPrinter.printInfo("- Checking file systems")
        # self.infoPrinter.incIndent()
        # if True:
        #     # what we can check is very limited:
        #     # 1. no way to fsck ext4 root partition when it's on-line
        #     # 2. fscking vfat partition when it's on-line always finds dirty-bit
        #     if self.bAutoFix:
        #         fatFsckCmd = "/usr/sbin/fsck.vfat -a"
        #     else:
        #         fatFsckCmd = "/usr/sbin/fsck.vfat -n"

        #     if isinstance(layout, FmStorageLayoutBiosSimple):
        #         pass
        #     elif isinstance(layout, FmStorageLayoutBiosLvm):
        #         pass
        #     elif isinstance(layout, FmStorageLayoutEfiSimple):
        #         FmUtil.shellExec("%s %s" % (fatFsckCmd, layout.hddEspParti))
        #     elif isinstance(layout, FmStorageLayoutEfiLvm):
        #         for hdd in layout.lvmPvHddList:
        #             FmUtil.shellExec("%s %s" % (fatFsckCmd, FmUtil.devPathDiskToPartition(hdd, 1)))
        #     elif isinstance(layout, FmStorageLayoutEfiBcacheLvm):
        #         if layout.ssd is not None:
        #             FmUtil.shellExec("%s %s" % (fatFsckCmd, layout.ssdEspParti))
        #         for hdd in layout.lvmPvHddDict:
        #             FmUtil.shellExec("%s %s" % (fatFsckCmd, FmUtil.devPathDiskToPartition(hdd, 1)))
        #     else:
        #         assert False
        # self.infoPrinter.decIndent()

    def _checkMachineInfo(self):
        """Check /etc/machine-info"""

        if not os.path.exists(FmConst.machineInfoFile):
            raise FmCheckException("\"%s\" does not exist" % (FmConst.machineInfoFile))
        ret = FmUtil.getMachineInfo(FmConst.machineInfoFile)
        if "CHASSIS" not in ret:
            raise FmCheckException("no CHASSIS in \"%s\"" % (FmConst.machineInfoFile))
        if ret["CHASSIS"] not in ["desktop", "laptop", "server", "tablet", "handset"]:
            raise FmCheckException("invalid CHASSIS in \"%s\"" % (FmConst.machineInfoFile))

    def _checkPureSystemFiles(self):
        layout = self.param.storageManager.getStorageLayout()
        with TmpMount(layout.getRootDev()) as mp:
            # check /
            if os.stat("/").st_mode != 0o40755:
                self.infoPrinter.printError("Incorrect mode for \"/\" directory.")

            # check /boot
            if layout.isReady() and layout.getType() == "efi":
                ret = os.listdir(os.path.join(mp.mountpoint, "boot"))
                if not (ret == [] or ret == [".keep"]):
                    self.infoPrinter.printError("The original \"/boot\" directory should be empty.")

            # check /etc/fstab
            # FIXME
            if os.path.exists(os.path.join(mp.mountpoint, "etc", "fstab")):
                with open(os.path.join(mp.mountpoint, "etc", "fstab"), "r") as f:
                    for line in f.read().split("\n"):
                        if not line.startswith("#") and line.strip() != "":
                            self.infoPrinter.printError("/etc/fstab should not exist.")

            # check /etc/sysctl.conf
            # FIXME
            if os.path.exists(os.path.join(mp.mountpoint, "etc", "sysctl.conf")):
                self.infoPrinter.printError("/etc/sysctl.conf should not exist.")

            # check /dev
            ret = set()
            for fn in os.listdir(os.path.join(mp.mountpoint, "dev")):
                if not fn.startswith(".keep"):
                    ret.add(fn)
            ret -= set(["console", "null", "tty"])
            if len(ret) > 0:
                if self.bAutoFix:
                    for fn in ret:
                        FmUtil.forceDelete(os.path.join(mp.mountpoint, "dev", fn))
                else:
                    self.infoPrinter.printError("The original \"/dev\" directory should contain only \"console\", \"null\" and \"tty\".")
            # if FmUtil.getMajorMinor(os.path.join(mp.mountpoint, "dev", "console")) != (5, 1):
            #     raise Exception("/dev/console should have major number 5 and minor number 1")
            # if FmUtil.getMajorMinor(os.path.join(mp.mountpoint, "dev", "null")) != (1, 3):
            #     raise Exception("/dev/null should have major number 1 and minor number 3")
            # if FmUtil.getMajorMinor(os.path.join(mp.mountpoint, "dev", "tty")) != (1, 5):
            #     raise Exception("/dev/tty should have major number 1 and minor number 5")

            # check /usr/local
            # FIXME
            if os.path.exists(os.path.join(mp.mountpoint, "usr", "local")):
                self.infoPrinter.printError("/usr/local should not existv")

            # check /srv
            # FIXME
            if os.path.exists(os.path.join(mp.mountpoint, "srv")):
                self.infoPrinter.printError("/srv should not exist.")

            # check /tmp
            ret = os.listdir(os.path.join(mp.mountpoint, "tmp"))
            if not (ret == [] or ret == [".keep"]):
                self.infoPrinter.printError("The original \"/tmp\" directory should be empty.")

            # check all files for:
            # 1. broken link
            # 2. suid/sgid/sticky bit
            if False:
                excludeList = ["/tmp", "/var/tmp"]
                for root, dirs, files in os.walk(mp.mountpoint):
                    if any(root.startswith(os.path.join(mp.mountpoint, x[1:]) + "/") for x in excludeList):
                        continue
                    for dn in dirs:
                        fulldn = os.path.join(root, dn)
                        showdn = os.path.join(root.replace(mp.mountpoint, "", 1), dn)
                        if not showdn.startswith("/"):
                            showdn = "/" + showdn
                        if not os.path.exists(fulldn):
                            # self.infoPrinter.printError("Directory \"%s\" is a broken symlink." % (showdn))
                            pass                # FIXME
                        else:
                            m = os.stat(fulldn).st_mode
                            if not (m & stat.S_IRUSR):
                                self.infoPrinter.printError("Directory \"%s\" is not readable by owner." % (showdn))
                            if not (m & stat.S_IWUSR):
                                self.infoPrinter.printError("Directory \"%s\" is not writeable by owner." % (showdn))
                            if not (m & stat.S_IRGRP) and (m & stat.S_IWGRP):
                                self.infoPrinter.printError("Directory \"%s\" is not readable but writable by group." % (showdn))
                            if not (m & stat.S_IROTH) and (m & stat.S_IWOTH):
                                self.infoPrinter.printError("Directory \"%s\" is not readable but writable by other." % (showdn))
                            if not (m & stat.S_IRGRP) and ((m & stat.S_IROTH) or (m & stat.S_IWOTH)):
                                self.infoPrinter.printError("Directory \"%s\" is not readable by group but readable/writable by other." % (showdn))
                            if not (m & stat.S_IWGRP) and (m & stat.S_IWOTH):
                                self.infoPrinter.printError("Directory \"%s\" is not writable by group but writable by other." % (showdn))
                            if m & stat.S_ISUID:
                                self.infoPrinter.printError("Directory \"%s\" should not have SUID bit set." % (showdn))
                            if m & stat.S_ISGID:
                                # if showdn.startswith("/var/lib/portage"):
                                #     pass        # FIXME, portage set SGID for these directories?
                                # elif showdn.startswith("/var/log/portage"):
                                #     pass        # FIXME, portage set SGID for these directories?
                                # elif showdn.startswith("/var/log/journal"):
                                #     pass        # FIXME, systemd set SGID for these directories?
                                # else:
                                #     self.infoPrinter.printError("Directory \"%s\" should not have SGID bit set." % (showdn))
                                pass            # FIXME
                            if m & stat.S_ISVTX:
                                # self.infoPrinter.printError("Directory \"%s\" should not have sticky bit set." % (showdn))
                                pass            # FIXME
                    for fn in files:
                        fullfn = os.path.join(root, fn)
                        showfn = os.path.join(root.replace(mp.mountpoint, "", 1), fn)
                        if not showfn.startswith("/"):
                            showfn = "/" + showfn
                        if not os.path.exists(fullfn):
                            # self.infoPrinter.printError("File \"%s\" is a broken symlink." % (showfn))
                            pass
                        else:
                            m = os.stat(fullfn).st_mode
                            if not (m & stat.S_IRUSR):
                                self.infoPrinter.printError("File \"%s\" is not readable by owner." % (showfn))
                            # if not (m & stat.S_IWUSR):
                            #     FIXME: strange that many file has this problem
                            #     self.infoPrinter.printError("File \"%s\" is not writeable by owner." % (showfn))
                            if not (m & stat.S_IRGRP) and (m & stat.S_IWGRP):
                                self.infoPrinter.printError("File \"%s\" is not readable but writable by group." % (showfn))
                            if not (m & stat.S_IROTH) and (m & stat.S_IWOTH):
                                self.infoPrinter.printError("File \"%s\" is not readable but writable by other." % (showfn))
                            if not (m & stat.S_IRGRP) and ((m & stat.S_IROTH) or (m & stat.S_IWOTH)):
                                self.infoPrinter.printError("File \"%s\" is not readable by group but readable/writable by other." % (showfn))
                            if not (m & stat.S_IWGRP) and (m & stat.S_IWOTH):
                                self.infoPrinter.printError("File \"%s\" is not writable by group but writable by other." % (showfn))
                            if (m & stat.S_ISUID):
                                bad = False
                                if not (m & stat.S_IXUSR):
                                    bad = True
                                if not (m & stat.S_IXGRP) and ((m & stat.S_IRGRP) or (m & stat.S_IWGRP)):
                                    bad = True
                                if not (m & stat.S_IXOTH) and ((m & stat.S_IROTH) or (m & stat.S_IWOTH)):
                                    bad = True
                                if bad:
                                    self.infoPrinter.printError("File \"%s\" is not a good executable, but has SUID bit set." % (showfn))
                            if m & stat.S_ISGID:
                                # self.infoPrinter.printError("File \"%s\" should not have SGID bit set." % (showfn))
                                pass            # FIXME
                            if m & stat.S_ISVTX:
                                # self.infoPrinter.printError("File \"%s\" should not have sticky bit set." % (showfn))
                                pass            # FIXME

    def _checkHostsFile(self):
        content = ""
        content += "127.0.0.1 localhost\n"
        content += "::1 localhost\n"                    # selenium fails when "::1 localhost" exist in /etc/hosts ?
        if FmUtil.readFile("/etc/hosts") != content:
            if self.bAutoFix:
                with open("/etc/hosts", "w") as f:
                    f.write(content)
            else:
                self.infoPrinter.printError("File /etc/hosts has invalid content.")

    def _checkPamCfgFiles(self):
        # FIXME: change to INSTALL_MASK?
        modBlackList = [
            "pam_group.so",         # so that uid/gid relationship is always clear
        ]

        # PAM-free system?
        if not os.path.exists("/etc/pam.d"):
            return

        for fn in os.listdir("/etc/pam.d"):
            fullfn = os.path.join("/etc/pam.d", fn)
            cfgDict = FmUtil.pamParseCfgFile(fullfn)

            # check module
            for modIntf, items in cfgDict.items():
                for ctrlFlag, modArgs in items:
                    if ctrlFlag == "include":
                        continue
                    mod = modArgs.split(" ")[0]
                    if not os.path.exists("/lib64/security/" + mod):
                        self.infoPrinter.printError("Non-exist module \"%s\" in PAM config file \"%s\"." % (mod, fullfn))
                    if mod in modBlackList:
                        self.infoPrinter.printError("Prohibited module \"%s\" in PAM config file \"%s\"." % (mod, fullfn))
                    if modIntf.replace("-", "") not in FmUtil.pamGetModuleTypesProvided(mod):
                        self.infoPrinter.printError("Module \"%s\" is not suitable for %s in PAM config file \"%s\"." % (mod, modIntf, fullfn))

            # check order
            # FIXME
            for items in cfgDict.values():
                ctrlFlagCur = None
                for ctrlFlag, modArgs in items:
                    if ctrlFlag == "include":
                        if not (ctrlFlagCur is None or ctrlFlagCur == "include"):
                            self.infoPrinter.printError("Inappropriate \"include\" control flag order in PAM config file \"%s\"." % (fullfn))
                    if ctrlFlag != "optional" and ctrlFlagCur == "optional":
                        self.infoPrinter.printError("Inappropriate \"optional\" control flag order in PAM config file \"%s\"." % (fullfn))
                    ctrlFlagCur = ctrlFlag

    def _checkLmSensorsCfgFiles(self):
        fn = "/etc/modules-load.d/lm_sensors.conf"
        if not os.path.exists(fn):
            self.infoPrinter.printError("You should use \"sensors-detect\" command from package \"sys-apps/lm-sensors\" to generate \"%s\"." % (fn))

    def _checkEtcUdevRuleFiles(self):
        # check /etc/udev/hwdb.d
        hwdbDir = "/etc/udev/hwdb.d"
        if not os.path.exists(hwdbDir):
            self.infoPrinter.printError("\"%s\" does not exist." % (hwdbDir))
        else:
            for fn in os.listdir(hwdbDir):
                if fn.startswith("."):
                    continue
                self.infoPrinter.printError("\"%s\" should not exist." % (os.path.join(hwdbDir, fn)))

        # check /etc/udev/rules.d
        rulesDir = "/etc/udev/rules.d"
        if not os.path.exists(rulesDir):
            self.infoPrinter.printError("\"%s\" does not exist." % (rulesDir))
        else:
            for fn in os.listdir(rulesDir):
                fullfn = os.path.join(rulesDir, fn)
                if fn.startswith("."):
                    continue
                elif fn.startswith("72-"):
                    lineList = [x.strip() for x in FmUtil.readFile(fullfn).split("\n")]

                    # find and check first line
                    firstLineNo = -1
                    firstLineTagName = None
                    for i in range(0, len(lineList)):
                        line = lineList[i]
                        if line != "" and not line.startswith("#"):
                            firstLineNo = i
                            m = re.fullmatch('ACTION=="remove", GOTO="(.*)_end"', line)
                            if m is not None:
                                firstLineTagName = m.group(1)
                            break
                    if firstLineNo == -1:
                        self.infoPrinter.printError("No valid line in \"%s\"." % (fullfn))
                        continue
                    if firstLineTagName is None:
                        self.infoPrinter.printError("Line %d is invalid in \"%s\"." % (firstLineNo + 1, fullfn))
                        continue

                    # find and check last line
                    lastLineNo = -1
                    for i in reversed(range(firstLineNo + 1, len(lineList))):
                        line = lineList[i]
                        if line != "" and not line.startswith("#"):
                            if re.fullmatch('LABEL="%s_end"' % (firstLineTagName), line) is not None:
                                lastLineNo = i
                            break
                    if lastLineNo == -1:
                        self.infoPrinter.printError("No valid end line in \"%s\"." % (fullfn))
                        continue

                    # check middle lines
                    pat = '.*, TAG-="uaccess", TAG-="seat", TAG-="master-of-seat", ENV{ID_SEAT}="", ENV{ID_AUTOSEAT}="", ENV{ID_FOR_SEAT}=""'
                    for i in range(firstLineNo + 1, lastLineNo):
                        line = lineList[i]
                        if line != "" and not line.startswith("#"):
                            if re.fullmatch(pat, line) is None:
                                self.infoPrinter.printError("Line %d is invalid in \"%s\"." % (i + 1, fullfn))
                                break
                else:
                    self.infoPrinter.printError("\"%s\" should not exist." % (fullfn))

    def _checkServiceFiles(self):
        mustEnableServiceList = [
            "bluetooth.service",            # userspace daemon for bluetooth hardware
            "cups.service",                 # multiplex daemon for printer
            "iio-sensor-proxy.service",     # multiplex daemon for iio-sensor
            "iwd.service",                  # userspace daemon for WiFi/802.1X
        ]

        for s in mustEnableServiceList:
            libFn = os.path.join("/lib/systemd/system", s)
            if not os.path.exists(libFn):
                continue
            if not FmUtil.systemdIsServiceEnabled(s):
                self.infoPrinter.printError("\"%s\" is not enabled." % (s))

    def _checkFirmware(self):
        processedList = []
        for ver in sorted(os.listdir("/lib/modules"), reverse=True):
            verDir = os.path.join("/lib/modules", ver)
            for fullfn in glob.glob(os.path.join(verDir, "**", "*.ko"), recursive=True):
                # python-kmod bug: can only recognize the last firmware in modinfo
                # so use the command output of modinfo directly
                for line in FmUtil.cmdCall("/bin/modinfo", fullfn).split("\n"):
                    m = re.fullmatch("firmware: +(\\S.*)", line)
                    if m is None:
                        continue
                    firmwareName = m.group(1)
                    if firmwareName in processedList:
                        continue
                    if not os.path.exists(os.path.join("/lib/firmware", firmwareName)):
                        self.infoPrinter.printError("Firmware \"%s\" does not exist. (required by \"%s\")" % (firmwareName, fullfn))
                    processedList.append(firmwareName)

    def _checkHomeDir(self):
        """Check /home"""

        if not os.path.exists("/home"):
            self.infoPrinter.printError("\"/home\" does not exist.")
        else:
            for fn in os.listdir("/home"):
                if fn == ".keep":
                    continue
                fullfn = os.path.join("/home", fn)
                s = os.stat(fullfn)
                if s.st_mode != 0o40700:
                    if self.bAutoFix:
                        os.chmod(fullfn, 0o40700)
                    else:
                        self.infoPrinter.printError("Invalid permission for directory \"%s\"." % (fullfn))
                if pwd.getpwuid(s.st_uid).pw_name != fn:
                    self.infoPrinter.printError("Invalid owner for directory \"%s\"." % (fullfn))
                if grp.getgrgid(s.st_gid).gr_name != fn:
                    self.infoPrinter.printError("Invalid owner group for directory \"%s\"." % (fullfn))

    def _checkPortageDataDir(self):
        """Check /var/lib/portage"""

        # check /var/lib/portage
        if not os.path.isdir(FmConst.portageDataDir):
            if self.bAutoFix:
                os.mkdir(FmConst.portageDataDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (FmConst.portageDataDir))

    def _checkPortageCacheDir(self):
        """Check /var/cache/portage"""

        # check /var/cache/portage
        if not os.path.isdir(FmConst.portageCacheDir):
            if self.bAutoFix:
                FmUtil.ensureDir(FmConst.portageCacheDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (FmConst.portageCacheDir))

        # check /var/cache/portage/ebuild2
        if not os.path.isdir(FmConst.ebuild2Dir):
            if self.bAutoFix:
                FmUtil.ensureDir(os.path.dirname(FmConst.ebuild2Dir))
                FmUtil.gitClone("https://github.com/fpemud/ebuild2", FmConst.ebuild2Dir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (FmConst.ebuild2Dir))

        # check /var/cache/portage/repofiles
        if not os.path.isdir(FmConst.repofilesDir):
            if self.bAutoFix:
                FmUtil.ensureDir(FmConst.repofilesDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (FmConst.repofilesDir))

        # check /var/cache/portage/laymanfiles
        if not os.path.isdir(FmConst.laymanfilesDir):
            if self.bAutoFix:
                FmUtil.ensureDir(FmConst.laymanfilesDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (FmConst.laymanfilesDir))

        # check /var/cache/portage/kcache
        if not os.path.isdir(FmConst.kcacheDir):
            if self.bAutoFix:
                FmUtil.ensureDir(FmConst.kcacheDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (FmConst.kcacheDir))

        # check /var/cache/portage/distfiles
        if not os.path.isdir(FmConst.distDir):
            if self.bAutoFix:
                FmUtil.ensureDir(FmConst.distDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (FmConst.distDir))

    def _checkEbuild2Dir(self):
        """Check /var/cache/portage/ebuild2"""

        # all packages in ebuild2 directory should exists in a repository or overlay
        if True:
            oDirInfo = set(FmUtil.repoGetEbuildDirList(FmConst.ebuild2Dir))

            for repoName in self.pkgwh.repoman.getRepositoryList():
                if not self.pkgwh.repoman.isRepoExist(repoName):
                    continue
                repoDir = self.pkgwh.repoman.getRepoDir(repoName)
                dirInfo = set(FmUtil.repoGetEbuildDirList(repoDir))
                oDirInfo = oDirInfo - dirInfo

            for oname in self.pkgwh.layman.getOverlayList():
                dirInfo = set(FmUtil.repoGetEbuildDirList(self.pkgwh.layman.getOverlayDir(oname)))
                oDirInfo = oDirInfo - dirInfo

            for vi in oDirInfo:
                self.infoPrinter.printError("\"%s\" has invalid package \"%s\"" % (FmConst.ebuild2Dir, vi))

    def _checkPortageCfgMakeProfile(self):
        """Check make.profile"""

        if not os.path.exists(FmConst.portageCfgMakeProfile):
            raise FmCheckException("%s must exist" % (FmConst.portageCfgMakeProfile))

        tlist = FmUtil.realPathSplit(os.path.realpath(FmConst.portageCfgMakeProfile))
        if not re.fullmatch("[0-9\\.]+", tlist[-1]):
            raise FmCheckException("%s must points to a vanilla profile (eg. default/linux/amd64/17.0)" % (FmConst.portageCfgMakeProfile))

    def _checkPortageMakeConf(self):
        """Check make.conf"""

        # check CHOST variable
        if True:
            chost = FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "CHOST")
            if chost != "":
                raise FmCheckException("variable CHOST should not exist in %s" % (FmConst.portageCfgMakeConf))

        # check/fix ACCEPT_LICENSE variable
        if FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "ACCEPT_LICENSE") != "*":
            if self.bAutoFix:
                FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "ACCEPT_LICENSE", "*")
            else:
                raise FmCheckException("invalid value of variable ACCEPT_LICENSE in %s" % (FmConst.portageCfgMakeConf))

        # check/fix DISTDIR variable
        if FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "DISTDIR") != FmConst.distDir:
            if self.bAutoFix:
                FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "DISTDIR", FmConst.distDir)
            else:
                raise FmCheckException("invalid value of variable DISTDIR in %s" % (FmConst.portageCfgMakeConf))

        # check ACCEPT_KEYWORDS variable
        if True:
            keywordList = ["~%s" % (x) for x in self.pkgwh.getKeywordList()]
            tlist = FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "ACCEPT_KEYWORDS").split(" ")
            if set(tlist) != set(keywordList):
                if self.bAutoFix:
                    FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "ACCEPT_KEYWORDS", " ".join(keywordList))
                else:
                    raise Exception("invalid value of variable ACCEPT_KEYWORDS in %s" % (FmConst.portageCfgMakeConf))

        # check/fix EMERGE_DEFAULT_OPTS variable
        value = FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "EMERGE_DEFAULT_OPTS")
        if re.search("--quiet-build\\b", value) is None:
            if self.bAutoFix:
                value += " --quiet-build"
                FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "EMERGE_DEFAULT_OPTS", value.lstrip())
            else:
                raise FmCheckException("variable EMERGE_DEFAULT_OPTS in %s should contain --quiet-build argument" % (FmConst.portageCfgMakeConf))
        value = FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "EMERGE_DEFAULT_OPTS")
        if True:
            m = re.search("--backtrack(=([0-9]+))?\\b", value)
            if m is None:
                if self.bAutoFix:
                    value += " --backtrack=%d" % (30)
                    FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "EMERGE_DEFAULT_OPTS", value.lstrip())
                else:
                    raise FmCheckException("variable EMERGE_DEFAULT_OPTS in %s should contain --backtrack argument" % (FmConst.portageCfgMakeConf))
            elif m.group(2) is None or int(m.group(2)) < 30:
                if self.bAutoFix:
                    value = value.replace(m.group(0), "--backtrack=%d" % (30))
                    FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "EMERGE_DEFAULT_OPTS", value)
                else:
                    raise FmCheckException("variable EMERGE_DEFAULT_OPTS in %s has an inappropriate --backtrack argument" % (FmConst.portageCfgMakeConf))

        # check/fix GENTOO_DEFAULT_MIRROR variable
        if FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "GENTOO_DEFAULT_MIRROR") != FmConst.defaultGentooMirror:
            if self.bAutoFix:
                FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "GENTOO_DEFAULT_MIRROR", FmConst.defaultGentooMirror)
            else:
                raise FmCheckException("variable GENTOO_DEFAULT_MIRROR in %s does not exist or has invalid value" % (FmConst.portageCfgMakeConf))

        # check/fix RSYNC_DEFAULT_MIRROR variable
        if FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "RSYNC_DEFAULT_MIRROR") != FmConst.defaultRsyncMirror:
            if self.bAutoFix:
                FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "RSYNC_DEFAULT_MIRROR", FmConst.defaultRsyncMirror)
            else:
                raise FmCheckException("variable RSYNC_DEFAULT_MIRROR in %s does not exist or has invalid value" % (FmConst.portageCfgMakeConf))

        # check/fix KERNEL_DEFAULT_MIRROR variable
        if FmUtil.getMakeConfVar(FmConst.portageCfgMakeConf, "KERNEL_DEFAULT_MIRROR") != FmConst.defaultKernelMirror:
            if self.bAutoFix:
                FmUtil.setMakeConfVar(FmConst.portageCfgMakeConf, "KERNEL_DEFAULT_MIRROR", FmConst.defaultKernelMirror)
            else:
                raise FmCheckException("variable KERNEL_DEFAULT_MIRROR in %s does not exist or has invalid value" % (FmConst.portageCfgMakeConf))

    def _checkPortageCfgDir(self):
        """Check /etc/portage directory"""

        if not os.path.exists(FmConst.myCertFile) or not os.path.exists(FmConst.myPrivKeyFile):
            if self.bAutoFix:
                cert, key = FmUtil.genSelfSignedCertAndKey("-", 1024)
                FmUtil.dumpCertAndKey(cert, key, FmConst.myCertFile, FmConst.myPrivKeyFile)
            else:
                raise FmCheckException("%s or %s does not exist" % (FmConst.myCertFile, FmConst.myPrivKeyFile))

        flist = glob.glob(os.path.join(FmConst.portageCfgDir, "*-"))
        if flist != []:
            if self.bAutoFix:
                for fn in flist:
                    FmUtil.forceDelete(fn)
            else:
                raise FmCheckException("redundant files (example: %s) exist" % (flist[0]))

        self.__checkAndFixEtcDir(FmConst.portageCfgReposDir)           # /etc/portage/repos.conf
        self.__checkAndFixEtcDir(FmConst.portageCfgMaskDir)            # /etc/portage/package.mask
        self.__checkAndFixEtcDir(FmConst.portageCfgUnmaskDir)          # /etc/portage/package.unmask
        self.__checkAndFixEtcDir(FmConst.portageCfgUseDir)             # /etc/portage/package.use
        self.__checkAndFixEtcDir(FmConst.portageCfgAcceptKeywordsDir)  # /etc/portage/package.accept_keywords
        self.__checkAndFixEtcDir(FmConst.portageCfgLicDir)             # /etc/portage/package.license
        self.__checkAndFixEtcDir(FmConst.portageCfgEnvDir)             # /etc/portage/package.env
        self.__checkAndFixEtcDir(FmConst.portageCfgEnvDataDir)         # /etc/portage/env
        self.__checkAndFixEtcDir(FmConst.kernelMaskDir)                # /etc/portage/kernel.mask
        self.__checkAndFixEtcDir(FmConst.kernelUseDir)                 # /etc/portage/kernel.use

    def _checkPortageCfgReposDir(self):
        """Check /etc/portage/repos.conf directory"""

        # remove redundancy
        fileList = []
        for repoName in self.pkgwh.repoman.getRepositoryList():
            if self.pkgwh.repoman.isRepoExist(repoName):
                fileList.append(self.pkgwh.repoman.getRepoCfgReposFile(repoName))
        for overlayName in self.pkgwh.layman.getOverlayList():
            fileList.append(self.pkgwh.layman.getOverlayCfgReposFile(overlayName))
        for fn in os.listdir(FmConst.portageCfgReposDir):
            fullfn = os.path.join(FmConst.portageCfgReposDir, fn)
            if fullfn not in fileList:
                if self.bAutoFix:
                    os.remove(fullfn)
                else:
                    raise FmCheckException("redundant repository configuration file %s" % (fullfn))

    def _checkPortageCfgMaskDir(self):
        """Check /etc/portage/package.mask directory"""

        self.__initCheckAndFixEtcSymlink()

        # standard files
        commonDir = os.path.join(FmConst.dataDir, "etc-common")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgMaskDir, "?-base",               # /etc/portage/package.mask/01-base
                                     commonDir, "package.mask.base")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgMaskDir, "?-base_bugfix",        # /etc/portage/package.mask/02-base_bugfix
                                     commonDir, "package.mask.base_bugfix")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgMaskDir, "?-base_patch",         # /etc/portage/package.mask/03-base_patch
                                     commonDir, "package.mask.base_patch")

        # /etc/portage/package.mask/bugfix
        self.__checkAndFixEtcEmptyFile(FmConst.portageCfgMaskDir, "bugfix")

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.portageCfgMaskDir)

        # check package atom validity
        # porttree = portage.db[portage.root]["porttree"]
        # cpvAll = porttree.dbapi.cpv_all()
        # for fn in os.listdir(FmConst.portageCfgMaskDir):
        #     fullfn = os.path.join(FmConst.portageCfgMaskDir, fn)
        #     for pkgAtom in FmUtil.portageReadCfgMaskFile(fullfn):
        #         if len(porttree.dbapi.match(pkgAtom)) == 0:
        #             raise FmCheckException("invalid package atom \"%s\" in %s" % (pkgAtom, fullfn))

    def _checkPortageCfgUnmaskDir(self):
        """Check /etc/portage/package.unmask directory"""

        self.__initCheckAndFixEtcSymlink()

        # standard files
        commonDir = os.path.join(FmConst.dataDir, "etc-common")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgUnmaskDir, "?-base",
                                     commonDir, "package.unmask.base")

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.portageCfgUnmaskDir)

    def _checkPortageCfgUseDir(self):
        """Check /etc/portage/package.use directory"""

        self.__initCheckAndFixEtcSymlink()

        # standard files
        commonDir = os.path.join(FmConst.dataDir, "etc-common")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgUseDir, "?-base",
                                     commonDir, "package.use.base")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgUseDir, "?-base_bugfix",
                                     commonDir, "package.use.base_bugfix")

        # /etc/portage/package.use/30-hardware
        # /etc/portage/package.use/90-python-targets
        # /etc/portage/package.use/91-ruby-targets
        if self.bAutoFix:
            self.pkgwh.refreshHardwareUseFlags(self.param.hwInfoGetter.current())
            self.pkgwh.refreshTargetUseFlags()
        else:
            self.pkgwh.checkHardwareUseFlags(self.param.hwInfoGetter.current())
            self.pkgwh.checkTargetUseFlags()

        # /etc/portage/package.use/97-linguas
        # FIXME: support syncupd
        if self.bAutoFix:
            self.pkgwh.refreshLinguasUseFlags()
        else:
            self.pkgwh.checkLinguasUseFlags()

        # /etc/portage/package.use/98-autouse-manual
        self.__checkAndFixEtcEmptyFile(FmConst.portageCfgUseDir, "98-autouse-manual")

        # /etc/portage/package.use/99-autouse
        self.__checkAndFixEtcEmptyFile(FmConst.portageCfgUseDir, "99-autouse")
        fn = os.path.join(FmConst.portageCfgUseDir, "99-autouse")
        for pkgAtom, useList in FmUtil.portageParseCfgUseFile(FmUtil.readFile(fn)):
            pkgName = FmUtil.portageGetPkgNameFromPkgAtom(pkgAtom)
            if pkgName != pkgAtom:
                raise FmCheckException("invalid package name \"%s\" in %s" % (pkgAtom, fn))
            for uf in useList:
                if uf.startswith("-"):
                    raise FmCheckException("invalid USE flag \"%s\" for package \"%s\" in %s" % (uf, pkgAtom, fn))

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.portageCfgUseDir)

        # check use flag existence

        # porttree = portage.db[portage.root]["porttree"]
        # cpvAll = porttree.dbapi.cpv_all()
#         for fn in os.listdir(FmConst.portageCfgUseDir):
#             fullfn = os.path.join(FmConst.portageCfgUseDir, fn)
#             for pkgAtom, useList in FmUtil.portageReadCfgUseFile(fullfn):
#                 if useList[0].endswith(":"):
#                     # convert EXPAND_USE to normal use flags
#                     useList = [useList[0][:-1].lower() + "_" + x.lstrip("-") for x in useList[1:] if x != "-*"]
#                 else:
#                     useList = [x.lstrip("-") for x in useList]
#
#                 if pkgAtom == "*/*":
#                     for u in useList:
#                         bFound = False
#                         for cpv in cpvAll:
#                             iuseList = porttree.dbapi.aux_get(cpv, ["IUSE"])[0].split()
#                             iuseList = [x.lstrip("+") for x in iuseList]
#                             if u in iuseList:
#                                 bFound = True
#                                 break
#                         if bFound:
#                             break
#                     if not bFound:
#                         raise FmCheckException("invalid USE flag \"%s\" for \"%s\" in %s" % (u, pkgAtom, fullfn))
#                 else:
#                     cpvList = porttree.dbapi.match(pkgAtom)
#                     if len(cpvList) == 0:
#                         raise FmCheckException("invalid package atom \"%s\" in %s" % (pkgAtom, fullfn))
#                     if FmUtil.portageIsSimplePkgAtom(pkgAtom):
#                         cpvList = cpvList[-1:]                     # checks only the latest version for simple package atom (eg: media-video/smplayer)
#                     for cpv in cpvList:
#                         iuseList = porttree.dbapi.aux_get(cpv, ["IUSE"])[0].split()
#                         iuseList = [x.lstrip("+") for x in iuseList]
#                         for u in useList:
#                             if u not in iuseList:
#                                 print(iuseList)
#                                 raise FmCheckException("invalid USE flag \"%s\" for package atom \"%s\" in %s" % (u, pkgAtom, fullfn))

        # check use flag conflict
        pass

    def _checkPortageCfgAcceptKeywordDir(self):
        """Check /etc/portage/package.accept_keywords directory"""

        self.__initCheckAndFixEtcSymlink()

        commonDir = os.path.join(FmConst.dataDir, "etc-common")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgAcceptKeywordsDir, "?-base",
                                     commonDir, "package.accept_keywords")

        # /etc/portage/package.accept_keywords/99-autokeyword
        self.__checkAndFixEtcEmptyFile(FmConst.portageCfgAcceptKeywordsDir, "99-autokeyword")

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.portageCfgAcceptKeywordsDir)

    def _checkPortageCfgLicDir(self):
        """Check /etc/portage/package.license directory"""

        # standard files
        commonDir = os.path.join(FmConst.dataDir, "etc-common")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgLicDir, "01-base",
                                     commonDir, "package.license")

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.portageCfgLicDir)

    def _checkPortageCfgEnvDir(self):
        """Check /etc/portage/package.env directory"""

        # standard files
        commonDir = os.path.join(FmConst.dataDir, "etc-common")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgEnvDir, "01-base",               # /etc/portage/package.env/01-base
                                     commonDir, "package.env")
        self.__checkAndFixEtcSymlink(FmConst.portageCfgEnvDataDir, "01-base",           # /etc/portage/env/01-base (directory symlink)
                                     commonDir, "env.base")

        # /etc/portage/package.env/01-base and /etc/portage/env/01-base should be consistent
        with open(os.path.join(FmConst.portageCfgEnvDir, "01-base"), "r") as f:
            lineList = f.read().split("\n")
            lineList = [x.strip() for x in lineList]
            lineList = [x for x in lineList if x != "" and not x.startswith("#")]
            lineList = [x.split(" ")[0] for x in lineList]
            lineList.remove("*/*")
            dirList = FmUtil.getFileList(os.path.join(FmConst.portageCfgEnvDataDir, "01-base"), 2, "d")
            if set(lineList) != set(dirList):
                raise FmCheckException("invalid content in %s" % (os.path.join(FmConst.portageCfgEnvDir, "01-base")))

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.portageCfgEnvDir)

    def _checkPortageCfgProvidedFile(self):
        """Check /etc/portage/profile/package.provided"""

        if self.bAutoFix:
            self.pkgwh.refreshPackageProvided()
        else:
            self.pkgwh.checkPackageProvided()

    def _checkKernelMaskDir(self):
        """Check /etc/portage/kernel.mask directory"""

        # standard files
        commonDir = os.path.join(FmConst.dataDir, "etc-common")
        self.__checkAndFixEtcSymlink(FmConst.kernelMaskDir, "?-not_adapted",            # /etc/portage/kernel.mask/01-not_adapted
                                     commonDir, "kernel.mask.not_adapted")

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.kernelMaskDir)

    def _checkKernelUseDir(self):
        """Check /etc/portage/kernel.use directory"""

        # remove redundant files
        if self.bAutoFix:
            self.__clearInvalidEtcSymlink(FmConst.kernelUseDir)

    def _checkCfgDispatchConfFile(self):
        """Check dispatch-conf.conf"""

        buf = ""
        with open(FmConst.cfgDispatchConf, "r") as f:
            buf = f.read()

        # check the existence of variable "archive-dir"
        m = re.search("^archive-dir=(.*)$", buf, re.M)
        if m is None:
            raise FmCheckException("no config item archive-dir in %s" % (FmConst.cfgDispatchConf))

        # check/fix value for variable "archive-dir"
        if m.group(1) != os.path.join("${EPREFIX}", FmConst.configArchiveDir):
            if self.bAutoFix:
                newLine = "archive-dir=%s" % (os.path.join("${EPREFIX}", FmConst.configArchiveDir))
                buf = buf.replace(m.group(0), newLine)
                with open(FmConst.cfgDispatchConf, 'w') as f:
                    f.write(buf)
            else:
                raise FmCheckException("invalid value of config item archive-dir in %s" % (FmConst.cfgDispatchConf))

    def _checkPkgWarehouse(self):
        # check unread news
        if FmUtil.cmdCall("/usr/bin/eselect", "news", "count") != "0":
            if self.bAutoFix:
                FmUtil.cmdCallIgnoreResult("/usr/bin/eselect", "news", "read", "all")
            else:
                self.infoPrinter.printError("There are unread portage news items, please use \"eselect news read all\".")

    def _checkRepositories(self, bFullCheck=True):
        """Check repositories"""

        # all repositories should exist
        for repoName in self.pkgwh.repoman.getRepositoryList():
            if not self.pkgwh.repoman.isRepoExist(repoName):
                if self.bAutoFix:
                    self.pkgwh.repoman.createRepository(repoName)
                else:
                    self.infoPrinter.printError("Repository \"%s\" does not exist" % (repoName))

        # check all repositories
        for repoName in self.pkgwh.repoman.getRepositoryList():
            # FIXME: this function throws exception directly, there should a way to auto fix it
            try:
                self.pkgwh.repoman.checkRepository(repoName, self.bAutoFix)
            except RepositoryCheckError as e:
                raise FmCheckException(e.message)

        # basic check stops here
        if not bFullCheck:
            return

        # there should be no same ebuild directory between repositories
        if True:
            infoDict = dict()
            for repoName in self.pkgwh.repoman.getRepositoryList():
                if not self.pkgwh.repoman.isRepoExist(repoName):
                    continue
                repoDir = self.pkgwh.repoman.getRepoDir(repoName)
                infoDict[repoName] = set(FmUtil.repoGetEbuildDirList(repoDir))

            for k, v in list(infoDict.items()):
                for k2, v2 in list(infoDict.items()):
                    if k == k2:
                        continue
                    vi = list(v & v2)
                    if len(vi) > 0:
                        raise FmCheckException("repository \"%s\" and \"%s\" has same package \"%s\"" % (k, k2, vi[0]))

    def _checkOverlays(self, bFullCheck=True):
        """Check overlays"""

        # check all overlays
        for overlayName in self.pkgwh.layman.getOverlayList():
            try:
                self.pkgwh.layman.checkOverlay(overlayName, self.bAutoFix)
            except OverlayCheckError as e:
                raise FmCheckException(e.message)

        # basic check stops here
        if not bFullCheck:
            return

        for oname in self.pkgwh.layman.getOverlayList():
            oDir = self.pkgwh.layman.getOverlayDir(oname)

            # overlays should not have same repo_name
            if True:
                overlayRepoName = self.pkgwh.layman.getOverlayMetadata(oname, "repo-name")
                for repoName in self.pkgwh.repoman.getRepositoryList():
                    if not self.pkgwh.repoman.isRepoExist(repoName):
                        continue
                    if self.pkgwh.repoman.getRepoMetadata(repoName, "repo-name") == overlayRepoName:
                        raise FmCheckException("repository \"%s\" and overlay \"%s\" has same repo_name" % (repoName, oname))
                for oname2 in self.pkgwh.layman.getOverlayList():
                    if oname == oname2:
                        continue
                    if self.pkgwh.layman.getOverlayMetadata(oname2, "repo-name") == overlayRepoName:
                        raise FmCheckException("overlay \"%s\" and \"%s\" has same repo_name" % (oname2, oname))

            # there should be no same set files between overlays
            if True:
                infoDict = dict()
                for oname2 in self.pkgwh.layman.getOverlayList():
                    oSetDir = os.path.join(self.pkgwh.layman.getOverlayFilesDir(oname2), "set")
                    infoDict[oname2] = set(os.listdir(oSetDir)) if os.path.exists(oSetDir) else set()
                for oname2 in self.pkgwh.layman.getOverlayList():
                    if oname == oname2:
                        continue
                    vi = list(infoDict[oname] & infoDict[oname2])
                    if len(vi) == 0:
                        continue
                    raise FmCheckException("overlay \"%s\" and \"%s\" has same set file \"%s\"" % (oname, oname2, vi[0]))
#                    for f in vi:
#                        fname1 = os.path.join(self.pkgwh.layman.getOverlayFilesDir(k), "set", f)
#                        fname2 = os.path.join(self.pkgwh.layman.getOverlayFilesDir(k2), "set", f)
#                        if not FmUtil.fileHasSameContent(fname1, fname2):
#                            raise FmCheckException("overlay \"%s\" and \"%s\" has same set file \"%s\"" % (k, k2, f))

            # there should be no same ebuild directory between repository and overlay
            if True:
                infoDict = dict()
                for repoName in self.pkgwh.repoman.getRepositoryList():
                    if not self.pkgwh.repoman.isRepoExist(repoName):
                        continue
                    repoDir = self.pkgwh.repoman.getRepoDir(repoName)
                    infoDict[repoName] = set(FmUtil.repoGetEbuildDirList(repoDir))

                oDirInfo = set(FmUtil.repoGetEbuildDirList(oDir))
                for k, v in infoDict.items():
                    vi = list(v & oDirInfo)
                    if len(vi) > 0:
                        raise FmCheckException("repository \"%s\" and overlay \"%s\" has same package \"%s\"" % (k, oname, vi[0]))

    def _checkUsersAndGroups(self):
        # make sure passwd/group/shadow are tidy
        if self.bAutoFix:
            with strict_pgs.PasswdGroupShadow(readOnly=False, msrc="fpemud-refsystem") as pgs:
                pass

        # do checks
        with strict_pgs.PasswdGroupShadow() as pgs:
            pgs.verify()
            if len(pgs.getStandAloneGroupList()) > 0:
                raise FmCheckException("there should be no stand alone groups")

    def _checkSystemLocale(self):
        """Check system locale configuration"""

        fn = "/etc/locale.conf"
        content = "LANG=\"C.utf8\""     # we don't accept LANGUAGE and LC_* variables

        # check if /etc/locale.conf exists
        if not os.path.exists(fn):
            if not self.bAutoFix:
                self.infoPrinter.printError("Locale is not configured.")
            else:
                with open(fn, "w") as f:
                    f.write(content + "\n")
            return

        # check if content of /etc/locale.conf is correct
        lines = FmUtil.readListFile(fn)
        if len(lines) != 1 or lines[0] != content:
            if not self.bAutoFix:
                self.infoPrinter.printError("System locale should be configured as \"C.utf8\".")
            else:
                with open(fn, "w") as f:
                    f.write(content + "\n")
            return

    def _checkSystemServices(self):
        for s in FmUtil.systemdGetAllServicesEnabled():
            print(s)
            if not FmUtil.systemdIsUnitRunning(s):
                self.infoPrinter.printError("Service \"%s\" is enabled but not running.")

    def _checkSystemTime(self):
        # check timezone configuration
        while True:
            if not os.path.exists("/etc/timezone") or not os.path.exists("/etc/localtime"):
                self.infoPrinter.printError("Timezone is not properly configured.")
                break
            tz = None
            with open("/etc/timezone", "r") as f:
                tz = os.path.join("/usr/share/zoneinfo", f.read().rstrip("\n"))
            if not os.path.exists(tz):
                self.infoPrinter.printError("Timezone is not properly configured.")
                break
            if not filecmp.cmp("/etc/localtime", tz):
                self.infoPrinter.printError("Timezone is not properly configured.")
                break
            break

        # check system time
        try:
            for i in range(0, 4):
                try:
                    nc = ntplib.NTPClient()
                    ret = nc.request("%d.pool.ntp.org" % (i))
                    if abs(ret.offset) > 1.0:
                        # we tolerant an offset of 1 seconds
                        self.infoPrinter.printError("System time is incorrect. Maybe you need network time synchronization?")
                    break
                except:
                    if i == 3:
                        raise
        except Exception as e:
            self.infoPrinter.printError("Error occured when checking system time, %s." % (str(e)))

    def _checkPackageContentFile(self, pkgNameVer):
        contf = os.path.join(FmConst.portageDbDir, pkgNameVer, "CONTENTS_2")
        if not os.path.exists(contf):
            if self.bAutoFix:
                FmUtil.cmdCallIgnoreResult("/usr/bin/emerge", "-1", "=%s" % (pkgNameVer))
                if not os.path.exists(contf):
                    self.infoPrinter.printError("Content file %s is missing, auto-fix failed." % (contf))
            else:
                self.infoPrinter.printError("Content file %s is missing." % (contf))

    def _checkPackageFileScope(self, pkgNameVer):
        # There're some directories and files I think should not belong to any package, but others don't think so...
        dirlist = [
            "/boot",
            "/home",
            "/lib/modules",
            "/lib/firmware",
            "/root",
            "/var",
        ]

        # get file list for this package
        cmdStr = r"/bin/cat /var/db/pkg/%s/CONTENTS " % (pkgNameVer)
        cmdStr += r'| /bin/sed -e "s:^obj \(.*\) [[:xdigit:]]\+ [[:digit:]]\+$:\1:" '
        cmdStr += r'| /bin/sed -e "s:^sym \(.*\) -> .* .*$:\1:" '
        cmdStr += r'| /bin/sed -e "s:^dir \(.*\)$:\1:" '
        ret = FmUtil.shellCall(cmdStr).split("\n")

        # check
        for fn in ret:
            for d in dirlist:
                # FIXME: don't know why, I can't remove /var after remove /var/* for some packages using patch_post script
                if d == "/var":
                    if fn.startswith(d + "/"):
                        self.infoPrinter.printError("\"%s\" should not be installed by package manager. (add to \"/usr/lib/tmpfiles.d/*.conf\"?)" % (fn))
                else:
                    if fn == d or fn.startswith(d + "/"):
                        self.infoPrinter.printError("\"%s\" should not be installed by package manager. (add to \"/usr/lib/tmpfiles.d/*.conf\"?)" % (fn))

    def _checkPakcageMd5(self, pkgNameVer):
        ignoreList = [
            '/etc',
            '/var',
        ]

        contf = os.path.join(FmConst.portageDbDir, pkgNameVer, "CONTENTS_2")
        if not os.path.exists(contf):
            # FIXME
            self.infoPrinter.printError("CONTENTS_2 file for %s is missing." % (pkgNameVer))
            return

        for item in FmUtil.portageParseVarDbPkgContentFile(contf):
            bIgnore = False
            for p in ignoreList:
                if item[1].startswith(p + "/"):
                    bIgnore = True
            if bIgnore:
                continue

            if item[0] == "dir":
                if not os.path.exists(item[1]):
                    self.infoPrinter.printError("Directory %s is missing." % (item[1]))
                else:
                    s = os.stat(item[1])
                    if s.st_uid != item[3]:
                        self.infoPrinter.printError("Directory %s failes for uid verification." % (item[1]))
                    if s.st_gid != item[4]:
                        self.infoPrinter.printError("Directory %s failes for gid verification." % (item[1]))
            elif item[0] == "obj":
                if not os.path.exists(item[1]):
                    self.infoPrinter.printError("File %s is missing" % (item[1]))
                else:
                    if not FmUtil.verifyFileMd5(item[1], item[2]):
                        self.infoPrinter.printError("File %s fails for MD5 verification." % (item[1]))
                    s = os.stat(item[1])
                    if s.st_mode != item[3]:
                        self.infoPrinter.printError("File %s failes for permission verification." % (item[1]))
                    if s.st_uid != item[4]:
                        self.infoPrinter.printError("File %s failes for uid verification." % (item[1]))
                    if s.st_gid != item[5]:
                        self.infoPrinter.printError("File %s failes for gid verification." % (item[1]))
            elif item[0] == "sym":
                if not os.path.islink(item[1]):
                    self.infoPrinter.printError("Symlink %s is missing." % (item[1]))
                else:
                    if os.readlink(item[1]) != item[2]:
                        self.infoPrinter.printError("Symlink %s fails for target verification." % (item[1]))
                    if not os.path.exists(item[1]):
                        self.infoPrinter.printError("Symlink %s is broken." % (item[1]))
                    else:
                        s = os.stat(item[1])
                        if s.st_uid != item[3]:
                            self.infoPrinter.printError("Symlink %s failes for uid verification." % (item[1]))
                        if s.st_gid != item[4]:
                            self.infoPrinter.printError("Symlink %s failes for gid verification." % (item[1]))
            else:
                assert False

    def _checkPkgEbuild2(self, pkgNameVer):
        e2dir = Ebuild2Dir()
        fbasename = FmUtil.portageGetPkgNameFromPkgAtom(pkgNameVer)
        if e2dir.hasPkgCheckScript(fbasename):
            try:
                e2dir.execPkgCheckScript(fbasename)
            except Ebuild2CheckError as e:
                self.infoPrinter.printError(e.message)

    def _checkItemSystemCruft(self):
        obj = _CruftFinder(self.param)
        for cf in obj.findCruft():
            self.infoPrinter.printError("Cruft file found: %s" % (cf))

    def __checkAndFixEtcDir(self, etcDir):
        if not os.path.exists(etcDir):
            if self.bAutoFix:
                os.mkdir(etcDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (etcDir))
        elif not os.path.isdir(etcDir):
            if self.bAutoFix:
                etcDir2 = etcDir + ".2"
                os.mkdir(etcDir2)
                os.rename(etcDir, os.path.join(etcDir2, self.__portageGetUnknownFilename(etcDir2)))
                os.rename(etcDir2, etcDir)
            else:
                raise FmCheckException("\"%s\" is not a directory" % (etcDir))

    def __initCheckAndFixEtcSymlink(self):
        self._etcSymIndex = 1
        self._etcSymLinkList = []

    def __checkAndFixEtcSymlink(self, etcDir, linkName, libDir, targetName):
        assert os.path.exists(os.path.join(libDir, targetName))

        if "?" in linkName:
            linkName = linkName.replace("?", "%02d" % (self._etcSymIndex))
            self._etcSymIndex += 1

        linkFile = os.path.join(etcDir, linkName)
        targetFile = os.path.join(libDir, targetName)

        # <linkFile> does not exist, fix: create the symlink
        if not os.path.lexists(linkFile):
            if self.bAutoFix:
                os.symlink(targetFile, linkFile)
            else:
                raise FmCheckException("\"%s\" must be a symlink to \"%s\"" % (linkFile, targetFile))

        # <linkFile> is not a symlink, fix: keep the original file, create the symlink
        if not os.path.islink(linkFile):
            if self.bAutoFix:
                os.rename(linkFile, os.path.join(etcDir, self.__portageGetUnknownFilename(etcDir)))
                os.symlink(targetFile, linkFile)
            else:
                raise FmCheckException("\"%s\" must be a symlink to \"%s\"" % (linkFile, targetFile))

        # <linkFile> is wrong, fix: re-create the symlink
        if os.readlink(linkFile) != targetFile:
            if self.bAutoFix:
                os.unlink(linkFile)
                os.symlink(targetFile, linkFile)
            else:
                raise FmCheckException("\"%s\" must be a symlink to \"%s\"" % (linkFile, targetFile))

        self._etcSymLinkList.append(linkFile)

    def __checkAndFixEtcEmptyFile(self, etcDir, fileName):
        fn = os.path.join(etcDir, fileName)
        if not os.path.exists(fn):
            if self.bAutoFix:
                FmUtil.touchFile(fn)
            else:
                raise FmCheckException("\"%s\" does not exist" % (fn))

    def __clearInvalidEtcSymlink(self, etcDir):
        for fn in os.listdir(etcDir):
            fullfn = os.path.join(etcDir, fn)
            if os.path.islink(fullfn) and fullfn not in self._etcSymLinkList:
                os.unlink(fullfn)

    def __checkAndFixFile(self, filename, content):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                if f.read() == content:
                    return
                else:
                    if not self.bAutoFix:
                        raise FmCheckException("\"%s\" has invalid content" % (filename))
        else:
            if not self.bAutoFix:
                raise FmCheckException("\"%s\" does not exist" % (filename))

        with open(filename, "w") as f:
            f.write(content)

    def __portageGetUnknownFilename(self, dirpath):
        if not os.path.exists(os.path.join(dirpath, "90-unknown")):
            return "90-unknown"
        i = 2
        while True:
            if not os.path.exists(os.path.join(dirpath, "90-unknown-%d" % (i))):
                return "90-unknown-%d" % (i)
            i += 1


class FmCheckException(Exception):

    def __init__(self, message):
        super(FmCheckException, self).__init__(message)


class _DiskPartitionTableChecker:

    def __init__(self):
        # struct mbr_partition_record {
        #     uint8_t  boot_indicator;
        #     uint8_t  start_head;
        #     uint8_t  start_sector;
        #     uint8_t  start_track;
        #     uint8_t  os_type;
        #     uint8_t  end_head;
        #     uint8_t  end_sector;
        #     uint8_t  end_track;
        #     uint32_t starting_lba;
        #     uint32_t size_in_lba;
        # };
        self.mbrPartitionRecordFmt = "8BII"
        assert struct.calcsize(self.mbrPartitionRecordFmt) == 16

        # struct mbr_header {
        #     uint8_t                     boot_code[440];
        #     uint32_t                    unique_mbr_signature;
        #     uint16_t                    unknown;
        #     struct mbr_partition_record partition_record[4];
        #     uint16_t                    signature;
        # };
        self.mbrHeaderFmt = "440sIH%dsH" % (struct.calcsize(self.mbrPartitionRecordFmt) * 4)
        assert struct.calcsize(self.mbrHeaderFmt) == 512

    def checkDisk(self, devPath):
        pttype = FmUtil.getBlkDevPartitionTableType(devPath)
        if pttype == "gpt":
            self._checkGptDisk(devPath)
        elif pttype == "dos":
            self._checkMbrDisk(devPath)
        else:
            raise _DiskPartitionTableCheckerFailure("Unknown disk partition table type")

    def _checkGptDisk(self, devPath):
        # get Protective MBR header
        mbrHeader = None
        with open(devPath, "rb") as f:
            buf = f.read(struct.calcsize(self.mbrHeaderFmt))
            mbrHeader = struct.unpack(self.mbrHeaderFmt, buf)

        # check Protective MBR header
        if not FmUtil.isBufferAllZero(mbrHeader[0]):
            raise _DiskPartitionTableCheckerFailure("Protective MBR Boot Code should be empty")
        if mbrHeader[1] != 0:
            raise _DiskPartitionTableCheckerFailure("Protective MBR Disk Signature should be zero")
        if mbrHeader[2] != 0:
            raise _DiskPartitionTableCheckerFailure("reserved area in Protective MBR should be zero")

        # check Protective MBR Partition Record
        if True:
            pRec = struct.unpack_from(self.mbrPartitionRecordFmt, mbrHeader[3], 0)
            if pRec[4] != 0xEE:
                raise _DiskPartitionTableCheckerFailure("the first Partition Record should be Protective MBR Partition Record (OS Type == 0xEE)")
            if pRec[0] != 0:
                raise _DiskPartitionTableCheckerFailure("Boot Indicator in Protective MBR Partition Record should be zero")

        # other Partition Record should be filled with zero
        if not FmUtil.isBufferAllZero(mbrHeader[struct.calcsize(self.mbrPartitionRecordFmt):]):
            raise _DiskPartitionTableCheckerFailure("all the Partition Record should be filled with zero")

        # get and check primary and backup GPT header
        pass

    def _checkMbrDisk(self, devPath):
        pass


class _DiskPartitionTableCheckerFailure(Exception):

    def __init__(self, message):
        self.message = message


class _CruftFinder:

    def __init__(self, param):
        self.param = param

        self.ignoreList = [
            '/dev',
            '/etc/passwd',
            '/etc/group',
            '/etc/shadow',
            '/etc/gshadow',
            '/etc/passwd-',
            '/etc/group-',
            '/etc/shadow-',
            '/etc/gshadow-',
            '/etc/subuid',
            '/etc/subuid-',
            '/etc/subgid',
            '/etc/subgid-',
            '/home',
            '/lost+found',
            '/media',
            '/mnt',
            '/proc',
            '/root',
            '/run',
            '/sys',
            '/tmp',
            '/usr/share/mime',
            '/var/tmp',
        ]

    def findCruft(self):
        systemFileSet = self._getSystemFileSet()

        portageFileSet = FmUtil.portageGetInstalledFileSet()

        portageFileSet = self._expandPortageFileSet(portageFileSet)

        cruftFileSet = systemFileSet - portageFileSet
        cruftFileSet |= self._getSharedMimeInfoCruftFileSet(portageFileSet)
        cruftFileSet = self._filterTrashDir(cruftFileSet)
        cruftFileSet = self._filterPycache(cruftFileSet)
        cruftFileSet = self._filterIconThemeCache(cruftFileSet, portageFileSet)
        cruftFileSet = self._filterDotKeep(cruftFileSet)

        vartree = portage.db[portage.root]['vartree']
        for cp in vartree.dbapi.cp_all():
            cruftFileSet = self._pkgCruftFilter(cruftFileSet, cp)

        return sorted(list(cruftFileSet))

    def _getSystemFileSet(self):
        cmdStr = "/usr/bin/find / '(' -false "
        for f in self.ignoreList:
            cmdStr += "-or -path \"%s\" " % (f)
        cmdStr += "')' -prune -or -print0"

        ret = FmUtil.shellCall(cmdStr)
        return set(ret.split("\x00"))

    def _expandPortageFileSet(self, fileSet):
        # deal with *.py
        nret = set()
        for f in fileSet:
            if f.endswith(".py"):
                nret.add(f + "c")
                nret.add(f + "o")
        ret = fileSet | nret

        # deal with directory symlink
        nret = set()
        for f in ret:
            f2 = os.path.join(os.path.realpath(os.path.dirname(f)), os.path.basename(f))
            if f2 != f:
                nret.add(f2)
        ret |= nret

        return ret

    def _getSharedMimeInfoCruftFileSet(self, portageFileSet):
        if not os.path.exists("/usr/share/mime"):
            return set()

        if not os.path.exists("/usr/bin/update-mime-database"):
            raise Exception("executable /usr/bin/update-mime-database is not installed")

        # get file set in /usr/share/mime
        mimeSet = set(FmUtil.cmdCall("/usr/bin/find", "/usr/share/mime", "-print0").split("\x00"))

        # create a a temporary mime directory and get its file set
        newMimeDir = os.path.join(self.param.tmpDir, "mime")
        os.mkdir(newMimeDir)
        FmUtil.cmdCall("/bin/cp", "-r", "/usr/share/mime/packages", newMimeDir)
        FmUtil.cmdCall("/usr/bin/update-mime-database", newMimeDir)
        shutil.rmtree(os.path.join(newMimeDir, "packages"))

        newMimeSet = set(FmUtil.cmdCall("/usr/bin/find", newMimeDir, "-print0").split("\x00"))
        newMimeSet = {x.replace(newMimeDir, "/usr/share/mime") for x in newMimeSet}

        # get cruft file list
        retSet = mimeSet
        retSet -= newMimeSet
        retSet -= portageFileSet
        return retSet

    def _filterTrashDir(self, cruftFileSet):
        retSet = set()
        for x in cruftFileSet:
            m = re.search("^(.*)/.Trash(-[0-9]+)?(/.*)?$", x)
            if m is not None and (m.group(1) == "" or FmUtil.isMountPoint(m.group(1))):
                continue
            retSet.add(x)
        return retSet

    def _filterPycache(self, cruftFileSet):
        retSet = set()
        for x in cruftFileSet:
            if "__pycache__" in FmUtil.realPathSplit(x):
                continue
            retSet.add(x)
        return retSet

    def _filterIconThemeCache(self, cruftFileSet, portageFileSet):
        retSet = set()
        for x in cruftFileSet:
            if os.path.basename(x) == "icon-theme.cache":
                if os.path.join(os.path.dirname(x), "index.theme") in portageFileSet:
                    continue
            retSet.add(x)
        return retSet

#    def _filterSymlink(self, cruftFileSet, portageFileSet):
#        sFileSet = set()
#        for x in cruftFileSet:
#            if os.path.islink(x):
#                if os.path.realpath(x) in portageFileSet:
#                    while x != "/":
#                        sFileSet.add(x)
#                        x = os.path.dirname(x)
#        return cruftFileSet - sFileSet

    def _filterDotKeep(self, cruftFileSet):
        sFileSet = set()
        for x in cruftFileSet:
            if os.path.basename(x) == ".keep":
                while x != "/":
                    sFileSet.add(x)
                    x = os.path.dirname(x)
        return cruftFileSet - sFileSet

    def _pkgCruftFilter(self, cruftFileSet, pkgName):
        patternSet = Ebuild2Dir().getCruftFilterPatternSet(pkgName)

        if len(patternSet) == 0:
            return cruftFileSet

        retSet = set()
        for x in cruftFileSet:
            if any(fnmatch.fnmatchcase(x, pattern) for pattern in patternSet):
                continue
            retSet.add(x)

        return retSet

    def _listDirs(self, dirname):
        ret = []
        for d in os.listdir(dirname):
            if os.path.isdir(os.path.join(dirname, d)):
                ret.append(d)
        return ret
