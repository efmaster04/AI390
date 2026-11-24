"""Small auditable Okapi BM25 and reciprocal rank fusion implementations."""
from collections import Counter
import math
import re
import unicodedata


def tokenize(text):
    text = unicodedata.normalize("NFC", text).replace("İ", "i").replace("I", "ı").lower()
    return re.findall(r"[^\W_]+", text, re.UNICODE)


class BM25:
    def __init__(self, texts, k1=1.5, b=0.75):
        self.counts = [Counter(tokenize(t)) for t in texts]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.avg = sum(self.lengths)/len(self.lengths) if self.lengths else 1
        df = Counter(t for c in self.counts for t in c)
        n = len(texts)
        self.idf = {t: math.log(1+(n-v+0.5)/(v+0.5)) for t, v in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query):
        terms = set(tokenize(query))
        return [sum(self.idf.get(t, 0)*counts.get(t, 0)*(self.k1+1) /
                    (counts.get(t, 0)+self.k1*(1-self.b+self.b*length/(self.avg or 1)))
                    for t in terms) for counts, length in zip(self.counts, self.lengths)]


def reciprocal_rank_fusion(rankings, constant=60):
    if constant <= 0:
        raise ValueError("RRF constant must be positive")
    scores = Counter()
    for ranking in rankings:
        if len(ranking) != len(set(ranking)):
            raise ValueError("Ranking contains duplicate IDs")
        for rank, item in enumerate(ranking, 1):
            scores[item] += 1/(constant+rank)
    return sorted(scores, key=lambda item: (-scores[item], item)), dict(scores)
