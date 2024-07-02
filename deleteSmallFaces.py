import bpy
import bmesh

MINAREA = .05

activeMesh = bpy.context.object.data
bm = bmesh.new()
bm.from_mesh(activeMesh)
facesToDelete = []

print("model has " + str(len(bm.faces)) + " faces")
print("making array of faces with area less than " + str(MINAREA))
for f in bm.faces:
    if(f.calc_area() < MINAREA):
        facesToDelete.append(f)
print(len(facesToDelete))
bmesh.ops.delete(bm, geom=facesToDelete, context="FACES")
print("model now has " + str(len(bm.faces)) + " faces")
print("writing out mesh")
bm.to_mesh(activeMesh)
bm.free()
print("done")

'''
class SimpleOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.simple_operator"
    bl_label = "Simple Object Operator"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        main(context)
        return {'FINISHED'}
'''