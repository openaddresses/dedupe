#!/usr/bin/env python3
''' Combine State and CBSA areas into a continuous output quilt.

Reads shapes from geodata/tl_2016_us_state.shp and geodata/tl_2016_us_cbsa.shp,
splits them into 1x1 degree boxes, subtracts CBSA areas from states, and writes
a unified shapefile.
'''
from osgeo import ogr, osr
import collections, math, sys

def create_output_ds(filename):
    '''
    '''
    out_driver = ogr.GetDriverByName('ESRI Shapefile')
    sref = osr.SpatialReference(); sref.ImportFromEPSG(4326)
    out_ds = out_driver.CreateDataSource(filename)
    out_layer = out_ds.CreateLayer('boxes', srs=sref, geom_type=ogr.wkbMultiPolygon)
    out_layer.CreateFields([
        ogr.FieldDefn('lon', ogr.OFTInteger), ogr.FieldDefn('lat', ogr.OFTInteger),
        ogr.FieldDefn('geoid', ogr.OFTString), ogr.FieldDefn('name', ogr.OFTString)
        ])
    
    return out_ds, out_layer

def add_feature(layer, geom, lon, lat, geoid, name):
    '''
    '''
    defn = layer.GetLayerDefn()
    feature = ogr.Feature(defn)
    feature.SetGeometry(geom)
    feature.SetField('lon', lon)
    feature.SetField('lat', lat)
    feature.SetField('geoid', geoid)
    feature.SetField('name', name)
    layer.CreateFeature(feature)

def create_box_geom(x, y):
    '''
    '''
    wkt_tpl = 'POLYGON(({x1} {y1},{x1} {y2},{x2} {y2},{x2} {y1},{x1} {y1}))'
    wkt = wkt_tpl.format(x1=int(x), y1=int(y), x2=int(x+1), y2=int(y+1))
    return ogr.CreateGeometryFromWkt(wkt)

def iterate_boxes(feature):
    '''
    '''
    xmin, xmax, ymin, ymax = feature.GetGeometryRef().GetEnvelope()
    
    x = math.floor(xmin)
    while x < xmax:
        y = math.floor(ymin)
        while y < ymax:
            yield (x, y)
            y += 1
        x += 1

out_ds, out_layer = create_output_ds(*sys.argv[1:])
states_ds = ogr.Open('geodata/tl_2016_us_state.shp')
cbsa_ds = ogr.Open('geodata/tl_2016_us_cbsa.shp')
boxed_geoms = collections.defaultdict(list)

for cbsa_feature in cbsa_ds.GetLayer(0):
    print(cbsa_feature.GetField('NAME'), file=sys.stderr)
    
    for (x, y) in iterate_boxes(cbsa_feature):
        box_geom = create_box_geom(x, y)
        cbsa_geom = cbsa_feature.GetGeometryRef()
        
        if not box_geom.Intersects(cbsa_geom):
            continue
        
        boxed_geom = box_geom.Intersection(cbsa_geom)
        boxed_geoms[(x, y)].append(boxed_geom)
        
        add_feature(out_layer, boxed_geom, x, y,
            cbsa_feature.GetField('GEOID'), cbsa_feature.GetField('NAME'))

for state_feature in states_ds.GetLayer(0):
    print(state_feature.GetField('NAME'), file=sys.stderr)
    
    for (x, y) in iterate_boxes(state_feature):
        box_geom = create_box_geom(x, y)
        state_geom = state_feature.GetGeometryRef()
        
        if not box_geom.Intersects(state_geom):
            continue
        
        boxed_geom = box_geom.Intersection(state_geom)
        for other_geom in boxed_geoms[(x, y)]:
            # Substract CBSA areas from state area
            boxed_geom = boxed_geom.Difference(other_geom)
        
        add_feature(out_layer, boxed_geom, x, y,
            state_feature.GetField('GEOID'), state_feature.GetField('NAME'))

out_ds.SyncToDisk()
