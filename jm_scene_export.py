import bpy
import json

bl_info = {
    "name": "Export JM's scene",
    "description": "Exports data from a Scene for use with JM's iOS project",
    "author": "James Mintram",
    "version": (0, 1),
    "blender": (2, 75, 0),
    "category": "Export",
}


output_objects =[   ("Cameras", "CAMERA",), 
                    ("Props", "PROP",)]


def get_custom_properties(obj):
    return dict([(K, obj[K]) for K in obj.keys() if K not in '_RNA_UI'])


def get_tagged_objects(object_tag):
    return [obj for obj in bpy.data.objects if obj.name.find(object_tag) == 0]


def get_tagged_object_data(object_tag):
    objects = get_tagged_objects(object_tag)

    object_data = [{"name": current_object.name,
                    "location": current_object.location[:], 
                    "rotation": current_object.rotation_euler[:],
                    "properties": get_custom_properties(current_object)
                    } for current_object in objects]

    return object_data  


def write_some_data(context, filepath, use_some_setting):
    print("Exporting to file")
    
    output_data = {}

    for current_object_type in output_objects:
        output_data[current_object_type[0]] = get_tagged_object_data(current_object_type[1])

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump( output_data, f, sort_keys=True, indent=4, )
    
    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportSomeData(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Some Data"

    # ExportHelper mixin class uses this
    filename_ext = ".json.txt"

    filter_glob = StringProperty(
            default="*.json.txt",
            options={'HIDDEN'},
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting = BoolProperty(
            name="Example Boolean",
            description="Example Tooltip",
            default=True,
            )

    type = EnumProperty(
            name="Target",
            description="Whether you are outputting to a file or Database",
            items=(('OPT_A', "File", "Output to a local file"),
                   ('OPT_B', "Database", "Output to a local database")),
            default='OPT_A',
            )

    def execute(self, context):
        return write_some_data(context, self.filepath, self.use_setting)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportSomeData.bl_idname, text="JM Export Operator")


def register():
    bpy.utils.register_class(ExportSomeData)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportSomeData)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_test.some_data('INVOKE_DEFAULT')