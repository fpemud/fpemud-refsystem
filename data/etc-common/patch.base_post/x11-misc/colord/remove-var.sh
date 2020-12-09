#!/bin/bash

echo "d /var/lib/color" >> "${D}/usr/lib/tmpfiles.d/colord.conf"
echo "d /var/lib/color/icc" >> "${D}/usr/lib/tmpfiles.d/colord.conf"

###############################################################################

rm -rf ${D}/var/lib/color/icc
[ -z "$(ls -A ${D}/var/lib/color)" ] && rmdir ${D}/var/lib/color

rm -rf ${D}/var/lib/colord/icc
[ -z "$(ls -A ${D}/var/lib/colord)" ] && rmdir ${D}/var/lib/colord

[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
