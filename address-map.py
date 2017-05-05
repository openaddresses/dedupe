#!/usr/bin/env python3
''' Map OpenAddresses data to nearby zoom=19 web mercator tiles.

Uses a simple quadtile implementation to output (tile key, JSON) lines of text
suitable for sorting in a map/reduce implementation. Optimized for and tested
with simple commandline implementations like bashreduce:

    http://blog.last.fm/2009/04/06/mapreduce-bash-script

Assumes that stdin containes sorted, space-delimited lines with a meaningful
alphanumeric key at the beginning. Writes groupings to output files, and emits
filenames to stdout.
'''
from expand import Address
import sys, json, itertools, operator

lines = (line.split(' ', 1) for line in sys.stdin)

for (key, lines) in itertools.groupby(lines, key=operator.itemgetter(0)):
    count, filename = 0, 'addresses-{}.txt'.format(key)
    print(filename, file=sys.stdout)
    
    with open(filename, 'w') as file:
        for (_, line) in lines:
            address = Address(*json.loads(line))
            for tile in address.quadtiles(zoom=19):
                print(tile, address.tojson(), file=file)
            count += 1
                
    print('Wrote', count, 'addresses to', filename, file=sys.stderr)
