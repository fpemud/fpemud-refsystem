#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/os-prober" >> "${D}/usr/lib/tmpfiles.d/os-prober.conf"

###############################################################################

rm -rf ${D}/var/lib/os-prober
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
