#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/AccountsService" >> "${D}/usr/lib/tmpfiles.d/accountsservice.conf"
echo "d /var/lib/AccountsService/icons" >> "${D}/usr/lib/tmpfiles.d/accountsservice.conf"
echo "d /var/lib/AccountsService/users" >> "${D}/usr/lib/tmpfiles.d/accountsservice.conf"

###############################################################################

rm -rf ${D}/var/lib/AccountsService/icons
rm -rf ${D}/var/lib/AccountsService/users
[ -z "$(ls -A ${D}/var/lib/AccountsService)" ] && rmdir ${D}/var/lib/AccountsService
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
