import xml.etree.ElementTree as ET
from copy import deepcopy as DC
from time import time
import re
import logging
import sys
import pickle

log = logging.getLogger(__name__)

ET.register_namespace("xml", "http://www.w3.org/XML/1998/namespace")
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


# |$ for a default empty match
re_int = re.compile(r"t\d+|$")


# For sorting a "s" section in ssj; returns key as integer.
# example: "S123.t34" --> 34
def re_lmbd(el):
    s = re_int.findall(el)[0]
    if len(s) == 0:
        return 0
    else:
        return int(s[1:])


class SsjEntry:
    def __init__(self, ssj_id, s, deep_links):
        # See ssj xml structure.
        self.id = ssj_id
        self.s = DC(s)
        self.deep_links = DC(deep_links)


class SsjDict:
    def __init__(self):
        self.entries = {}

    """
    def read_xml(self, filepath):
        # No data loss.
        log.info("SsjDict.read_xml({})".format(filepath))
        t_start = time()
        tree = ET.parse(filepath)
        root = tree.getroot()
        stats = {
            "skipped": [],
            "duplicates": []
        }

        for s in root.iter("s"):
            s_id = s.attrib[XML_ID]
            tokens = {}
            for token in s:
                if token.tag == "linkGrp":
                    continue

                if token.tag == "w":
                    tokens[token.attrib[XML_ID]] = {
                        "msd": token.attrib["msd"],
                        "lemma": token.attrib["lemma"],
                        "word": token.text
                    }
                elif token.tag == "c":
                    tokens[token.attrib[XML_ID]] = {
                        "word": token.text
                    }
                else:
                    # <S />
                    pass

            linkGrps = s.findall("linkGrp")
            if len(linkGrps) < 2:
                # Take only entries with both deep and shallow
                # syntactic annotation
                stats["skipped"].append(s_id)
                continue

            linkG = {}
            for el in linkGrps:
                if el.attrib["type"] == "dep":
                    linkG["dep"] = el
                elif el.attrib["type"] == "SRL":
                    linkG["SRL"] = el
                else:
                    raise KeyError("Unknown linkGrp.")

            if s_id in self.entries:
                stats["duplicates"].append(s_id)
            self.entries[s_id] = SsjEntry(
                s_id,
                s.attrib["n"],
                tokens,
                create_edge_dict(linkG["dep"]),
                create_edge_dict(linkG["SRL"])
            )

        t_end = time()
        log.info("Time: {}s.".format(t_end - t_start))
        log.info(
            "{} duplicates, skipped {} elements (missing linkGrp).".format(
                len(stats["duplicates"]), len(stats["skipped"]))
        )
    """

    def read_xml_v2(self, filepath):
        NS_DICT = {
            "tei": "http://www.tei-c.org/ns/1.0",
            "xml": "http://www.w3.org/XML/1998/namespace",
        }

        def ns_prefix(ns):
            return "{" + NS_DICT[ns] + "}"

        def helper_get_sentence(tree_s):
            # all w and pc elements
            ret = []
            for el in tree_s.iter():
                if (
                    el.tag == ns_prefix("tei") + "w" or
                    el.tag == ns_prefix("tei") + "pc"
                ):
                    ret.append(el)
            return ret

        def helper_get_functor_links(tree_s):
            # links for SRL linkGrp
            lg = None
            for linkGrp in tree_s.findall("tei:linkGrp", NS_DICT):
                if linkGrp.attrib["type"] == "SRL":
                    lg = linkGrp
                    break
            else:
                return []
            ret = []
            for link in lg:
                ret.append(link)
            return ret

        def helper_gen_deep_links(link_list):
            deep_links = []
            for link in link_list:
                deep_links.append({
                    "from": link.attrib["target"].split(" ")[0][1:],
                    "to": link.attrib["target"].split(" ")[1][1:],
                    "functor": link.attrib["ana"].split(":")[1]
                })
            return deep_links

        log.info("SsjDict.read_xml({})".format(filepath))
        t_start = time()
        stats = {
            "total_count": 0,
            "deep_roles_count": 0,
            "duplicated_sid": 0,
        }
        tree = ET.parse(filepath)
        root = tree.getroot()

        for s in root.findall(".//tei:s", NS_DICT):
            stats["total_count"] += 1
            s_id = s.attrib[ns_prefix("xml") + "id"]

            # get_functors (deep semantic roles)
            functor_links = helper_get_functor_links(s)
            if len(functor_links) == 0:
                continue
            stats["deep_roles_count"] += 1

            # get_sentence
            tokens = {}
            for token in helper_get_sentence(s):
                tid = token.attrib[ns_prefix("xml") + "id"]
                if token.tag == ns_prefix("tei") + "w":
                    tokens[tid] = {
                        "msd": token.attrib["ana"].split(":")[1],
                        "lemma": token.attrib["lemma"],
                        "word": token.text
                    }
                elif token.tag == ns_prefix("tei") + "pc":
                    tokens[tid] = {
                        "word": token.text
                    }
                else:
                    log.warning("Unrecognized sentence element: " + token.tag)
                    exit(1)

            if s_id in self.entries:
                log.warning("duplicated sentence: " + s_id)
                stats["duplicated_sid"] += 1
                continue

            self.entries[s_id] = SsjEntry(
                s_id,
                tokens,
                helper_gen_deep_links(functor_links)
            )

        t_end = time()
        log.info("Time: {}s.".format(t_end - t_start))
        log.info(str(stats))


if __name__ == "__main__":
    # testing
    log.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    log.addHandler(ch)

    # Load
    fpath = "../../data/ssj500k-sl.TEI/ssj500k-sl.body.xml"
    ssj = SsjDict()
    ssj.read_xml_v2(fpath)
    with open("ssj_test.pickle", "wb") as file:
        pickle.dump(ssj, file)
