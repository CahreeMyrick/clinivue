"""Rank a configurable inventory of chest X-ray concepts with BioMedCLIP.

This contrastive model scores supplied text; it does not generate observations
or establish that an entity is present. Scores are cosine similarities.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps
import torch
import torch.nn.functional as F
from open_clip import create_model_from_pretrained, get_tokenizer

MODEL_ID = 'hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224'
CONCEPTS = {
    'overall': ['normal chest X-ray', 'abnormal chest X-ray'],
    'finding': [
        'atelectasis', 'cardiomegaly', 'airspace consolidation', 'pulmonary edema',
        'pleural effusion', 'pneumonia', 'pneumothorax', 'lung opacity',
        'pulmonary nodule', 'lung mass', 'interstitial lung opacities',
        'emphysema', 'hyperinflation', 'pulmonary fibrosis', 'pleural thickening',
        'calcified granuloma', 'hilar enlargement', 'widened mediastinum',
        'elevated hemidiaphragm', 'rib fracture', 'scoliosis',
        'aortic calcification', 'hiatal hernia', 'subcutaneous emphysema',
    ],
    'anatomy': [
        'lungs', 'heart', 'mediastinum', 'trachea', 'pulmonary hila',
        'diaphragm', 'costophrenic angles', 'ribs', 'clavicles', 'thoracic spine',
    ],
    'device': [
        'endotracheal tube', 'enteric tube', 'central venous catheter',
        'chest tube', 'cardiac pacemaker', 'sternotomy wires',
        'prosthetic heart valve', 'ECG electrodes',
    ],
    'view': ['frontal chest X-ray', 'lateral chest X-ray'],
}


def load_candidates(path=None):
    groups = json.loads(path.read_text()) if path else CONCEPTS
    if not isinstance(groups, dict) or not groups:
        raise ValueError('Candidates must be a JSON object mapping categories to nonempty lists of strings.')
    candidates = []
    for category, labels in groups.items():
        if not isinstance(labels, list) or not labels or not all(isinstance(s, str) and s.strip() for s in labels):
            raise ValueError(f'Invalid candidate list for {category!r}.')
        for label in dict.fromkeys(labels):
            prompt = label if category in {'overall', 'view'} else f'chest X-ray showing {label}'
            candidates.append({'category': category, 'entity': label, 'prompt': prompt})
    return candidates


@torch.inference_mode()
def rank_entities(image, candidates, device='cpu', batch_size=16):
    model, preprocess = create_model_from_pretrained(MODEL_ID)
    model = model.to(device).eval()
    tokenizer = get_tokenizer(MODEL_ID)
    image_features = F.normalize(model.encode_image(preprocess(image).unsqueeze(0).to(device)), dim=-1)
    scores = []
    for offset in range(0, len(candidates), batch_size):
        tokens = tokenizer([c['prompt'] for c in candidates[offset:offset + batch_size]], context_length=256)
        text_features = F.normalize(model.encode_text(tokens.to(device)), dim=-1)
        scores.extend((image_features @ text_features.T).squeeze(0).cpu().tolist())
    return sorted([{**candidate, 'cosine_similarity': score}
                   for candidate, score in zip(candidates, scores)],
                  key=lambda row: row['cosine_similarity'], reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', type=Path, default=Path(__file__).with_name('chest_xray.png'))
    parser.add_argument('--candidates', type=Path, help='JSON mapping categories to lists of entity names.')
    parser.add_argument('--output', type=Path, default=Path('outputs/biomedclip_entities.json'))
    parser.add_argument('--device', choices=['cpu', 'cuda', 'mps'], default='cpu')
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--top-k', type=int, default=5, help='Number printed per category; all scores are saved.')
    args = parser.parse_args()
    if args.batch_size <= 0 or args.top_k <= 0:
        parser.error('batch-size and top-k must be positive.')
    try:
        candidates = load_candidates(args.candidates)
        with Image.open(args.image) as source:
            image = ImageOps.exif_transpose(source).convert('RGB')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    ranked = rank_entities(image, candidates, args.device, args.batch_size)
    groups = {category: [row for row in ranked if row['category'] == category]
              for category in dict.fromkeys(row['category'] for row in candidates)}
    result = {
        'model': MODEL_ID,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'image': str(args.image.resolve()),
        'image_sha256': hashlib.sha256(args.image.read_bytes()).hexdigest(),
        'image_size': list(image.size),
        'context_length': 256,
        'interpretation': 'Ranked text-image matches, not confirmed findings or disease probabilities. '
                          'Limited to the supplied candidate inventory; no localization or text generation.',
        'rankings_by_category': groups,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['interpretation'])
    for category, rows in groups.items():
        print(f'\n{category.upper()} — top {min(args.top_k, len(rows))} of {len(rows)} candidates')
        for row in rows[:args.top_k]:
            print(f"  {row['cosine_similarity']:.4f}  {row['entity']}")
    print(f'\nSaved all {len(ranked)} candidate scores to {args.output}')


if __name__ == '__main__':
    main()
