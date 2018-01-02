import bpy
import math
import mathutils
from bpy_extras.io_utils import axis_conversion

bl_info = {
    "name": "Export JM's Skeleton",
    "description": "",
    "author": "James Mintram",
    "version": (0, 1),
    "blender": (2, 75, 0),
    "category": "Export",
}

reserved_properties = (
        'cycles_visibility'
    )

def ProcessBone(armature, bone, bone_array, parent_id, depth = 0):
    my_id = len(bone_array)

    # bone_matrix = bone.matrix_local.inverted()
    # change_base = axis_conversion(
    #     from_forward = '-Y', 
    #     from_up='Z', 
    #     to_forward='Z', 
    #     to_up='Y').to_4x4()

    # print (str(change_base))

    change_base = mathutils.Matrix([
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, -1, 0, 0],
        [0, 0, 0, 1]])

    transform = bone.matrix_local.copy() 
    parentBone = bone.parent

    if parentBone:
        transform =  parentBone.matrix_local.inverted() * transform

    # test = parentBone.matrix_local * bone.matrix_local
    # test = bone.matrix_local.copy()
    print (bone.name)
    print (str(transform.transposed()))
    print (str((change_base * transform).transposed()))
    # print ("LocalToParent: \n" + str(transform.transposed()))
    # print ("LocalToWorld: \n" + str(bone.matrix_local.transposed()))
    # print (str(transform * mathutils.Vector([0, 0, 0, 1])))
    # if parentBone:
    #    print (str(parentBone.matrix_local * transform * mathutils.Vector([0, 0, 0, 1])))
    print('------------------------------------------------------\n')


    # transform = change_base * transform 

    # transform = transform.transposed()

    loc, quat, sca = transform.decompose()

    bone_data = {
        "parent": parent_id,
        "loc": loc,
        "rot": quat,
        "mat": transform,
        "name": bone.name
    }

    bone_array.append(bone_data)


    # print ("{:<32} ID: {:>4}  Parent: {:>4}  Mat: \n{} ".format(
    #         '-' * depth + bone.name,
    #         my_id,
    #         parent_id,
    #         str(transform.transposed())))

    # print ("{:<32} ID: {:>4}  Parent: {:>4}  Tran: {:40}  Rot: {:32}".format(
    #         '-' * depth + bone.name,
    #         my_id,
    #         parent_id,
    #         str(loc),
    #         str(quat)))

    for subnode in bone.children:
        ProcessBone(armature, subnode, bone_array, my_id, depth + 1)

def ProcessArmature(context, node):
    if (node.type != "ARMATURE"):
        return False
    
    armature = node.data

    if armature is None:
        return False

    pose_position = armature.pose_position
    armature.pose_position = 'REST'
    context.scene.update()

    bone_array = []
    for bone in armature.bones:
        if (not bone.parent):
            ProcessBone(armature, bone, bone_array, -1)

    armature.pose_position = pose_position
    context.scene.update()

    return {
        "name": node.name,
        "count": len(bone_array),
        "bones": bone_array
    }
    

def check_valid_selection(selection):
    if len(selection) != 1:
        return False
    if selection[0].type != "ARMATURE":
        return False
    return True


def FormatInt(i):
    return str(i)

def FormatFloat(f):
    if ((math.isinf(f)) or (math.isnan(f))):
        return "0.0"
    
    return str(f)

def FormatArg(text):
    if isinstance(text, int):
        return FormatInt(text)
    elif isinstance(text, float):
        return FormatFloat(text)
    return text

def FormatText(text, *args):
    formatted_args = [FormatArg(arg) for arg in args]
    return text.format(*formatted_args)

def FormatQuat(quat, prefix=''):
    return FormatText('{0}w="{1}" {0}x="{2}" {0}y="{3}" {0}z="{4}"',
        prefix,
        quat.w,
        quat.x,
        quat.y,
        quat.z)

def FormatVec3(vec3, prefix=''):
    return FormatText('{0}x="{1}" {0}y="{2}" {0}z="{3}"',
        prefix,
        vec3.x,
        vec3.y,
        vec3.z)

def FormatMat4(mat4, prefix=''):
    attr_str = ''
    for i in range(4):
        for j in range(4):
            attr_str += ' {}{}{}="{}" '.format(
                prefix, 
                i, j, 
                FormatArg(mat4[j][i]))

    return attr_str

def Write(file, text, *args):
    formatted_text = FormatText(text, *args)

    file.write(bytes(str(formatted_text), "UTF-8"))


def skeleton_write(file, skeleton):
    Write(file, 
        '<skeleton bone_count="{}" name="{}">\n',
        skeleton['count'],
        skeleton['name'])

    for bone in skeleton['bones']:
        Write(file, '    <bone {} {} {} parent="{}" name="{}"/>\n',
                FormatQuat(bone['rot'], 'rot_'),
                FormatVec3(bone['loc'], 'loc_'),
                FormatMat4(bone['mat'], 'mat_'),
                bone['parent'],
                bone['name'])
    
    Write(file, '</skeleton>\n')

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportSkelData(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_test.skel_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Skeleton"

    # ExportHelper mixin class uses this
    filename_ext = ".skel.xml"

    filter_glob = StringProperty(
            default="*.skel.xml",
            options={'HIDDEN'},
            )

    def execute(self, context):
        objects = bpy.context.selected_objects

        if not check_valid_selection(objects):
            self.report({'ERROR'}, "Must have an armature selected to export a skeleton")
            return {'CANCELLED'}
        
        skeleton = ProcessArmature(context, objects[0])

        file = open(self.filepath, "wb")
        skeleton_write(file, skeleton)
        file.close()
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportSkelData.bl_idname, text="JM Export Skel Operator")


def register():
    bpy.utils.register_class(ExportSkelData)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportSkelData)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_test.some_data('INVOKE_DEFAULT')
