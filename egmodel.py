import json

import torch.nn.functional as F
from torch import Tensor
from transformers import AutoModel, AutoTokenizer
from ts.torch_handler.base_handler import BaseHandler


class ModelHandler(BaseHandler):
    def initialize(self, context):
        self.initialized = True
        self.tokenizer = AutoTokenizer.from_pretrained("thenlper/gte-base")
        self.model = AutoModel.from_pretrained("thenlper/gte-base")

    def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
        last_hidden = last_hidden_states.masked_fill(
            ~attention_mask[..., None].bool(), 0.0
        )
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

    def preprocess(self, data):
        text = data[0].get("data")
        if text is None:
            text = data[0].get("body")
        return text

    def inference(self, text):
        inputs = self.tokenizer(text, return_tensors="pt")
        outputs = self.model(**inputs)
        embedding = self.average_pool(
            outputs.last_hidden_state, inputs["attention_mask"]
        )
        embedding = F.normalize(embedding, p=2, dim=1)
        embedding_str = json.dumps(embedding.tolist()[0])
        return [embedding_str]

    def postprocess(self, inference_output):
        return inference_output
