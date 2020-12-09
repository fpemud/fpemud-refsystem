#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/gentoo" >> "${D}/usr/lib/tmpfiles.d/eselect.conf"
echo "d /var/lib/gentoo/news 0775" >> "${D}/usr/lib/tmpfiles.d/eselect.conf"

###############################################################################

rm -rf ${D}/var/lib/gentoo/news
[ -z "$(ls -A ${D}/var/lib/gentoo)" ] && rmdir ${D}/var/lib/gentoo
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
