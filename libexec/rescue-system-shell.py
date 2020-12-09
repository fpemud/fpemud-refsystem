#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import sys
import time
import json
import glob
import shutil
import ctypes
import subprocess


class Main:

    def main(self):
        selfDir = os.path.dirname(os.path.realpath(__file__))

        if os.getuid() != 0:
            print("You must run this command as root!")
            sys.exit(1)

        # another instance is running?
        pass

        # /mnt/gentoo or /mnt/gentoo/boot is mounted
        if _Util.isMountPoint("/mnt/gentoo"):
            print("Error: /mnt/gentoo should not be mounted")
            sys.exit(1)
        if _Util.isMountPoint("/mnt/gentoo/boot"):
            print("Error: /mnt/gentoo/boot should not be mounted")
            sys.exit(1)

        # get storage layout for target system
        out = _Util.shellCall("%s %s" % (os.path.join(selfDir, "rescue-storage-manager.py"), "_to_json"))
        layoutName = out.split("\n")[0]
        layoutData = json.loads(out.split("\n")[1])

        # get rootDev and bootDev
        if layoutName == "empty":
            print("Error: Empty storage layout.")
            sys.exit(1)
        elif layoutName == "bios-simple":
            rootDev = layoutData["hddRootParti"]
            bootDev = None
        elif layoutName == "bios-lvm":
            rootDev = os.path.join("/dev/mapper", "%s-%s" % (layoutData["lvmVg"], layoutData["lvmRootLv"]))
            bootDev = None
        elif layoutName == "efi-simple":
            rootDev = layoutData["hddRootParti"]
            bootDev = layoutData["hddEspParti"]
        elif layoutName == "efi-lvm":
            rootDev = os.path.join("/dev/mapper", "%s-%s" % (layoutData["lvmVg"], layoutData["lvmRootLv"]))
            bootDev = layoutData["bootHdd"] + "1"
        elif layoutName == "efi-bcache-lvm":
            rootDev = os.path.join("/dev/mapper", "%s-%s" % (layoutData["lvmVg"], layoutData["lvmRootLv"]))
            if layoutData["ssd"] is not None:
                bootDev = layoutData["ssdEspParti"]
            else:
                bootDev = layoutData["bootHdd"] + "1"
        else:
            assert False

        # mount directories (layer 1)
        mountList = [
            ("/mnt/gentoo", "%s /mnt/gentoo" % (rootDev)),
        ]
        with _DirListMount(mountList):
            if not _Util.isGentooRootDir("/mnt/gentoo"):
                print("Error: Invalid content in root device %s" % (rootDev))
                sys.exit(1)

            # mount directories (layer 2)
            mountList = [
                ("/mnt/gentoo/proc", "-t proc -o nosuid,noexec,nodev proc /mnt/gentoo/proc"),
                ("/mnt/gentoo/sys", "--rbind /sys /mnt/gentoo/sys", "--make-rslave /mnt/gentoo/sys"),
                ("/mnt/gentoo/dev", "--rbind /dev /mnt/gentoo/dev", "--make-rslave /mnt/gentoo/dev"),
                ("/mnt/gentoo/run", "--bind /run /mnt/gentoo/run"),
                ("/mnt/gentoo/tmp", "-t tmpfs -o mode=1777,strictatime,nodev,nosuid tmpfs /mnt/gentoo/tmp"),
            ]
            # if os.path.exists("/sys/firmware/efi/efivars"):
            #     mountList += [
            #         ("/mnt/gentoo/sys/firmware/efi/efivars", "-t efivarfs -o nosuid,noexec,nodev /mnt/gentoo/sys/firmware/efi/efivars"),
            #     ]
            if bootDev is not None:
                mountList += [
                    ("/mnt/gentoo/boot", "%s /mnt/gentoo/boot" % (bootDev)),
                ]
            with _DirListMount(mountList):
                if not os.path.exists("/mnt/gentoo/run/udev"):
                    os.makedirs("/mnt/gentoo/run/udev")
                if not os.path.exists("/mnt/gentoo/usr/src/linux"):
                    os.makedirs("/mnt/gentoo/usr/src/linux")

                # mount directories (layer 3)
                mountList = [
                    ("/mnt/gentoo/run/udev", "--rbind /run/udev /mnt/gentoo/run/udev", "--make-rslave /mnt/gentoo/run/udev"),
                    ("/mnt/gentoo/usr/src/linux", "-t tmpfs tmpfs /mnt/gentoo/usr/src/linux"),
                ]
                with _DirListMount(mountList):
                    # do real work
                    self._fillUsrSrcLinux("/mnt/gentoo", "/mnt/gentoo/usr/src/linux")
                    with _CopyResolvConf("/etc/resolv.conf", "/mnt/gentoo"):
                        subprocess.run("FPEMUD_REFSYSTEM_SETUP=1 /usr/bin/chroot /mnt/gentoo /bin/sh", shell=True)

    def _fillUsrSrcLinux(self, mntGentooDir, usrSrcLinuxDir):
        # see "usr-src-linux.sh" in project "fpemud-refsystem"

        flist = glob.glob("%s/boot/config-*" % (mntGentooDir))
        if flist != []:
            fn = flist[0]           # example: /mnt/gentoo/boot/config-x86_64-4.11.9
            shutil.copyfile(fn, os.path.join(usrSrcLinuxDir, ".config"))
            ver = os.path.basename(fn).split("-")[2]
            version = ver.split(".")[0]
            patchlevel = ver.split(".")[1]
            sublevel = ver.split(".")[2]
        else:
            _Util.shellCall("/bin/gunzip -c /proc/config.gz > %s" % (os.path.join(usrSrcLinuxDir, ".config")))
            version = _Util.shellCall("/usr/bin/uname -r | /usr/bin/cut -d '.' -f 1")
            patchlevel = _Util.shellCall("/usr/bin/uname -r | /usr/bin/cut -d '.' -f 2")
            sublevel = _Util.shellCall("/usr/bin/uname -r | /usr/bin/cut -d '.' -f 3")

        with open(os.path.join(usrSrcLinuxDir, "Makefile"), "w") as f:
            f.write("VERSION = %s\n" % (version))
            f.write("PATCHLEVEL = %s\n" % (patchlevel))
            f.write("SUBLEVEL = %s\n" % (sublevel))
            f.write("EXTRAVERSION = \n")


class _DirListMount:

    def __init__(self, mountList):
        self.okList = []
        for item in mountList:      # mountList = (directory, mount-commad-1, mount-command-2, ...)
            dir = item[0]
            if not os.path.exists(dir):
                os.makedirs(dir)
            for i in range(1, len(item)):
                try:
                    _Util.shellCall("%s %s" % ("/bin/mount", item[i]))
                    self.okList.insert(0, dir)
                except subprocess.CalledProcessError:
                    for dir2 in self.okList:
                        _Util.cmdCallIgnoreResult("/bin/umount", "-l", dir2)
                    raise

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        for d in self.okList:
            _Util.cmdCallIgnoreResult("/bin/umount", "-l", d)


class _CopyResolvConf:

    def __init__(self, srcFile, dstDir):
        self.srcf = srcFile
        self.dstf = os.path.join(dstDir, "etc", "resolv.conf")
        self.exists = os.path.exists(self.dstf)
        shutil.copy2(self.srcf, self.dstf)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.exists:
            with open(self.dstf, "w") as f:
                f.truncate()
        else:
            os.unlink(self.dstf)


class _InterProcessCounter:

    def __init__(self, name):
        self.name = name
        self.librt = ctypes.CDLL("librt.so", use_errno=True)

        # # https://github.com/erikhvatum/py_interprocess_shared_memory_blob
        # self.shm_open_argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_unit32]

        # self.pthread_rwlockattr_t = ctypes.c_byte * 8
        # self.pthread_rwlockattr_t_p = ctypes.POINTER(self.pthread_rwlockattr_t)

        # self.pthread_rwlock_t = ctypes.c_byte * 56
        # self.pthread_rwlock_t_p = ctypes.POINTER(self.pthread_rwlock_t)

        # API = [
        #     ('pthread_rwlock_destroy', [pthread_rwlock_t_p], 'pthread'),
        #     ('pthread_rwlock_init', [pthread_rwlock_t_p, pthread_rwlockattr_t_p], 'pthread'),
        #     ('pthread_rwlock_unlock', [pthread_rwlock_t_p], 'pthread'),
        #     ('pthread_rwlock_wrlock', [pthread_rwlock_t_p], 'pthread'),
        #     ('pthread_rwlockattr_destroy', [pthread_rwlockattr_t_p], 'pthread'),
        #     ('pthread_rwlockattr_init', [pthread_rwlockattr_t_p], 'pthread'),
        #     ('pthread_rwlockattr_setpshared', [pthread_rwlockattr_t_p, ctypes.c_int], 'pthread'),
        #     ('shm_open', shm_open_argtypes, 'os'),
        #     ('shm_unlink', [ctypes.c_char_p], 'os')
        # ]

    def incr(self):
        pass

    def decr(self):
        pass


class _Util:

    @staticmethod
    def isGentooRootDir(dirname):
        dirset = set(["bin", "dev", "etc", "lib", "proc", "sbin", "sys", "tmp", "usr", "var"])
        return dirset <= set(os.listdir(dirname))

    @staticmethod
    def touchFile(filename):
        assert not os.path.exists(filename)
        f = open(filename, 'w')
        f.close()

    @staticmethod
    def getMountDeviceForPath(pathname):
        for line in _Util.cmdCall("/bin/mount").split("\n"):
            m = re.search("^(.*) on (.*) type ", line)
            if m is not None and m.group(2) == pathname:
                return m.group(1)
        return None

    @staticmethod
    def isMountPoint(pathname):
        return _Util.getMountDeviceForPath(pathname) is not None

    @staticmethod
    def cmdCall(cmd, *kargs):
        # call command to execute backstage job
        #
        # scenario 1, process group receives SIGTERM, SIGINT and SIGHUP:
        #   * callee must auto-terminate, and cause no side-effect
        #   * caller must be terminated by signal, not by detecting child-process failure
        # scenario 2, caller receives SIGTERM, SIGINT, SIGHUP:
        #   * caller is terminated by signal, and NOT notify callee
        #   * callee must auto-terminate, and cause no side-effect, after caller is terminated
        # scenario 3, callee receives SIGTERM, SIGINT, SIGHUP:
        #   * caller detects child-process failure and do appopriate treatment

        ret = subprocess.run([cmd] + list(kargs),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode > 128:
            # for scenario 1, caller's signal handler has the oppotunity to get executed during sleep
            time.sleep(1.0)
        if ret.returncode != 0:
            print(ret.stdout)
            ret.check_returncode()
        return ret.stdout.rstrip()

    @staticmethod
    def cmdCallWithRetCode(cmd, *kargs):
        ret = subprocess.run([cmd] + list(kargs),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode > 128:
            time.sleep(1.0)
        return (ret.returncode, ret.stdout.rstrip())

    @staticmethod
    def cmdCallIgnoreResult(cmd, *kargs):
        ret = subprocess.run([cmd] + list(kargs),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode > 128:
            time.sleep(1.0)

    @staticmethod
    def shellCall(cmd):
        # call command with shell to execute backstage job
        # scenarios are the same as FmUtil.cmdCall

        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             shell=True, universal_newlines=True)
        if ret.returncode > 128:
            # for scenario 1, caller's signal handler has the oppotunity to get executed during sleep
            time.sleep(1.0)
        if ret.returncode != 0:
            print(ret.stdout)
            ret.check_returncode()
        return ret.stdout.rstrip()


###############################################################################


if __name__ == "__main__":
    Main().main()
