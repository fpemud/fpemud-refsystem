#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/arpd" >> "${D}/usr/lib/tmpfiles.d/iproute2.conf"

###############################################################################

rm -rf ${D}/var/lib/arpd
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
