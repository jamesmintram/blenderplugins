"""
    TODO:
        Use already loaded material if it exists
        Import Normals
"""
import bpy
from struct import *
import os
import bmesh

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
    """
        float[3]    position    Vertex position.
        float[2][2] texcoord    Vertex texture coordinates. 0=surface, 1=lightmap.
        float[3]    normal      Vertex normal.
        ubyte[4]    color       Vertex color. RGBA.
    """


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
    """
        int index
    """
    index_offset, index_length = headers[11]
    
    index_size = 4 #We can take liberties here
    index_count = int(index_length / index_size)
    index_chunk = Struct("{}i".format(index_count))

    return index_chunk.unpack(file_data[index_offset:index_offset+index_length])


def load_materials(file_data, headers, base_path):
    """
        string[64]  name        Texture name.
        int         flags       Surface flags.
        int         contents    Content flags.
    """


    def load_material_texture(texture_file):
        filename = os.path.join(base_path, texture_file + ".jpg")
        try:
            img = bpy.data.images.load(str(filename))
            cTex = bpy.data.textures.new('ColorTex', type = 'IMAGE')
            cTex.image = img
            return cTex
        except:
            print ("Cannot load image {}".format(filename))
        return None


    def material_from_pack(material):
        """ 
            Extract just the data we want from the full chunk
        """
        texture_file_name = material[0].decode("utf-8").replace('\x00', '').strip()
        return (
            texture_file_name,
            load_material_texture(texture_file_name)
        )
    texture_offset, texture_length = headers[1]
    texture_chunk = Struct("64sii") 
    texture_size = texture_chunk.size
    texture_count = int(texture_length / texture_size)

    textures = []
    for current_texture_idx in range(texture_count):
        texture_file_position = texture_offset + current_texture_idx * texture_size
        packed_texture = texture_chunk.unpack(file_data[texture_file_position : texture_file_position+texture_size])
        current_texture = material_from_pack(packed_texture)
        textures.append(current_texture)
    
    return textures


def load_faces(file_data, headers, indices):
    """
        int         texture     Texture index.
        int         effect      Index into lump 12 (Effects), or -1.
        int         type        Face type. 1=polygon, 2=patch, 3=mesh, 4=billboard
        int         vertex      Index of first vertex.
        int         n_vertexes  Number of vertices.
        int         meshvert    Index of first meshvert.
        int         n_meshverts Number of meshverts.
        int         lm_index    Lightmap index.
        int[2]      lm_start    Corner of this face's lightmap image in lightmap.
        int[2]      lm_size     Size of this face's lightmap image in lightmap.
        float[3]    lm_origin   World space origin of lightmap.
        float[2][3] lm_vecs     World space lightmap s and t unit vectors.
        float[3]    normal      Surface normal.
        int[2]      size        Patch dimensions.
    """


    def swap_winding(indices):
        return (indices[0], indices[2], indices[1])
    

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
        """ 
            Extract just the data we want from the full chunk
        """
        triangle_list = indices_from_face(face_data)
        return [(face_data[0], triangles,) for triangles in triangle_list]

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

        new_faces = face_from_pack(current_face)
        faces.extend(new_faces)

    return faces


def apply_uvs(mesh, bsp_verts):
    """
        Apply the UVs available in the BSP data to a Blender mesh
    """

    mesh.uv_textures.new("UVs")
    bm = bmesh.new()
    bm.from_mesh(mesh)

    if hasattr(bm.faces, "ensure_lookup_table"): 
        bm.faces.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv[0]

    for face_idx, current_face in enumerate(bm.faces):
        current_face.loops[0][uv_layer].uv = bsp_verts[current_face.loops[0].vert.index][1]
        current_face.loops[1][uv_layer].uv = bsp_verts[current_face.loops[1].vert.index][1]
        current_face.loops[2][uv_layer].uv = bsp_verts[current_face.loops[2].vert.index][1]
    
    bm.to_mesh(mesh)


def create_mesh_from_data(mesh_name, bsp_verts, bsp_faces, materials, scale_factor):
    """
        Creates a blender mesh from the raw data loaded from a BSP - and the materials
        created from the BSP.
    """


    def vertex_stream(vertices, stream_id):
        for vertex in vertices:
            yield vertex[stream_id]

    # Create mesh and object
    me = bpy.data.meshes.new(mesh_name+'Mesh')
    ob = bpy.data.objects.new("LEVEL" + mesh_name, me)
    ob.show_name = True

    # Link object to scene
    bpy.context.scene.objects.link(ob)
    
    # Create the vertex data
    face_list = list(vertex_stream(bsp_faces, 1))
    mesh_verts = list(vertex_stream(bsp_verts, 0))

    me.from_pydata(mesh_verts, [], face_list)

    # Update mesh with new data
    me.update()
    apply_uvs(me, bsp_verts)

    # Add materials to mesh
    for cmaterial in materials:
        me.materials.append(cmaterial)

    # Apply material indexes to mesh faces
    face_materials = list(vertex_stream(bsp_faces, 0))

    for polygon_idx, current_polygon in enumerate(me.polygons):
        current_polygon.material_index = face_materials[polygon_idx]

    # Add additional properties to the new object
    ob['scale_factor'] = scale_factor

    return ob


def create_materials_from_data(textures):
    """
        Create all of the materials used by the BSP level.
    """

    materials = []

    #Set colour to incremenet from 0 - 8
    colour_inc = 1.0 / len(textures)
    colour = 0

    for current_material in textures:
        mat = bpy.data.materials.new(current_material[0])
        mat.diffuse_color = (0, colour, 0,)
        mat.diffuse_shader = 'LAMBERT' 
        mat.diffuse_intensity = 1.0 
        mat.specular_color = (1, 1, 1,)
        mat.specular_shader = 'COOKTORR'
        mat.specular_intensity = 0.5
        mat.alpha = 1
        mat.ambient = 1
        mat.use_shadeless = True

        mtex = mat.texture_slots.add()
        mtex.texture = current_material[1]
        mtex.texture_coords = 'UV'
        mtex.use_map_color_diffuse = True 

        materials.append(mat)
        colour += colour_inc
        
    return materials


def read_some_data(context, filepath, scale_factor):

    f = open(filepath, 'rb')
    data = f.read()
    f.close()

    # would normally load the data here
    bsp_header, file_position = load_bsp_header(data, 0)
    chunk_headers, file_position = load_headers(data, file_position)
    
    # Load all the data from the BSP file
    verts = load_verts(data, chunk_headers, scale_factor)
    indices = load_indices(data, chunk_headers)
    faces = load_faces(data, chunk_headers, indices)
    textures = load_materials(data, chunk_headers, os.path.dirname(filepath))

    # Create our blender objects
    materials = create_materials_from_data (textures)
    create_mesh_from_data("NewLevel", verts, faces, materials, scale_factor)

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import FloatProperty, StringProperty
from bpy.types import Operator


class ImportSomeData(Operator, ImportHelper):
    """Import a Quake 3 BSP level"""
    bl_idname = "import_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import a Quake3 BSP"

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
    self.layout.operator(ImportSomeData.bl_idname, text="Quake 3 BSP Import")


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
