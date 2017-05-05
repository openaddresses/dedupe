#!/usr/bin/env python3
''' Reduce mapped OpenAddresses duplicates to a new GeoJSON file.

Accepts sorted input from expand-map.py and iterates over address rows within
named web mercator tiles. Optimized for and tested with simple commandline
implementations like bashreduce:

    http://blog.last.fm/2009/04/06/mapreduce-bash-script

Uses simple string matching on number, street, and unit fields to compare
normalized representations of nearby address records and dedupe them. Matching
address points will be coalesced into linestring geometries showing connections
between points.

Certain U.S.-specific street name tokens like "Av"/"Ave"/"Avenue", "E"/"East",
or "2nd"/"Second" are treated as identical to maximize matches.
'''
import itertools, pprint, re, networkx, json, hashlib, sys, operator

from expand import Address

graph = networkx.Graph()
lines = (line.split(' ', 1) for line in sys.stdin)

count = 0

for (key, rows) in itertools.groupby(lines, key=operator.itemgetter(0)):
    count += 1
    #print('.', sep='', end='', file=sys.stderr)

    addresses = [Address(*json.loads(row)) for (_, row) in rows]
            
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
    properties = dict(hash=hash, number=address.number, street=address.street, unit=address.unit)
    
    if len(neighbor_hashes) == 0:
        geometry = dict(type='Point', coordinates=[address.lon, address.lat])
    
    else:
        geometry = dict(type='MultiPoint', coordinates=[[address.lon, address.lat]])
        for (i, hash) in zip(itertools.count(2), neighbor_hashes):
            seen_hashes.add(hash)
            neighbor = graph.node[hash]['address']
            geometry['coordinates'].append([neighbor.lon, neighbor.lat])

    feature = dict(geometry=geometry, properties=properties)
    features.append(feature)

print(len(features), 'merged features.', file=sys.stderr)

json.dump(dict(type='FeatureCollection', features=features), sys.stdout)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
