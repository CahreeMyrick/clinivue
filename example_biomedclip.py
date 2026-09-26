import argparse
from pathlib import Path

import torch
import matplotlib.pyplot as plt

from PIL import Image, ImageDraw
from open_clip import create_model_from_pretrained, get_tokenizer


# ============================================================
# BioMedCLIP
# ============================================================

BIOMEDCLIP_ID = (
    "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
)



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
    biomed_model, biomed_preprocess = create_model_from_pretrained(BIOMEDCLIP_ID)
    biomed_tokenizer = get_tokenizer(BIOMEDCLIP_ID)
    biomed_model.eval()

    prompts = [
        f"chest X-ray showing {label}"
        for label in LABELS
    ]

    image_tensor = biomed_preprocess(
        image
    ).unsqueeze(0)

    text_tokens = biomed_tokenizer(prompts, context_length=256)

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

from chex_localization import CheXLocalizationService, DEFAULT_CHECKPOINT


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

def main():
    parser = argparse.ArgumentParser(description="Rank chest X-ray concepts with BioMedCLIP.")
    parser.add_argument("image", nargs="?", type=Path,
                        default=Path(__file__).with_name("chest_xray.png"))
    parser.add_argument("--output", type=Path, help="Save the plot instead of opening a window.")
    parser.add_argument("--chex-checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--chex-device", default="cpu", choices=["cpu", "cuda", "mps"])
    parser.add_argument("--chex-threshold", type=float, default=0.5)
    args = parser.parse_args()
    if not args.chex_checkpoint.expanduser().is_file():
        parser.error(f"ChEX checkpoint not found: {args.chex_checkpoint}. "
                     "See README.md and pass --chex-checkpoint PATH.")
    image_path = args.image

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

    top_k = [(label, score) for label, score in ranked
             if label != "normal chest X-ray"][:3]

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

    chex = CheXLocalizationService(
        args.chex_checkpoint, args.chex_device, args.chex_threshold
    ).load()
    detections = chex.localize_many(image, candidate_prompts)
    print(f"\nChEX returned {len(detections)} regions:")
    for detection in detections:
        print(f"{detection['label']:25s} {detection['score']:.4f} {detection['box']}")
    if not detections:
        print("No regions exceeded the ChEX region-weight threshold.")

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
        "ChEX localized regions"
    )


    plt.tight_layout()
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"\nSaved plot to {args.output}")
    else:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
