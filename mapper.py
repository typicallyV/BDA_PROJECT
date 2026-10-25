#!/usr/bin/env python3
import csv
import sys
reader = csv.DictReader(sys.stdin)
for row in reader:
    platform = (row.get("platform") or "").strip()
    if platform and platform.lower() != "platform":
        sys.stdout.write(platform + "\t1\n")
