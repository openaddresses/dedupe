''' Map OpenAddresses data to nearby zoom=18 web mercator tiles.

Uses a simple quadtile implementation to output (tile key, JSON) lines of text
suitable for sorting in a map/reduce implementation. Optimized for and tested
with simple commandline implementations like bashreduce:

    http://blog.last.fm/2009/04/06/mapreduce-bash-script

Assumes that import.py has already been run, and internally configured with
bounding boxes in California and Montana. Modify the value of bbox variable
to change the active area.
'''
import psycopg2, re, sys

from expand import Address

bbox = 'POINT (-122.0683 37.2920)', 'POINT (-121.9917 37.3390)'
#bbox = -122.04137, 37.31545, -122.03168, 37.32306 # one block in cupertino
#bbox = -122.0683, 37.2920, -121.9917, 37.3390 # all of cupertino
bbox = -122.203, 37.200, -121.699, 37.480 # all of the south bay

#bbox = -112.0812, 46.5730, -111.9473, 46.6384 # helena, MT
#bbox = -114.523, 45.265, -109.679, 47.210 # southwest montana
bbox = -115.90, 44.30, -103.68, 49.05 # all of montana

count = 0

with psycopg2.connect('postgres://oa:oa@localhost/oa') as conn:
    with conn.cursor() as db:
            p1 = 'POINT({:.4f} {:.4f})'.format(*bbox[:2])
            p2 = 'POINT({:.4f} {:.4f})'.format(*bbox[2:])
            print(p1, p2, file=sys.stderr)

            db.execute('''
                SELECT source, hash,
                       -- lon and lat in degrees:
                       ST_X(location) as lon, ST_Y(location) as lat,
                       -- x and y in mercator meters:
                       ST_X(ST_Transform(location, 900913)) as x,
                       ST_Y(ST_Transform(location, 900913)) as y,
                       number, street, unit, city, district, region, postcode
                FROM addresses WHERE location && ST_SetSRID(ST_MakeBox2d(%s, %s), 4326)
              --  AND number = '10340' AND street = 'WESTACRES DR'
                AND number != '' AND street != ''
                ''', (p1, p2))
        
            for row in db.fetchall():
                count += 1
                #print('.', sep='', end='', file=sys.stderr)
                
                address = Address(*row)
                for tile in address.quadtiles(zoom=18):
                    print(tile, address.tojson(), file=sys.stdout)

print('-', count, 'address rows.', file=sys.stderr)
