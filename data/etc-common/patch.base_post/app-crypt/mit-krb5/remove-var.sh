#!/bin/bash

mkdir -p "${D}/usr/lib/tmpfiles.d"
echo "d /var/lib/krb5kdc" >> "${D}/usr/lib/tmpfiles.d/mit-krb5.conf"

###############################################################################

rm -rf ${D}/var/lib/krb5kdc
[ -z "$(ls -A ${D}/var/lib)" ] && rmdir ${D}/var/lib
[ -z "$(ls -A ${D}/var)" ] && rmdir ${D}/var
