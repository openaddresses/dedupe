#!/usr/bin/env python3
from osgeo import ogr, osr
from expand import Address
import itertools, zipfile, csv, requests, io, sys

def feature_box_key(feature):
    '''
    '''
    return feature.GetField('lon'), feature.GetField('lat')

sref4326 = osr.SpatialReference(); sref4326.ImportFromEPSG(4326)
sref900913 = osr.SpatialReference(); sref900913.ImportFromEPSG(900913)
mercator = osr.CoordinateTransformation(sref4326, sref900913)

openaddr_url = 'https://results.openaddresses.io/index.json'
url_template = requests.get(openaddr_url).json().get('tileindex_url')

areas_ds = ogr.Open('geodata/areas.shp')
areas_features = sorted(areas_ds.GetLayer(0), key=feature_box_key)

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
                continue
        
            lon, lat = addr_geom.GetX(), addr_geom.GetY()
            addr_geom.Transform(mercator)
            x, y = addr_geom.GetX(), addr_geom.GetY()
        
            address = Address(
                row['OA:Source'], row['HASH'], lon, lat, x, y,
                row['NUMBER'], row['STREET'], row['UNIT'], row['CITY'],
                row['DISTRICT'], row['REGION'], row['POSTCODE']
                )

            print(area_geoid, address.tojson(), file=sys.stdout)
