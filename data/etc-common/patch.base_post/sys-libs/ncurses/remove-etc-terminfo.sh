#!/bin/bash

# copy all the files in /etc/terminfo to the corresponding position in /usr/share/terminfo
for fn in `/usr/bin/find "${D}/etc/terminfo" -type f` ; do
    fn2="${fn/\/etc\/terminfo//usr/share/terminfo}"         # this demostrates bash's wierd syntax
    rm -f "${fn2}"
    cp "${fn}" "${fn2}"
done

# finally, we remove /etc/terminfo
rm -rf "${D}/etc/terminfo"
