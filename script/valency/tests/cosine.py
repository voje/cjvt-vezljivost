from valency.tfigf import TfIgf
from sklearn.metrics.pairwise import linear_kernel

texts = [
    "Testno besedilo za testiranje cosine similarity.",
    "Malo drugačno testno besedilo za testiranje cosine similarity.",
    "Malo spremenjen drugačen stavek, ki je podoben prejšnjemu."
    "An english sentence that has zero similarity with the former ones."
]

tf = TfIgf(texts)

fnames = tf.tfidf.get_feature_names()

print(fnames)

scores = linear_kernel(tf.matrix, tf.matrix)

print(scores)

for i in range(len(texts)):
    for j in range(i + 1, len(texts)):
        print("cosine_similarity({}, {}): {}".format(
            i, j, scores[i][j]
        ))
