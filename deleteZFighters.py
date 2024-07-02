import bpy
import bmesh
import mathutils

MINAREA = .05
MINDISTANCE = 0 #the closest two faces can be to each other without being removed by the anti z fighting program
TOUCHTESTFACESCALE = -.01 #before checking if one faces vertexes are touching another faces vertexes, one of the faces is scaled down by this factor to avoid false positives
TOUCHTESTSCALES = [-.99, -.8, -.6, -.4, -.2 -.01]

activeMesh = bpy.context.object.data
bm = bmesh.new()
bm.from_mesh(activeMesh)
facesToDelete = []

def allFacesExceptLinkedFaces(faces, f):
    facesToRemove = []
    for edge in f.edges:
        for face in edge.link_faces:
            facesToRemove.append(face)
    facesToRemove = set(facesToRemove)
    for face in facesToRemove:
        try:
            faces.remove(face)
        except:
            pass
    #print("length of faces " + str(len(faces)))
    return faces

def arrExceptOne(arr, f):
    arr.remove(f)
    return arr

def anyVertexIntersections(f1:bmesh.types.BMFace, f2:bmesh.types.BMFace):
    centerpoint = f1.calc_center_median_weighted()
    for vert in f1.verts:
        for amount in TOUCHTESTSCALES:
            scaledDownVec = vert.co + ((vert.co - centerpoint) * amount)
            if(bmesh.geometry.intersect_face_point(f2, scaledDownVec)):
                return True
    return False

def scaleFace(f, amount) -> list[mathutils.Vector]: #amount should be any float. Examples: 1:double face size, .5:larger by half, 0:no change -.2:80% of original size, -.5:half the size -.8:20% of orig size
    vecList:list[mathutils.Vector] = [] # -1:reduced to a single point, beyond -1: start growing again, but flipped in 2 axes
    centerpoint = f.calc_center_median_weighted()
    for vert in f.verts:
        vecList.append(vert.co + ((vert.co - centerpoint) * amount))
    return vecList

def facesWouldZFight(f1, f2):
    #print("next three numbers are vertex to plane distances")
    #print(mathutils.geometry.distance_point_to_plane(f1.verts[0].co, f2.verts[0].co, f2.normal))
    #print(mathutils.geometry.distance_point_to_plane(f1.verts[1].co, f2.verts[0].co, f2.normal))
    #print(mathutils.geometry.distance_point_to_plane(f1.verts[2].co, f2.verts[0].co, f2.normal))
    if((f1.normal != f2.normal) and (f1.normal.reflect(f1.normal) != f2.normal)): #checks if the faces are angled the same way or the exact opposite way. If they are they could be z fighting
        #print("Normals were not the same")
        return False
    if(abs(mathutils.geometry.distance_point_to_plane(f1.verts[0].co, f2.verts[0].co, f2.normal)) > MINDISTANCE):
        #print("Faces were apart from each other")
        return False #we can check how far apart the faces are with just one vertex since we already checked if the normals are the same
    if(anyVertexIntersections(f1, f2) or anyVertexIntersections(f2, f1)): #If none of one faces vertex projections are within the other faces area it is not z fighting
        #print("No vertex was in the area of the other face") #We test both faces being scaled down because deleteZFightersTestModel2.blend shows a case where scaling one of the faces down results in no intersections whereas scaling the other down still results in one intersection
        return True #we scale the face down above to avoid thinking that faces where one point touches the other face are z fighting
    return False

print("Model has " + str(len(bm.faces)) + " faces")
print("Deleting faces that are closer than " + str(MINDISTANCE))
vertCounter = 0

facesToIterate = list(bm.faces)
for f1 in facesToIterate:
    for f2 in allFacesExceptLinkedFaces(list(facesToIterate), f1): #might use mathutils.geometry.points_in_planes(planes)
        if(facesWouldZFight(f1, f2)):
            #print("Faces zfighting")
            #print(f1.calc_area())
            #print(f2.calc_area())
            if(f1.calc_area() >= f2.calc_area()):
                facesToDelete.append(f2)
                try:
                    facesToIterate.remove(f2)
                except:
                    pass
            else:
                facesToDelete.append(f1)
                break
                '''
                removing this from the list is too eager as it may be fighting with other faces
                try:
                    facesToIterate.remove(f2)
                except:
                    pass
                '''
    print(str(vertCounter))
    vertCounter += 1

facesToDelete = list(set(facesToDelete)) #remove dupes as bmesh.ops.delete will fail if given duplicates
print("Deleting " + str(len(facesToDelete)) + " faces")
print(type(facesToDelete))
bmesh.ops.delete(bm, geom=facesToDelete, context="FACES")
print("model now has " + str(len(bm.faces)) + " faces")
print("writing out mesh")
bm.to_mesh(activeMesh)
bm.free()
print("done")

'''
#This scaleFace function is not used as it was more efficient to rewrite the intersections function to scale it within itself once I started to do multiple scaling checks
def scaleFace(f, amount) -> list[mathutils.Vector]: #amount should be any float. Examples: 1:double face size, .5:larger by half, 0:no change -.2:80% of original size, -.5:half the size -.8:20% of orig size
    vecList:list[mathutils.Vector] = [] # -1:reduced to a single point, beyond -1: start growing again, but flipped in 2 axes
    centerpoint = f.calc_center_median_weighted()
    for vert in f.verts:
        vecList.append(vert.co + ((vert.co - centerpoint) * amount))
    return vecList

#this version of scaleFace actually changes the dimensions of the face
def scaleFace(f, amount): #amount 2 would double face size, .5 would make it half the size, this makes a new face of those dimensions
    face = f.copy()
    centerpoint = face.calc_center_median_weighted()
    for vert in face.verts:
        vert.co += (vert.co - centerpoint) * amount
    return face

def addSeqToList(arr, seq):
    for el in seq:
        arr.append(el)
    return arr

def allFacesExceptVertFaces(faces, v):
    for face in v.link_faces:
        faces.remove(face)
    return faces

def allVertsExceptFaceVerts(verts, f):
    bef = len(verts)
    for vert in f.verts:
        verts.remove(vert)
    print(bef - len(verts))
    return verts

def allEdgesExceptFaceEdges(edges, f):
    for edge in f.edges:
        edges.remove(edge)
    return edges

def edgeIntersectsFace(e, f):
    if(mathutils.geometry.intersect_line_plane(e.verts[0].co, e.verts[1].co, f.verts[0].co, f.normal) == None):
        return False
    if(not bmesh.geometry.intersect_face_point(f, e.verts[0].co)):
        return False
    return True
'''