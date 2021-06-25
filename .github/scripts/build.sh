#!/bin/bash

PRO_DIR=$(pwd)

echo ${PRO_DIR}

sed -i "s#project_home#${PRO_DIR}#g" main.spec

rm -f dist/main && pyinstaller --onefile main.spec

echo "finish"