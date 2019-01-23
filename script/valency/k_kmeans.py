from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from nltk.cluster.kmeans import KMeansClusterer
from sklearn.metrics import silhouette_score
import nltk
from collections import Counter


class KmeansClass():
    def __init__(self, vallex):
        self.vallex = vallex

    def bisection_kmeans(self, hw_lemma):
        self.kmeans_wrapper(hw_lemma, algorithm=bkm, db_coll_name="km_bkm")

    def normal_kmeans(self, hw_lemma):
        self.kmeans_wrapper(
            hw_lemma, algorithm=k_means, db_coll_name="km_normal")

    def kmeans_wrapper(self, hw_lemma, algorithm, db_coll_name):
        db_entries = list(self.vallex.db[db_coll_name].find({
            "headword": hw_lemma
        }))
        entry = self.vallex.entries[hw_lemma]
        if len(db_entries) == len(entry.raw_frames):
            return None  # already in db, skip
        ssj_ids = []
        sentences = []
        for rf in entry.raw_frames:
            ssj_ids.append(rf.tids[0])
            # print(self.vallex.get_sentence(rf.tids[0]))
            # print(rf.to_string())
            deep_members = [hw_lemma]
            for dr in rf.deep:
                deep_members.append(self.vallex.get_token(dr["dep"])["lemma"])
            expanded_dm = []
            for dm in deep_members:
                exp = self.vallex.slownet_interface.root_chain(dm)
                expanded_dm.extend(exp)
            # expanded_dm is a bow that represents this sentence
            sentences.append(" ".join(list(set(expanded_dm))))
        # use silhouette score to determine best number of senses
        try:
            labels = silhouette_wrapper(sentences, algorithm)
        except ValueError as e:
            print(e)
            return None
        n_unique_labels = len(set(labels))
        for i in range(len(labels)):
            key = {"headword": hw_lemma, "ssj_id": ssj_ids[i]}
            db_entry = {
                "headword": hw_lemma,
                "ssj_id": ssj_ids[i],
                "sense_id": "{}_({})".format(labels[i], n_unique_labels)
            }
            self.vallex.db[db_coll_name].update(key, db_entry, upsert=True)
        return None


def k_means(sentences, n_clusters):
    # sklearn k-means with euclidean distance
    tfidf = TfidfVectorizer()
    tfidf_ed = tfidf.fit_transform(sentences)
    model = KMeans(n_clusters=n_clusters)
    labels = model.fit_predict(tfidf_ed)

    if len(set(labels)) == 1:
        return (labels, 0)

    sscore = silhouette_score(
        tfidf_ed.toarray(), labels, metric=nltk.cluster.util.cosine_distance)
    return (labels, sscore)  # numpy array


def nltk_kmeans(sentences, n_clusters):
    # nltk's k-means
    # (slower than sklearn's k-means)
    tfidf = TfidfVectorizer()
    tfidf_ed = tfidf.fit_transform(sentences)
    kclusterer = KMeansClusterer(
        n_clusters,
        distance=nltk.cluster.util.cosine_distance,
        repeats=25
    )
    labels = kclusterer.cluster(
        tfidf_ed.toarray(), assign_clusters=True)
    return labels  # list


def silhouette_wrapper(sentences, algorithm):
    results = []
    for n_clusters in range(1, 11):  # [1, 10]
        if n_clusters > (len(sentences) - 1):
            continue
        labels, sscore = algorithm(sentences, n_clusters=n_clusters)
        results.append({
            "labels": labels,
            "sscore": sscore,
        })
    best_score = -2
    best_labels = []
    for res in results:
        if res["sscore"] > best_score:
            best_score = res["sscore"]
            best_labels = res["labels"]
    return best_labels


def bkm(sentences, n_clusters, n_trials=50):
    # bisecting k-means implemented as described in Steinbach 2000
    # input sentences should be tokenized and stemmed

    # safety check:
    if n_clusters >= len(sentences):
        labels = [0 for i in range(len(sentences))]
        return (labels, -1)

    """
    # nltk's kmeans occasionally crashes
    # going to use more nltk one
    kclusterer = KMeansClusterer(
        2,
        distance=nltk.cluster.util.cosine_distance,
        repeats=25,
        avoid_empty_clusters=True
    )
    """
    model = KMeans(n_clusters=2)

    tfidf = TfidfVectorizer()
    tfidf_ed = tfidf.fit_transform(sentences)
    A = tfidf_ed.toarray()
    labels = [0 for i in range(tfidf_ed.shape[0])]
    stuck_counter = {
        "n_labels": 0,
        "count": 0
    }
    while len(set(labels)) < n_clusters:
        n_labels = len(set(labels))
        if n_labels == stuck_counter["n_labels"]:
            stuck_counter["count"] += 1
            if stuck_counter["count"] >= 20:
                return (labels, 0)
        else:
            stuck_counter["n_labels"] = n_labels
        largest_clstr_lab = Counter(labels).most_common(1)  # [(id, len)]
        lc_idx = [
            i for i, e in enumerate(labels) if e == largest_clstr_lab[0][0]
        ]
        # Mask out largets cluster columns.
        Aex = A[lc_idx, :]

        ex_labels = model.fit_predict(Aex)
        """
        ex_labels = kclusterer.cluster(
            Aex, assign_clusters=True)
        """
        # Run over labels, selected by lc_idx and raise their
        # label_id by 0 or 1 (based on ex_labels)
        for i in range(len(ex_labels)):
            labels[lc_idx[i]] += ex_labels[i]
        # print(labels)
    if len(set(labels)) == 1:
        return (labels, 0)

    sscore = silhouette_score(
        A, labels, metric=nltk.cluster.util.cosine_distance)
    return (labels, sscore)


if __name__ == "__main__":
    # rahlo lemmatizirani stavki, iščemo 3 gruče
    # (matematika, plezanje in vreme)
    sentences1 = [
        "avtomobil balon copata",
        "avtomobil copata copata",
        "detergent evangelij fiktiven",
        "detergent detergent detergent",
        "avtomobil gorila gorila",
        "gorila copata gorila",
    ]
    sentences = [
        "števila ena, dva, tri in štiri so manjša od pet",
        "pet minus tri je dva",
        "tri dve ena bum",
        "plez oprema je dražji del športa",
        "po plez je treba oprema ičistiti in pospraviti",
        "plez se mora naučiti pravilno uporabljati plez oprema",
        "v ponedeljek so napovedane močne plohe",
        "prestali smo plohe, napovedane so še nadaljne padavine",
        "napovedane so snežne padavine",
    ]

    # print(k_means(sentences, 3))
    # print(nltk_kmeans(sentences, 3))
    # print(bkm(sentences, 3))
    # print(silhouette_wrapper(sentences, bkm))
    print(silhouette_wrapper(sentences, k_means))
