#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/chrony" >> "${D}/usr/lib/tmpfiles.d/chrony.conf"
echo "d /var/log/chrony" >> "${D}/usr/lib/tmpfiles.d/chrony.conf"

###############################################################################

rm -rf ${D}/var/lib/chrony
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib

rm -rf ${D}/var/log/chrony
[ -z "$(ls -A ${D}/var/log)" ] && rmdir ${D}/var/log

[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
