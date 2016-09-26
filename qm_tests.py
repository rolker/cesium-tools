#!/usr/bin/env python

import os
import math
import quantized_mesh_tile.global_geodetic
import quantized_mesh_tile.terrain
import quantized_mesh_tile.llh_ecef

geodetic = quantized_mesh_tile.global_geodetic.GlobalGeodetic(True)

bounds = geodetic.TileBounds(1,1,2)

w,s,e,n = bounds

dx = e-w
dy = n-s

triangles = []

size = 35

delta = 1/float(size)

maxz = 500000.0

for i in range(size):
    pi0 = i*delta
    pi1 = (i+1)*delta
    zi0 = math.sin(pi0*3.14*4)
    zi1 = math.sin(pi1*3.14*4)
    for j in range(size):
        pj0 = j*delta
        pj1 = (j+1)*delta
        zj0 = math.sin(pj0*3.14*2)
        zj1 = math.sin(pj1*3.14*2)
        triangles.append(((w+pi0*dx,s+pj0*dy,zi0*zj0*maxz),
                        (w+pi1*dx,s+pj0*dy,zi1*zj0*maxz),
                        (w+pi1*dx,s+pj1*dy,zi1*zj1*maxz)
                        ))
        triangles.append(((w+pi0*dx,s+pj0*dy,zi0*zj0*maxz),
                        (w+pi1*dx,s+pj1*dy,zi1*zj1*maxz),
                        (w+pi0*dx,s+pj1*dy,zi0*zj1*maxz)
                        ))

print triangles

tile = quantized_mesh_tile.encode(triangles,bounds=bounds,hasLighting=True)

#for i in range (len(tile.vLight)):
#    tile.vLight[i] = [0.0,0.0,1.0]

fname = 'test.terrain'
if os.path.isfile(fname):
    os.remove(fname)
tile.toFile(fname)

ecefVertices = []
for v in tile.getVerticesCoordinates():
    ecefVertices.append(quantized_mesh_tile.llh_ecef.LLH2ECEF(v[0], v[1], v[2]))

ed_tile = quantized_mesh_tile.decode(fname,bounds=bounds,hasLighting=True)

#print tile.vLight

print 'pre-encode-decode'
print tile
print
print 'post-encode-decode'
print ed_tile
print
print 'pre: ',len(tile.vLight),tile.vLight
print
print 'post:',len(ed_tile.vLight),ed_tile.vLight

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

scale = 1.0/3000000.0
yaw = 0.0
pitch = 0.0

rotating = False
start_x = 0
start_y = 0
start_pitch = 0.0
start_yaw = 0.0

erad = 6371000.0
norm_scale = 0.02

def display():
    global scale
    global pitch
    global yaw
    global tile
    vp = glGetIntegerv(GL_VIEWPORT)
    w,h = vp[2:]
    aspect = float(w)/float(h)
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    gluPerspective(45,aspect,1,10)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glTranslatef(0,0,-5)
    glScalef(scale,scale,scale)
    
    glRotated(pitch,1.0,0.0,0.0)
    glRotated(yaw,0.0,1.0,0.0)
    glTranslated(-tile.header['centerX'],-tile.header['centerY'],-tile.header['centerZ'])

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glColor3f(0.0,1.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,0.0,0.0)
    glVertex3f(erad,0.0,0.0)
    glVertex3f(0.0,0.0,0.0)
    glVertex3f(0.0,erad,0.0)
    glVertex3f(0.0,0.0,0.0)
    glVertex3f(0.0,0.0,erad)
    glEnd()
    
    glColor3f(0.5,0.5,0.5)
    glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
    glBegin(GL_TRIANGLES)
    for i in tile.indices:
        glVertex3dv(ecefVertices[i])
    glEnd()

    glColor3f(0.75,0.0,0.75)
    
    glBegin(GL_LINES)
    for i in range(len(ecefVertices)):
        glVertex3dv(ecefVertices[i])
        glVertex3d(ecefVertices[i][0]+tile.vLight[i][0]*erad*norm_scale,
                   ecefVertices[i][1]+tile.vLight[i][1]*erad*norm_scale,
                   ecefVertices[i][2]+tile.vLight[i][2]*erad*norm_scale)
    glEnd()

    glColor3f(0.5,0.9,0.5)
    
    glBegin(GL_LINES)
    for i in range(len(ecefVertices)):
        glVertex3dv(ecefVertices[i])
        glVertex3d(ecefVertices[i][0]+ed_tile.vLight[i][0]*erad*norm_scale,
                   ecefVertices[i][1]+ed_tile.vLight[i][1]*erad*norm_scale,
                   ecefVertices[i][2]+ed_tile.vLight[i][2]*erad*norm_scale)
    glEnd()

    
    glutSwapBuffers()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glutPostRedisplay();

def mouse(button,state,x,y):
    global scale
    global rotating
    global start_x
    global start_y
    global start_pitch
    global start_yaw
    #print 'button:',button,'state:',state,'x:',x,'y:',y
    if button == 0:
        if state == 0:
            rotating = True
            start_x = x
            start_y = y
            start_pitch = pitch
            start_yaw = yaw
        else:
            rotating = False
    if button == 3 and state == 1:
        scale = scale *1.5
        glutPostRedisplay()
    if button == 4 and state == 1:
        scale = scale /1.5
        glutPostRedisplay()

def motion(x,y):
    global yaw
    global pitch
    if rotating:
        dx = x-start_x
        dy = y-start_y
        yaw = start_yaw+dx
        pitch = min(90.0,max(-90.0,start_pitch+dy))
        glutPostRedisplay()

if __name__ == '__main__':
    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(640,480)
    glutCreateWindow("Quantized mesh test")

    glutReshapeFunc(reshape)
    glutDisplayFunc(display)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)

    glutMainLoop()
