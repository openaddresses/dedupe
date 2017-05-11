#!/usr/bin/env python3
''' Map OpenAddresses data to nearby zoom=19 web mercator tiles.

Uses a simple quadtile implementation to output (tile key, JSON) lines of text
suitable for sorting in a map/reduce implementation. Optimized for and tested
with simple commandline implementations like bashreduce:

    http://blog.last.fm/2009/04/06/mapreduce-bash-script

Assumes that named file contains space-delimited lines with a meaningful
alphanumeric key at the beginning. Writes groupings to output files,
and emits unsorted filenames to stdout.
'''
from expand import Address
import sys, json, itertools, operator, argparse, os, fcntl

parser = argparse.ArgumentParser(description='Map addresses to files named for areas.')
parser.add_argument('input', help='Text file containing area-prefixed address data.')

args = parser.parse_args()
dirname = os.path.dirname(args.input)

with open(args.input) as file:
    lines = (line.split(' ', 1) for line in file)

    for (key, lines) in itertools.groupby(lines, key=operator.itemgetter(0)):
        count, filename = 0, os.path.join(dirname, 'addresses-{}.txt'.format(key))
    
        with open(filename, 'a') as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            for (_, line) in lines:
                address = Address(*json.loads(line))
                addr_json = address.tojson()
                for tile in address.quadtiles(zoom=19):
                    print(tile, addr_json, file=file)
                count += 1
            print('Added', count, 'addresses to', filename, file=sys.stderr)
            print(filename, file=sys.stdout)
            fcntl.flock(file, fcntl.LOCK_UN)
