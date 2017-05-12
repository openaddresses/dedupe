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
import argparse, itertools, pprint, re, json, hashlib, datetime, \
    sys, operator, subprocess, io, math, statistics, csv, sqlite3

from expand import Address

def iterate_addresses(db):
    '''
    '''
    while True:
        try:
            res = db.execute('select args_list from addrs limit 1')
            (addr_args, ) = res.fetchone()
        except TypeError:
            break
        else:
            yield Address(*json.loads(addr_args))

def load_neighbors(db, hash):
    '''
    '''
    neighbors = dict()
    
    res1 = db.execute('''select edges.hash2, addrs.args_list from edges, addrs
                         where edges.hash1 = ? and addrs.hash = edges.hash2''', (hash, ))

    res2 = db.execute('''select edges.hash1, addrs.args_list from edges, addrs
                         where edges.hash2 = ? and addrs.hash = edges.hash1''', (hash, ))

    for (h, a) in res1:
        neighbors[h] = Address(*json.loads(a))
    
    for (h, a) in res2:
        neighbors[h] = Address(*json.loads(a))

    return neighbors

def delete_address(db, hash):
    '''
    '''
    db.execute('delete from addrs where hash = ?', (hash, ))

def add_address(db, hash, args_list):
    '''
    '''
    try:
        db.execute('insert into raw_addrs (hash, args_list) values (?, ?)',
                   (hash, args_list))
    except sqlite3.IntegrityError:
        pass
    else:
        pass # print('insert addrs', (hash))

def add_edge(db, hash1, hash2):
    '''
    '''
    try:
        db.execute('insert into edges (hash1, hash2) values (?, ?)', (hash1, hash2))
    except sqlite3.IntegrityError:
        pass
    else:
        pass # print('insert edges', (hash1, hash2))

db = sqlite3.connect(':memory:')
db.execute('create table raw_addrs ( hash text, args_list text )')
db.execute('create table addrs ( hash text, args_list text, primary key (hash) )')
db.execute('create table edges ( hash1 text, hash2 text, primary key (hash1, hash2) )')

parser = argparse.ArgumentParser(description='Reduce mapped OpenAddresses duplicates to a new GeoJSON file.')

parser.add_argument('input', help='Text file containing tile-prefixed address data.')
parser.add_argument('output', help='CSV file for deduped addresses.')

args = parser.parse_args()

start = datetime.datetime.now()
print('Sorting lines from', args.input, '...', file=sys.stderr)
sorter = subprocess.Popen(['sort', '-k', '1,20', args.input], stdout=subprocess.PIPE)
lines = (line.split(' ', 1) for line in io.TextIOWrapper(sorter.stdout))

for (key, rows) in itertools.groupby(lines, key=operator.itemgetter(0)):
    #print('.', sep='', end='', file=sys.stderr)

    key_addresses = list()
    for row in rows:
        try:
            _, addr_args = row
            addr = Address(*json.loads(addr_args))
        except:
            pass
        else:
            key_addresses.append(addr)
            add_address(db, addr.hash, addr_args)
    
    for (addr1, addr2) in itertools.combinations(key_addresses, 2):
        if addr1.matches(addr2):
            add_edge(db, min(addr1.hash, addr2.hash), max(addr1.hash, addr2.hash))

sorter.wait()

(count, ) = db.execute('select count(*) from addrs').fetchone()
print('-', count, 'addresses at', (datetime.datetime.now() - start), file=sys.stderr)

db.execute('insert into addrs select distinct hash, args_list from raw_addrs')
db.execute('create index edge1 on edges (hash1)')
db.execute('create index edge2 on edges (hash2)')
print('Indexed edges at', (datetime.datetime.now() - start), file=sys.stderr)

merged_count = 0

with open(args.output, 'w') as file:
    out = csv.DictWriter(file, ('NUMBER', 'STREET', 'UNIT', 'LAT', 'LON', 'OA:COUNT', 'OA:RADIUS'))
    out.writeheader()
    
    for address in iterate_addresses(db):
        neighbors = load_neighbors(db, address.hash)
        longitude, latitude = address.lon, address.lat
        neighbor_count, neighbor_radius = 1, None
        
        if len(neighbors) > 0:
            # When there are matching nearby neighbors, record the center of
            # the identified point cluster and note count of duplicate points.
            xs, ys = [address.x], [address.y]
            lons, lats = [address.lon], [address.lat]
            for (neighbor_hash, neighbor) in neighbors.items():
                lons.append(neighbor.lon)
                lats.append(neighbor.lat)
                xs.append(neighbor.x)
                ys.append(neighbor.y)
                neighbor_count += 1
                delete_address(db, neighbor_hash)
            longitude = statistics.mean(lons)
            latitude = statistics.mean(lats)
            x, y = statistics.mean(xs), statistics.mean(ys)
            hypots = [math.hypot(x - x1, y - y1) for (x1, y1) in zip(xs, ys)]
            neighbor_radius = int(statistics.mean(hypots))
    
        delete_address(db, address.hash)
        merged_count += 1

        out.writerow({
            'NUMBER': address.number,
            'STREET': address.street,
            'UNIT': address.unit,
            'LON': longitude,
            'LAT': latitude,
            'OA:COUNT': neighbor_count,
            'OA:RADIUS': neighbor_radius,
            })

    print(merged_count, 'merged addresses at', (datetime.datetime.now() - start), file=sys.stderr)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
