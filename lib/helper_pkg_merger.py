#!/usr/bin/python3.6
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import subprocess
from fm_util import FmUtil
from fm_param import FmConst


class PkgMerger:

    def touchPortageTree(self):
        FmUtil.cmdCallIgnoreResult("/usr/bin/emerge", "-s", "non-exist-package")

    def fetchPkg(self, cmd, autouse=True):
        while autouse and self._updateUseFlag("/usr/bin/emerge -p %s" % (cmd)):
            pass
        FmUtil.shellExec("/usr/bin/emerge --fetchonly %s" % (cmd))

    def emergePkg(self, cmd, autouse=True):
        while autouse and self._updateUseFlag("/usr/bin/emerge -p %s" % (cmd)):
            pass
        FmUtil.shellExec("/usr/bin/emerge %s" % (cmd))

    def smartEmergePkg(self, pretendCmd, realCmd, cfgProtect=True, quietFail=False, pkgName=None):
        # features:
        # 1. auto resolve circular dependencies
        # 2. (one-by-one + try-version) mode

        if not cfgProtect:
            cpStr = "CONFIG_PROTECT=\"-* /.fpemud-refsystem\""
        else:
            cpStr = ""
        pretendCmd2 = "/usr/bin/emerge -p %s" % (pretendCmd)
        realCmd2 = "%s /usr/bin/emerge %s" % (cpStr, realCmd)

        rc, out = FmUtil.shellCallWithRetCode(pretendCmd2)
        if rc != 0:
            smartEmergeUseFile = os.path.join(FmConst.portageCfgUseDir, "smart-emerge")

            if quietFail:
                return

            if "possible to break this cycle" in out:
                # change use flag temporaryly according to the suggestion
                if not os.path.exists(smartEmergeUseFile):
                    info = None     # (pkg-atom, change-use)
                    for m in re.finditer(r"- (\S+/\S+) \(Change USE: (\S+)\)(\n \(.*?\))?", out):
                        if m.group(3) is None:
                            info = (m.group(1), m.group(2))
                            break
                    if info is not None:
                        try:
                            with open(smartEmergeUseFile, "w") as f:
                                f.write("=%s %s" % (info[0], info[1]))
                            self.smartEmergePkg(pretendCmd, realCmd, cfgProtect=cfgProtect, pkgName=pkgName)
                        finally:
                            FmUtil.forceDelete(smartEmergeUseFile)
                        self.smartEmergePkg(pretendCmd, realCmd, cfgProtect=cfgProtect, pkgName=pkgName)
            elif "Multiple package instances within a single package slot" in out:
                # use (strict one-by-one) mode when slot conflict occured
                for line in out.split("\n"):
                    m = re.search("^\\[ebuild(.*?)\\] (\\S+)", line)
                    if m is not None:
                        pkgAtom = m.group(2)
                        if pkgName is not None and pkgName == FmUtil.portageGetPkgNameFromPkgAtom(pkgAtom):
                            # this is the target package
                            FmUtil.shellExec(realCmd2)
                        else:
                            rc2, out2 = FmUtil.shellCallWithRetCode("/usr/bin/emerge -p -uN -1 =%s" % (pkgAtom))
                            if rc2 != 0:
                                if "Multiple package instances within a single package slot" in out2:
                                    # ignore slot conflict package currently
                                    continue
                            FmUtil.shellExec("/usr/bin/emerge -uN -1 =%s" % (pkgAtom))
            else:
                # we need user intervention
                FmUtil.shellExec(realCmd2)
        else:
            try:
                FmUtil.shellExec(realCmd2)
            except subprocess.CalledProcessError as e:
                # terminated by signal, no further processing needed
                if e.returncode > 128:
                    raise

                # use (one-by-one + try-version) mode when failure
                out = FmUtil.shellCall(pretendCmd2)
                complete = False
                while not complete:
                    complete = True
                    for line in out.split("\n"):
                        m = re.search("^\\[ebuild.*?\\] (\\S+)", line)
                        if m is None:
                            continue
                        pkgAtom = m.group(1)

                        if pkgName is not None and pkgName == FmUtil.portageGetPkgNameFromPkgAtom(pkgAtom):
                            # this is the target package
                            FmUtil.shellExec(realCmd2)
                        else:
                            rc2 = None
                            out2 = None
                            try:
                                tempMaskFile = os.path.join(FmConst.portageCfgMaskDir, "temp-")
                                with open(tempMaskFile, "w") as f:
                                    f.write("=%s" % (pkgAtom))
                                rc2, out2 = FmUtil.cmdCallWithRetCode(pretendCmd2)
                            finally:
                                FmUtil.forceDelete(tempMaskFile)

                            if rc2 != 0:
                                # we need this specific package version
                                FmUtil.shellExec("/usr/bin/emerge -uN -1 =%s" % (pkgAtom))
                            else:
                                # alternative package version exists
                                try:
                                    FmUtil.shellExec("/usr/bin/emerge -uN -1 =%s" % (pkgAtom))
                                except subprocess.CalledProcessError as e:
                                    # terminated by signal, no further processing needed
                                    if e.returncode > 128:
                                        raise

                                    # mask the current version, fall back to alternative
                                    bugfixMaskFile = os.path.join(FmConst.portageCfgMaskDir, "bugfix")
                                    buf = ""
                                    if os.path.exists(bugfixMaskFile):
                                        with open(bugfixMaskFile, "r") as f:
                                            buf = f.read()
                                    if buf == "" or buf[-1] == "\n":
                                        buf += "=%s\n" % (pkgAtom)
                                    else:
                                        buf += "\n=%s\n" % (pkgAtom)
                                    with open(bugfixMaskFile, "w") as f:
                                        f.write(buf)
                                    out = out2
                                    complete = False
                                    break

    def unmergePkg(self, pkgName):
        FmUtil.cmdExec("/usr/bin/emerge", "-C", pkgName)

    def _updateUseFlag(self, pretendCmd2):
        fn = os.path.join(FmConst.portageCfgUseDir, "99-autouse")
        useLine = []
        useMap = dict()

        rc, out = FmUtil.shellCallWithRetCode(pretendCmd2)
        bStart = False
        for line in out.split("\n"):
            if not bStart:
                if line == "The following USE changes are necessary to proceed:":
                    bStart = True
                continue
            if line == "":
                bStart = False
                break
            if line.startswith(" ") or line.startswith("#"):
                continue
            tlist = line.split(" ")
            pkgAtom = tlist[0]
            useList = tlist[1:]
            if any(x.startswith("-") for x in useList):
                return                                      # unable to process USE flag "-*"
            useLine.append((tlist[0], tlist[1:]))

        if useLine == []:
            return False

        for pkgAtom, useList in FmUtil.portageParseCfgUseFile(FmUtil.readFile(fn)):
            pkgName = FmUtil.portageGetPkgNameFromPkgAtom(pkgAtom)
            if pkgName in useMap:
                useMap[pkgName] |= set(useList)
            else:
                useMap[pkgName] = set(useList)
        for pkgAtom, useList in useLine:
            pkgName = FmUtil.portageGetPkgNameFromPkgAtom(pkgAtom)
            if pkgName in useMap:
                useMap[pkgName] |= set(useList)
            else:
                useMap[pkgName] = set(useList)
        with open(fn, "w") as f:
            f.write(FmUtil.portageGenerateCfgUseFileByUseMap(useMap))
        return True
