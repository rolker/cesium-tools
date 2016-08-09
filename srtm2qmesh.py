#!/usr/bin/env python

import sys
import os
import math
import json
import scipy.io.netcdf

import quantized_mesh_tile.global_geodetic
import quantized_mesh_tile.topology
import quantized_mesh_tile.terrain
# https://pypi.python.org/pypi/quantized-mesh-tile/
# pip install quantized-mesh-tile

class Grd:
    def __init__(self,fname):
        self.ncfile = scipy.io.netcdf.netcdf_file(fname)
        self.xcount = self.ncfile.dimensions['lon']
        self.ycount = self.ncfile.dimensions['lat']
        self.latVar = self.ncfile.variables['lat']
        self.lonVar = self.ncfile.variables['lon']
        self.zVar = self.ncfile.variables['z']
        self.minx = self.lonVar[0]
        self.miny = self.latVar[0]
        self.maxx = self.lonVar[-1]
        self.maxy = self.latVar[-1]
        self.dx = (self.maxx-self.minx)/(self.xcount-1.0)
        self.dy = (self.maxy-self.miny)/(self.ycount-1.0)
        
    def getPointAtIndex(self,xi,yi):
        lat = self.latVar[int(yi)]
        lon = self.lonVar[int(xi)]
        d = self.zVar[int(yi),int(xi)]
        return Point(lat,lon,d)
        
class Point:
    def __init__(self,lat,lon,height=None):
        self.lat = lat
        self.lon = lon
        self.height = height
        
    def __str__(self):
        return 'lat: '+str(self.lat)+', lon: '+str(self.lon)+', height: '+str(self.height)
    
    def __repr__(self):
        return '('+self.__str__()+')'
    
    def asTriple(self):
        h = self.height
        if math.isnan(h):
            h = 0.0
        return (self.lon,self.lat,h)

if len(sys.argv) != 2:
    print 'Usage: base2qmesh params.json'
    sys.exit(1)

params = json.load(open(sys.argv[1]))
print params

geodetic = quantized_mesh_tile.global_geodetic.GlobalGeodetic(True)

base = Grd(params['basemap'])
print base.xcount,'x',base.ycount
print base.minx,base.miny,'-',base.maxx,base.maxy
print 'dx,dy',base.dx,base.dy

layer = {'tilesjon':'2.1.0',
         'format':'quantized-mesh-1.0',
         'scheme':'tms',
         'minzoom':0,
         'tiles':('{z}/{x}/{y}.terrain',),
         'available':[]
        }

for level in range(params['baseLevels']):
    layer['maxzoom']=level
    factor = 2**level
    for x in range(2*factor):
        for y in range(factor):
            print geodetic.TileBounds(x,y,level)
            fname = os.path.join(params['outputDirectory'],str(level)+'/'+str(x)+'/'+str(y)+'.terrain')
            print '\t',fname
            dn = os.path.dirname(fname)
            if not os.path.isdir(dn):
                os.makedirs(os.path.dirname(fname))
            if os.path.isfile(fname):
                os.remove(fname)
            b = geodetic.TileBounds(x,y,level)
            xStep = ((b[2]-b[0])/params['tileSize'])/base.dx
            yStep = ((b[3]-b[1])/params['tileSize'])/base.dy
            print '\txStep:',xStep,'yStep:',yStep
            xi = (b[0]-base.minx)/base.dx
            yi = (b[1]-base.miny)/base.dy
            print '\txi,yi:',xi,yi
            print '\t',base.getPointAtIndex(xi,yi)
            sys.stdout.flush()
            triangles = []
            verticies = []
            for j in range(params['tileSize']):
                for i in range(params['tileSize']):
                    if i < (params['tileSize']) and j < (params['tileSize']):
                        t1 = base.getPointAtIndex(xi+i*xStep,yi+j*yStep)
                        t2 = base.getPointAtIndex(xi+(i+1)*xStep,yi+j*yStep)
                        t3 = base.getPointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep)
                        triangles.append((t1.asTriple(),t2.asTriple(),t3.asTriple()))
                        t1 = base.getPointAtIndex(xi+i*xStep,yi+j*yStep)
                        t2 = base.getPointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep)
                        t3 = base.getPointAtIndex(xi+i*xStep,yi+(j+1)*yStep)
                        triangles.append((t1.asTriple(),t2.asTriple(),t3.asTriple()))
                    if i == (params['tileSize']-1) and j == (params['tileSize']-1):
                        print '\t',base.getPointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep)

            tile = quantized_mesh_tile.encode(triangles,bounds=geodetic.TileBounds(x,y,level),hasLighting=True)
            tile.toFile(fname)
            #print quantized_mesh_tile.topology.TerrainTopology(geometries=triangles)

open(os.path.join(params['outputDirectory'],'layer.json'),'w').write(json.dumps(layer))