#!/usr/bin/env python

import sys
import os
import math
import json
import scipy.io.netcdf

import quantized_mesh_tile.global_geodetic
import quantized_mesh_tile.terrain
# https://pypi.python.org/pypi/quantized-mesh-tile/
# pip install quantized-mesh-tile

class Grd:
    def __init__(self,fname,tileSize):
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
        self.maxZoom = int(math.log(180/(self.dy*tileSize),2))
        
    def getPointAtIndex(self,xi,yi):
        if xi < 0 or yi < 0 or xi >= self.xcount or yi >= self.ycount:
            return None
        lat = self.latVar[int(yi)]
        lon = self.lonVar[int(xi)]
        d = self.zVar[int(yi),int(xi)]
        return Point(lat,lon,d)
    
    def interpolatePointAtIndex(self,xi,yi,interpolateX=False,interpolateY=False,verbose=False):
        if (not interpolateX and not interpolateY):
            return self.getPointAtIndex(xi,yi)
        if xi < 0 or yi < 0 or xi >= self.xcount or yi >= self.ycount:
            return None
        xi0 = int(xi)
        xi1 = min(xi0+1,self.xcount-1)
        xp = xi-xi0
        yi0 = int(yi)
        yi1 = min(yi0+1,self.ycount-1)
        yp = yi-yi0
        lon0 = self.lonVar[xi0]
        lon1 = self.lonVar[xi1]
        lon = lon0*(1.0-xp)+lon1*xp
        lat0 = self.latVar[yi0]
        lat1 = self.latVar[yi1]
        lat = lat0*(1.0-yp)+lat1*yp
        d00 = self.zVar[yi0,xi0]
        d01 = self.zVar[yi1,xi0]
        d10 = self.zVar[yi0,xi1]
        d11 = self.zVar[yi1,xi1]
        d0 = d00*(1.0-yp)+d01*yp
        d1 = d10*(1.0-yp)+d11*yp
        d = d0*(1.0-xp)+d1*xp
        if verbose:
            print 'ds:',d00,d01,d10,d11,'d:',d,'xp:',xp,'yp:',yp,
        return Point(lat,lon,d)
        

    def __str__(self):
        return 'size: '+str(self.xcount)+'x'+str(self.ycount)+' bounds: '+str(self.minx)+','+str(self.miny)+' - '+str(self.maxx)+','+str(self.maxy)+' dx,dy:'+str(self.dx)+','+str(self.dy)+' max zoom: '+str(self.maxZoom)

        
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


def createTile(x,y,level,params,base,maps=None):
    print geodetic.TileBounds(x,y,level)
    fname = os.path.join(params['outputDirectory'],str(level)+'/'+str(x)+'/'+str(y)+'.terrain')
    print '\t',fname
    dn = os.path.dirname(fname)
    if not os.path.isdir(dn):
        os.makedirs(os.path.dirname(fname))
    if os.path.isfile(fname):
        os.remove(fname)
    b = geodetic.TileBounds(x,y,level)
    m = base
    if level >= base.maxZoom:
        m = maps[0]
    
    xStep = ((b[2]-b[0])/params['tileSize'])/m.dx
    yStep = ((b[3]-b[1])/params['tileSize'])/m.dy
    print '\txStep:',xStep,'yStep:',yStep
    xi = (b[0]-m.minx)/m.dx
    yi = (b[1]-m.miny)/m.dy
    print '\txi,yi:',xi,yi
    print '\t',m.getPointAtIndex(xi,yi)
    print '\tinterp\t',m.interpolatePointAtIndex(xi,yi,True,True,True)
    sys.stdout.flush()
    triangles = []
    verticies = []
    for j in range(params['tileSize']):
        if j == 0:
            yedge0 = True
        else:
            yedge0 = False
        if j == (params['tileSize']-1):
            yedge1 = True
        else:
            yedge1 = False
        for i in range(params['tileSize']):
            if i == 0:
                xedge0 = True
            else:
                xedge0 = False
            if i == (params['tileSize']-1):
                xedge1 = True
            else:
                xedge1 = False

            if i < (params['tileSize']) and j < (params['tileSize']):
                t1 = m.interpolatePointAtIndex(xi+i*xStep,yi+j*yStep,xedge0,yedge0)
                t2 = m.interpolatePointAtIndex(xi+(i+1)*xStep,yi+j*yStep,xedge1,yedge0)
                t3 = m.interpolatePointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep,xedge1,yedge1)
                if t1 is not None and t2 is not None and t3 is not None:
                    triangles.append((t1.asTriple(),t2.asTriple(),t3.asTriple()))
                t1 = m.interpolatePointAtIndex(xi+i*xStep,yi+j*yStep,xedge0,yedge0)
                t2 = m.interpolatePointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep,xedge1,yedge1)
                t3 = m.interpolatePointAtIndex(xi+i*xStep,yi+(j+1)*yStep,xedge0,yedge1)
                if t1 is not None and t2 is not None and t3 is not None:
                    triangles.append((t1.asTriple(),t2.asTriple(),t3.asTriple()))
            if i == (params['tileSize']-1) and j == (params['tileSize']-1):
                print '\tget\t',m.getPointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep)
                print '\tinterp\t',m.interpolatePointAtIndex(xi+(i+1)*xStep,yi+(j+1)*yStep,xedge1,yedge1,True)

    if len(triangles):
        tile = quantized_mesh_tile.encode(triangles,bounds=geodetic.TileBounds(x,y,level),hasLighting=True)
        tile.toFile(fname)


if len(sys.argv) != 2:
    print 'Usage: base2qmesh params.json'
    sys.exit(1)

params = json.load(open(sys.argv[1]))
print params

geodetic = quantized_mesh_tile.global_geodetic.GlobalGeodetic(True)

base = Grd(params['basemap'],params['tileSize'])
print base

maxLevel = params['baseLevels']
maps = []
for m in params['maps']:
    print m
    maps.append(Grd(m,params['tileSize']))
    maxLevel = max(maxLevel,maps[-1].maxZoom)
    print maps[-1]
    

layer = {'tilesjon':'2.1.0',
         'format':'quantized-mesh-1.0',
         'scheme':'tms',
         'minzoom':0,
         'tiles':('{z}/{x}/{y}.terrain',),
         'available':[]
        }

for level in range(maxLevel):
    layer['maxzoom']=level
    factor = 2**level
    print level,factor
    sys.stdout.flush()
    if level < params['baseLevels']:
        for x in range(2*factor):
            for y in range(factor):
                createTile(x,y,level,params,base)
    else:
        x0,y0= geodetic.LonLatToTile(maps[0].minx,maps[0].miny,level)
        x1,y1= geodetic.LonLatToTile(maps[0].maxx,maps[0].maxy,level)
        print 'level:',level,'indecies:',x0,y0,'-',x1,y1
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):
                createTile(x,y,level,params,base,maps)

open(os.path.join(params['outputDirectory'],'layer.json'),'w').write(json.dumps(layer))