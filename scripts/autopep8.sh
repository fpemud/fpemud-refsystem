#!/bin/bash

FILES="./sysman ./usrman"
FILES="${FILES} $(find ./lib -name '*.py' | tr '\n' ' ')"

autopep8 -ia --ignore=E408,E501 ${FILES}
