#!/bin/bash

echo "d /var/lib/udisks2" >> "${D}/usr/lib/tmpfiles.d/udisks2.conf"

###############################################################################

rm -rf ${D}/var/lib/udisks2
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
