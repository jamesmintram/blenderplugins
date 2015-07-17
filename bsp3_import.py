import bpy
from struct import *

bl_info = {
    "name": "Import Q3 BSP",
    "description": "Imports a Quake3 BSP",
    "author": "James Mintram",
    "version": (0, 1),
    "blender": (2, 75, 0),
    "category": "Import",
}

def load_bsp_header(file_data, file_position):
    bsp_header = Struct("4si") #Followed by 17 chunks
    chunk_size = bsp_header.size

    magic, version = bsp_header.unpack(file_data[file_position:file_position + chunk_size])
    file_position += chunk_size

    return (magic, version), file_position


def load_headers(file_data, file_position):
    bsp_chunk = Struct("ii") #Offset Length
    chunk_size = bsp_chunk.size

    chunk_headers = []
    for chunk in range(17):
        chunk_headers.append(bsp_chunk.unpack(file_data[file_position:file_position+chunk_size]))
        file_position += chunk_size

    return chunk_headers, file_position


def load_verts(file_data, headers, scale_factor):
    def vert_from_pack(vert_data):
        return (
                (vert_data[0] * scale_factor, vert_data[1] * scale_factor, vert_data[2] * scale_factor,), #XYZ
                (vert_data[3], vert_data[4],), #UV1
                (vert_data[5], vert_data[6],), #UV2
                (vert_data[7], vert_data[8], vert_data[9],), #Normal
                (vert_data[10], vert_data[11], vert_data[12], vert_data[13],), #RGBA
            )

    vert_offset, vert_length = headers[10]
    vert_chunk = Struct("3f2f2f3f4B") 
    vert_size = vert_chunk.size
    vert_count = int(vert_length / vert_size)

    

    print ("Found {} vertices".format(vert_count))

    vertices = []

    for current_vert_idx in range(vert_count):
        vert_file_position = vert_offset + current_vert_idx * vert_size
        current_vert = vert_chunk.unpack(file_data[vert_file_position : vert_file_position+vert_size])
        vertices.append(vert_from_pack(current_vert))

    return vertices

def load_indices(file_data, headers):    
    index_offset, index_length = headers[11]
    
    index_size = 4 #We can take liberties here
    index_count = int(index_length / index_size)
    index_chunk = Struct("{}i".format(index_count))

    return index_chunk.unpack(file_data[index_offset:index_offset+index_length])



def load_faces(file_data, headers, indices):
    def indices_from_face(face_data):
        base_vertex = face_data[3]
        base_index = face_data[5]
        index_count = face_data[6]

        faces_indices = [base_vertex + indices[base_index + current_index] 
                            for current_index in range(index_count)]

        #Split into lists of 3 - ie triangles
        faces = []
        for current_face_idx in range(0, len(faces_indices), 3):
            faces.append(faces_indices[current_face_idx:current_face_idx+3])

        return faces

    def face_from_pack(face_data):
        return (
                face_data[0],   #Texture
                indices_from_face(face_data)
            )

    face_offset, face_length = headers[13]
    face_chunk = Struct("iiiiiiii2i2i3f3f3f3f2i") 
    face_size = face_chunk.size
    face_count = int(face_length / face_size)

    faces = []

    for current_face_idx in range(face_count):
        face_file_position = face_offset + current_face_idx * face_size
        current_face = face_chunk.unpack(file_data[face_file_position : face_file_position+face_size])

        #Check we are a valid face (Could use a filter later)
        if current_face[2] != 1: continue #Only support meshes at the moment

        faces.append(face_from_pack(current_face))

    return faces

def vertex_stream(vertices, stream_id):
    for vertex in vertices:
        yield vertex[stream_id]

def create_mesh_from_data(mesh_name, bsp_verts, bsp_faces, scale_factor):
    # Create mesh and object
    me = bpy.data.meshes.new(mesh_name+'Mesh')
    ob = bpy.data.objects.new("LEVEL" + mesh_name, me)
    ob.show_name = True
    ob['scale_factor'] = scale_factor

    # Link object to scene
    bpy.context.scene.objects.link(ob)

    triangles = [triangle for triangle_list in vertex_stream(bsp_faces, 1) for triangle in triangle_list]

    # Verts Edges UVs?
    me.from_pydata(list(vertex_stream(bsp_verts, 0)), [], triangles)

    # Update mesh with new data
    me.update()
    return ob



def read_some_data(context, filepath, scale_factor):

    f = open(filepath, 'rb')
    data = f.read()
    f.close()

    # would normally load the data here
    bsp_header, file_position = load_bsp_header(data, 0)
    chunk_headers, file_position = load_headers(data, file_position)
    
    verts = load_verts(data, chunk_headers, scale_factor)
    indices = load_indices(data, chunk_headers)
    faces = load_faces(data, chunk_headers, indices)
    create_mesh_from_data("NewLevel", verts, faces, scale_factor)

    return {'FINISHED'}




# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import FloatProperty, StringProperty
from bpy.types import Operator


class ImportSomeData(Operator, ImportHelper):
    """Import a Quake 3 BSP level"""
    bl_idname = "import_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import a Quak3 BSP"

    # ImportHelper mixin class uses this
    filename_ext = ".bsp"

    filter_glob = StringProperty(
            default="*.bsp",
            options={'HIDDEN'},
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    scale_factor = FloatProperty(
            name="Scale factor",
            description="Scale Factor ",
            default=0.02,
            )

    def execute(self, context):
        return read_some_data(context, self.filepath, self.scale_factor)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="Text Import Operator")


def register():
    bpy.utils.register_class(ImportSomeData)
    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSomeData)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_test.some_data('INVOKE_DEFAULT')
