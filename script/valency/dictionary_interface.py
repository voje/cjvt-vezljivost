from valency import k_utils
import logging
from time import time
from valency.k_utils import dict_safe_key as dsk
from copy import deepcopy as DC

log = logging.getLogger(__name__)

# Upper limit for how many senses a lemma can have.
GUL = 20
SLOWNET_CACHE = "slownet_glosses_cache"


class DictionaryInterface:
    def __init__(self, vallex, dictionary):
        self.vallex = vallex
        self.dictionary = "interface"

    def find(self, lemma):
        return []

    def contains(self, lemma, upper_limit=GUL):
        # useless. need to check if sense_glosses returns non empty list
        res = self.find(lemma)
        if upper_limit is not None and len(res) > upper_limit:
            return False
        return (len(res) is not 0)

    def cached_glosses(self, lemma):
        # preprocessed self_glosses (not used)
        res = list(self.vallex.db.cached_glosses.find(
            {"lemma": lemma, "dictionary": self.dictionary}))
        if len(res) == 0:
            return []
        return res[0]["glosses"]

    def sense_glosses(self, lemma):
        # array: gloss for each sense
        # gloss: {"gloss": ["<sense>", ...], "def": ["<sense"], ...}
        return "dictionary_interface.py: not_yet_implemented"

    # Recursively pull strgins out of a dictionary,
    # based on a list of keys.
    # uses self.recursion_buffer
    def pull_strings_wrapper(self, element, keys):
        if element is None:
            return []
        self.recursion_buffer = []
        self.pull_strings(element, keys)
        return self.recursion_buffer[:]

    def pull_strings(self, element, keys):
        # Recursively pull values out of a dict.
        # correct key + element as string or list of strings
        for k, e in element.items():
            if k not in keys:
                continue
            if isinstance(e, dict):
                self.pull_strings(e, keys)
            elif isinstance(e, str):
                self.recursion_buffer.append(e)
            elif isinstance(e, list):
                for ee in e:
                    if isinstance(ee, dict):
                        self.pull_strings(ee, keys)
                    elif isinstance(ee, str):
                        self.recursion_buffer.append(ee)


class Sskj(DictionaryInterface):
    def __init__(self, vallex):
        super().__init__(vallex, "sskj")

    def find(self, lemma):
        res = list(self.vallex.db.sskj.find(
            {"ns0:entry.ns0:form.ns0:orth": lemma}
        ))
        return res

    def sense_glosses(self, lemma, upper_limit=GUL):
        entries = self.find(lemma)
        if upper_limit is not None and len(entries) > upper_limit:
            log.info("sense_glosses({}): too many sense entries".format(lemma))
            return []
        senses = []
        if len(entries) == 0:
            return []
        for e in entries:
            senses.extend(dsk(
                e["ns0:entry"], "ns0:sense"))
        keys = [
            "ns0:def", "ns0:cit", "ns0:quote",
            "ns0:gloss", "ns0:sense", "ns0:orth",
            "ns0:form", "#text"
        ]
        glosses = []
        for s in senses:
            gloss = self.pull_strings_wrapper(s, keys)
            if len(gloss) == 0:
                continue
            glosses.append({
                "gloss": gloss,
                "def": self.pull_strings_wrapper(s, ["ns0:sense", "ns0:def"])
            })
        return glosses


class SloWnet(DictionaryInterface):
    def __init__(self, vallex):
        super().__init__(vallex, "slownet")
        self.hypernym_buffer = []

    def slo_to_eng(self, lemma):

        def helper_get_eng_lemmas(r):
            res = []
            for literal in dsk(r, "SYNONYM"):
                if literal["@xml:lang"] == "en":
                    for lt in dsk(literal, "LITERAL"):
                        res.append(lt["#text"])
            return res

        # takes a slo token, returns array of english counterparts
        results = self.find(lemma)
        eng_lemmas = []
        for r in results:
            eng_lemmas.extend(helper_get_eng_lemmas(r))
        return eng_lemmas

    def helper_get_hypernyms(self, entry):
        res = []
        dd = dsk(entry, "ILR")
        for d in dd:
            if d["@type"] == "hypernym":
                res.append(d["#text"])
        return res

    def helper_get_en_literals(self, entry):
        res = []
        synonyms = dsk(entry, "SYNONYM")
        for syn in synonyms:
            if syn["@xml:lang"] == "en":
                literals = dsk(syn, "LITERAL")
                for lit in literals:
                    res.append(lit["#text"])
        return res

    def rek_root_chain(self, slownet_id):
        entry = self.find_by_id(slownet_id)
        if entry is None:
            return []
        res = self.helper_get_en_literals(entry)
        for hypernym_id in self.helper_get_hypernyms(slownet_id):
            res.extend(self.rek_root_chain(hypernym_id))
        return res

    def root_chain(self, lemma):
        cached = list(self.vallex.db.cached_root_chains.find({
            "lemma": lemma
        }))
        if cached:
            return cached[0]["data"]

        res = self.slo_to_eng(lemma)
        entries = self.find(lemma)
        start_hypernym_ids = []
        for ent in entries:
            start_hypernym_ids.extend(self.helper_get_hypernyms(ent))
        for shi in start_hypernym_ids:
            res.extend(self.rek_root_chain(shi))
        self.vallex.db.cached_root_chains.insert({
            "lemma": lemma,
            "data": res
        })
        return res

    def find_by_id(self, slownet_id):
        res = list(self.vallex.db.slownet.find({"ID": slownet_id}))
        if len(res) == 0:
            log.error("ID: {} not in db.slownet.".format(slownet_id))
            return None
        return res[0]

    def find(self, lemma):
        return list(self.vallex.db.slownet.find({"slo_lemma": lemma}))
        """
        # elemMatch for array query
        res = list(self.vallex.db.slownet.find({
            "SYNONYM": {'$elemMatch': {
                "LITERAL": {'$elemMatch': {"#text": lemma}}
            }}
        }))
        """

    def hypernyms(self, slownet_id, level):
        if level == 3:
            return
        elements = list(self.vallex.db.slownet.find({"ID": slownet_id}))
        if len(elements) == 0:
            return
        for e in elements:
            ei = self.extract_element_info(e)
            self.hypernym_buffer.append({
                "def": ei["domain"] + ei["def"],
                "gloss": ei["domain"] + ei["def"] + ei["usage"]
            })
            for ilr in ei["ilr"]:
                self.hypernyms(ilr, level + 1)

    def extract_element_info(self, e):
        domain = []
        dd = dsk(e, "DOMAIN")
        for d in dd:
            domain.append(d)
        definition = []
        dd = dsk(e, "DEF")
        for d in dd:
            if d["@xml:lang"] == "en":
                definition.append(d["#text"])
        ilr = []
        dd = dsk(e, "ILR")
        for d in dd:
            if d["@type"] == "hypernym":
                ilr.append(d["#text"])
        usage = []
        dd = dsk(e, "USAGE")
        for d in dd:
            if d["@xml:lang"] == "en":
                usage.append(d["#text"])
        return {
            "domain": domain,
            "def": definition,
            "ilr": ilr,
            "usage": usage,
        }

    def sense_glosses(self, lemma, upper_limit=GUL):
        # stime = time()

        # caching
        db_key = {
            "lemma": lemma,
            "upper_limit": upper_limit
        }
        cache = list(self.vallex.db[SLOWNET_CACHE].find(db_key))
        if len(cache) > 0:
            return cache[0]["data"]

        entries = self.find(lemma)
        if upper_limit is not None and len(entries) > upper_limit:
            # log.info("sense_glosses({}): too many senses".format(lemma))
            return []
        ret_glosses = []
        for e in entries:
            defs = []
            glosses = []
            self.hypernym_buffer = []
            ei = self.extract_element_info(e)
            self.hypernym_buffer.append({
                "def": ei["domain"] + ei["def"],
                "gloss": ei["domain"] + ei["def"] + ei["usage"]
            })
            for ilr in ei["ilr"]:
                self.hypernyms(ilr, 1)

            [defs.extend(x["def"]) for x in self.hypernym_buffer]
            [glosses.extend(x["gloss"]) for x in self.hypernym_buffer]
            ret_glosses.append({
                "def": defs,
                "gloss": glosses,
            })

        # log.debug("slownet.sense_glosses({}): {:.2f}s".format(
        #     lemma, time() - stime))

        # caching
        db_entry = {
            "lemma": db_key["lemma"],
            "upper_limit": db_key["upper_limit"],
            "data": ret_glosses
        }
        self.vallex.db.slownet_sense_glosses.update(
            db_key, db_entry, upsert=True
        )
        return ret_glosses


class Sskj2(DictionaryInterface):
    def __init__(self, vallex):
        super().__init__(vallex, "sskj")

    def find(self, lemma):
        pos = "glagol"
        if lemma[-1] == "_":
            pos = "pridevnik"
        res = list(self.vallex.db.sskj.find({
            "izt_clean": lemma,
            "pos": pos
        }))
        return res

    def count_senses(self, lemma):
        entries = self.find(lemma)
        if len(entries) == 0:
            return 0
        ol = dsk(entries[0], "ol")
        if len(ol) == 0:
            return 1
        return len(ol[0]["li"])

    def sense_glosses(self, lemma, upper_limit=GUL):

        def helper_dict_safe_add(dic, key, el):
            if key not in dic:
                dic[key] = []
            dic[key].append(el)

        def helper_pull_rec(el_lst, res_dct):
            for el in el_lst:
                if isinstance(el, dict):
                    if ("@title" in el) and ("#text" in el):
                        helper_dict_safe_add(
                            res_dct, el["@title"], el["#text"])
                    if "span" in el:
                        helper_pull_rec(dsk(el, "span"), res_dct)
                    if ("ol" in el) and ("li" in el["ol"]):
                        helper_pull_rec(el["ol"]["li"], res_dct)
                    if "li" in el:
                        helper_pull_rec(el["li"], res_dct)

        entries = self.find(lemma)
        if len(entries) == 0:
            return []
        if len(entries) > 1:
            log.warning("{} entries for {} in sskj2.".format(
                len(entries), lemma))
        glosses_per_entry = []
        for idx, entry in enumerate(entries):
            res_dict = {}
            if "span" in entry:
                helper_pull_rec(dsk(entry, "span"), res_dict)
            # senses
            res_dict["senses"] = []
            if ("ol" in entry) and ("li" in entry["ol"]):
                for el in dsk(entry["ol"], "li"):
                    tmp = {"sskj_sense_id": el["span"][0]}
                    helper_pull_rec(dsk(el, "span"), tmp)
                    helper_pull_rec(dsk(el, "ol"), tmp)
                    res_dict["senses"].append(DC(tmp))

            def helper_create_gloss(dct):
                keys = ["Razlaga", "Zgled", "Stranska razlaga", "Sopomenka"]
                ret = []
                for k in keys:
                    ret.extend(dsk(dct, k))
                return ret

            glosses = []
            n_senses = len(res_dict["senses"])
            if n_senses == 0:
                glosses.append({
                    "sskj_sense_id": "1-1",
                    "gloss": helper_create_gloss(res_dict),
                    "def": dsk(res_dict, "Razlaga")
                })
                return glosses

            for sense in res_dict["senses"]:
                glosses.append({
                    "sskj_sense_id": "{}-{}".format(
                        sense["sskj_sense_id"], n_senses),
                    "gloss": helper_create_gloss(sense),
                    "def": dsk(sense, "Razlaga")
                })
            glosses_per_entry.append(glosses)

        # add entry_id before the_sense id
        # entry_id-sskj_sense_id-n_senses
        all_glosses = []
        for idx, glosses in enumerate(glosses_per_entry):
            entry_id = idx + 1  # start with 1
            for gloss in glosses:
                gloss["sskj_sense_id"] = "{}-{}".format(
                    entry_id, gloss["sskj_sense_id"])
                all_glosses.append(gloss)
        return all_glosses
