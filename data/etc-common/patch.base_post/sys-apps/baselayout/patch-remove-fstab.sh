#!/bin/bash

# it seems that /etc/fstab is installed in pkg_postinst so INSTALL_MASK has no effect.
rm -f "${D}/etc/fstab"