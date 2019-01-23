from valency import k_utils
from valency.tfigf import TfIgf
from sklearn.metrics.pairwise import linear_kernel
import logging
from time import time

log = logging.getLogger(__name__)


# Four lesk algorithms with a common interface
class LeskFour():
    def __init__(self, vallex):
        self.vallex = vallex

    def update_db(self, collname, hw, ssj_id, sense_id, sense_desc):
        key = {"ssj_id": ssj_id}
        entry = {
            "headword": hw,
            "ssj_id": ssj_id,
            "sense_id": sense_id,
            "sense_desc": sense_desc
        }
        self.vallex.db[collname].update(key, entry, upsert=True)

    def lesk_nltk(self, mytid):
        data = self.vallex.get_context1(
            mytid,
            collname="sskj",
            radius=None,
            min_token_len=3,
            get_glosses=False
        )
        idx_map = []
        tfigf_input = []

        if data["hw"] is None:
            return (-1, [])

        idx_map.append([])
        for gloss in data["hw"]["glosses"]:
            st = k_utils.tokenize_multiple(
                gloss["gloss"], stem=k_utils.stem_slo)
            tfigf_input.append(" ".join(st))
            idx_map[-1].append(len(tfigf_input) - 1)

        idx_map.append([])
        context = [data["hw"]["lemma"]]
        for e in data["context"]:
            context.append(e["lemma"])
        stemmed_context = k_utils.tokenize_multiple(
            context, stem=k_utils.stem_slo)
        tfigf_input.append(" ".join(stemmed_context))
        idx_map[-1].append(len(tfigf_input) - 1)

        tf = TfIgf(tfigf_input)

        scores = []
        for hw_gloss_idx in idx_map[0]:
            context_idx = idx_map[1][0]
            scores.append(tf.compare(hw_gloss_idx, context_idx))

        """
        print("--->{}\nsentence: {}".format(
            data["hw"]["lemma"], self.vallex.get_sentence(mytid)))
        print("[[" + tfigf_input[-1] + "]]")
        for i, s in enumerate(scores):
            print("{:<10}[[{}]]\n{}".format(
                s,
                tfigf_input[idx_map[0][i]],
                data["hw"]["glosses"][i]["gloss"]
            ))
        """
        best_score_idx = -1
        best_score = -1
        for i, s in enumerate(scores):
            if s > best_score:
                best_score_idx = i
                best_score = s
        """
        log.debug("{}: {} <- {}".format(
            data["hw"]["lemma"], scores[best_score_idx], scores))
        """

        if best_score_idx >= 0:
            sense_id = data["hw"]["glosses"][best_score_idx]["sskj_sense_id"]
        else:
            sense_id = "{}-{}".format(best_score_idx + 1, len(scores))

        self.update_db(
            collname="lf_lesk_nltk",
            hw=data["hw"]["lemma"],
            ssj_id=mytid,
            sense_id=sense_id,
            sense_desc=data["hw"]["glosses"][best_score_idx]["def"]
        )
        return best_score_idx, scores

    def lesk_sl(self, mytid):
        data = self.vallex.get_context1(
            mytid,
            collname="sskj",
            radius=2,
            min_token_len=0,
            get_glosses=False
        )
        idx_map = []
        tfigf_input = []

        if data["hw"] is None:
            return (-1, [])

        idx_map.append([])
        for gloss in data["hw"]["glosses"]:
            st = k_utils.tokenize_multiple(
                gloss["gloss"], stem=None)
            tfigf_input.append(" ".join(st))
            idx_map[-1].append(len(tfigf_input) - 1)

        idx_map.append([])
        context = [data["hw"]["lemma"]]
        for e in data["context"]:
            context.append(e["lemma"])
        stemmed_context = k_utils.tokenize_multiple(
            context, stem=None)
        tfigf_input.append(" ".join(stemmed_context))
        idx_map[-1].append(len(tfigf_input) - 1)

        tf = TfIgf(tfigf_input)

        scores = []
        for hw_gloss_idx in idx_map[0]:
            context_idx = idx_map[1][0]
            scores.append(tf.compare(hw_gloss_idx, context_idx))

        best_score_idx = -1
        best_score = -1
        for i, s in enumerate(scores):
            if s > best_score:
                best_score_idx = i
                best_score = s

        if best_score_idx >= 0:
            sense_id = data["hw"]["glosses"][best_score_idx]["sskj_sense_id"]
        else:
            sense_id = "{}-{}".format(best_score_idx + 1, len(scores))

        self.update_db(
            collname="lf_lesk_sl",
            hw=data["hw"]["lemma"],
            ssj_id=mytid,
            sense_id=sense_id,
            sense_desc=data["hw"]["glosses"][best_score_idx]["def"]
        )
        return best_score_idx, scores

    def lesk_al(self, mytid):
        stime = time()
        data = self.vallex.get_context1(
            mytid,
            collname="slownet",
            radius=2,
            min_token_len=3,
            get_glosses=True
        )
        idx_map = []
        tfigf_input = []

        if data["hw"] is None:
            return (-1, [])

        idx_map.append([])
        for gloss in data["hw"]["glosses"]:
            st = k_utils.tokenize_multiple(
                gloss["gloss"], stem=k_utils.stem_eng)
            tfigf_input.append(" ".join(st))
            idx_map[-1].append(len(tfigf_input) - 1)

        for token in data["context"]:
            idx_map.append([])
            for gloss in token["glosses"]:
                st = k_utils.tokenize_multiple(
                    gloss["gloss"], stem=k_utils.stem_eng)
                tfigf_input.append(" ".join(st))
                idx_map[-1].append(len(tfigf_input) - 1)

        tf = TfIgf(tfigf_input)
        cosine_sims = linear_kernel(tf.matrix, tf.matrix)

        paths = k_utils.permute_paths(idx_map)

        # For each hw sense, find the best score (combination of the
        # hw sense and token senses (path through the sentence))
        scores = []
        for hw_sense_idx in range(len(idx_map[0])):
            hw_sense_paths = [x for x in paths if x[0][1] == hw_sense_idx]
            best_sense_score = -1
            for path in hw_sense_paths:
                score = 0
                cos_idx_hw = idx_map[path[0][0]][path[0][1]]
                for token in path[1:]:
                    cos_idx_tok = idx_map[token[0]][token[1]]
                    score += cosine_sims[cos_idx_hw][cos_idx_tok]
                if score > best_sense_score:
                    best_sense_score = score
            scores.append(best_sense_score)

        best_score_idx = -1
        best_score = -1
        for i, s in enumerate(scores):
            if s > best_score:
                best_score_idx = i
                best_score = s

        self.update_db(
            collname="lf_lesk_al",
            hw=data["hw"]["lemma"],
            ssj_id=mytid,
            sense_id="{}-{}".format(best_score_idx + 1, len(scores)),
            sense_desc=data["hw"]["glosses"][best_score_idx]["def"]
        )
        log.debug("lesk_al time: {:.2f}".format(time() - stime))
        return best_score_idx, scores

    def lesk_ram(self, mytid):
        stime = time()
        data = self.vallex.get_context1(
            mytid,
            collname="slownet",
            radius=None,
            min_token_len=3,
            get_glosses=False
        )
        idx_map = []
        tfigf_input = []

        if data["hw"] is None:
            return (-1, [])

        idx_map.append([])
        for gloss in data["hw"]["glosses"]:
            st = k_utils.tokenize_multiple(
                gloss["gloss"], stem=k_utils.stem_eng)
            tfigf_input.append(" ".join(st))
            idx_map[-1].append(len(tfigf_input) - 1)

        idx_map.append([])
        context = [data["hw"]["lemma"]]
        for e in data["context"]:
            context.append(e["lemma"])
        # translate lemmas into eng
        eng_context = []
        for lemma in context:
            eng_context.extend(self.vallex.slownet_interface.slo_to_eng(lemma))
        stemmed_context = k_utils.tokenize_multiple(
            eng_context, stem=k_utils.stem_eng)
        tfigf_input.append(" ".join(stemmed_context))
        idx_map[-1].append(len(tfigf_input) - 1)

        tf = TfIgf(tfigf_input)
        cosine_sims = linear_kernel(tf.matrix, tf.matrix)

        # For each hw sense, find the best score (combination of the
        # hw sense and token senses (path through the sentence))
        scores = []
        cos_idx_con = idx_map[-1]
        for hw_sense_idx in range(len(idx_map[0])):
            cos_idx_hw = idx_map[0][hw_sense_idx]
            scores.append(cosine_sims[cos_idx_hw][cos_idx_con])

        best_score_idx = -1
        best_score = -1
        for i, s in enumerate(scores):
            if s > best_score:
                best_score_idx = i
                best_score = s

        self.update_db(
            collname="lf_lesk_ram",
            hw=data["hw"]["lemma"],
            ssj_id=mytid,
            sense_id="{}-{}".format(best_score_idx + 1, len(scores)),
            sense_desc=data["hw"]["glosses"][best_score_idx]["def"]
        )

        log.debug("lesk_ram time: {:.2f}".format(time() - stime))
        return best_score_idx, scores
