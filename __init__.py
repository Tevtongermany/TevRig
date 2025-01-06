import json
import os
import subprocess
import webbrowser
import bpy
import mathutils

bl_info = {
    "name": "Facial TevRIG",
    "author": "Tevtongermany",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "description": "Tool For importing Face Rig on default Fortnite rigs",
    "category": "Export",
}



def get_addon_directory():
    return os.path.dirname(os.path.realpath(__file__))

def get_json_files():
    json_dir = os.path.join(get_addon_directory(), 'facerig')

    try:
        files = [(f, f, "") for f in os.listdir(json_dir) if f.endswith('.json')]
        if not files:
            files.append(('None', 'No JSON files found', ''))
        return files
    except FileNotFoundError:
        return [('None', 'Directory not found', '')]


def combine_shape_keys(obj, new_shape_key_name, shape_key_data):
    basis = obj.data.shape_keys.key_blocks['Basis']
    new_shape = obj.shape_key_add(name=new_shape_key_name, from_mix=False)
    new_shape.interpolation = 'KEY_LINEAR'
    
    for key_name, value in shape_key_data.items():
        if key_name in obj.data.shape_keys.key_blocks:
            key_block = obj.data.shape_keys.key_blocks[key_name]
            for i in range(len(obj.data.vertices)):
                new_shape.data[i].co += (key_block.data[i].co - basis.data[i].co) * value
    
    # Move the new shape key above the old ones but below the Basis
    num_keys = len(obj.data.shape_keys.key_blocks)
    basis_index = obj.data.shape_keys.key_blocks.keys().index('Basis')
    new_shape_index = obj.active_shape_key_index
    while new_shape_index > basis_index + 1:
        obj.active_shape_key_index = new_shape_index
        bpy.ops.object.shape_key_move(type='UP')
        new_shape_index -= 1

def load_shape_key_combinations():
    shape_key_combinations = {}
    combination_file_path = os.path.join(get_addon_directory(),"3L.txt")
    with open(combination_file_path, 'r') as file:
        lines = file.readlines()
        
    current_key = None
    for line in lines:
        line = line.strip()
        if line.endswith(':'):
            current_key = line[:-1]
            shape_key_combinations[current_key] = {}
        elif current_key is not None and line:
            if ':' in line:
                try:
                    shape, value = line.split(':')
                    shape_key_combinations[current_key][shape.strip()] = float(value.strip())
                except ValueError:
                    print(f"Skipping invalid line: {line}")
    return shape_key_combinations

def is_metahuman(mesh:bpy.types.Mesh):
    if mesh.shape_keys.key_blocks.get("jawFwd"):
        return True
    return False

class Prop(bpy.types.PropertyGroup):
    json_file: bpy.props.EnumProperty(
        items=get_json_files(),
        name="JSON Files",
        description="Select a JSON file to import",
    )  # type: ignore
    license_code: bpy.props.StringProperty(
        name="License Code",
        description="Enter the license code",
    )# type: ignore

class childwithoutparent:
    def __init__(self, bone, Parent) -> None:
        self.bone = bone
        self.Parent = Parent

class PT_Main(bpy.types.Panel):
    bl_category = "TevRig"
    bl_label = "Tevtongermany's Rig"
    bl_region_type = 'UI'
    bl_space_type = 'VIEW_3D'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.facerigprop

        importbox = layout.box()
        licensebox = layout.box()

        importbox.label(text="Import", icon="LINKED")
        importbox.prop(props, "json_file")
        importbox.operator("edfs.import", text="Import FaceRig")
        importbox.operator("edfs.openfolder", text="Open Folder")

        licensebox.label(text="License", icon="HELP")
        licensebox.operator("edfs.open_license", text="License")

        links = layout.box()
        links.label(text="Links")
        links.operator("edfs.open_discord",text="Support Server")
        links.operator("edfs.open_kofi",text="Support me on Ko-Fi!!")


class OP_Import(bpy.types.Operator):
    bl_idname = "edfs.import"
    bl_label = "Import FaceRig"
    bl_description = "Imports the current selected FaceRig json"

    button_pressed = 0

    def execute(self, context):
        props = context.scene.facerigprop
        selected_file = props.json_file

        if selected_file == 'None':
            self.report({'WARNING'}, "No JSON file selected or no files available")
            return {'CANCELLED'}

        active = bpy.context.active_object

        if active is None:
            self.report({'ERROR_INVALID_INPUT'}, "Nothing Selected")
            return {'CANCELLED'}

        if active.type != "MESH":
            OP_Import.button_pressed += 1

            if OP_Import.button_pressed < 3:
                self.report({'ERROR_INVALID_INPUT'}, "Please Select a mesh instead of anything else!")
            elif OP_Import.button_pressed < 6:
                self.report({'ERROR_INVALID_INPUT'}, "Select a mesh instead of anything else!!!!")
            elif OP_Import.button_pressed < 9:
                self.report({'ERROR_INVALID_INPUT'}, "Brother Select a mesh instead of anything else")
            elif OP_Import.button_pressed < 12:
                self.report({'ERROR_INVALID_INPUT'}, "BRO READ SELECT A FUCKING MESH INSTEAD OF ANYTHING ELSE")
            else:
                self.report({'ERROR_INVALID_INPUT'}, "AHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")
                
            return {'CANCELLED'}

        # Reset button_pressed if a mesh is selected
        OP_Import.button_pressed = 0
        model: bpy.types.Object = bpy.data.objects.get(active.name_full)

        print("model name: " + model.name)
        bpy.context.window.cursor_set('WAIT')
        wm = bpy.context.window_manager

        json_dir = os.path.join(get_addon_directory(), 'facerig')
        filepath = os.path.join(json_dir, selected_file)

        with bpy.data.libraries.load(os.path.join(json_dir, selected_file[:-5] + ".blend")) as (data_from, data_to):
            for obj in data_from.objects:
                if not bpy.data.objects.get(obj):
                    data_to.objects.append(obj)

        json_filepath = filepath
        with open(json_filepath, "r") as f:
            Shapekey_data = json.load(f)

        if active.type == "MESH":
            mesh: bpy.types.Mesh = model.data

            armature: bpy.types.Armature = None
            armature_obj: bpy.types.Object = None
            for modifier in active.modifiers:
                if modifier.type == "ARMATURE":
                    armature = modifier.object
                    armature_obj = modifier.object
                    break

        BonesUsed = Shapekey_data["BonesWithShape"]
        shapkeyAmount = len(mesh.shape_keys.key_blocks)



        # Took me 2 hours to find this shit 😭😭🙏🙏
        bpy.context.view_layer.objects.active = armature_obj
        armature_obj.select_set(True)

        bpy.ops.object.mode_set(mode="EDIT")
        edit_bone: bpy.types.ArmatureEditBones = armature.data.edit_bones
        pose_bone: bpy.types.ArmatureEditBones = armature.pose.bones

        needs_parenting: list[childwithoutparent] = []


        wm.progress_begin(0, 3)
        finishedAmount = 0
        
        for bone in BonesUsed:
            
            bpy.ops.object.mode_set(mode="EDIT")
            bone_name = bone["boneName"]
            properties = bone["Properties"]
            bone_head = properties["boneHead"]
            bone_tail = properties["boneTail"]
            bone_Rotation = properties["boneRotation"]
            parent = properties["parent"]
            custom_shape = bone["CustomShape"]
            custom_shape_rotation = bone["CustomShapeRotation"]
            custom_shape_location = bone["CustomShapeLocation"]
            custom_shape_scale = bone["CustomShapeScale"]
            scale_to_bone_length = bone["ScaleToBoneLenght"]
            wireframe = bone["Wireframe"]
            color = bone["Color"]

            if edit_bone.get(bone_name) is not None:
                continue
            new_bone = edit_bone.new(bone_name)
            new_bone.head = bone_head
            new_bone.tail = bone_tail
            new_bone.roll = bone_Rotation
            new_bone.show_wire = wireframe

            new_childwithoutparent = childwithoutparent(new_bone.name, parent)
            needs_parenting.append(new_childwithoutparent)

            bpy.ops.object.mode_set(mode="POSE")

            new_posebone: bpy.types.PoseBone = pose_bone.get(bone_name)

            if custom_shape is not None:  # Can fail sometimes if the meshes dont get appended for some reason
                new_posebone.custom_shape = bpy.data.objects.get(custom_shape)
                new_posebone.custom_shape.rotation_euler = mathutils.Euler(custom_shape_rotation)
                new_posebone.custom_shape.location = mathutils.Vector(custom_shape_location)
                new_posebone.custom_shape.scale = mathutils.Vector(custom_shape_scale)
                new_posebone.use_custom_shape_bone_size = scale_to_bone_length
                new_posebone.custom_shape.show_wire = wireframe
                new_posebone.color.palette = color

            if bone["BoneConstrains"] is not None:
                for constrain in bone["BoneConstrains"]:
                    new_constrain: bpy.types.LimitLocationConstraint = new_posebone.constraints.new("LIMIT_LOCATION")
                    new_constrain.name = constrain["name"]
                    new_constrain.owner_space = constrain["owner_space"]
                    new_constrain.use_min_x = constrain["use_min_x"]
                    new_constrain.use_min_y = constrain["use_min_y"]
                    new_constrain.use_min_z = constrain["use_min_z"]
                    new_constrain.use_max_x = constrain["use_max_x"]
                    new_constrain.use_max_y = constrain["use_max_y"]
                    new_constrain.use_max_z = constrain["use_max_z"]
                    new_constrain.min_x = constrain["min_x"]
                    new_constrain.min_y = constrain["min_y"]
                    new_constrain.min_z = constrain["min_z"]
                    new_constrain.max_x = constrain["max_x"]
                    new_constrain.max_y = constrain["max_y"]
                    new_constrain.max_z = constrain["max_z"]
        wm.progress_update(1)
        bpy.ops.object.mode_set(mode="EDIT")

        for kids_needing_parents in needs_parenting:
            try:
                finishedAmount += 1
                wm.progress_update(finishedAmount)
                parent_bone = edit_bone.get(kids_needing_parents.Parent)
                child_bone = edit_bone.get(kids_needing_parents.bone)
                
                print(f"Processing: Parent={kids_needing_parents.Parent}, Child={kids_needing_parents.bone}")
                print(f"Resolved: Parent Bone={parent_bone}, Child Bone={child_bone}")
                
                if parent_bone is None:
                    print(f"Parent bone {kids_needing_parents.Parent} not found.")
                    continue
                
                if child_bone is None:
                    print(f"Child bone {kids_needing_parents.bone} not found.")
                    continue
                
                child_bone.parent = parent_bone
            except Exception as e:
                print(f"An error occurred: {e}")

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.objects.active = model

        model.select_set(True)
        shape_key_combinations = load_shape_key_combinations()

        if is_metahuman(mesh=mesh):
            for new_shape_key, data in shape_key_combinations.items():
                combine_shape_keys(model,new_shape_key, data)

        if mesh.shape_keys:
            for shapekey_info in Shapekey_data["ShapeKeys"]:
                shapekey_name = shapekey_info["ShapeKey"]
                if shapekey_name not in mesh.shape_keys.key_blocks:
                    continue
                shapekey = mesh.shape_keys.key_blocks[shapekey_name]

                if shapekey.id_data.animation_data is None:
                    shapekey.id_data.animation_data_create()

                fcurve = shapekey.id_data.animation_data.drivers.new(
                    data_path=f'key_blocks["{shapekey_name}"].value'
                )
                fcurve.driver.type = 'SCRIPTED'
                fcurve.driver.expression = shapekey_info["Expression"]
                for var_info in shapekey_info["Variables"]:
                    var = fcurve.driver.variables.new()
                    var.name = var_info["Variable"]
                    var.type = var_info["Type"]
                    for target_info in var_info["Targets"]:
                        target = var.targets[0]
                        target.id = armature_obj
                        target.data_path = target_info["DataPath"]
                        if var.type == 'TRANSFORMS':
                            target.bone_target = target_info["Bone"]
                            target.transform_type = target_info["TransformType"]
                            target.transform_space = target_info["TransformSpace"]
        bpy.context.window.cursor_set('DEFAULT')
        return {'FINISHED'}

class OP_OpenFolder(bpy.types.Operator):
    bl_idname = "edfs.openfolder"
    bl_label = "Open Folder"
    bl_description = "Open up the folder with the facerig json files"

    def execute(self, context):
        json_dir = os.path.join(get_addon_directory(), 'facerig')
        subprocess.Popen(fr'explorer /select,"{json_dir}"')
        return {'FINISHED'}

class OP_OpenLicense(bpy.types.Operator):
    bl_idname = "edfs.open_license"
    bl_label = "Open License"
    bl_description = "Open License for tev rig"

    def execute(self, context):
        webbrowser.open("https://github.com/Tevtongermany/TevRIG-License/blob/main/License.md")
        return {'FINISHED'}

class OP_Discord(bpy.types.Operator):

    bl_idname = "edfs.open_discord"
    bl_label = "Open Discord"
    bl_description = "Open Discord"

    def execute(self, context):
        webbrowser.open("https://discord.gg/RcERx28W96")
        return {'FINISHED'}
    
class OP_kofi(bpy.types.Operator):

    bl_idname = "edfs.open_kofi"
    bl_label = "Open ko-fi"
    bl_description = "Open ko-fi"

    def execute(self, context):
        webbrowser.open("https://ko-fi.com/tevtongermany")
        return {'FINISHED'}

operators = [PT_Main, OP_Import, Prop, OP_OpenFolder, OP_OpenLicense,OP_kofi,OP_Discord]
def register():
    for operator in operators:
        bpy.utils.register_class(operator)
    bpy.types.Scene.facerigprop = bpy.props.PointerProperty(type=Prop)

def unregister():
    for cls in operators:
        try:
            bpy.utils.unregister_class(cls)
        except:
            ...
    del bpy.types.Scene.facerigprop

if __name__ == "__main__":
    register()
