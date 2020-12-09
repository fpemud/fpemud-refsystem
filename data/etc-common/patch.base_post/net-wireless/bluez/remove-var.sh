#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/bluetooth" >> "${D}/usr/lib/tmpfiles.d/bluez.conf"

###############################################################################

rm -rf ${D}/var/lib/bluetooth
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
