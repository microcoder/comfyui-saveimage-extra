import os
import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import numpy as np
from comfy.comfy_types import IO, InputTypeDict
from comfy.cli_args import args
import folder_paths
from inspect import cleandoc


class CombineExtraDataNode:
    """
    Combine parameters into a JSON string
    """

    DESCRIPTION = cleandoc(__doc__ or "")
    CATEGORY = "image"

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "optional": {
                "model_name": (IO.ANY, {}),
                "prompt": (IO.STRING, {"forceInput": True}),
                "seed": (IO.INT, {"forceInput": True}),
                "steps": (IO.INT, {"forceInput": True}),
                "cfg": (IO.FLOAT, {"forceInput": True}),
            }
        }

    RETURN_TYPES = (IO.STRING,)
    FUNCTION = "combine"


    def combine(self, **kwargs):
        data = {k: v for k, v in kwargs.items() if v is not None}  # Фильтруем None и оставляем только известные ключи (опционально)
        return (json.dumps(data, ensure_ascii=False),)  # return from the node as STRING


class SaveImageExtraNode:
    """
    Saves the input images with PNG metadata to your ComfyUI output directory
    """

    DESCRIPTION = cleandoc(__doc__ or "")
    CATEGORY = "image"
    SEARCH_ALIASES = ["save", "save image", "export image", "output image", "write image", "download"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."}),
                "extradata": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    def save_images(self, images, filename_prefix="ComfyUI", extradata="", prompt=None, extra_pnginfo=None):
        
        filename_prefix += self.prefix_append
        
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
            filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0]
        )
        
        results = list()

        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                
                # if prompt is not None:
                #     metadata.add_text("prompt", json.dumps(prompt))
                
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                
                if extradata.strip():
                    try:
                        _extradata = json.loads(extradata)

                        if isinstance(_extradata, dict):
                            for key, value in _extradata.items():
                                # If value is string, save as is
                                # Else — serialize to JSON (for numbers, bool, null)
                                if isinstance(value, str):
                                    metadata.add_text(key, value)
                                else:
                                    metadata.add_text(key, json.dumps(value, ensure_ascii=False))
                        else:
                            # If JSON — not object (example, str или collection), save as is
                            metadata.add_text('extradata', extradata)
                    except json.JSONDecodeError:
                        # Если это не JSON — сохраняем всю строку под одним ключом
                        metadata.add_text('extradata', extradata)

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}.png"

            img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })

            counter += 1

        return { "ui": { "images": results } }



NODE_CLASS_MAPPINGS = {
    "CombineExtraDataNode": CombineExtraDataNode,
    "SaveImageExtraNode": SaveImageExtraNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineExtraDataNode": "Combine Extra Data",
    "SaveImageExtraNode": "Save Image Extra",
}
