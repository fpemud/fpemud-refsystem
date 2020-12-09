#!/bin/bash

# remove plymouth in emergency.service
sed -i "/plymouth/d" "${D}/lib/systemd/system/emergency.service"

# remove plymouth in rescue.service
sed -i "s/ *plymouth-start\\.service *//g" "${D}/lib/systemd/system/rescue.service"
sed -i "/plymouth/d"                       "${D}/lib/systemd/system/rescue.service"
