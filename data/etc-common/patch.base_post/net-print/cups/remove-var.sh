#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/log/cups" >> "${D}/usr/lib/tmpfiles.d/cups.conf"
echo "d /var/spool/cups 0710 root lp" >> "${D}/usr/lib/tmpfiles.d/cups.conf"
echo "d /var/spool/cups/tmp 0755 root lp" >> "${D}/usr/lib/tmpfiles.d/cups.conf"

###############################################################################

rm -rf ${D}/var/log/cups
[ -z "$(ls -A ${D}/var/log)" ] && rmdir ${D}/var/log

rm -rf ${D}/var/spool/cups/tmp
[ -z "$(ls -A ${D}/var/spool/cups)" ] && rmdir ${D}/var/spool/cups
[ -z "$(ls -A ${D}/var/spool)" ] && rmdir ${D}/var/spool

[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
