#!/bin/bash

# Copyright 2018-2025 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

set -euo pipefail

for FIT in "$@" ; do
    GPX="${FIT}.gpx"
    if [ -f "${GPX}" ] ; then
        continue
    fi

    echo "${FIT}"
    gpsbabel -i garmin_fit -f "${FIT}" -o gpx -F "${GPX}"
done
