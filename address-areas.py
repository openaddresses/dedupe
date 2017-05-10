#!/usr/bin/env python3
''' Stream OpenAddresses data mapped to shapefile areas to stdout.

Downloads data from 1x1 degree OpenAddresses tile index, checks for overlap
with each shapefile area, and outputs to stdout:

    {geoid 1} [{source}, {hash}, {lon}, {lat}, {x}, {y}, {number}, {street}, {unit}, ...]
    {geoid 2} [{source}, {hash}, {lon}, {lat}, {x}, {y}, {number}, {street}, {unit}, ...]
    {geoid 3} [{source}, {hash}, {lon}, {lat}, {x}, {y}, {number}, {street}, {unit}, ...]
    ...
'''
from osgeo import ogr, osr
from expand import Address
import argparse, itertools, zipfile, csv, requests, io, sys

def feature_box_key(feature):
    '''
    '''
    return feature.GetField('lon'), feature.GetField('lat')
    
parser = argparse.ArgumentParser(description='Stream addresses for area shapes to stdout.')

parser.add_argument('--areas', default='geodata/areas.shp',
                    help='Datasource containing areas to use for groups. '
                         'Default value "geodata/areas.shp".')

parser.add_argument('output', help='Output file.')

args = parser.parse_args()

sref4326 = osr.SpatialReference(); sref4326.ImportFromEPSG(4326)
sref900913 = osr.SpatialReference(); sref900913.ImportFromProj4('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs')
mercator = osr.CoordinateTransformation(sref4326, sref900913)

openaddr_url = 'https://results.openaddresses.io/index.json'
url_template = requests.get(openaddr_url).json().get('tileindex_url')

areas_ds = ogr.Open(args.areas)
areas_features = sorted(areas_ds.GetLayer(0), key=feature_box_key)

output = open(args.output, 'w')

for ((lon, lat), features) in itertools.groupby(areas_features, feature_box_key):
    areas = {feat.GetField('geoid'): feat.GetGeometryRef() for feat in features if feat.GetGeometryRef()}

    print('Downloading', (lon, lat), 'with', len(areas), 'areas', file=sys.stderr)
    addr_resp = requests.get(url_template.format(lon=lon, lat=lat))
    addr_zip = zipfile.ZipFile(io.BytesIO(addr_resp.content))
    addr_buff = addr_zip.open('addresses.csv')
    addr_rows = csv.DictReader(io.TextIOWrapper(addr_buff))
    
    for row in addr_rows:
        addr_geom = ogr.Geometry(wkt='POINT({LON} {LAT})'.format(**row))
        
        for (area_geoid, area_geom) in areas.items():
            if not addr_geom.Within(area_geom):
                # Skip addresses outside the local area
                continue
            
            if not row['NUMBER'] and not row['STREET']:
                # Skip blank addresses
                continue
        
            lon, lat = addr_geom.GetX(), addr_geom.GetY()
            addr_geom.Transform(mercator)
            x, y = addr_geom.GetX(), addr_geom.GetY()
        
            address = Address(
                row['OA:Source'], row['HASH'], lon, lat, x, y,
                row['NUMBER'], row['STREET'], row['UNIT']
                )

            print(area_geoid, address.tojson(), file=output)
