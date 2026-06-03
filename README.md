# NFT Gen 🎨

Automated NFT metadata generator for generative art collections. Creates trait combinations, rarity scores, and metadata compliant with OpenSea standards.

## Features

- Trait combination engine with rarity weighting
- OpenSea-compatible metadata JSON
- Rarity score calculation
- Collection statistics
- Batch generation with seed control

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python generate.py --collection my_nft --count 100
```

## GPU Requirements

| Component | GPU | VRAM | Notes |
|-----------|-----|------|-------|
| Metadata generation | None | — | CPU only |
