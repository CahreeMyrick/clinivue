from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests
import torch
import matplotlib.pyplot as plt
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor


MODEL_ID = "microsoft/maira-2"


FINDINGS = [
    "pleural effusion",
    "pneumothorax",
    "atelectasis",
    "consolidation",
    "opacity",
    "cardiomegaly",
    "pulmonary edema",
    "edema",
    "infiltrate",
    "fracture",
]

ANATOMY = [
    "left lung",
    "right lung",
    "left lower lobe",
    "right lower lobe",
    "left upper lobe",
    "right upper lobe",
    "cardiac silhouette",
    "pleural space",
    "mediastinum",
]

LATERALITY = [
    "left",
    "right",
    "bilateral",
]

SEVERITY = [
    "trace",
    "small",
    "mild",
    "moderate",
    "large",
    "severe",
]


class MairaPipeline:
    def __init__(self, model_id: str = MODEL_ID):
        self.device = self._get_device()

        print(f"Using device: {self.device}")
        print(f"Loading model: {model_id}")

        self.processor = AutoProcessor.from_pretrained(
            model_id,
            trust_remote_code=True,
            use_fast=True
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
        )

        self.model = self.model.eval().to(self.device)

    @staticmethod
    def _get_device() -> torch.device:
        if torch.cuda.is_available():
            return torch.device("cuda")

        if torch.backends.mps.is_available():
            return torch.device("mps")

        return torch.device("cpu")

    @staticmethod
    def load_image(image_path: str | Path) -> Image.Image:
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image does not exist: {image_path}"
            )

        return Image.open(image_path).convert("RGB")

    def generate_grounded_report(
        self,
        image_path: str | Path,
        indication: str = "",
        technique: str = "",
        comparison: str = "",
    ) -> list[Any]:

        image = self.load_image(image_path)

        inputs = self.processor.format_and_preprocess_reporting_input(
            current_frontal=image,
            current_lateral=None,
            prior_frontal=None,
            indication=indication,
            technique=technique,
            comparison=comparison,
            prior_report=None,
            return_tensors="pt",
            get_grounding=False,
        )

        inputs = inputs.to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=450,
                use_cache=True,
            )

        prompt_length = inputs["input_ids"].shape[-1]

        generated_ids = output_ids[0][prompt_length:]

        decoded = self.processor.decode(
            generated_ids,
            skip_special_tokens=True,
        )

        parsed = (
            self.processor
            .convert_output_to_plaintext_or_grounded_sequence(
                decoded
            )
        )

        return parsed

    def ground_phrase(
        self,
        image_path: str | Path,
        phrase: str,
    ) -> Any:

        image = self.load_image(image_path)

        inputs = (
            self.processor
            .format_and_preprocess_phrase_grounding_input(
                frontal_image=image,
                phrase=phrase,
                return_tensors="pt",
            )
        )

        inputs = inputs.to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=150,
                use_cache=True,
            )

        prompt_length = inputs["input_ids"].shape[-1]

        generated_ids = output_ids[0][prompt_length:]

        decoded = self.processor.decode(
            generated_ids,
            skip_special_tokens=True,
        )

        return (
            self.processor
            .convert_output_to_plaintext_or_grounded_sequence(
                decoded
            )
        )


def contains_term(text: str, term: str) -> bool:
    pattern = rf"\b{re.escape(term.lower())}\b"

    return bool(
        re.search(
            pattern,
            text.lower(),
        )
    )


def extract_entities(text: str) -> dict[str, list[str]]:
    entities = {
        "findings": [],
        "anatomy": [],
        "laterality": [],
        "severity": [],
    }

    for term in FINDINGS:
        if contains_term(text, term):
            entities["findings"].append(term)

    for term in ANATOMY:
        if contains_term(text, term):
            entities["anatomy"].append(term)

    for term in LATERALITY:
        if contains_term(text, term):
            entities["laterality"].append(term)

    for term in SEVERITY:
        if contains_term(text, term):
            entities["severity"].append(term)

    return entities


def build_structured_findings(
    grounded_report: list[Any],
) -> list[dict[str, Any]]:

    results = []

    for item in grounded_report:

        if isinstance(item, tuple) and len(item) == 2:
            text, boxes = item
        else:
            text = str(item)
            boxes = None

        entities = extract_entities(text)

        result = {
            "text": text,
            "entities": entities,
            "boxes": boxes or [],
        }

        results.append(result)

    return results


def print_results(
    structured_results: list[dict[str, Any]],
) -> None:

    print("\n" + "=" * 70)
    print("STRUCTURED MAIRA-2 OUTPUT")
    print("=" * 70)

    for index, result in enumerate(
        structured_results,
        start=1,
    ):
        print(f"\nFinding {index}")
        print("-" * 40)

        print(f"Text: {result['text']}")

        print(
            f"Findings: "
            f"{result['entities']['findings']}"
        )

        print(
            f"Anatomy: "
            f"{result['entities']['anatomy']}"
        )

        print(
            f"Laterality: "
            f"{result['entities']['laterality']}"
        )

        print(
            f"Severity: "
            f"{result['entities']['severity']}"
        )

        print(
            f"Bounding boxes: "
            f"{result['boxes']}"
        )


def get_sample_data() -> dict[str, Image.Image | str]:
    """
    Download chest X-rays from IU-Xray.
    """

    frontal_image_url = (
        "https://openi.nlm.nih.gov/imgs/512/145/145/"
        "CXR145_IM-0290-1001.png"
    )

    lateral_image_url = (
        "https://openi.nlm.nih.gov/imgs/512/145/145/"
        "CXR145_IM-0290-2001.png"
    )

    def download_and_open(url: str) -> Image.Image:
        response = requests.get(
            url,
            headers={"User-Agent": "MAIRA-2"},
            stream=True,
        )

        response.raise_for_status()

        return Image.open("xray.png").convert("RGB")

    frontal_image = download_and_open(
        frontal_image_url
    )

    lateral_image = download_and_open(
        lateral_image_url
    )

    sample_data = {
        "frontal": frontal_image,
        "lateral": lateral_image,
        "indication": "None.",
        "comparison": "None.",
        "technique": "PA view of the chest.",
        "phrase": "None.",
    }

    return sample_data


def main():

    sample_data = get_sample_data()

    # -----------------------------------------------------
    # Load MAIRA-2
    # -----------------------------------------------------

    print("Loading MAIRA-2...")

    processor = AutoProcessor.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        use_fast=True
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
    )

    # -----------------------------------------------------
    # Select device
    # -----------------------------------------------------

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    print(f"Using device: {device}")

    model = model.eval()
    model = model.to(device)

    # -----------------------------------------------------
    # Prepare input
    # -----------------------------------------------------

    processed_inputs = (
        processor.format_and_preprocess_reporting_input(
            current_frontal=sample_data["frontal"],
            current_lateral=None,
            prior_frontal=None,
            indication=sample_data["indication"],
            technique=sample_data["technique"],
            comparison=sample_data["comparison"],
            prior_report=None,
            return_tensors="pt",
            get_grounding=False,
        )
    )

    processed_inputs = processed_inputs.to(device)

    # -----------------------------------------------------
    # Generate report
    # -----------------------------------------------------

    print("Generating report...")

    with torch.no_grad():

        output_decoding = model.generate(
            **processed_inputs,
            max_new_tokens=300,
            use_cache=True,
        )

    # -----------------------------------------------------
    # Decode output
    # -----------------------------------------------------

    prompt_length = (
        processed_inputs["input_ids"].shape[-1]
    )

    decoded_text = processor.decode(
        output_decoding[0][prompt_length:],
        skip_special_tokens=True,
    )

    decoded_text = decoded_text.lstrip()

    # -----------------------------------------------------
    # Convert MAIRA-2 output
    # -----------------------------------------------------

    prediction = (
        processor
        .convert_output_to_plaintext_or_grounded_sequence(
            decoded_text
        )
    )

    print("\nParsed prediction:")
    print(prediction)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    # Display the first image on the left axis
    axes[0].imshow(sample_data["frontal"])
    axes[0].axis('off')  # Hide pixel coordinate axes
    axes[0].set_title('First Image')

    # Display the second image on the right axis
    axes[1].imshow(sample_data["lateral"])
    axes[1].axis('off')
    axes[1].set_title('Second Image')

    # Show the side-by-side plot
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()