import json
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoTokenizer, AutoModel


def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


tokenizer = AutoTokenizer.from_pretrained("thenlper/gte-base")
model = AutoModel.from_pretrained("thenlper/gte-base")


def generate_embedding(text: str) -> str:
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    embedding = average_pool(outputs.last_hidden_state, inputs["attention_mask"])
    embedding = F.normalize(embedding, p=2, dim=1)
    embedding_str = json.dumps(embedding.tolist()[0])
    return embedding_str
