import torch
import matplotlib.pyplot as plt

from PIL import Image, ImageDraw, ImageFont
from open_clip import create_model_from_pretrained, get_tokenizer


# ============================================================
# BioMedCLIP
# ============================================================

BIOMEDCLIP_ID = (
    "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
)

biomed_model, biomed_preprocess = create_model_from_pretrained(
    BIOMEDCLIP_ID
)

biomed_tokenizer = get_tokenizer(BIOMEDCLIP_ID)

biomed_model.eval()


LABELS = [
    "atelectasis",
    "cardiomegaly",
    "consolidation",
    "pulmonary edema",
    "pleural effusion",
    "pneumonia",
    "pneumothorax",
    "normal chest X-ray",
]


def biomedclip_rank(image: Image.Image):
    prompts = [
        f"chest X-ray showing {label}"
        for label in LABELS
    ]

    image_tensor = biomed_preprocess(
        image
    ).unsqueeze(0)

    text_tokens = biomed_tokenizer(prompts)

    with torch.no_grad():
        image_features = biomed_model.encode_image(
            image_tensor
        )

        text_features = biomed_model.encode_text(
            text_tokens
        )

    image_features /= image_features.norm(
        dim=-1,
        keepdim=True
    )

    text_features /= text_features.norm(
        dim=-1,
        keepdim=True
    )

    scores = (
        image_features
        @ text_features.T
    ).squeeze(0)

    ranked = sorted(
        zip(
            LABELS,
            scores.tolist()
        ),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked


# ============================================================
# ChEX Adapter
# ============================================================

class CheXLocalizationService:
    """
    Adapter around the ChEX repository.

    Expected output format:

    [
        {
            "label": "pleural effusion",
            "score": 0.88,
            "box": [x1, y1, x2, y2],
            "description": "..."
        }
    ]
    """

    def __init__(self):
        self.model = None

    def load(self):
        """
        Load ChEX checkpoint and configuration here.

        The exact code depends on the ChEX repo's internal
        Hydra/model-loading configuration.
        """
        raise NotImplementedError(
            "Connect this adapter to the ChEX repository model loader."
        )

    def localize(
        self,
        image: Image.Image,
        prompt: str
    ):
        """
        Run:

            image + textual prompt
                    ↓
                   ChEX
                    ↓
            boxes + descriptions
        """

        raise NotImplementedError(
            "Connect this method to ChEX inference."
        )


# ============================================================
# Visualization
# ============================================================

def draw_detections(
    image: Image.Image,
    detections
):
    output = image.copy()

    draw = ImageDraw.Draw(output)

    for detection in detections:
        x1, y1, x2, y2 = detection["box"]

        label = detection["label"]
        score = detection["score"]

        draw.rectangle(
            [x1, y1, x2, y2],
            width=4
        )

        draw.text(
            (x1, max(0, y1 - 20)),
            f"{label} {score:.2f}"
        )

    return output


# ============================================================
# Main
# ============================================================

image_path = "xray.png"

image = Image.open(
    image_path
).convert("RGB")


# ------------------------------------------------------------
# 1. BioMedCLIP concept ranking
# ------------------------------------------------------------

ranked = biomedclip_rank(image)

print("\nBioMedCLIP concept ranking:\n")

for label, score in ranked:
    print(
        f"{label:25s} {score:.4f}"
    )


# ------------------------------------------------------------
# 2. Select concepts worth localizing
# ------------------------------------------------------------

top_k = ranked[:3]

candidate_prompts = [
    label
    for label, score in top_k
]

print("\nCandidate concepts for ChEX:")

for concept in candidate_prompts:
    print(f"- {concept}")


# ------------------------------------------------------------
# 3. ChEX localization
# ------------------------------------------------------------

chex = CheXLocalizationService()

# After connecting the ChEX repo:
#
# chex.load()
#
# detections = []
#
# for concept in candidate_prompts:
#     result = chex.localize(
#         image=image,
#         prompt=concept
#     )
#
#     detections.extend(result)


# Temporary mock result so the rest of the pipeline works.
# REMOVE once ChEX inference is connected.

detections = [
    {
        "label": "pleural effusion",
        "score": 0.86,
        "box": [300, 350, 500, 550],
        "description": (
            "Localized region consistent with "
            "pleural fluid accumulation."
        ),
    }
]


# ------------------------------------------------------------
# 4. Draw localized findings
# ------------------------------------------------------------

visualized = draw_detections(
    image,
    detections
)


# ------------------------------------------------------------
# 5. Show combined BioMedCLIP + ChEX result
# ------------------------------------------------------------

fig, axes = plt.subplots(
    1,
    2,
    figsize=(14, 7)
)


axes[0].imshow(image)
axes[0].axis("off")

axes[0].set_title(
    "Original chest X-ray"
)


axes[1].imshow(visualized)
axes[1].axis("off")

axes[1].set_title(
    "Localized findings"
)


plt.tight_layout()
plt.show()
