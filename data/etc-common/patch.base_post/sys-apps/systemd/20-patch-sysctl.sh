#!/bin/bash

# change 99-sysctl.conf from a symlink to an empty file
/bin/rm -f "${D}/etc/sysctl.d/99-sysctl.conf"
/bin/touch "${D}/etc/sysctl.d/99-sysctl.conf"