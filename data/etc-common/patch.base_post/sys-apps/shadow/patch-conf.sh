#!/bin/bash

# change SUB_UID_COUNT from 65536 to 100000
# the orginal configuration leads to unaligned range in /etc/subuid
/bin/sed -i 's/\(^SUB_UID_COUNT\s*\) \d*.*$/\1100000/g' "${D}/etc/login.defs"

# same as above
/bin/sed -i 's/\(^SUB_GID_COUNT\s*\) \d*.*$/\1100000/g' "${D}/etc/login.defs"