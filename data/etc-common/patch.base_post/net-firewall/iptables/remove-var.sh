#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/iptables" >> "${D}/usr/lib/tmpfiles.d/iptables.conf"

###############################################################################

rm -rf ${D}/var/lib/iptables
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
