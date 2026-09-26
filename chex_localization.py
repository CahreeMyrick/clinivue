"""Prompt localization using the official ChEX encoder and detector modules.

Text generation and training/evaluation modules are intentionally not loaded.
"""
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import torch
from torch import nn
from torchvision.ops import box_convert

ROOT = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = ROOT / 'models' / 'chex_stage3' / 'checkpoint_best.pth'


def boxes_to_original(boxes, image_size):
    """Undo ChEX's centered square crop; boxes are normalized cxcywh."""
    width, height = image_size
    side = min(width, height)
    left, top = (width - side) // 2, (height - side) // 2
    corners = box_convert(boxes, 'cxcywh', 'xyxy').clamp(0, 1) * side
    return corners + corners.new_tensor([left, top, left, top])


class CheXLocalizationService:
    def __init__(self, checkpoint=DEFAULT_CHECKPOINT, device='cpu', threshold=0.5):
        self.checkpoint = Path(checkpoint).expanduser()
        self.device = torch.device(device)
        if not 0 <= threshold <= 1:
            raise ValueError('ChEX threshold must be between 0 and 1.')
        self.threshold = threshold
        self.model = None

    def load(self):
        if not self.checkpoint.is_file():
            raise FileNotFoundError(
                f'ChEX checkpoint not found: {self.checkpoint}. Download the official '
                'stage-3 checkpoint (see README.md) and pass --chex-checkpoint PATH.'
            )
        source = str(ROOT / 'chex' / 'src')
        if source not in sys.path:
            sys.path.insert(0, source)
        from omegaconf import OmegaConf
        from model.img_encoder.chexzero_img_encoder import ChexzeroImageEncoder
        from model.txt_encoder.chexzero_txt_encoder import ChexzeroTextEncoder
        from model.detector.token_decoder_detector import TokenDetector

        # Official training checkpoints contain config and optimizer metadata.
        # Only load checkpoints from a trusted source.
        checkpoint = torch.load(self.checkpoint, map_location='cpu', weights_only=False)
        config = OmegaConf.create(checkpoint['config_dict'])
        if config.model_class != 'ChEX':
            raise ValueError('Expected a complete ChEX checkpoint.')
        model = nn.ModuleDict({
            'img_encoder': ChexzeroImageEncoder(config.img_encoder, config, load_pretrained=False),
            'txt_encoder': ChexzeroTextEncoder(config.txt_encoder, config, load_pretrained=False),
            'detector': TokenDetector(config.detector, config),
        })
        # Post-decoder and language-model weights only affect descriptions, not boxes.
        state = {key: value for key, value in checkpoint['state_dict'].items()
                 if key.split('.', 1)[0] in model}
        model.load_state_dict(state, strict=True)
        self.model = model.to(self.device).eval()
        return self

    @torch.inference_mode()
    def localize(self, image: Image.Image, prompt: str):
        return self.localize_many(image, [prompt])

    @torch.inference_mode()
    def localize_many(self, image: Image.Image, prompts):
        if self.model is None:
            raise RuntimeError('Call load() before localization.')
        if not prompts:
            return []
        import cv2
        side = min(image.size)
        left, top = (image.width - side) // 2, (image.height - side) // 2
        gray = np.asarray(image.convert('L'), dtype=np.float32) / 255.0
        gray = gray[top:top + side, left:left + side]
        gray = cv2.resize(gray, (224, 224), interpolation=cv2.INTER_LINEAR)
        pixels = torch.from_numpy((gray - 0.505) / 0.248).unsqueeze(0).to(self.device)
        encoded = self.model['img_encoder'](pixels)
        queries = self.model['txt_encoder'].encode_sentences(list(prompts))
        result = self.model['detector'](encoded_image=encoded, query_tokens=queries)
        if result.multiboxes is None or result.multiboxes_weights is None:
            raise ValueError('Expected the multi-region ChEX stage-3 detector.')
        boxes = boxes_to_original(result.multiboxes[0].cpu(), image.size)
        scores = result.multiboxes_weights[0].cpu()
        detections = []
        for label, prompt_boxes, prompt_scores in zip(prompts, boxes, scores):
            for box, score in zip(prompt_boxes.tolist(), prompt_scores.tolist()):
                if score >= self.threshold and box[2] > box[0] and box[3] > box[1]:
                    detections.append({'label': label, 'score': score, 'box': box})
        return detections
