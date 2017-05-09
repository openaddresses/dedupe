#!/usr/bin/env python3
''' Split geographic areas into 1x1-degree GeoJSON files.

Output a list of filenames.
'''
from osgeo import ogr
import argparse, itertools, sys, tempfile, os

def feature_box_key(feature):
    '''
    '''
    return feature.GetField('lon'), feature.GetField('lat')
    
parser = argparse.ArgumentParser(description='Stream addresses for area shapes to stdout.')

parser.add_argument('--areas', default='geodata/areas.shp',
                    help='Datasource containing areas to use for groups. '
                         'Default value "geodata/areas.shp".')

args = parser.parse_args()

areas_ds = ogr.Open(args.areas)
areas_features = sorted(areas_ds.GetLayer(0), key=feature_box_key)

dirname = tempfile.mkdtemp(prefix='areas-', dir='.')
print(dirname, file=sys.stderr)

for ((lon, lat), grouped) in itertools.groupby(areas_features, feature_box_key):
    features = list(grouped)
    filename = 'areas-{:03d}_{}_{}.geojson'.format(len(features), lon, lat)
    filepath = os.path.join(dirname, filename)
    print(filepath, file=sys.stdout)
    
    with open(filepath, 'w') as file:
        print('{ "type": "FeatureCollection", "features": [', file=file)
        
        while features:
            feature = features.pop(0)
            print(feature.ExportToJson(), end=(',\n' if features else '\n'), file=file)
        
        print('] }', file=file)
