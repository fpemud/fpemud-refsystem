#!/bin/bash

touch "${D}/usr/lib/tmpfiles.d/portage.conf"
echo "d /var/log/portage 2755 portage portage" >> "${D}/usr/lib/tmpfiles.d/portage.conf"
echo "d /var/log/portage/elog 2755 portage portage" >> "${D}/usr/lib/tmpfiles.d/portage.conf"

###############################################################################

# FIXME: seems no effect, why?
rm -rf ${D}/var/log/portage/elog
[ -z "$(ls -A ${D}/var/log/portage)" ] && rmdir ${D}/var/log/portage
[ -z "$(ls -A ${D}/var/log)" ] && rmdir ${D}/var/log
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
