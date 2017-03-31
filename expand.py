''' Expand duplicate OpenAddresses data to a new GeoJSON file.

Uses libpostal v0.3.4 (https://github.com/openvenues/libpostal) to compare
normalized representations of nearby address records and dedupe them. Matching
address points will be coalesced into linestring geometries showing connections
between points.

Assumes that import.py has already been run, and internally configured with
bounding boxes near Cupertino, CA. Modify the value of bbox variable to change
the active area.
'''
from postal import expand, parser
import psycopg2, itertools, pprint, re, networkx, json

comma_squash = re.compile(r'\s+,')
space_squash = re.compile(r'\s\s+')

class Address:
    def __init__(self, source, hash, lon, lat, address, lang):
        print('Address:', address)
        self.address = address
        self.parses = parsed_expansions(address, lang)
        print('Parses:', [(p.house_number, p.road) for p in self.parses])
        self.source = source
        self.hash = hash
        self.lon = lon
        self.lat = lat
    
    def matches(self, other):
        for (p1, p2) in itertools.product(self.parses, other.parses):
            if not p1.house_number or not p1.road:
                continue
            elif not p2.house_number or not p2.road:
                continue
            elif p1.house_number == p2.house_number and p1.road == p2.road:
                return True
        return False

class Parse:
    def __init__(self, house_number=None, road=None, city=None, postcode=None, **kwargs):
        self.house_number = house_number
        self.road = road
        self.city = city
        self.postcode = postcode

EXPAND_KWARGS = dict(lowercase=True, address_components=expand.ADDRESS_HOUSE_NUMBER | expand.ADDRESS_STREET | expand.ADDRESS_UNIT | expand.ADDRESS_LOCALITY)

def parsed_expansions(address, lang):
    '''
    '''
    return [Parse(**{k: v for (v, k) in parser.parse_address(expanded, lang, 'us')})
            for expanded
            in expand.expand_address(address, lang, **EXPAND_KWARGS)]

def parsed_overlaps(parse1, parse2):
    '''
    
        >>> parsed_overlaps({'a': 1}, {'a': 1})
        1.0
        >>> parsed_overlaps({'a': 1}, {'a': 2})
        0.0
        >>> parsed_overlaps({'a': 1}, {'b': 1})
        0.0
        >>> parsed_overlaps({'a': 1, 'b': 2}, {'b': 2, 'c': 3})
        1.0
        >>> parsed_overlaps({'a': 1, 'b': 2}, {'b': -2, 'c': 3})
        0.0
        >>> parsed_overlaps({'a': 1, 'b': 2, 'c': -3}, {'b': 2, 'c': 3})
        0.5
    '''
    keys1, keys2 = set(parse1.keys()), set(parse2.keys())
    common_keys = keys1 & keys2
    if len(common_keys) == 0:
        return 0.
    matched_keys = [k for k in common_keys if parse1[k] == parse2[k]]
    return len(matched_keys) / len(common_keys)

addresses = [
    '20820 BONNY DR, CUPERTINO 95014',
    '20820 BONNY DR, CUPERTINO 95014-2976',
    '20820 PEPPER TREE LN, CUPERTINO 95014-2917',
    '123 24th st., CUPERTINO 95014-2917',
    '123 twenty-fourth st., CUPERTINO 95014-2917',
    'ул Каретный Ряд, д 4, строение 7',
    ]

for address in addresses:
    expanded = expand.expand_address(address, 'en', **EXPAND_KWARGS)
    print('ex', address, expanded)
    for parsed_expansion in parsed_expansions(address, 'en'):
        print(' pa', address, parsed_expansion.__dict__)

for address in addresses:
    print('pa', address, parser.parse_address(address, 'en'))

##

bbox = 'POINT (-122.0683 37.2920)', 'POINT (-121.9917 37.3390)'
bbox = -122.0683, 37.2920, -121.9917, 37.3390
bbox = -122.04137, 37.31545, -122.03168, 37.32306

step = .002
xs = ((x, x + step*2) for x in itertools.takewhile(lambda x: x < bbox[2], itertools.count(bbox[0], step)))
ys = ((y, y + step*2) for y in itertools.takewhile(lambda y: y < bbox[3], itertools.count(bbox[1], step)))

graph = networkx.Graph()

with psycopg2.connect('postgres://oa:oa@localhost/oa') as conn:
    with conn.cursor() as db:
        for ((x1, x2), (y1, y2)) in list(itertools.product(xs, ys)):
            p1 = 'POINT({:.4f} {:.4f})'.format(x1, y1)
            p2 = 'POINT({:.4f} {:.4f})'.format(x2, y2)
            print(p1, p2)

            db.execute('''
                SELECT source, hash, ST_X(location) as lon, ST_Y(location) as lat,
                (number||' '||street||' '||unit||', '||city||' '||district||' '||region||' '||postcode) as address
                FROM addresses WHERE location && ST_SetSRID(ST_MakeBox2d(%s, %s), 4326)
                AND number = '10340' AND street = 'WESTACRES DR'
                ''', (p1, p2))
        
            addresses = [Address(src, hash, lon, lat, space_squash.sub(r' ', comma_squash.sub(r',', addr)), 'en')
                         for (src, hash, lon, lat, addr) in db.fetchall()]
            
            for addr in addresses:
                graph.add_node(addr.hash, {'address': addr})
            
            for (addr1, addr2) in itertools.combinations(addresses, 2):
                if addr1.matches(addr2):
                    graph.add_edge(addr1.hash, addr2.hash)

seen_hashes = set()
features = list()

for hash in graph.nodes():
    if hash in seen_hashes:
        continue
    
    address = graph.node[hash]['address']
    neighbor_hashes = graph.neighbors(hash)
    seen_hashes.add(hash)
    properties = dict(hash=hash, addr=address.address)
    
    if len(neighbor_hashes) == 0:
        geometry = dict(type='Point', coordinates=[address.lon, address.lat])
    
    else:
        geometry = dict(type='MultiLineString', coordinates=[])
        for (i, hash) in zip(itertools.count(2), neighbor_hashes):
            seen_hashes.add(hash)
            neighbor = graph.node[hash]['address']
            geometry['coordinates'].append([[address.lon, address.lat], [neighbor.lon, neighbor.lat]])
            properties['hash{}'.format(i)] = hash
            properties['addr{}'.format(i)] = neighbor.address

    feature = dict(geometry=geometry, properties=properties)
    features.append(feature)

with open('expanded.geojson', 'w') as file:
    json.dump(dict(type='FeatureCollection', features=features), file)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
