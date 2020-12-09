#!/bin/bash

# By doing this, wine won't add unwanted menu entries and change the mime database.
# But, wine won't create start menu entries when executing a msi either.
# So, take attention.
find "${D}" -name "winemenubuilder.exe" | xargs rm -f
find "${D}" -name "winemenubuilder.exe.so" | xargs rm -f