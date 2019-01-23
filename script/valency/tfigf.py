from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


class TfIgf:
    def __init__(self, texts):
        # Text is is an array of strins
        # strins should contain stemmed tokens
        self.tfidf = TfidfVectorizer()
        self.matrix = self.tfidf.fit_transform(texts)

    def to_string(self):
        retstr = (
            "array: {}"
            "matrix: {}"
        ).format(
            self.tfidf.get_feature_names(),
            self.matrix
        )
        return retstr

    def overlaps(self, v1, v2):
        matches = np.dot(v1.T, v2).diagonal()
        return np.count_nonzero(matches)

    def compare(self, idx1, idx2, score=None):
        if score is None:
            score = self.overlaps
        v1 = self.matrix[idx1]
        v2 = self.matrix[idx2]
        return score(v1, v2)


if __name__ == "__main__":
    texts = [
        "one two three four",
        "one four",
        "three four"
    ]
    tf = TfIgf(texts)
    print(tf.compare(2, 1))
