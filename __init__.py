bl_info = {
    "name": "Remove Background",
    "author": "tintwotin",
    "version": (1, 0),
    "blender": (3, 40, 0),
    "location": "Sequencer > Strip > Remove Background",
    "description": "Removes Background of a VSE strip",
    "warning": "",
    "doc_url": "",
    "category": "Sequencer",
}


import importlib.util
import bpy, sys, subprocess, os
from PIL import Image
import site

app_path = site.USER_SITE
if app_path not in sys.path:
    sys.path.append(app_path)
pybin = sys.executable
try:
    subprocess.call([pybin, "-m", "ensurepip"])
except ImportError:
    pass


class OPERATOR_OT_RemoveBackgroundOperator(bpy.types.Operator):
    """Remove the background from a VSE strip and import the resulting images as a new strip in the original scene"""

    bl_idname = "vse.remove_background"
    bl_label = "Remove Background"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.space_data.type == "SEQUENCE_EDITOR"

    def execute(self, context):
        # Get the VSE strip that you want to copy
        strip = context.scene.sequence_editor.active_strip
        # bpy.ops.sequencer.select_all(action='DESELECT')
        # strip.select = True

        # Skip the strip if it's a sound strip
        if strip.type == "SOUND":
            self.report(
                {"ERROR"}, "Can only remove background from movie or image strips"
            )
            return {"CANCELLED"}
        # Create a new scene and set it as the active scene
        new_scene = bpy.data.scenes.new("Export Scene")
        context.window.scene = new_scene

        # Add a sequencer to the new scene
        new_scene.sequence_editor_create()

        # Add the strip to the new scene
        if strip.type == "MOVIE":
            new_strip = new_scene.sequence_editor.sequences.new_movie(
                name=strip.name,
                filepath=bpy.path.abspath(strip.filepath),
                channel=strip.channel,
                frame_start=int(strip.frame_start),
            )
            new_strip.frame_final_start = int(strip.frame_final_start)
            new_strip.frame_final_end = int(strip.frame_final_end)
            new_strip.frame_offset_start = int(strip.frame_offset_start)
            new_strip.frame_offset_end = int(strip.frame_offset_end)
        elif strip.type == "IMAGE":
            # Assume it's an image strip
            new_strip = new_scene.sequence_editor.sequences.new_image(
                name=strip.name,
                filepath=bpy.path.abspath(strip.filepath),
                channel=strip.channel,
                frame_start=int(strip.frame_start),
            )
            new_strip.frame_final_start = int(strip.frame_final_start)
            new_strip.frame_final_end = int(strip.frame_final_end)
            new_strip.frame_offset_start = int(strip.frame_offset_start)
            new_strip.frame_offset_end = int(strip.frame_offset_end)
        else:
            return {"CANCELLED"}
        # Set the frame range for the new scene to match the strip
        new_scene.frame_start = int(strip.frame_final_start)
        new_scene.frame_end = int(strip.frame_final_end)

        # Set the output settings for the scene
        output_path = os.path.dirname(os.path.abspath(strip.filepath))
        folder_name = os.path.basename(strip.filepath)
        output_path = output_path + "/" + folder_name + "_image_sequence/"
        context.scene.render.filepath = output_path
        context.scene.render.image_settings.file_format = "PNG"

        # Render the scene
        msg = "Saving images to disk."
        self.report({"INFO"}, msg)
        bpy.ops.render.render(animation=True)

        # Install rembg - if not installed
        try:
            if importlib.util.find_spec("rembg[gpu]") is None:
                subprocess.check_call([pybin, "-m", "pip", "install", "rembg[gpu]"])
        except Exception:
            print("Unable to install the rembg[gpu] library")
            return {"CANCELLED"}
        from rembg import remove
        from PIL import Image
        import time

        files = []

        # Remove the background from all images in the image sequence
        for i in range(int(strip.frame_start), int(strip.frame_final_end) + 1):
            filepath = "{}{:04d}.png".format(output_path, i)
            file_name = "{:04d}.png".format(i)
            msg = str("{:04d}".format(i) + "/" + str(int(strip.frame_final_end)))
            self.report({"INFO"}, msg)
            try:
                input = Image.open(filepath)
                output = remove(input)
                output.save(filepath)
                files.append(file_name)
            except Exception:
                pass
        # Close the new scene
        bpy.ops.scene.delete()

        # Add the images with the removed backgrounds as a new image strip in the original scene
        filepath = "{}{:04d}.png".format(output_path, i)

        image_strip = bpy.context.scene.sequence_editor.sequences.new_image(
            name="Removed_Background_" + folder_name,
            filepath=filepath,
            channel=strip.channel + 1,
            frame_start=int(strip.frame_final_start),
        )
        # Add images of the sequence
        for f in files:
            image_strip.elements.append(f)

        image_strip.frame_final_duration = strip.frame_final_duration
        bpy.ops.sequencer.refresh_all()
        return {"FINISHED"}


def menu_append(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(
        OPERATOR_OT_RemoveBackgroundOperator.bl_idname, icon="ASSET_MANAGER"
    )


def register():
    bpy.utils.register_class(OPERATOR_OT_RemoveBackgroundOperator)
    bpy.types.SEQUENCER_MT_strip.append(menu_append)


def unregister():
    bpy.utils.unregister_class(OPERATOR_OT_RemoveBackgroundOperator)
    bpy.types.SEQUENCER_MT_strip.remove(menu_append)


if __name__ == "__main__":
    register()
