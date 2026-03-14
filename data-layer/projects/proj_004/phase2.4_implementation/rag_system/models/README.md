# Models Directory

## Why models are not in git

Model files (bert-base-uncased) are **not tracked in git** because:
- Total size: ~440MB (pytorch_model.bin + model.safetensors)
- Git is not designed for large binary files
- Would slow down clone/pull operations significantly

## How to download models

### Option 1: Manual Download (Recommended)
Download from HuggingFace: https://huggingface.co/bert-base-uncased/tree/main

Required files:
```
models/bert-base-uncased/
├── config.json
├── tokenizer.json
├── vocab.txt
├── model.safetensors (or pytorch_model.bin)
```

### Option 2: Auto-download (First Run)
The code will automatically download models on first run if not present:
```python
from transformers import AutoModel, AutoTokenizer

model = AutoModel.from_pretrained("bert-base-uncased")
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
```

## Current Setup

- Model: `bert-base-uncased`
- Embedding dimension: 768
- Provider: HuggingFace Transformers
- Usage: Local embedding service (no API cost)

## Alternative: Use API-based Embedding

If you prefer not to download models, modify `core/retrieval.py`:
```python
# Use Zhipu API instead
embedding_service = EmbeddingService(
    api_key="your-api-key",
    model="embedding-3",
    provider="zhipu"
)
```