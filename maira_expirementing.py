from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor


MODEL_ID = "microsoft/maira-2"


# ---------------------------------------------------------
# Simple vocabulary-based entity extraction.
# Replace this later with a medical NER / ontology linker.
# ---------------------------------------------------------

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
        """
        Generate a chest X-ray report with grounding information.

        Expected approximate output:

        [
            (
                "There is a small right pleural effusion.",
                [(x1, y1, x2, y2)]
            ),
            (
                "No pneumothorax.",
                None
            )
        ]
        """

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
            get_grounding=True,
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
        """
        Ask MAIRA-2 to localize a specific phrase.

        Example:

            phrase = "Pleural effusion"

        Expected approximate output:

            (
                "Pleural effusion.",
                [(x1, y1, x2, y2)]
            )
        """

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
    """
    Extract simple medical entities from a generated finding.

    This is intentionally simple so you can see the pipeline clearly.
    """

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
    """
    Convert MAIRA-2 output into a cleaner structure.
    """

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

        print(
            f"Text: {result['text']}"
        )

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


def main():
    # Change this to your chest X-ray image.
    image_path = "chest_xray.png"

    pipeline = MairaPipeline()

    # -----------------------------------------------------
    # Step 1:
    # Generate a grounded radiology report.
    # -----------------------------------------------------

    grounded_report = pipeline.generate_grounded_report(
        image_path=image_path,
        indication="",
        technique="",
        comparison="",
    )

    print("\nRaw MAIRA-2 output:")
    print(grounded_report)

    # -----------------------------------------------------
    # Step 2:
    # Convert generated findings into structured entities.
    # -----------------------------------------------------

    structured_results = build_structured_findings(
        grounded_report
    )

    print_results(
        structured_results
    )

    # -----------------------------------------------------
    # Step 3:
    # Optionally ground every detected abnormality again.
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("PHRASE GROUNDING")
    print("=" * 70)

    unique_findings = set()

    for result in structured_results:
        for finding in result["entities"]["findings"]:
            unique_findings.add(finding)

    for finding in sorted(unique_findings):
        print(
            f"\nGrounding phrase: {finding}"
        )

        grounding_result = pipeline.ground_phrase(
            image_path=image_path,
            phrase=finding,
        )

        print(
            grounding_result
        )


if __name__ == "__main__":
    main()
