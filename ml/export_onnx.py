"""Export all-MiniLM-L6-v2 to a committed ONNX artifact for RAM-cheap inference.

Run once as a dev tool (needs torch + transformers, which are NOT production deps):

    python -m ml.export_onnx

Writes ``ml/artifacts/onnx/model.onnx`` (the transformer, dynamically int8-quantized)
and ``ml/artifacts/onnx/tokenizer.json`` (the WordPiece tokenizer). At inference the
backend loads these through ``onnxruntime`` + ``tokenizers`` instead of pulling in
torch/sentence-transformers and downloading the model live from HuggingFace Hub — the
path that OOM-kills Render's 512MB free tier (see ml/features.py._embed).

The exported model outputs raw ``last_hidden_state``; mean pooling + L2 normalization
are reapplied at inference to reproduce sentence-transformers' embeddings exactly. This
script prints a cosine parity check against sentence-transformers and refuses to ship a
quantized model whose embeddings drift past QUANT_COSINE_MIN, falling back to fp32.
"""

import shutil
import tempfile
from pathlib import Path

import numpy as np

from ml.common import ARTIFACT_DIR, SBERT_MODEL_NAME

ONNX_DIR = ARTIFACT_DIR / "onnx"
MODEL_PATH = ONNX_DIR / "model.onnx"
TOKENIZER_PATH = ONNX_DIR / "tokenizer.json"

MAX_SEQ_LENGTH = 256  # sentence_bert_config.json for this model
OPSET = 17
QUANT_COSINE_MIN = 0.99  # ship int8 only if it stays this close to fp32/torch

# A few representative strings spanning the kinds of text _embed() sees.
PARITY_TEXTS = [
    "senior software engineer with 8 years of python and fastapi experience",
    "job title: data scientist. requirements: python, sql, machine learning",
    "graphic and brand designer skilled in figma, illustrator and typography",
    "backend developer building low-latency payment services in java and go",
    "",
]


def _mean_pool(last_hidden: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    """Attention-mask-weighted mean over tokens, then L2 normalize — the exact
    pooling sentence-transformers applies for all-MiniLM-L6-v2."""
    mask = attention_mask[..., None].astype(np.float32)
    summed = (last_hidden * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), 1e-9, None)
    pooled = summed / counts
    norm = np.linalg.norm(pooled, axis=1, keepdims=True)
    return pooled / np.clip(norm, 1e-12, None)


def _export_fp32(fp32_path: Path) -> None:
    import torch
    from transformers import AutoModel

    model = AutoModel.from_pretrained(SBERT_MODEL_NAME)
    model.eval()

    class Wrapper(torch.nn.Module):
        """Expose only last_hidden_state so the ONNX graph has one clean output."""

        def __init__(self, backbone):
            super().__init__()
            self.backbone = backbone

        def forward(self, input_ids, attention_mask, token_type_ids):
            out = self.backbone(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
            )
            return out.last_hidden_state

    wrapped = Wrapper(model)
    # Dummy batch of 2 short sequences so dynamic axes are inferred, not baked.
    dummy = {
        "input_ids": torch.ones(2, 8, dtype=torch.long),
        "attention_mask": torch.ones(2, 8, dtype=torch.long),
        "token_type_ids": torch.zeros(2, 8, dtype=torch.long),
    }
    dynamic_axes = {
        "input_ids": {0: "batch", 1: "sequence"},
        "attention_mask": {0: "batch", 1: "sequence"},
        "token_type_ids": {0: "batch", 1: "sequence"},
        "last_hidden_state": {0: "batch", 1: "sequence"},
    }
    with torch.no_grad():
        torch.onnx.export(
            wrapped,
            (dummy["input_ids"], dummy["attention_mask"], dummy["token_type_ids"]),
            str(fp32_path),
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["last_hidden_state"],
            dynamic_axes=dynamic_axes,
            opset_version=OPSET,
            do_constant_folding=True,
            dynamo=False,
        )


def _onnx_embed(session, tokenizer, texts: list[str]) -> np.ndarray:
    rows = []
    for text in texts:
        enc = tokenizer.encode(text.strip().lower())
        ids = np.array([enc.ids], dtype=np.int64)
        mask = np.array([enc.attention_mask], dtype=np.int64)
        types = np.zeros_like(ids)
        (hidden,) = session.run(
            ["last_hidden_state"],
            {"input_ids": ids, "attention_mask": mask, "token_type_ids": types},
        )
        rows.append(_mean_pool(hidden, mask)[0])
    return np.vstack(rows)


def _reference_embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    sbert = SentenceTransformer(SBERT_MODEL_NAME, device="cpu")
    return sbert.encode(
        [t.strip().lower() for t in texts],
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def _cosines(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.array([float(np.dot(x, y)) for x, y in zip(a, b)])


def _load_tokenizer():
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(TOKENIZER_PATH))
    tok.enable_truncation(max_length=MAX_SEQ_LENGTH)
    return tok


def main() -> None:
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from onnxruntime.quantization import QuantType, quantize_dynamic

    ONNX_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Ship the tokenizer that matches the model's preprocessing exactly.
    src_tok = hf_hub_download(SBERT_MODEL_NAME, "tokenizer.json")
    shutil.copyfile(src_tok, TOKENIZER_PATH)
    print(f"tokenizer -> {TOKENIZER_PATH}")

    # 2. Export fp32, then dynamic int8 quantize.
    with tempfile.TemporaryDirectory() as tmp:
        fp32_path = Path(tmp) / "model_fp32.onnx"
        quant_path = Path(tmp) / "model_int8.onnx"
        print("exporting fp32 ONNX (needs torch/transformers)...")
        _export_fp32(fp32_path)
        print("quantizing (dynamic int8)...")
        quantize_dynamic(
            str(fp32_path), str(quant_path), weight_type=QuantType.QInt8
        )

        tokenizer = _load_tokenizer()
        ref = _reference_embed(PARITY_TEXTS)

        candidates = [("int8", quant_path), ("fp32", fp32_path)]
        chosen = None
        for tag, path in candidates:
            sess = ort.InferenceSession(
                str(path), providers=["CPUExecutionProvider"]
            )
            cos = _cosines(_onnx_embed(sess, tokenizer, PARITY_TEXTS), ref)
            size_mb = path.stat().st_size / 1e6
            print(f"{tag}: {size_mb:.1f}MB  cosine min={cos.min():.5f} "
                  f"mean={cos.mean():.5f}")
            if tag == "int8" and cos.min() >= QUANT_COSINE_MIN:
                chosen = (tag, path)
                break
            if tag == "fp32":
                chosen = (tag, path)

        tag, path = chosen
        shutil.copyfile(path, MODEL_PATH)
        print(f"\nshipping {tag} model -> {MODEL_PATH} "
              f"({MODEL_PATH.stat().st_size / 1e6:.1f}MB)")


if __name__ == "__main__":
    main()
