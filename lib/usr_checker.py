#!/usr/bin/python3.6
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import pwd
import grp
import portage
import fnmatch
from fm_util import FmUtil
from fm_param import FmConst
from fm_param import UsrParam
from helper_pkg_warehouse import Ebuild2Dir
from helper_pkg_warehouse import Ebuild2CheckError


class FmChecker:

    def __init__(self, param, uid):
        assert isinstance(param, UsrParam)

        self.param = param
        self.infoPrinter = self.param.infoPrinter

        self.uid = uid
        self.userName = pwd.getpwuid(uid).pw_name
        self.homeDir = FmUtil.getHomeDir(self.userName)

        self.bAutoFix = False

    def doCheck(self, bAutoFix):
        self.bAutoFix = bAutoFix

        if not os.path.exists(self.homeDir):
            self.infoPrinter.printError("directory \"%s\" does not exist." % (self.homeDir))
            return

        self.infoPrinter.printInfo(">> Check directory %s..." % (self.homeDir))
        self.infoPrinter.incIndent()
        self._checkItem002()
        self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Check files in directory %s..." % (self.homeDir))
        self.infoPrinter.incIndent()
        self._checkItem003()
        self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Check user configuration...")
        self.infoPrinter.incIndent()
        self._checkItem004()
        self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Do per-package check...")
        self.infoPrinter.incIndent()
        try:
            for pkgNameVer in sorted(FmUtil.getFileList(FmConst.portageDbDir, 2, "d")):
                if FmUtil.repoIsSysFile(pkgNameVer):
                    continue
                if pkgNameVer.split("/")[1].startswith("-MERGING"):
                    continue
                self._checkPkgEbuild2(pkgNameVer)
        finally:
            self.infoPrinter.decIndent()

        self.infoPrinter.printInfo(">> Find user cruft files...")
        self.infoPrinter.incIndent()
        try:
            self._checkCruft()
        finally:
            self.infoPrinter.decIndent()

    def _checkItem002(self):
        self.infoPrinter.printInfo("- Processing")

        # check home directory permission
        s = os.stat(self.homeDir)
        if s.st_mode != 0o40700:
            self.infoPrinter.printError("Invalid permission for directory \"%s\"." % (self.homeDir))
        if pwd.getpwuid(s.st_uid).pw_name != self.userName:
            self.infoPrinter.printError("Invalid owner for directory \"%s\"." % (self.homeDir))
        if grp.getgrgid(s.st_gid).gr_name != self.userName:
            self.infoPrinter.printError("Invalid owner group for directory \"%s\"." % (self.homeDir))

    def _checkItem003(self):
        self.infoPrinter.printInfo("- Processing")

        # no system mount point in home directory
        pass

        # check file permission for all the files in home directory
        for root, dirs, files in os.walk(self.homeDir):
            for f in files:
                fullfn = os.path.join(root, f)
                if not os.path.exists(fullfn):
                    continue        # ignore broken link
                s = os.lstat(fullfn)
                owner = pwd.getpwuid(s.st_uid).pw_name
                owner_group = grp.getgrgid(s.st_gid).gr_name
                if owner != self.userName:
                    self.infoPrinter.printError("Invalid owner (%s) for file \"%s\"." % (owner, fullfn))
                if owner_group != self.userName:
                    self.infoPrinter.printError("Invalid owner group (%s) for file \"%s\"." % (owner_group, fullfn))
            for d in dirs:
                fullfn = os.path.join(root, d)
                s = os.lstat(fullfn)
                owner = pwd.getpwuid(s.st_uid).pw_name
                owner_group = grp.getgrgid(s.st_gid).gr_name
                if owner != self.userName:
                    self.infoPrinter.printError("Invalid owner (%s) for directory \"%s\"." % (owner, fullfn))
                if owner_group != self.userName:
                    self.infoPrinter.printError("Invalid owner group (%s) for directory \"%s\"." % (owner_group, fullfn))

    def _checkItem004(self):
        self.infoPrinter.printInfo("- Processing")

        # check locale setting
        if True:
            profileFn = os.path.join(self.homeDir, ".profile")
            localeStr = None
            if os.path.exists(profileFn):
                for line in FmUtil.readFile(profileFn).split("\n"):
                    line = line.strip()
                    m = re.fullmatch("export LANG=[\'\"]?(\\S*?)[\'\"]?", line)
                    if m is not None:
                        if localeStr is not None:
                            self.infoPrinter.printError("Duplicate locale definition.")
                        localeStr = m.group(1)
            if localeStr is None:
                self.infoPrinter.printError("No locale defined.")
            else:
                localeList = [x for x in FmUtil.cmdCall("/usr/bin/locale", "-a").split("\n") if x != ""]
                if localeStr not in localeList:
                    self.infoPrinter.printError("Locale definition (%s) is invalid." % (localeStr))

        # check broken link in configuration directories
        for root, dirs, files in os.walk(self.homeDir):
            # filter
            tlist = FmUtil.realPathSplit(self.homeDir)
            tlist = FmUtil.realPathSplit(root)[len(tlist):]
            if len(tlist) == 0:
                # under self.homeDir
                files = [x for x in files if x.startswith(".") and x not in [".cache"]]
            else:
                # under subdirectories
                lvlOneDir = tlist[0]
                if not (lvlOneDir.startswith(".") and lvlOneDir in [".cache"]):
                    continue

            # check
            for f in files:
                fullfn = os.path.join(root, f)
                if not os.path.exists(fullfn):
                    self.infoPrinter.printError("File \"%s\" is a broken link." % (fullfn))

    def _checkPkgEbuild2(self, pkgNameVer):
        e2dir = Ebuild2Dir()
        fbasename = FmUtil.portageGetPkgNameFromPkgAtom(pkgNameVer)
        if e2dir.hasUserPkgCheckScript(fbasename):
            self.infoPrinter.printInfo("- Processing package %s..." % (pkgNameVer))
            self.infoPrinter.incIndent()
            try:
                e2dir.execUserPkgCheckScript(fbasename, self.uid, self.userName, self.homeDir)
            except Ebuild2CheckError as e:
                self.infoPrinter.printError(e.message)
            finally:
                self.infoPrinter.decIndent()

    def _checkCruft(self):
        self.infoPrinter.printInfo("- Processing")
        self.infoPrinter.incIndent()
        try:
            def filterByPatternSet(cruftFileSet, patternSet):
                ret = set()
                for fn in cruftFileSet:
                    if not any(fnmatch.fnmatchcase(fn, pattern) for pattern in patternSet):
                        ret.add(fn)
                return ret

            # get whole file set
            cruftFileSet = set()
            for f in set(FmUtil.cmdCall("/usr/bin/find", self.homeDir, "-print0").split("\x00")):
                if f.startswith(self.homeDir + "/."):
                    # we think non dot-files are all data files
                    cruftFileSet.add(f)

            # global filter
            if True:
                globalFilter = [
                    '.profile',
                    '.config',
                    '.local',
                    '.local/share',
                    '.local/share/recently-used.xbel',      # seems a freedesktop standard file
                    '.local/share/Trash',
                    '.local/share/Trash/*',
                    '.local/share/applications',
                    '.local/share/applications/*',
                    '.cache',
                ]

                patternSet = set()
                for x in globalFilter:
                    patternSet.add(os.path.join(self.homeDir, x))
                    patternSet.add(os.path.realpath(os.path.join(self.homeDir, x)))

                cruftFileSet = filterByPatternSet(cruftFileSet, patternSet)

            # per-package filter
            for cp in portage.db[portage.root]['vartree'].dbapi.cp_all():
                patternSet = Ebuild2Dir().getUserCruftFilterPatternSet(self.userName, self.homeDir, cp)
                if len(patternSet) == 0:
                    # for performance
                    continue
                cruftFileSet = filterByPatternSet(cruftFileSet, patternSet)

            # show
            for cf in sorted(list(cruftFileSet)):
                self.infoPrinter.printError("Cruft file found: %s" % (cf))
        finally:
            self.infoPrinter.decIndent()
