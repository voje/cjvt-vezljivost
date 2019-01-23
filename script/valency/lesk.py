# -*- coding: utf-8 -*-

from time import time
from valency import k_utils
from valency import sskj_scraper
import pprint
import random
import math
from valency import mongo_tools
import logging

log = logging.getLogger(__name__)

pp = pprint.PrettyPrinter()


class Lesk:
    def __init__(self, vallex):
        self.vallex = vallex

        # dictionary of "word": "slownet_id"
        self.slo_to_id = self.vallex.db.slo_to_id.find_one()
        self.XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
        self.slownet_cache = {}

        # Speed of lesk (combinatorial pruning)
        self.SENS_LIMIT = 5
        self.MAX_PATHS = 200

    def cache_synset(self, synset_id):
        synset = self.vallex.db.slownet.find_one({"ID": synset_id})
        if synset is None:
            return False
        if synset_id not in self.slownet_cache:
            self.slownet_cache[synset_id] = synset
        return True

    def synset_to_tokens(self, synset_id, depth=None, min_token_len=None):
        if depth == 0:  # None != 0
            return []
        depth = depth or 1
        global_res = []

        if not self.cache_synset(synset_id):
            return []
        if "cached_tokens" in self.slownet_cache[synset_id]:
            return self.slownet_cache[synset_id]["cached_tokens"]

        sentences = []
        usages = k_utils.dict_safe_key(
            self.slownet_cache[synset_id], "USAGE")
        for u in usages:
            if u["@xml:lang"] == "en":
                sentences.append(u["#text"])
        defins = k_utils.dict_safe_key(
            self.slownet_cache[synset_id], "DEF")
        for d in defins:
            if d["@xml:lang"] == "en":
                sentences.append(d["#text"])
        res = []
        for sent in sentences:
            res.extend(k_utils.tokenize(sent, min_token_len=min_token_len))
        self.slownet_cache[synset_id]["cached_tokens"] = global_res
        global_res.extend(res)

        # Recursive step
        ilrs = k_utils.dict_safe_key(
            self.slownet_cache[synset_id], "ILR")
        allowed_ilr_types = ["hypernym", "eng_derivative"]
        for ss_id in [
            ilr["#text"] for ilr in ilrs if ilr["@type"] in allowed_ilr_types
        ]:
            global_res.extend(
                self.synset_to_tokens(ss_id, depth - 1)
            )
        return global_res

    # obsolete
    def slownet_senses(self, lemma):
        # Input: token.
        # Looks for senses in slownet + adds 2 more layers of hypernyms.
        # Output: list of Sense objects.

        # Preprocess and store in mongodb.
        dic_senses = self.vallex.db.senses.find_one({"lemma": lemma})
        if dic_senses is not None:
            senses = []
            for dic_sense in dic_senses["senses"]:
                s = Sense()
                s.decode_dict(dic_sense)
                senses.append(s)
            return senses

        ts = time()
        senses = []
        sense_id = 0  # give ids to senses of a word
        if lemma not in self.slo_to_id:
            return senses
        for slow_id in self.slo_to_id[lemma]:
            sense = self.slownet_sense(slow_id, lemma, sense_id)
            if sense is not None:
                senses.append(sense)
                sense_id += 1
        print("Prepared {} senses for lemma [{}] in {:.2f}s".format(
            len(senses), lemma, time() - ts
        ))
        dic_senses = []
        for sense in senses:
            dic_senses.append(sense.encode_dict())
        self.vallex.db.senses.insert({"lemma": lemma, "senses": dic_senses})
        return senses

    # obsolete
    def slownet_sense(self, slow_id, token, sense_id):
        # Creates a Sense object,
        # traversing a sense and its hypernyms, collecting data.
        # Sense.sloWNet_data.append(slowNet_extract_synset_data(synset))
        sense = Sense(token, sense_id)
        sense = self.slownet_sense_rec(slow_id, sense, 0, "Root")
        return sense

    # obsolete
    def slownet_sense_rec(self, slow_id, sense, depth, ilr_type):
        if len(sense.slownet_data) >= 3:
            return sense
        synset = self.vallex.db.slownet.find_one({"ID": slow_id})
        data = self.slownet_extract_synset_data(synset)
        # Handle infinite loops (check if sense_id was already visited):
        new_synset_id = data["slownet_id"]
        for sd in sense.slownet_data:
            if new_synset_id == sd["slownet_id"]:
                return sense
        data["depth"] = depth
        data["ilr_type"] = ilr_type
        sense.slownet_data.append(data)
        if "ILR" in synset:
            tmplist = synset["ILR"]
        else:
            return sense
        if not isinstance(tmplist, list):
            tmplist = [tmplist]
        for ilr in tmplist:
            ilr_id1 = ilr["#text"]
            ilr_type1 = ilr["@type"]
            sense = self.slownet_sense_rec(
                ilr_id1, sense, depth + 1, ilr_type1
            )
        return sense

    # obsolete
    def slownet_extract_synset_data(self, synset):
        liter = []
        tmplist = synset["SYNONYM"]
        if not isinstance(tmplist, list):
            tmplist = [tmplist]
        for synonym in tmplist:
            if synonym["@xml:lang"] == "sl":
                if "LITERAL" in synonym:
                    tmplist = synonym["LITERAL"]
                    if not isinstance(tmplist, list):
                        tmplist = [tmplist]
                    for literal in tmplist:
                        liter.append(literal["#text"])
        domain = []
        if "DOMAIN" in synset:
            tmplist = synset["DOMAIN"]
            if not isinstance(tmplist, list):
                tmplist = [tmplist]
            domain = [x for x in tmplist]

        data = {
            "slownet_id": synset["ID"],
            "literal": liter,
            "ilr_type": "None",
            "depth": -1,
            "domain": domain
        }
        return data

    # obsolete
    def lesk(self, token, context):
        tstart = time()
        # input: verb token vrom ssj + context tokens (tokens around the verb)
        # I only need the lemmas for now.
        # output: sense of that token, based on context

        # First, gather data.

        # Look at top 5 senses for each token.
        verb_senses = self.slownet_senses(token["lemma"])
        if len(verb_senses) == 0:
            # print("Verb {} not found in sloWNet; stopping lesk().".format(
            #     token["lemma"]))
            return None
        if len(verb_senses) == 1:
            return (0, verb_senses)

        if len(verb_senses) > self.SENS_LIMIT:
            verb_senses = verb_senses[:self.SENS_LIMIT]
        all_senses = []
        for tkn in context:
            senses = self.slownet_senses(tkn["lemma"])
            if len(senses) > 0:
                all_senses.append(senses)
        for i in range(len(all_senses)):
            if len(all_senses[i]) > self.SENS_LIMIT:
                all_senses[i] = all_senses[i][:self.SENS_LIMIT]

        for verb_sense in verb_senses:
            sskj_words = set()
            sense_words = verb_sense.get_3_literals()
            for sw in sense_words:
                tmp_words = self.vallex.db.sskj.find_one({"word": sw})
                if tmp_words is None:
                    tmp_words = []
                    """
                    # try scraping
                    tmp_words = self.sskj_scraper.scrape(sw)
                    if len(tmp_words) > 0:
                        # save to db
                        self.db.insert({"word": sw, "bag": tmp_words})
                    """
                else:
                    tmp_words = tmp_words["bag"]
                """
                if (len(tmp_words)) > 100:
                    tmp_words = set(list(tmp_words)[:100])
                """
                sskj_words.update(set(tmp_words))
                if len(sskj_words) == 0:
                    print(
                        "No text representation for head word; "
                        "stopping lesk().")
                    return None
            verb_sense.sskj_data = sskj_words

        for senses in all_senses:
            # print("len(word_senses) = {}".format(len(senses)))
            for sense in senses:
                sskj_words = set()
                sense_words = sense.get_3_literals()
                for sw in sense_words:
                    tmp_words = self.vallex.db.sskj.find_one({"word": sw})
                    if tmp_words is None:
                        tmp_words = []
                        # try scraping
                        """
                        tmp_words = self.sskj_scraper.scrape(sw)
                        print("{:0.2f}".format(time() - utime))
                        if len(tmp_words) > 0:
                            # save to db
                            self.db.insert({"word": sw, "bag": tmp_words})
                            print("{:0.2f}".format(time() - utime))
                        """
                    else:
                        tmp_words = tmp_words["bag"]
                    """
                    if (len(tmp_words)) > 100:
                        tmp_words = set(list(tmp_words)[:100])
                    """
                    sskj_words.update(set(tmp_words))
            sense.sskj_data = sskj_words

        # Actual lesk algorithm.
        paths = k_utils.permute_paths(all_senses)
        if len(paths) > self.MAX_PATHS:
            paths = random.sample(paths, self.MAX_PATHS)
        # print("paths: {}".format(len(paths)))
        # each path gets its own score (verb sense -> many paths)

        scores = []
        for i in range(len(verb_senses)):
            scores.append([])
            for path in paths:
                # For each path (combination of senses), count
                # the number of overlapping words.
                score = 0.0
                cnt = 0
                for coords in path:
                    cnt += 1
                    compare_set = all_senses[coords[0]][coords[1]].sskj_data
                    tmp = len(
                        verb_senses[i].sskj_data.intersection(compare_set))
                    # Weight by both set sizes.
                    weight = len(verb_senses[i].sskj_data) * len(compare_set)
                    weight = weight or 1
                    tmp /= weight
                    score += tmp
                cnt = cnt or 1
                score /= cnt
                scores[i].append(score)

        """
        for sc in scores:
            print(sc)
        """
        max_score = 0
        ms_idx = (-1, -1)
        for i in range(len(scores)):
            for j in range(len(scores[i])):
                if scores[i][j] > max_score:
                    max_score = scores[i][j]
                    ms_idx = (i, j)

        print("SCORES:")
        print(ms_idx)
        for sc in scores:
            print(len(sc))
        """
        print("Sense slownet data:")
        print(verb_senses[ms_idx[0]].slownet_data)
        """

        print("Lesk.lesk for lemma {} in {:.2f}s.".format(
            token["lemma"], time() - tstart)
        )
        print("Max score ({}) for verb_sense[{}] ({} verb_senses).".format(
            max_score, ms_idx[0], len(verb_senses)))
        print()
        # Return index of sense + all senses.
        return (ms_idx[0], verb_senses)

    def lesk_take2(self, mid, tokens, debug=False):
        if debug:
            print(mid)
            print(tokens[mid])
        # mid -> main token index (the verb token index)
        # tokens -> [ {"lemma": "...", "msd": "..."}, ...]
        # t_lesk_take2 in val_struct.py (need those tokens ...)

        # clear cache
        self.slownet_cache = {}

        sense_ids = []
        for t in tokens:
            token_senses = []
            if t["lemma"] in self.slo_to_id:
                token_senses.extend(self.slo_to_id[t["lemma"]])
                if len(token_senses) > self.SENS_LIMIT:
                    token_senses = random.sample(token_senses, self.SENS_LIMIT)
            sense_ids.append(token_senses)

        if len(sense_ids[mid]) == 0:
            # print("Verb {} not found in SloWNet.".format(
            #     tokens[mid]))
            return None

        sense_ids[:] = [(x, 0) for x in sense_ids]
        sense_ids[mid] = (sense_ids[mid][0], 1)

        """
        # Start Debug print
        tprint = "(length of senses, boolean_is_mid)\n"
        tprint += "["
        for ss in sense_ids:
            tprint += "({:4d}, {}), ".format(len(ss[0]), ss[1])
        tprint += "]"
        print(tprint)
        # End Debug print
        """

        sense_ids[:] = [x for x in sense_ids if len(x[0]) > 0]
        for ss in range(len(sense_ids)):
            if sense_ids[ss][1] == 1:
                mid = ss
                break
        sense_ids[:] = [x[0] for x in sense_ids]
        paths = k_utils.permute_paths(sense_ids)
        if len(paths) > 500:
            paths = random.sample(paths, 500)

        if debug:
            print("Mid: {}".format(mid))
            print("len(paths): {}".format(len(paths)))
            sense_combos = 1
            for ss in sense_ids:
                sense_combos *= len(ss)
            print("sense_combos: {}".format(sense_combos))

            lns = "[{:3d}] -> ".format(len(sense_ids))
            for sid in sense_ids:
                lns += "{:4d}, ".format(len(sid))
            print(lns)

            print(paths[0])

        # { "slownet_sense_id": "score" }
        scores = {}
        for path in paths:
            score = 0
            # compare all pairs
            for i in range(len(path) - 1):
                for j in range(i + 1, len(path)):
                    id_a = sense_ids[path[i][0]][path[i][1]]
                    id_b = sense_ids[path[j][0]][path[j][1]]
                    tokens_a = self.synset_to_tokens(id_a)
                    tokens_b = self.synset_to_tokens(id_b)
                    overlaps = k_utils.find_overlaps_str(tokens_a, tokens_b)
                    for ol in overlaps:
                        score += math.pow(len(ol), 2)
            verb_id = sense_ids[path[mid][0]][path[mid][1]]
            if verb_id not in scores:
                scores[verb_id] = []
            scores[verb_id].append(score)
            # print(verb_id)
            # print(score)

        # print(scores)
        # Return max score id
        max_score = 0.0
        max_key = None
        for k, e in scores.items():
            for score in e:
                if score > max_score:
                    max_score = score
                    max_key = k

        return max_key

    def lesk_take3(self, tokens, debug=False):
        # Tokens are [verb token, other frame members]
        # Scoring: best (verb token, member) collocation.

        self.slownet_cache = {}

        # Throw out useless tokens like "biti".
        tmp_tokens = []
        for tk in tokens:
            if (
                "lemma" in tk and
                tk["lemma"] != "biti"
            ):
                tmp_tokens.append(tk)
        tokens = tmp_tokens

        if debug:
            for tk in tokens:
                print(tk)
            print("len_tokens: {}".format(len(tokens)))

        self.slownet_cache = {}

        sense_ids = []  # 2D array [W0: [s0, s1, s2], W1: [s0, s2, ...])
        for i, t in enumerate(tokens):
            if i == 0 and t["lemma"] not in self.slo_to_id:
                print("Verb {} not represented in SloWNet.".format(
                    t["lemma"]))
                return None
            if t["lemma"] in self.slo_to_id:
                token_senses = self.slo_to_id[t["lemma"]]
                sense_ids.append(token_senses)
            else:
                if debug:
                    print("{} not in slo_to_id".format(t["lemma"]))

        # If headword has 1 sense, return it.
        if len(sense_ids[0]) == 1:
            return sense_ids[0][0]

        for i, ss in enumerate(sense_ids):
            if debug:
                print("len_sids: {}".format(len(ss)))
            if len(ss) > 100:
                if debug:
                    print("too many senses for lemma: {}".format(
                        tokens[i]["lemma"]))
                return

        # sense_ids[0] is the headword verb
        paths = k_utils.permute_paths(sense_ids)
        # No restrictions for number of paths, for now.
        if debug:
            print("len_paths: {}".format(len(paths)))

        if len(sense_ids) == 1:
            if debug:
                print("No sense_ids for inner participants.")
            return None  # Return most common sense of hw?

        overlap_score_cache = {}
        scores = {}
        DEPTH = 3
        MIN_T_L = 3
        for path in paths:
            hw_coord = path[0]
            hw_slownet_id = sense_ids[hw_coord[0]][hw_coord[1]]
            hw_bow = self.synset_to_tokens(
                hw_slownet_id, depth=DEPTH, min_token_len=MIN_T_L)
            for ip_coord in path[1:]:
                ip_slownet_id = sense_ids[ip_coord[0]][ip_coord[1]]
                cache_key = ",".join([hw_slownet_id, ip_slownet_id])
                if cache_key in overlap_score_cache:
                    score = overlap_score_cache[cache_key]
                else:
                    ip_bow = self.synset_to_tokens(
                        ip_slownet_id, depth=DEPTH, min_token_len=MIN_T_L)
                    overlaps = k_utils.find_overlaps_str(hw_bow, ip_bow)
                    score = len(overlaps)
                    overlap_score_cache[cache_key] = score
                if hw_slownet_id not in scores:
                    scores[hw_slownet_id] = {
                        "scores": [],
                        "sum": 0
                    }
                scores[hw_slownet_id]["scores"].append(score)
                scores[hw_slownet_id]["sum"] += score

        if debug:
            print("scores:")
            for k, e in scores.items():
                print("score_sum for {}: {}".format(
                    k, e["sum"]))

        top_score = (None, 0)
        for slownet_id, scc in scores.items():
            """
            for sc in scc:
                if sc > top_score[1]:
                    top_score = (slownet_id, sc)
            """
            if scc["sum"] > top_score[1]:
                top_score = (slownet_id, scc["sum"])

        return top_score[0]

    def simple_lesk_sskj(
        self, context_sentence, word_lemma, min_token_len=None
    ):
        # The one I'm actually using.
        if min_token_len is None:
            min_token_len = 0
        # returns (
        #   overlap_score,
        #   sense_id (nth-all)
        #   sskj_sense object
        # )
        #
        # def lesk(context_sentence, ambiguous_word, pos=None, synsets=None)
        sense_glosses = self.vallex.sskj_interface.sense_glosses(word_lemma)
        if len(sense_glosses) == 0:
            return None
        # nltk lesk modified
        context = k_utils.tokenize(
            context_sentence, min_token_len=min_token_len)
        winner = (-1, -1, None)
        for i, sense_gloss in enumerate(sense_glosses):
            all_sentences = ""
            for sens in sense_gloss["gloss"]:
                all_sentences += sens
            sense_bow = k_utils.tokenize(
                all_sentences, min_token_len=min_token_len)
            # overlap = set(context).intersection(set(sense_bow))
            # score = len(overlap)
            k_overlap = k_utils.find_overlaps_str(context, sense_bow)
            # n-gram matches give a higher k_score
            k_score = sum([pow(len(x), 2) for x in k_overlap])
            if k_score > winner[0]:
                winner = (k_score, i, sense_gloss)
        sense_id = "{}-{}".format(winner[1] + 1, len(sense_glosses))
        return (winner[0], sense_id, winner[2])

    # Tests
    def t_slownet_id_to_token(self):
        for k, e in self.slo_to_id.items():
            for eid in e:
                if random.randint(0, 100) < 20:
                    res = lesk.synset_to_tokens(eid)
                    if random.randint(0, 100) < 10:
                        print(res)

    def t_simple_lesk_sskj(self):
        context_sentence = "Avtomobil rdeče barve je hitro letel."
        word_lemma = "leteti"
        print(self.simple_lesk_sskj(context_sentence, word_lemma))


# obsolete?
class Sense:
    def __init__(self, lemma=None, sense_id=None):
        self.id = sense_id
        self.lemma = lemma
        self.slownet_data = []
        self.sskj_data = set()

    def encode_dict(self):
        dic = {
            "id": self.id,
            "lemma": self.lemma,
            "slownet_data": self.slownet_data,
        }
        return dic

    def decode_dict(self, dic):
        # Create a Sense() forst, then call this.
        # print(dic)
        self.id = dic["id"]
        self.lemma = dic["lemma"]
        self.slownet_data = dic["slownet_data"]
        self.sskj_data = set()  # Data in db.texts.sskj[lemma]

    def get_3_literals(self):
        res = set()
        for level in self.slownet_data:
            for literal in level["literal"]:
                if literal not in res:
                    res.add(literal)
                    if len(res) >= 3:
                        return list(res)
        return list(res)

    def to_string(self):
        res = ""
        res += "Sense id: {:<10}, lemma: {}\n".format(self.id, self.lemma)
        res += "slownet_data.domain: {}\n.".format(
            self.slownet_data[0]["domain"])
        res += "slownet_data.literal: {}\n.".format(
            self.slownet_data[0]["literal"])
        # res += "sskj_data:\n{}".format(self.sskj_data)
        return res


if __name__ == "__main__":
    test_token = {"lemma": "prepeljati"}
    context = (
        "Tekma je postregla s kar precej padci, "
        "tri smučarje so morali zaradi trdih pristankov, "
        "potem ko jih je na skokih katapultiralo visoko v zrak, "
        "v dolino prepeljati z akiji in motornimi sanmi."
    )
    context = [
        {"lemma": str.lower(x)} for x in context.split(" ") if len(x) > 3
    ]

    lesk = Lesk()
    lesk.t_simple_lesk_sskj()
