#!/bin/bash

DSTDIR=/usr/src/linux

if [ -e /proc/config.gz ] ; then
    # mount the sucking Gentoo Linux kernel source directory
    /bin/mount -t tmpfs -o mode=0755,size=1M,strictatime,nosuid,nodev tmpfs ${DSTDIR}

    # create a dot config file
    /bin/gunzip -c /proc/config.gz > ${DSTDIR}/.config

    # fake a Makefile
    touch ${DSTDIR}/Makefile
    echo "# Faked by fpemud-refsystem to fool the linux-info.eclass" >> ${DSTDIR}/Makefile
    echo "" >> ${DSTDIR}/Makefile
    echo "VERSION = $(/usr/bin/uname -r | /usr/bin/cut -d '.' -f 1)" >> ${DSTDIR}/Makefile
    echo "PATCHLEVEL = $(/usr/bin/uname -r | /usr/bin/cut -d '.' -f 2)" >> ${DSTDIR}/Makefile
    echo "SUBLEVEL = $(/usr/bin/uname -r | /usr/bin/cut -d '.' -f 3)" >> ${DSTDIR}/Makefile
    echo "EXTRAVERSION = " >> ${DSTDIR}/Makefile
fi