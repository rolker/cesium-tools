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

target_size = 100

class Srtm:
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

if len(sys.argv) != 3:
    print 'Usage: srtm2qmesh infile outdir'
    sys.exit(1)

geodetic = quantized_mesh_tile.global_geodetic.GlobalGeodetic(True)

outdir = sys.argv[2]

srtm = Srtm(sys.argv[1])
print srtm.xcount,'x',srtm.ycount
print srtm.minx,srtm.miny,'-',srtm.maxx,srtm.maxy
print 'dx,dy',srtm.dx,srtm.dy

layer = {'tilesjon':'2.1.0',
         'format':'quantized-mesh-1.0',
         'scheme':'tms',
         'minzoom':0,
         'tiles':('{z}/{x}/{y}.terrain',),
         'available':[]
        }

for level in range(5):
    layer['maxzoom']=level
    factor = 2**level
    for x in range(2*factor):
        for y in range(factor):
            print geodetic.TileBounds(x,y,level)
            fname = os.path.join(outdir,str(level)+'/'+str(x)+'/'+str(y)+'.terrain')
            print '\t',fname
            dn = os.path.dirname(fname)
            if not os.path.isdir(dn):
                os.makedirs(os.path.dirname(fname))
            if os.path.isfile(fname):
                os.remove(fname)
            b = geodetic.TileBounds(x,y,level)
            xStep = ((b[2]-b[0])/target_size)/srtm.dx
            yStep = ((b[3]-b[1])/target_size)/srtm.dy
            print '\txStep:',xStep,'yStep:',yStep
            xi = (b[0]-srtm.minx)/srtm.dx
            yi = (b[1]-srtm.miny)/srtm.dy
            print '\txi,yi:',xi,yi
            print '\t',srtm.getPointAtIndex(xi,yi)
            sys.stdout.flush()
            triangles = []
            verticies = []
            for j in range(target_size):
                for i in range(target_size):
                    if i < (target_size) and j < (target_size):
                        t1 = srtm.getPointAtIndex(xi+i*xStep,yi+j*yStep)
                        t2 = srtm.getPointAtIndex(xi+(i+1)*xStep,yi+j*yStep)
                        t3 = srtm.getPointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep)
                        triangles.append((t1.asTriple(),t2.asTriple(),t3.asTriple()))
                        t1 = srtm.getPointAtIndex(xi+i*xStep,yi+j*yStep)
                        t2 = srtm.getPointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep)
                        t3 = srtm.getPointAtIndex(xi+i*xStep,yi+(j+1)*yStep)
                        triangles.append((t1.asTriple(),t2.asTriple(),t3.asTriple()))
                    if i == (target_size-1) and j == (target_size-1):
                        print '\t',srtm.getPointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep)

            tile = quantized_mesh_tile.encode(triangles,bounds=geodetic.TileBounds(x,y,level))
            tile.toFile(fname)
            #print quantized_mesh_tile.topology.TerrainTopology(geometries=triangles)

open(os.path.join(outdir,'layer.json'),'w').write(json.dumps(layer))