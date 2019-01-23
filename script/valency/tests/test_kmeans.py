# Also need scipy.
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


def run():
    besedila = [
        "Lastovka leti nad dvoriščem.",
        "Žerjavi letijo na jug.",
        "Divje gosi letijo v klinu.",
        "Letalo leti nad puščavo.",
        "Krogle letijo od vseh strani.",
        "Ure z njo so naglo letele.",
        "Čas leti.",
        "Dijak je letel iz šole.",
        "Kadar je razburjena, ji vse leti iz rok."
    ]

    words = []
    for b in besedila:
        for x in b.split(" "):
            words.append(x)
    unique_words = sorted(list(set(words)))
    for w in unique_words:
        print(w)
    print(len(unique_words))

    tfidf = TfidfVectorizer()
    res = tfidf.fit_transform(besedila)

    return tfidf

    out_k = 4
    model = KMeans(n_clusters=out_k)
    model.fit(res)

    labeled = {}
    for i in range(len(besedila)):
        li = model.labels_[i]
        if li not in labeled:
            labeled[li] = []
        labeled[li].append(besedila[i])
    for k, e in labeled.items():
        for b in e:
            print("{} - {}".format(k, b))
    return model


if __name__ == "__main__":
    run()
