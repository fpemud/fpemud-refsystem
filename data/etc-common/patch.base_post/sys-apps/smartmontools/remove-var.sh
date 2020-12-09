#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/db/smartmontools" >> "${D}/usr/lib/tmpfiles.d/smartmontools.conf"

###############################################################################

rm -rf ${D}/var/db/smartmontools
[ -z "$(ls -A ${D}/var/db)" ] && rmdir ${D}/var/db
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
