#!/bin/bash

# make systemd record journal in memory only, to eliminate disk writes
rm -rf "${D}/var/log/journal"