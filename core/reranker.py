# core/reranker.py
from typing import List, Tuple
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

class BgeReranker:
    def __init__(self, model_dir: str, device: str = None, batch_size: int = 4):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if batch_size < 1:
            raise ValueError("batch_size 必须至少为 1")
        self.device = device
        self.batch_size = batch_size
        # ★ 同 embedder：保留权重路径，让"精排是否真加载"可被报告自证
        self.model_dir = model_dir
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device)
        self.model.eval()

    @torch.no_grad()
    def rerank(self, query: str, pairs: List[Tuple[str, str]]) -> List[Tuple[str, float]]:
        """对候选做交叉编码精排。

        Args:
            query: 用户问题
            pairs: [(chunk_id, 正文)] —— ★ 第一个元素是 **id**，不是正文。

        Returns:
            [(chunk_id, score)]，按分数**降序**。

        ★ 这里曾有个会静默毁掉精排的 bug：
          初版返回的是 (passage_text, score)，而 `core/pipeline.py` 的契约是
          (doc_id, score)。后果是下游拿到"正文当 id"去查文档，
          `doc_lookup(正文)` 必然返回空串 —— 于是：
            ① 引用溯源显示空片段
            ② 评测时 rerank 档的 doc_id 与 gold_ids 对不上，
               消融表里 +Reranker 那一档的指标会莫名其妙地掉
          而且**不会报错**，只是结果悄悄错掉。
          排序本身是对的（按 score 降序），所以"看起来能用"—— 这才是它危险的地方。
        """
        if not pairs:
            return []
        scored = []
        for offset in range(0, len(pairs), self.batch_size):
            batch = pairs[offset:offset + self.batch_size]
            doc_ids = [doc_id for doc_id, _ in batch]
            texts_p = [text for _, text in batch]
            enc = self.tokenizer(
                [query] * len(batch), texts_p,
                padding=True, truncation=True, return_tensors="pt"
            ).to(self.device)
            scores = self.model(**enc).logits.squeeze(-1).cpu().numpy()
            scored.extend(zip(doc_ids, scores.tolist(), strict=True))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored
