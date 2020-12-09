#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/log/sandbox 0770 root portage" >> "${D}/usr/lib/tmpfiles.d/sandbox.conf"

###############################################################################

rm -rf ${D}/var/log/sandbox
[ -z "$(ls -A ${D}/var/log)" ] && rmdir ${D}/var/log
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
