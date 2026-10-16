#!/bin/bash
cd "$(dirname "$0")" || exit 1
python3 scripts/nostalgia.py play "$@"
status=$?
if [ "$status" -ne 0 ] && [ -t 0 ]; then
  read -r -p "按回车关闭窗口…"
fi
exit "$status"
