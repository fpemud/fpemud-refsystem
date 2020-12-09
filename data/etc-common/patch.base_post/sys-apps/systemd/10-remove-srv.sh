#!/bin/bash

# it's strange that creation of /srv is in home.conf
sed -i "/\\/srv/d" "${D}/usr/lib/tmpfiles.d/home.conf"