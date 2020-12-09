#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/empty" >> "${D}/usr/lib/tmpfiles.d/openssh.conf"

###############################################################################

rm -rf ${D}/var/empty
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
