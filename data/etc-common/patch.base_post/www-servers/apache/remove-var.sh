#!/bin/bash

# upstream sucks, these directories are tmpfs nowadays
rm -rf ${D}/var/run

###############################################################################

echo "d /var/lib/dav 750 apache apache" >> "${D}/usr/lib/tmpfiles.d/apache.conf"
echo "d /var/log/apache2 750 apache apache" >> "${D}/usr/lib/tmpfiles.d/apache.conf"
echo "d /var/www 755 root root" >> "${D}/usr/lib/tmpfiles.d/apache.conf"

###############################################################################

rm -rf ${D}/var/www

rm -rf ${D}/var/log/apache2
[ -z "$(ls -A ${D}/var/log)" ] && rmdir ${D}/var/log

rm -rf ${D}/var/lib/dav
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib

[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
