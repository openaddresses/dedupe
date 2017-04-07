''' Expand duplicate OpenAddresses data to a new GeoJSON file.

Uses simple string matching on number, street, and unit fields to compare
normalized representations of nearby address records and dedupe them. Matching
address points will be coalesced into linestring geometries showing connections
between points.

Assumes that import.py has already been run, and internally configured with
bounding boxes near Cupertino, CA. Modify the value of bbox variable to change
the active area.
'''
#from postal import expand, parser
import psycopg2, itertools, pprint, re, networkx, json, hashlib

comma_squash = re.compile(r'\s+,')
space_squash = re.compile(r'\s\s+')

class Address:
    def __init__(self, source, hash, lon, lat, number, street, unit, city, district, region, postcode):
        street_normal = ''.join([token_map.get(s, s) for s in street.lower().split()])
        print('Address:', (number, street, unit, city, district, region, postcode))
        self.source = source
        self.hash = hash
        self.lon = lon
        self.lat = lat

        self.number = number
        self.street = street
        self.street_normal = street_normal
        self.unit = unit
        self.city = city
        self.district = district
        self.region = region
        self.postcode = postcode
    
    def matches(self, other):
        return bool(
            self.number == other.number
            and self.street_normal == other.street_normal
            and self.unit == other.unit
            )
    
    def __str__(self):
        return self.number + ' ' + self.street + ', ' + self.unit

def parsed_expansions(address, lang):
    '''
    '''
    return [Parse(**{k: v for (v, k) in parser.parse_address(expanded, lang, 'us')})
            for expanded
            in expand.expand_address(address, lang, **EXPAND_KWARGS)]

bbox = 'POINT (-122.0683 37.2920)', 'POINT (-121.9917 37.3390)'
#bbox = -122.04137, 37.31545, -122.03168, 37.32306 # one block in cupertino
bbox = -122.0683, 37.2920, -121.9917, 37.3390 # all of cupertino
#bbox = -122.203, 37.200, -121.699, 37.480 # all of the south bay

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
                       number, street, unit, city, district, region, postcode
                FROM addresses WHERE location && ST_SetSRID(ST_MakeBox2d(%s, %s), 4326)
              --  AND number = '10340' AND street = 'WESTACRES DR'
                AND number != '' AND street != ''
                ''', (p1, p2))
        
            addresses = [Address(*row) for row in db.fetchall()]
            
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
    properties = dict(hash=hash, addr=str(address))
    
    if len(neighbor_hashes) == 0:
        geometry = dict(type='Point', coordinates=[address.lon, address.lat])
    
    else:
        geometry = dict(type='MultiLineString', coordinates=[])
        for (i, hash) in zip(itertools.count(2), neighbor_hashes):
            seen_hashes.add(hash)
            neighbor = graph.node[hash]['address']
            geometry['coordinates'].append([[address.lon, address.lat], [neighbor.lon, neighbor.lat]])
            properties['hash{}'.format(i)] = hash
            properties['addr{}'.format(i)] = str(neighbor)

    feature = dict(geometry=geometry, properties=properties)
    features.append(feature)

with open('expanded.geojson', 'w') as file:
    json.dump(dict(type='FeatureCollection', features=features), file)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
