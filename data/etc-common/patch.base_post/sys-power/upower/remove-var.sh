#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/upower" >> "${D}/usr/lib/tmpfiles.d/upower.conf"

###############################################################################

rm -rf ${D}/var/lib/upower
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
