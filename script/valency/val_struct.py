from time import time
from copy import deepcopy as DC
from valency.frame import Frame
from valency.reduce_functions import *
from valency.lesk import *
from valency import mongo_tools
import random
import logging
from valency.evaluation import Evaluation
from valency.dictionary_interface import SloWnet, Sskj2
from valency.leskFour import LeskFour
from valency.k_kmeans import KmeansClass
from valency.ssj_struct import SsjDict, SsjEntry
from valency.seqparser.seqparser import Seqparser
import pickle
import sys
import hashlib

log = logging.getLogger(__name__)


def split_id(myid):
    tmp = myid.split(".")
    sid = ".".join(tmp[:-1])
    tid = tmp[-1]
    return (sid, tid)


class ValEntry():
    def __init__(self, hw, frame):
        self.hw = hw
        self.raw_frames = [frame]
        self.has_senses = False


class Vallex():
    # Main class
    def __init__(self):
        # database
        self.db, err_msg = mongo_tools.basic_connection("127.0.0.1", 26633)
        if self.db is None:
            log.error((
                "Database not connected:"
                "{}".format(err_msg)
            ))
            exit(1)
        mongo_tools.check_collections(self.db, [
            "v2_users", "v2_senses", "v2_sense_map", "v2_user_tokens"
        ])
        mongo_tools.prepare_user_tokens(self.db)

        # these 3 might be obsolete for the web app (used for ML)
        self.db_senses_map = self.db.senses_map3
        self.slownet_interface = SloWnet(self)
        self.sskj_interface = Sskj2(self)

        # self.tokens["s0][t0"] = {word, lemma, msd, ...}
        self.tokens = {}

        # key = verb / adjective headword
        self.entries = {}

        # For alphabetical indexing in web app.
        self.sorted_words = {}
        # words = { first_letter: [hw1, hw2, ... sorted] }
        self.functors_index = {}
        self.has_se = []  # list of verbs with "se" ("bati se")

        # Used for ML (deprecated).
        self.leskFour = LeskFour(self)
        self.kmeans = KmeansClass(self)
        self.evaluation = Evaluation(self)
        self.test_samples = []

        # run self.process_after_read() after initiating Vallex

    def read_ssj(self, ssj):
        # ssj: object generated with ssj_strict.py.
        BANNED_HW = ["biti"]
        stats = {
            "P_count": 0,
            "skipped": 0,
        }
        log.info("Vallex.read_ssj({}).".format(
            ssj
        ))
        t_start = time()
        for ssj_id, entry in ssj.entries.items():
            # Read tokens
            skip_entry = False
            tmp_tokens = {}
            for ssj_tid, token in entry.s.items():
                sid, tid = split_id(ssj_tid)

                # safety checks
                if tid != "t" and not tid[1:].isdigit():
                    log.warning("dropping SID={} - corrupted keys".format(k))
                    skip_entry = True
                    break
                if tid in tmp_tokens:
                    log.error(
                        "Vallex.read_ssj(): Duplicated ssj_tid:" + ssj_tid)
                    exit(1)

                tmp_tokens[tid] = DC(token)
            if skip_entry:
                continue  # skip corrupted keys
            if sid in self.tokens:
                log.error("sid duplicate: " + sid)
                exit(1)
            self.tokens[sid] = DC(tmp_tokens)

            # Read frame data (each deep link gets its own raw frame).
            link_map = {}
            # hw_id: { hw_lemma: lemma, deep: [{functor: fnct, to: to}]}
            for deep_link in entry.deep_links:
                hw_id = deep_link["from"]
                hw_token = self.get_token(hw_id)
                hw_lemma = hw_token["lemma"]
                hw_bv = hw_token["msd"][0]
                if (hw_bv != "G" and hw_bv != "P"):
                    stats["skipped"] += 1
                    log.info("Skipping {}: not a verb or adjective.".format(
                        hw_lemma))
                    continue
                if hw_bv == "P":
                    hw_lemma = hw_lemma + "_"
                    stats["P_count"] += 1
                if hw_id in link_map:
                    link_map[hw_id]["deep"].append(deep_link)
                else:
                    link_map[hw_id] = {
                        "hw_lemma": hw_lemma,
                        "deep": [deep_link]
                    }
            for hw_id, data in link_map.items():
                hw_lemma = data["hw_lemma"]
                raw_frame = Frame(
                    hw=hw_lemma,
                    tids=[hw_id],
                    deep_links=data["deep"],
                    slots=None,
                )
                if hw_lemma not in self.entries:
                    self.entries[hw_lemma] = ValEntry(hw_lemma, raw_frame)
                else:
                    self.entries[hw_lemma].raw_frames.append(raw_frame)

        # cleanup banned
        for hw in BANNED_HW:
            if hw in self.entries:
                del(self.entries[hw])

        t_end = time()
        log.info("Finished build_from_ssj() in {:.2}s.".format(
            t_end - t_start
        ))
        log.info("Vallex has a total of {} key entries.".format(
            len(self.entries.keys())
        ))
        log.info("Number of adjectives: {}".format(stats["P_count"]))
        log.info("Number of skipped (not a verb or adjective): {}".format(
            stats["skipped"]))
        # Frames per hw
        """
        for k, e in self.entries.items():
            print(k + "," + str(len(e.raw_frames)))
        """

    def get_token(self, myid):
        # id = S123.t1
        sid, tid = split_id(myid)
        return self.tokens[sid][tid]

    def get_sentence(self, myid):
        sid, tid = split_id(myid)
        tmp = []
        sentence = ""
        for k, token in self.tokens[sid].items():
            if (k != "t") and (token["word"] is not None):
                tmp.append((k, token))
        for token in sorted(tmp, key=lambda x: int(x[0][1:])):
            sentence += (token[1]["word"] + " ")
        return sentence

    def get_tokenized_sentence(self, myid):
        sid, tid = split_id(myid)
        tmp = []
        sentence = []
        for k, token in self.tokens[sid].items():
            if k != "t":
                tmp.append((k, token))
        for token in sorted(tmp, key=lambda x: int(x[0][1:])):
            sentence.append((".".join([sid, token[0]]), token[1]))
        # return [(ssj_id, {word: _, lemma: _, msd: _}), ...]
        return sentence

    def process_after_read(
        self, sskj_senses_pickle_path, se_list_pickle_path,
        reload_sskj_senses
    ):
        tstart = time()

        # web app: index by hw
        self.sorted_words = {}
        self.gen_sorted_words()

        # web app: index by functor
        self.functors_index = {}
        self.gen_functors_index()

        # fill db.v2_senses
        self.has_se = []
        self.read_seqparser_pickles(
            sskj_senses_pickle_path, se_list_pickle_path, reload_sskj_senses)

        log.debug(
            "vallex.process_after_read(): {:.2f}s".format(time() - tstart))

    def gen_sorted_words(self):
        res = {}
        for hw, e in self.entries.items():
            letter = hw[0].lower()
            n_sent = len(e.raw_frames)
            if letter not in res:
                res[letter] = []
            res[letter].append((hw, n_sent))
        # sort and add to vallex object
        self.sorted_words = {}
        for letter, lst in res.items():
            self.sorted_words[letter] = k_utils.slo_bucket_sort(
                lst, key=lambda x: x[0])

    def gen_functors_index(self):
        for hw, e in self.entries.items():
            for frame in e.raw_frames:
                for slot in frame.slots:
                    if slot.functor not in self.functors_index:
                        self.functors_index[slot.functor] = []
                    self.functors_index[slot.functor].append(frame)

    def read_seqparser_pickles(
        self, sskj_senses_pickle_path, se_list_pickle_path,
        reload_sskj_senses
    ):
        log.info("read_seqparser_pickles()")
        log.info((
            "Reading list of has_se verbs from {}."
            "Sskj senses into db.v2_senses from {}."
        ).format(se_list_pickle_path, sskj_senses_pickle_path))
        AUTHOR_SSKJ = "SSKJ"
        ERR_MSG = (
            "Need to generate .pickle files first."
            "Use: "
            "$ python3 /script/valency/seqparser/seqparser.py"
            "Input is /data/sskj_v2.html."
        )

        # has_se
        with open(se_list_pickle_path, "rb") as f:
            self.has_se = pickle.load(f)
            if self.has_se is None:
                log.error(ERR_MSG)
                exit(1)
            self.has_se = sorted(self.has_se)
            log.info("Loaded self.has_se (len: {}) from {}.".format(
                len(self.has_se), se_list_pickle_path))

        # sskj senses
        if reload_sskj_senses:
            log.info("Reloading sskj_senses.")
            reply = self.db.v2_senses.remove({"author": AUTHOR_SSKJ})
            log.info(reply)

        query = list(self.db.v2_senses.find({"author": AUTHOR_SSKJ}))
        if len(query) > 0:
            log.info("Sskj senses already in database.")
            return
        tstart = time()
        data = None
        with open(sskj_senses_pickle_path, "rb") as f:
            data = pickle.load(f)
            if data is None:
                log.error(ERR_MSG)
                exit(1)
        for k, e in data.items():
            for sense in e["senses"]:
                db_entry = {
                    "hw": k,
                    "author": AUTHOR_SSKJ,
                    "desc": sense["sense_desc"],
                    # unique id for each sense
                    "sense_id": "{}-{}-{}-{}-{}".format(
                        AUTHOR_SSKJ,
                        sense["homonym_id"],
                        sense["sense_id"],
                        sense["sense_type"],
                        hashlib.sha256(
                            sense["sense_desc"].encode("utf-8")
                        ).hexdigest()[:5]
                    )
                }
                self.db.v2_senses.insert(db_entry)
                # print(db_entry)
        log.info("db.v2_senses prepared in {:.2f}s".format(time() - tstart))

    # Functions below can be used for interactively with flask_api.
    def test_dev(self):
        # self.prepare_sskj_senses()
        hw = "dajati"
        senses = self.sskj_interface.sense_glosses(hw)
        return str(senses)

    def calc_senses(self):
        # self.calc_all_senses(self.leskFour.lesk_nltk)
        # self.calc_all_senses(self.leskFour.lesk_sl)
        # self.calc_all_senses(self.leskFour.lesk_al)  # cca 8h!
        # self.calc_all_senses(self.leskFour.lesk_ram)
        self.calc_all_senses_kmeans(self.kmeans.bisection_kmeans)
        self.calc_all_senses_kmeans(self.kmeans.normal_kmeans)
        return "edit val_struct.py: calc_senses()"

    # deprecated functions (used for machine learning experiments)

    def prepare_sskj_senses(self):
        # obsolete, using read_seqparser_pickles()
        log.info("prepare_sskj_senses() (db.v2_senses)")
        query = list(self.db.v2_senses.find({"author": "SSKJ2"}))
        if len(query) > 0:
            log.info("Sskj senses already in database.")
            return
        tstart = time()
        log.info("Iterating over {} hw entries:".format(
            len(self.entries.keys())))
        for hw, e in self.entries.items():
            senses = self.sskj_interface.sense_glosses(hw)
            if len(senses) == 0:
                continue
            for sense in senses:
                # create sense from each description
                for i, de in enumerate(sense["def"]):
                    sense_def = sense["def"][i]
                    sense_def = sense_def[0].upper() + sense_def[1:]
                    if sense_def[-1] == ":" or sense_def[-1] == ";":
                        sense_def = sense_def[:-1] + "."
                    data = {
                        "hw": hw,
                        "author": "SSKJ2",
                        "desc": sense_def,
                        "sskj_id": sense["sskj_sense_id"],
                        "sskj_desc_id": i
                    }
                    self.db.v2_senses.insert(data)
        log.info("sskj_senses prepared in {:.2f}s".format(time() - tstart))

    def gen_sskj_sl(self):
        # Takes about an hour.
        tstart = time()
        log.info("Generating new sskj_simple_lesk with Simple Lesk.")
        for k, e in self.entries.items():
            self.gen_sskj_sl_one(e.hw)
        log.debug("gen_sskj_sl in {:.2f}s".format(time() - tstart))

    def gen_sskj_sl_one(self, hw, update_db=True):
        entry = None
        ttstart = time()
        e = self.entries.get(hw)
        if e is None:
            return
        for frame in e.raw_frames:
            tid = frame.tids[0]
            sentence = self.get_sentence(tid)
            res = self.lesk.simple_lesk_sskj(sentence, hw)
            if res is None:
                log.debug("headword {} not in sskj".format(hw))
                continue
            key = {"ssj_id": tid}
            entry = {
                "headword": hw,
                "ssj_id": tid,  # uniqe identifier
                "sense_id": res[1],
                # "sense_desc": k_utils.dict_safe_key(res[2], "ns0:def"),
                "sense_desc": res[2]["def"]
            }
            # log.debug(str(res[2]))
            # log.debug(entry["sense_id"])
            # log.debug(entry["sense_desc"])
            if update_db:
                self.db.sskj_simple_lesk.update(key, entry, upsert=True)
        log.debug("[*] sskj_ids for {} in {:.2f}s".format(
            hw, time() - ttstart))

    def get_context(self, myid, radius=None, min_lemma_size=None):
        radius = radius or 5
        min_lemma_size = min_lemma_size or 4
        # gives you the token and 10 of its neighbors
        sentence = self.get_sentence(myid)
        sentlen = len(sentence.split(" "))
        sid, tid = split_id(myid)
        idx = int(tid[1:])
        tokens_after = []
        i = idx
        while i < sentlen - 1 and len(tokens_after) < radius:
            i += 1
            token = self.get_token(sid + ".t" + str(i))
            if (
                token is not None and "lemma" in token and
                len(token["lemma"]) >= min_lemma_size and
                token["lemma"] != "biti"
            ):
                tokens_after.append(token)
        tokens_before = []
        i = idx
        while i > 1 and len(tokens_before) < radius:
            i -= 1
            token = self.get_token(sid + ".t" + str(i))
            if (
                token is not None and "lemma" in token and
                len(token["lemma"]) >= min_lemma_size and
                token["lemma"] != "biti"
            ):
                tokens_before.append(token)
        tokens = tokens_before + [self.get_token(myid)] + tokens_after
        # find position of original token:
        mid_idx = len(tokens_before)
        return (mid_idx, tokens)

    def get_sense_ids(self, collname, hw, sense_group=None):
        query = {"headword": hw}
        if sense_group is not None:
            query["sense_group"] = sense_group
        result = list(self.db[collname].find(query))
        sense_ids = {}
        for r in result:
            sense_ids[r["ssj_id"]] = r["sense_id"]
        return sense_ids

    def t_get_context(self):
        ii = 10
        for k, e in self.entries.items():
            for frame in e.raw_frames:
                if random.randint(0, 100) > 20:
                    continue
                ii -= 1
                if ii <= 0:
                    return

                mytid = frame.tids[0]
                print()
                print(mytid)
                print(self.get_token(mytid))
                sent = self.get_context(mytid, radius=3, min_lemma_size=4)
                print("mid: {}".format(sent[0]))
                for ii in range(len(sent[1])):
                    print("{} -> {}".format(
                        ii, sent[1][ii]))

    def t_simple_lesk_sskj(self):
        ii = 10
        for k, e in self.entries.items():
            if random.randint(0, 100) > 20:
                continue
            for frame in e.raw_frames:
                if random.randint(0, 100) > 20:
                    continue
                if ii == 0:
                    return
                ii -= 1

                print("\nTest frame: {}.".format(frame.tids))
                hw_token = self.get_token(frame.tids[0])
                print(hw_token)
                context_sentence = self.get_sentence(frame.tids[0])
                print(context_sentence)
                self.lesk.simple_lesk_sskj(
                    context_sentence=context_sentence,
                    word_lemma=hw_token["lemma"]
                )

    def process_kmeans(self):
        # Convert words to lemmas, cluseter using k-means.
        # Number of clusters from sskj.
        tstart = time()
        log.info("Processing senses using kmeans.")
        for k, e in self.entries.items():
            # Frame start
            ttstart = time()
            lemma = e.hw
            tokenized_sentences = []
            for frame in e.raw_frames:
                tid = frame.tids[0]
                tokenized_sentences.append(self.get_tokenized_sentence(tid))
            lemmatized_sentences = []
            for sent in tokenized_sentences:
                lemmatized = ""
                for token in sent:
                    if "lemma" in token[1]:
                        lemmatized += (token[1]["lemma"] + " ")
                lemmatized_sentences.append(lemmatized)
            lls = len(lemmatized_sentences)
            # We got the sentences
            sskj_entry = self.db.sskj.find_one(
                {"ns0:entry.ns0:form.ns0:orth": lemma})
            if sskj_entry is None:
                log.debug("headword {} has no <sense> in sskj".format(lemma))
                continue
            n_clusters = 1
            if "ns0:sense" in sskj_entry["ns0:entry"]:
                # Guess number of senses based on sskj senses.
                n_clusters = len(sskj_entry["ns0:entry"]["ns0:sense"])
            if lls >= n_clusters and n_clusters > 1:
                labels = k_kmeans.k_means(
                    sentences=lemmatized_sentences,
                    n_clusters=n_clusters
                )
                kmeans_ids = [str(x) + "-" + str(lls) for x in labels]
            elif n_clusters == 1:
                kmeans_ids = ["1-1" for x in lemmatized_sentences]
            elif lls < n_clusters:
                # Each sentence gets its own sense.
                kmeans_ids = []
                for i in range(lls):
                    kmeans_ids.append(str(i + 1) + "lt" + str(n_clusters))
            else:
                log.error("Shouldn't be here (val_struct: process_kmeans()")
                exit(1)

            # Feed sense ides of whole frame to database.
            for i in range(len(e.raw_frames)):
                tid = e.raw_frames[i].tids[0]
                key = {"ssj_id": tid}
                entry = {
                    "headword": lemma,
                    "ssj_id": tid,  # unique idenfitier
                    "sense_id": kmeans_ids[i],
                }
                self.db.kmeans.update(key, entry, upsert=True)

            log.debug("[*] kemans_ids for {} in {:.2f}s".format(
                lemma, time() - ttstart))
            # Frame end
        log.debug("process_kmeans in {:.2f}s".format(time() - tstart))

    def get_context1(
        self, mytid, collname, radius=None, min_token_len=3, get_glosses=None
    ):
        # returns {
        #   "hw": headword lemma and its glosses
        #   "context": a list of lemmas and their glosses around the hw that
        #        have entries in collname dictionary (if get_glosses=True)
        #   }
        # tstart = time()
        if get_glosses is None:
            get_glosses = False
        if radius is None:
            radius = 10000
        if collname == "slownet":
            dictionary_interface = self.slownet_interface
        elif collname == "sskj":
            dictionary_interface = self.sskj_interface
        else:
            log.error("argument error: get_context1(collname=<slownet/sskj>)")
            return []

        sentence = self.get_tokenized_sentence(mytid)
        # return [(ssj_id, {word: _, lemma: _, msd: _}), ...]
        hw_idx = -1
        for i, e in enumerate(sentence):
            if e[0] == mytid:
                hw_idx = i
                hw_lemma = e[1]["lemma"]
                break

        hw_glosses = dictionary_interface.sense_glosses(hw_lemma)
        if len(hw_glosses) == 0:
            log.info("hw: {} has 0 glosses".format(hw_lemma))
            return {
                "hw": None,
                "err": "headword {} has no glosses in {}".format(
                    hw_lemma, collname)
            }

        tokens_before = []
        ii = hw_idx - 1
        while(ii >= 0 and len(tokens_before) < radius):
            lemma = sentence[ii][1].get("lemma")
            if (
                lemma is not None and
                len(lemma) >= min_token_len
            ):
                if get_glosses:
                    glosses = dictionary_interface.sense_glosses(lemma)
                else:
                    glosses = [{"def": "--none--", "gloss": "--none--"}]
                if len(glosses) > 0:
                    tokens_before.insert(0, {
                        "lemma": lemma,
                        "glosses": glosses
                    })
            ii -= 1

        tokens_after = []
        ii = hw_idx + 1
        while(ii < len(sentence) and len(tokens_after) < radius):
            lemma = sentence[ii][1].get("lemma")
            if (
                lemma is not None and
                len(lemma) >= min_token_len
            ):
                if get_glosses:
                    glosses = dictionary_interface.sense_glosses(lemma)
                else:
                    glosses = [{"def": "--none--", "gloss": "--none--"}]
                if len(glosses) > 0:
                    tokens_after.append({
                        "lemma": lemma,
                        "glosses": glosses
                    })
            ii += 1

        # log.debug("context1({}): {:.2f}".format(mytid, time() - tstart))
        return {
            "hw": {"lemma": hw_lemma, "glosses": hw_glosses},
            "context": tokens_before + tokens_after
        }

    def test_context1(self, mytid, hw=""):
        res = ""
        context = self.get_context1(
            mytid, collname="slownet", radius=2, get_glosses=True)
        if context["hw"] is None:
            return context["err"] + "<br><br>"
        res = "hw: {}<br>sentence: {}<br>".format(
            hw, self.get_sentence(mytid))
        tfigf_input = []
        glosses = [context["hw"]] + context["context"]
        for e in glosses:
            res += "--->lemma: {} ({} senses)<br>".format(
                e["lemma"], len(e["glosses"]))
            for g in e["glosses"]:
                res += "{}<br>".format(str(g))
                tfigf_input.append(" ".join(k_utils.tokenize_multiple(
                    g["gloss"],
                    min_token_len=3,
                    stem=k_utils.stem_eng
                )))
        res += "<br><br>"
        return res

    def calc_all_senses(self, lesk_algorithm):
        allcount = 0
        count = 0
        for k, e in self.entries.items():
            allcount += len(e.raw_frames)
        for k, e in self.entries.items():
            if k == "biti":  # skip this huge bag of words
                continue
            for frame in e.raw_frames:
                count += 1
                if count % 10 == 0:
                    log.info("calc_all_senses: ({}/{})".format(
                        count, allcount))
                lesk_algorithm(frame.tids[0])
        return None

    def calc_all_senses_kmeans(self, kmeans_algorithm):
        tstart = time()
        allcount = len(self.entries)
        count = 0
        avg_times = []
        for key in self.entries:
            count += 1
            if key == "biti":
                continue
            # cluster frames of each entry
            log.info("calc_all_senses_kmeans: ({}/{}) [{}]".format(
                count, allcount, key))
            kmeans_algorithm(key)
            """
            try:
                kmeans_algorithm(key)
            except ValueError:
                continue
            """
            avg_times.append(1.0 * (time() - tstart) / count)
            log.info("avg_time: {:.2f}s".format(avg_times[-1]))
        log.info("calc_all_senses_kmeans in {:.2f}s.".format(time() - tstart))
        return None


if __name__ == "__main__":
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    log.addHandler(ch)
    # run ssj_struct to create a ssj_test.pickle file
    with open("ssj_test.pickle", "rb") as file:
        ssj = pickle.load(file)

    vallex = Vallex()
    vallex.read_ssj(ssj)

    vallex.sorted_words = {}
    vallex.gen_sorted_words()

    vallex.functors_index = {}
    vallex.gen_functors_index()
