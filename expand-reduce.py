#!/usr/bin/env python3
''' Reduce mapped OpenAddresses duplicates to a new GeoJSON file.

Accepts sorted input from expand-map.py and iterates over address rows within
named web mercator tiles. Optimized for and tested with simple commandline
implementations like bashreduce:

    http://blog.last.fm/2009/04/06/mapreduce-bash-script

Uses simple string matching on number, street, and unit fields to compare
normalized representations of nearby address records and dedupe them. Matching
address points will be coalesced into single point geometries with origin point
counts and average point cluster radius in web mercator meters.

Certain U.S.-specific street name tokens like "Av"/"Ave"/"Avenue", "E"/"East",
or "2nd"/"Second" are treated as identical to maximize matches.
'''
import argparse, itertools, pprint, re, networkx, json, hashlib, sys, operator, subprocess, io, math, statistics

from expand import Address

parser = argparse.ArgumentParser(description='Reduce mapped OpenAddresses duplicates to a new GeoJSON file.')

parser.add_argument('input', help='Text file containing tile-prefixed address data.')
parser.add_argument('output', help='GeoJSON file for deduped addresses.')

args = parser.parse_args()

print('Sorting lines from', args.input, '...', file=sys.stderr)
sorter = subprocess.Popen(['sort', '-k', '1,20', args.input], stdout=subprocess.PIPE)
lines = (line.split(' ', 1) for line in io.TextIOWrapper(sorter.stdout))
graph = networkx.Graph()

count = 0

for (key, rows) in itertools.groupby(lines, key=operator.itemgetter(0)):
    count += 1
    #print('.', sep='', end='', file=sys.stderr)

    addresses = list()
    for row in rows:
        try:
            _, addr_args = row
            addresses.append(Address(*json.loads(addr_args)))
        except:
            pass
            
    for addr in addresses:
        graph.add_node(addr.hash, {'address': addr})
    
    for (addr1, addr2) in itertools.combinations(addresses, 2):
        if addr1.matches(addr2):
            graph.add_edge(addr1.hash, addr2.hash)

print('-', count, 'address tiles.', file=sys.stderr)

seen_hashes = set()
features = list()

for hash in graph.nodes():
    if hash in seen_hashes:
        continue
    
    address = graph.node[hash]['address']
    neighbor_hashes = graph.neighbors(hash)
    seen_hashes.add(hash)
    geometry = dict(type='Point', coordinates=[address.lon, address.lat])
    properties = dict(number=address.number, street=address.street, unit=address.unit)
    neighbor_count, neighbor_radius = 1, None
    
    if len(neighbor_hashes) > 0:
        # When there are matching nearby neighbors, record the center of
        # the identified point cluster and note count of duplicate points.
        xs, ys = [address.x], [address.y]
        lons, lats = [address.lon], [address.lat]
        for (i, hash) in zip(itertools.count(2), neighbor_hashes):
            seen_hashes.add(hash)
            neighbor = graph.node[hash]['address']
            lons.append(neighbor.lon)
            lats.append(neighbor.lat)
            xs.append(neighbor.x)
            ys.append(neighbor.y)
            neighbor_count += 1
        geometry['coordinates'][0] = statistics.mean(lons)
        geometry['coordinates'][1] = statistics.mean(lats)
        x, y = statistics.mean(xs), statistics.mean(ys)
        hypots = [math.hypot(x - x1, y - y1) for (x1, y1) in zip(xs, ys)]
        neighbor_radius = int(statistics.mean(hypots))
    
    properties.update(radius=neighbor_radius, count=neighbor_count)
    feature = dict(geometry=geometry, properties=properties)
    features.append(feature)

print(len(features), 'merged features.', file=sys.stderr)

with open(args.output, 'w') as out:
    json.dump(dict(type='FeatureCollection', features=features), out)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
