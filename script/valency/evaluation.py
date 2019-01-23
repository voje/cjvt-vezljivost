from collections import Counter
from sklearn.metrics import adjusted_rand_score as ars
import logging
# from time import time

log = logging.getLogger(__name__)


class Evaluation():
    # Class for evaluation clustering approaches.
    def __init__(self, vallex):
        self.vallex = vallex
        self.eval_group = "eval1"

    def rand_index_old(self, M, A):
        # M = {M0, M1, ... Mn} - Manually created clusters (standard).
        # A = {A0, A1, ... An} - Cluster for evaluation.
        # M.keys needs to be a subset of A.keys
        # M, A = {
        #   <ssj_id>: <sense_id>
        # }
        mlist = [k for k, e in M.items()]
        pairs = []
        for i in range(len(mlist)):
            for el in mlist[i + 1:]:
                pairs.append((mlist[i], el))
        a = 0  # num of pairs belonging to the same cluster both in M and A.
        b = 0  # num of pairs belonging to diferent clusters both in M and A.
        for pair in pairs:
            m_ids = (M[pair[0]], M[pair[1]])
            a_ids = (A[pair[0]], A[pair[1]])
            if (m_ids[0] == m_ids[1] and a_ids[0] == a_ids[1]):
                a += 1
            elif (m_ids[0] != m_ids[1] and a_ids[0] != a_ids[1]):
                b += 1
        index = 1.0 * (a + b) / len(pairs)
        return index

    def rand_index(self, gold, unkn):
        # gold and eval are arrays of sample classes
        # sample should be mapped to index in both arrays
        if len(gold) != len(unkn):
            log.error("clustering_purity: input lengths don't match")
            return None
        cnt = 0.0
        score = 0.0
        for i in range(len(gold)):
            for j in range(i + 1, len(gold)):
                # print("({}, {}) - {}".format(i, j, len(gold)))
                cnt += 1
                if (gold[i] == gold[j]) and (unkn[i] == unkn[j]):
                    score += 1
                if (gold[i] != gold[j]) and (unkn[i] != unkn[j]):
                    score += 1
        return (score / cnt)

    def eval_all(self):
        query = list(self.vallex.db.user_senses.find({
            "sense_group": self.eval_group
        }))
        headwords = list(set([x["headword"] for x in query]))
        scores = {}
        for hw in headwords:
            score = self.eval_for_hw(hw)
            scores[hw] = score
        return scores

    def eval_for_hw(self, hw):
        def helper_extract(q, dic, collname):
            for el in q:
                if el["ssj_id"] == "" or el["sense_id"] == "":
                    continue
                if el["ssj_id"] not in dic:
                    dic[el["ssj_id"]] = []
                dic[el["ssj_id"]].append((collname, el["sense_id"]))
        dic = {}
        gold_query = list(self.vallex.db.user_senses.find({
            "headword": hw,
            "sense_group": self.eval_group
        }))
        helper_extract(gold_query, dic, "eval1")
        ssj_list = list(dic.keys())
        collections = [
            "km_bkm", "km_normal", "lf_lesk_nltk", "lf_lesk_sl",
            "lf_lesk_al", "lf_lesk_ram"
        ]
        # print(ssj_list)
        for c in collections:
            query = list(self.vallex.db[c].find({
                "headword": hw,
                "ssj_id": {"$in": ssj_list}
            }))
            helper_extract(query, dic, c)
        class_arrays = {self.eval_group: []}
        for c in collections:
            class_arrays[c] = []

        # check
        for k, e in dic.items():
            if len(e) != (len(collections) + 1):
                return None  # some algorithms didn't give a result
            # print("{}|| {}".format(k, e))

        def helper_find_class(arr, cls):
            for x in arr:
                if x[0] == cls:
                    return x[1]
            return None

        # ssj_id order matters!!!
        # needs to be the same in all arrays
        for ssj_id in ssj_list:
            el = dic[ssj_id]
            for c in class_arrays.keys():
                class_arrays[c].append(helper_find_class(el, c))

        # test
        """
        for k, e in class_arrays.items():
            print("{}|| {}".format(k, e))
        """

        # scoring
        scores = {}
        for c in collections:
            scores[c] = {
                "rand_idx": self.rand_index(
                    class_arrays[self.eval_group], class_arrays[c]),
                "clustering_purity": self.clustering_purity(
                    class_arrays[self.eval_group], class_arrays[c]),
                "ars": ars(
                    class_arrays[self.eval_group], class_arrays[c])
            }
        return scores

    def eval_single_old(self, hw, collname):
        test = list(self.vallex.db.user_senses.find({
            "headword": hw,
            "sense_group": self.eval_group
        }))
        ev = list(self.vallex.db[collname].find({
            "headword": hw
        }))
        if len(test) == 0 or len(ev) == 0:
            return (None, None)
        M = {}
        for el in test:
            M[el["ssj_id"]] = el["sense_id"]
        A = {}
        for el in ev:
            A[el["ssj_id"]] = el["sense_id"]
        index = self.rand_index(M, A)
        count = len(M.keys())
        return (index, count)

    def eval_collection_old(self, collname):
        results = []
        test_hws = list(set([
            x["headword"] for x in
            list(self.vallex.db.user_senses.find({
                "sense_group": self.eval_group
            }))
        ]))
        for hw in test_hws:
            ridx, count = self.eval_single(hw, collname)
            if ridx is not None:
                results.append({
                    "hw": hw,
                    "r_index": ridx,
                    "count": count
                })
        allcount = 0
        allscore = 0
        for r in results:
            allscore += r["r_index"] * r["count"]
            allcount += r["count"]
        index = 1.0 * allscore / allcount
        return index, sorted(results, key=lambda x: x["hw"])

    def clustering_purity(self, gold, unkn):
        # gold and eval are arrays of sample classes
        # sample should be mapped to index in both arrays
        if len(gold) != len(unkn):
            log.error("clustering_purity: input lengths don't match")
            return None
        clusters = {}
        for i in range(len(gold)):
            if gold[i] not in clusters:
                clusters[gold[i]] = []
            clusters[gold[i]].append(unkn[i])
        score = 0.0
        for k, e in clusters.items():
            cnt = Counter(e)
            score += cnt.most_common(1)[0][1]
        return (score / len(gold))


if __name__ == "__main__":
    ev = Evaluation(None)

    # go with input == two same length arrays [alg] [hand]
    golden = [
        "a", "a",
        "b", "b", "b",
        "c", "c", "c",
        "d", "d", "d", "d"
    ]

    golden1 = ["a", "a", "b", "b"]
    test1 = ["1", "2", "3", "4"]

    test_best = [
        "1", "1",
        "2", "2", "2",
        "3", "3", "3",
        "4", "4", "4", "4"
    ]

    test_medium = [
        "1", "1",
        "1", "2", "2",
        "3", "2", "3",
        "4", "3", "2", "4"
    ]

    test_worst = [
        "1", "2",
        "3", "4", "5",
        "6", "7", "8",
        "9", "10", "11", "12"
    ]

    """
    print(ev.clustering_purity(golden, test_best))
    print(ev.clustering_purity(golden, test_medium))
    print(ev.clustering_purity(golden, test_worst))
    """

    print(ev.rand_index1(golden, test_best))
    print(ev.rand_index1(golden1, test1))
    print(ev.rand_index1(golden, test_medium))
    print(ev.rand_index1(golden, test_worst))
