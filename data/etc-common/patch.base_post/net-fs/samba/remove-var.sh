#!/bin/bash

# upstream sucks, these directories are tmpfs nowadays
rm -rf ${D}/var/lock
rm -rf ${D}/var/run

###############################################################################

echo "d /var/lib/ctdb" >> "${D}/usr/lib/tmpfiles.d/samba.conf"
echo "d /var/lib/samba" >> "${D}/usr/lib/tmpfiles.d/samba.conf"
echo "d /var/lib/samba/bind-dns" >> "${D}/usr/lib/tmpfiles.d/samba.conf"
echo "d /var/lib/samba/private" >> "${D}/usr/lib/tmpfiles.d/samba.conf"
echo "d /var/lib/samba/usershare 755 root users" >> "${D}/usr/lib/tmpfiles.d/samba.conf"
echo "d /var/log/samba" >> "${D}/usr/lib/tmpfiles.d/samba.conf"

###############################################################################

rm -rf ${D}/var/log/samba
[ -z "$(ls -A ${D}/var/log)" ] && rmdir ${D}/var/log

rm -rf ${D}/var/lib/samba/{bind-dns,private,usershare}
[ -z "$(ls -A ${D}/var/lib/samba)" ] && rmdir ${D}/var/lib/samba

rm -rf ${D}/var/lib/ctdb
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib

[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
