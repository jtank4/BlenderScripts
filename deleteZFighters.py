import bpy
import bmesh
import mathutils

MAXAREA = .06 #The bigger this is, the more a shape can overlap without being considered z-fighting. If you're still seeing z fighting try lowering it, even to values like .00001
#Also note that since fewer faces will be deleted the larger it is, the longer the program will take to run as those faces will need to be retested for z fighting against other faces
MINDISTANCE = 0.1 #If two faces are further apart than this number they will not be considered to be z fighting
MINDOTPRODUCT = .99 #The dot product is calculated of two face's normals. This will be 1 if they are exactly aligned and less if not.
TOUCHTESTFACESCALE = -.01 #before checking if one face's vertexes are touching another face's vertexes, one of the faces is scaled down by this factor to avoid false positives
VERTEXTOLERANCE = -0.000005 #due to, I believe, floating point error, we can sometimes see a vertex being outside a plane when really it lies on a plane. This is a tolerance for that

activeMesh = bpy.context.object.data
bm = bmesh.new()
bm.from_mesh(activeMesh)
facesToDelete = []

def allFacesExceptLinkedFaces(faces, f):
    facesToRemove = [f] #We also will not test if the face itself is z fighting with itself
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

def anyVertexIntersections(vecList:list[mathutils.Vector], f2:bmesh.types.BMFace):
    for vec in vecList:
        #print(vec)
        if(bmesh.geometry.intersect_face_point(f2, vec)):
            return True
    return False

def scaleFace(f, amount) -> list[mathutils.Vector]: #amount should be any float. Examples: 1:double face size, .5:larger by half, 0:no change -.2:80% of original size, -.5:half the size -.8:20% of orig size
    vecList:list[mathutils.Vector] = [] # -1:reduced to a single point, beyond -1: start growing again, but flipped in 2 axes
    centerpoint = f.calc_center_median_weighted()
    for vert in f.verts:
        vecList.append(vert.co + ((vert.co - centerpoint) * amount))
    return vecList

def rotateFaceToCommonPlane(f1, flipFirst) -> list[mathutils.Vector]: #returns one vector for each vertex in the face describing its new coordinates
    if(flipFirst):
        rotator = f1.normal.rotation_difference(mathutils.Vector((0.0,-1.0,0.0)))
    else:
        rotator = f1.normal.rotation_difference(mathutils.Vector((0.0,1.0,0.0)))
    vecList:list[mathutils.Vector] = []
    for vert in f1.verts:
        newVec = mathutils.Vector(vert.co).rotate(rotator)
        vecList.append(newVec)
    return vecList

def getInwardPlane(e1, faceNormal, faceCenter): #gets a plane along edge 1 facing inside towards the face, used as the clipping plane in the getIntersection function
    vec1 = e1.verts[1].co - e1.verts[0].co
    #angleBetween = vec1.angle(vec2)
    crossP = vec1.cross(faceNormal)
    #Due to the direction of the edge being dependent on the vertex wrapping order, this cross product may return either a vector facing directly inward or directly outward.
    #In testing the wrapping order by checking the distance of the center median to the plane output by this function 254,652 faces were facing inward and 193,194 were facing out
    #Since the direction of the plane is important we do this test in the function. The added computation time is not very high even when this
    #function is called on every edge of every face on a model with 149,282 faces
    #No test - less than one second
    #test using distance_point_to_plane function - around 1 second
    #test using angle_between plane normal and (edge vertex - face center) - around 1 second
    dist = mathutils.geometry.distance_point_to_plane(faceCenter, e1.verts[1].co, crossP)
    if(dist > 0):
        return [e1.verts[1].co, (crossP)] #returns a vector with index 0 being a point on the plane, index 1 is the plane's normal
    else:
        return [e1.verts[1].co, (crossP)*(-1)]

def getIntersection(clipFace, subjectFace): #Uses the Sutherland–Hodgman algorithm to get the intersecting polygon between the two faces
    outputVerts = list()
    for sfVert in subjectFace.verts:
        outputVerts.append(sfVert.co)
    faceCenterMedian = clipFace.calc_center_median()
    for clipEdge in clipFace.edges:
        clipEdgePlane = getInwardPlane(clipEdge, clipFace.normal, faceCenterMedian)
        clipEdgePlaneCo = clipEdgePlane[0] #a coordinate on the plane
        clipEdgePlaneNo = clipEdgePlane[1] #the plane's normal
        inputVerts = outputVerts.copy()
        outputVerts.clear()
        for i in range(len(inputVerts)):
            curVert = inputVerts[i]
            prevVert = inputVerts[i-1]
            if(not isinstance(curVert, mathutils.Vector)):
                print("curVert")
                print(curVert)
            if(not isinstance(clipEdgePlaneCo, mathutils.Vector)):
                print("clipEdgePlaneCo")
                print(clipEdgePlaneCo)
            if(not isinstance(clipEdgePlaneNo, mathutils.Vector)):
                print("clipEdgePlaneNo")
                print(clipEdgePlaneNo)
            curVertDist = mathutils.geometry.distance_point_to_plane(curVert, clipEdgePlaneCo, clipEdgePlaneNo)
            curVertIn = (curVertDist >= VERTEXTOLERANCE)
            prevVertDist = mathutils.geometry.distance_point_to_plane(prevVert, clipEdgePlaneCo, clipEdgePlaneNo)
            prevVertIn = (prevVertDist >= VERTEXTOLERANCE)
            if(curVertIn and prevVertIn and curVertDist < 0 and prevVertDist < 0):
                print("Both verts were within tolerance of the plane but behind it")
                curVertIn = False
                prevVertIn = False #See comment regarding "the intersect line plane function" below as to why this check is needed
            if(curVertIn):
                if(not prevVertIn):
                    inters = mathutils.geometry.intersect_line_plane(curVert, prevVert, clipEdgePlaneCo, clipEdgePlaneNo)
                    #we calculate the intersection inside here because the two scenarios where we must calculate the
                    #intersection cannot both happen, and it could happen that we don't need to calculate it at all.
                    if not isinstance(inters, mathutils.Vector):
                        print("WARNING: current vert is in intersect_line_plane function returned None")
                        print("Current vert distance from clip plane:")
                        print(curVertDist)
                        print("Previous vert distance from clip plane:")
                        print(prevVertDist)
                    outputVerts.append(inters)
                outputVerts.append(curVert)
            else:
                if prevVertIn:
                    inters = mathutils.geometry.intersect_line_plane(curVert, prevVert, clipEdgePlaneCo, clipEdgePlaneNo)
                    if not isinstance(inters, mathutils.Vector): #the intersect line plane function will return None if the line is laying along the plane, or if the two points are both
                        #extremely close to the plane (I saw this happen with a 2.1e-07 distance to plane). To account for this I count points as being inside the clip plane even if they're
                        #slightly outside it. If this still happens, we'll print out a warning about it so the tolerance can be further increased. See VERTEXTOLERANCE
                        #if the tolerance is increased too far 
                        print("WARNING: previous vert is in intersect_line_plane function returned None")
                        print("Current vert distance from clip plane:")
                        print(curVertDist)
                        print("Previous vert distance from clip plane:")
                        print(prevVertDist)
                    outputVerts.append(inters)
    return outputVerts

def areaOverlapping(f1, f2) -> float: #gets two faces and returns an estimate of their overlapping area.
    intersection:list[mathutils.Vector] = getIntersection(f1, f2)
    if(len(intersection) < 3):
        return 0 #if the intersecting polygon has no verts it has an area of 0 and it means the faces we were testing aren't touching at all
    #it technically should not be able to have 1 or 2 verts but if it somehow does we'll just say it has 0 area because that's a point or a line
    areaTally = 0
    for i in range(len(intersection)): #This for loop is effectively breaking up a shape into triangles, estimating those triangle's area, and summing those estimates
        areaTally += (intersection[0] - intersection[i-1]).length*0.5*(intersection[i]-intersection[i-1]).length
    return areaTally #1/2bh is only accurate for right triangles and the triangles a shape breaks into generally won't be unless it's a quad. But the estimate gets something in the right order of magnitude.

def getLongestEdge(f): #gets the length of the longest edge
    longestLength = 0
    for edge in f.edges:
        edgeLength = edge.calc_length()
        if(edgeLength > longestLength):
            longestLength = edgeLength
    return longestLength
    

def facesWouldZFight(f1, f2):
    #print("next three numbers are vertex to plane distances")
    #print(mathutils.geometry.distance_point_to_plane(f1.verts[0].co, f2.verts[0].co, f2.normal))
    #print(mathutils.geometry.distance_point_to_plane(f1.verts[1].co, f2.verts[0].co, f2.normal))
    #print(mathutils.geometry.distance_point_to_plane(f1.verts[2].co, f2.verts[0].co, f2.normal))
    #print("face normals:")
    #print(f1.normal)
    #print(f2.normal)
    dotProd = f1.normal.dot(f2.normal)
    flipOne = False
    if(dotProd < 0):
        flipOne = True #if the dotproduct is negative the faces may be facing the exact opposite way, which means when rotating them in a later step one should be mirrored first
        dotProd *= -1
    if(dotProd < MINDOTPRODUCT): #if the dot product is less than .99 they are not aligned and wouldn't z fight
        #print("Dot product was " + str(dotProd) + " which is less than the required " + str(MINDOTPRODUCT))
        return False
    if(abs(mathutils.geometry.distance_point_to_plane(f1.verts[0].co, f2.verts[0].co, f2.normal)) > MINDISTANCE):
        #print("Faces were apart from each other on the axis of their normals")
        return False #we can check how far apart the faces are with just one vertex since we already checked if the normals are the same
    #If the faces are far apart from each other relative to their size, then they are likely not overlapping. This approach eliminated 1 second off a 7 second runtime
    #f1LongestEdge = getLongestEdge(f1) #get the length of the longest edge
    #f2LongestEdge = getLongestEdge(f2)
    #if((f1.verts[0].co - f2.verts[0].co).magnitude > (f1LongestEdge+f2LongestEdge)*2):
    #    return False
    '''
    if(flipOne):
        if(areaOverlapping(rotateFaceToCommonPlane(f1, False), rotateFaceToCommonPlane(f2, True)) > MAXAREA):
            return False
    else:
        if(areaOverlapping(rotateFaceToCommonPlane(f1, False), rotateFaceToCommonPlane(f2, False)) > MAXAREA):
            return False
    '''
    if(areaOverlapping(f1, f2) < MAXAREA):
        return False
    #if(not (anyVertexIntersections(scaleFace(f1, TOUCHTESTFACESCALE), f2))): #If none of one faces vertex projections are within the other faces area it is not z fighting
        #print("No vertex was in the area of the other face")
        #return False #we scale the face down above to avoid thinking that faces where one point touches the other face are z fighting
    return True

print("Model has " + str(len(bm.faces)) + " faces")
print("Deleting faces that are closer than " + str(MINDISTANCE))
vertCounter = 0

facesToIterate = list(bm.faces)
facesToSubIterate = list(bm.faces)
for f1 in facesToIterate:
    f1Removed = False
    for f2 in allFacesExceptLinkedFaces(list(facesToSubIterate), f1): #might use mathutils.geometry.points_in_planes(planes)
        if(facesWouldZFight(f1, f2)):
            #print("Faces zfighting")
            #print(f1.calc_area())
            #print(f2.calc_area())
            if(f1.calc_area() >= f2.calc_area()):
                #print("f2 removed")
                facesToDelete.append(f2)
                try:
                    facesToIterate.remove(f2)
                except:
                    pass
                try:
                    facesToSubIterate.remove(f2)
                except:
                    pass
            else:
                #print("f1 removed")
                facesToDelete.append(f1)
                try:
                    facesToSubIterate.remove(f1)
                    f1Removed = True
                except:
                    pass
                break
    #try:
    if(not f1Removed):
        #print("removing f1 from sub iterate list since any faces it z fights with have been removed")
        facesToSubIterate.remove(f1)
    #except:
    #    pass
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
