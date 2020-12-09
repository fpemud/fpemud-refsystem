#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/wxwidgets" >> "${D}/usr/lib/tmpfiles.d/eselect-wxwidgets.conf"

###############################################################################

rm -rf ${D}/var/lib/wxwidgets
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
