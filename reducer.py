#!/usr/bin/env python3
import sys
last = None
total = 0
for line in sys.stdin:
    key, value = line.rstrip("\n").split("\t", 1)
    if key == last:
        total += int(value)
    else:
        if last is not None:
            sys.stdout.write(last + "\t" + str(total) + "\n")
        last, total = key, int(value)
if last is not None:
    sys.stdout.write(last + "\t" + str(total) + "\n")
