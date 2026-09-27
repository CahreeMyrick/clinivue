# Clinivue

Install dependencies with Python 3.13 and uv:

```sh
uv sync
```

## ChEX checkpoint

Download the official [ChEX stage-3 archive](https://drive.google.com/file/d/1TFBOSV_jEdh2E6mBlv1qDlxJl9Wf9xZO/view).
It is approximately 10 GB; allow space for both the archive and extracted files.
Extract it and locate `checkpoint_best.pth` under its `checkpoints` directory.
Only use trusted checkpoints: the upstream training format requires Python pickle loading.

Run the combined example with the extracted checkpoint:

```sh
uv run python example_biomedclip.py --chex-checkpoint /path/to/checkpoint_best.pth
```

Alternatively put the checkpoint at `models/chex_stage3/checkpoint_best.pth` to
run without the checkpoint argument. Model files are ignored by Git.

To use another image and save the plot without opening a window:

```sh
uv run python example_biomedclip.py path/to/xray.png \
  --chex-checkpoint /path/to/checkpoint_best.pth --output result.png
```

The default image is `chest_xray.png`. BioMedCLIP's first run downloads its model
and tokenizer from Hugging Face. The example ranks concepts, excludes the normal
label from localization, and sends the top three remaining concepts to ChEX.

ChEX uses the official image encoder, text encoder, and multi-region detector,
loaded strictly from the complete checkpoint. No separate CheXzero download is
needed. Preprocessing uses the upstream centered square crop, 224-pixel resize,
and grayscale normalization; predicted boxes are mapped back to the original
image. CPU is the default; `--chex-device` also accepts `cuda` and `mps`.

`--chex-threshold` defaults to 0.5 and filters ChEX's region weights. These weights
and BioMedCLIP's cosine similarities are not disease probabilities. Empty results
are reported without substitute boxes. This integration performs localization;
it does not load ChEX's separate text-description generator.

Run adapter tests:

```sh
uv run python -m unittest discover -s tests
```

## Open-ended VLM entity extraction

`example_vlm.py` sends the image to a generative vision model and requests a
structured inventory of anatomy, findings, devices, and artifacts. Unlike
BioMedCLIP, it does not require a fixed candidate-label list. It preserves the full
image without cropping and requires no BioMedCLIP or ChEX checkpoints.

Use a vision-capable model already available on your server. For local Ollama,
the script uses its [compatible vision API](https://docs.ollama.com/api/openai-compatibility):

```sh
uv run python example_vlm.py chest_xray.png --model YOUR_VISION_MODEL
```

For a different compatible server:

```sh
export VLM_BASE_URL="https://your-server.example/v1"
export VLM_MODEL="your-vision-model"
# If authentication is required, set VLM_API_KEY in your shell.
uv run python example_vlm.py chest_xray.png
```

The endpoint must support image data URLs on `/chat/completions`. Running the
script sends the image to the selected endpoint. It does not start a server or
download model weights. You can also pass `--base-url`, `--model`, or
`--api-key-env NAME` directly. `.env` files are not automatically loaded.

Experiment with the prompt and preview the request without making an API call:

```sh
uv run python example_vlm.py --print-prompt > experiment_prompt.txt
uv run python example_vlm.py --model YOUR_VISION_MODEL \
  --prompt-file experiment_prompt.txt --question "Focus on visible devices and their locations." \
  --dry-run
uv run python example_vlm.py --model YOUR_VISION_MODEL \
  --question "Focus on visible devices and their locations." \
  --output outputs/vlm/devices.json
```

Keep the documented JSON structure when editing the prompt. `--json-mode`
enables the server's optional JSON response mode; omit it if unsupported.
`--max-tokens` controls the output budget (default 4096), `--timeout` controls the
request timeout, and `--max-side 1024` optionally downsizes the entire image while
preserving its aspect ratio. By default, the original resolution is sent.

Each result includes image dimensions/hash, model, endpoint, complete prompt,
raw API response, validated entities, and candidate localization prompts. Files
are saved under `outputs/vlm/` by default. Invalid or truncated model output is
saved with a `parse_error` and a nonzero exit status, so it can be inspected.

Entities distinguish present, absent, and uncertain observations, visible
evidence, possible interpretations, and qualitative certainty. These are model
outputs for exploration, not verified findings or an exhaustive inventory.
Candidate prompts include only present/uncertain findings and devices; they are
not bounding boxes and are not automatically sent to ChEX. Once ChEX weights
are available, the saved `candidate_localization_prompts` can be passed to
`CheXLocalizationService.localize_many(image, prompts)`.

## BioMedCLIP entity-matching experiment

To use BioMedCLIP directly, without an API server or ChEX checkpoint:

```sh
uv run python example_biomedclip_entities.py chest_xray.png
```

This scores 46 candidate descriptions across overall appearance, findings,
anatomy, devices, and view. It prints the top five per category and saves every
score and prompt to `outputs/biomedclip_entities.json`. BioMedCLIP is a
contrastive image/text model: it cannot answer an open-ended extraction prompt.
High-ranked candidates are image/text matches, not confirmed entities, and the
scores are not disease probabilities. Categories are ranked separately to make
comparison easier; there is no threshold that declares a finding present.

Supply your own inventory with `--candidates candidates.json`, for example:

```json
{
  "finding": ["pleural effusion", "pneumothorax", "lung opacity"],
  "device": ["chest tube", "cardiac pacemaker"]
}
```

Use `--top-k 10` to print more matches, `--output PATH` to save a separate run,
and `--device cpu|cuda|mps` to select a device. The model's own preprocessing is
used, matching `example_biomedclip.py`, with a text context length of 256.
