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
