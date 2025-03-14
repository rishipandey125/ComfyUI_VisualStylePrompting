import comfy
import torch

from .utils.attention_functions import VisualStyleProcessor
from .utils.cond_functions import cat_cond


class ApplyVisualStyle:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "reference_latent": ("LATENT",),
                "reference_cond": ("CONDITIONING",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "enabled": ("BOOLEAN", {"default": True}),
                "denoise": ("FLOAT", {"default": 1., "min": 0., "max": 1., "step": 1e-2}),
                "adain_q": ("BOOLEAN", {"default": True}),
                "adain_k": ("BOOLEAN", {"default": True}),
                "adain_v": ("BOOLEAN", {"default": False}),
                "skip_output_layers": ("INT", {"default": 24, "min": 0, "max": 72, "step": 1}),
            },
            "optional": {
                "init_image": ("IMAGE",),
            }
        }

    CATEGORY = "VisualStylePrompting/apply"
    RETURN_TYPES = ("MODEL", "CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("model", "positive", "negative", "latents")

    FUNCTION = "apply_visual_style_prompt"

    def apply_visual_style_prompt(
        self,
        model: comfy.model_patcher.ModelPatcher,
        clip,
        reference_latent,
        reference_cond,
        positive,
        negative,
        enabled,
        denoise,
        adain_q,
        adain_k,
        adain_v,
        skip_output_layers=0

    ):

    
        reference_samples = reference_latent["samples"]

        block_num = 0
        for n, m in model.model.diffusion_model.named_modules():
            if m.__class__.__name__ == "CrossAttention":
                is_self_attn = "attn1" in n  # Only swap self-attention layers
                is_output_block = "output_blocks" in n

                # explicitly only activate clearly output_blocks from skip_output_layers onwards
                is_enabled = is_self_attn and is_output_block and (block_num >= skip_output_layers)
                if is_output_block: 
                    block_num += 1

                if is_enabled:
                    print(n)
                    processor = VisualStyleProcessor(m, enabled=True, adain_queries=adain_q, adain_keys=adain_k, adain_values=adain_v)
                    m.forward = processor


        positive_cat = cat_cond(clip, reference_cond, positive)
        negative_cat = cat_cond(clip, negative, negative)

        latents = torch.zeros_like(reference_samples) #oh this is because the first one has to be the reference 
        latents = torch.cat([latents] * 2)
        latents[0] = reference_samples

        denoise_mask = torch.ones_like(latents)[:, :1, ...] * denoise

        denoise_mask[0] = 0.0

        return (model, positive_cat, negative_cat, {"samples": latents, "noise_mask": denoise_mask})

NODE_CLASS_MAPPINGS = {
    "ApplyVisualStyle": ApplyVisualStyle,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApplyVisualStyle": "Apply Visual Style Prompting",
}