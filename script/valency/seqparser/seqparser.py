from bs4 import BeautifulSoup as BS
import re
from collections import defaultdict
from time import time
import pickle
import json
from copy import deepcopy as DC

# Match sese ordinals (1., 2., ...)
rord = re.compile(r"^ *[0-9]+\. *$")

# Get rid of accented characters.
intab = "ÁÉÍÓÚàáäçèéêìíîñòóôöùúüčŔŕ"
outtb = "AEIOUaaaceeeiiinoooouuučRr"
transtab = str.maketrans(intab, outtb)


class Seqparser:
    def __init__(self):
        pass

    # main functions
    def html_to_raw_pickle(self, sskj_html_filepath, raw_pickle_filepath):
        entries = dict(self.parse_file(sskj_html_filepath, self.parse_line))
        print("entries len: " + str(len(entries)))
        with open(raw_pickle_filepath, "wb") as f:
            tmpstr = json.dumps(dict(entries))
            pickle.dump(tmpstr, f)
        # debugging

    def raw_pickle_to_parsed_pickle(
        self, raw_pickle_filepath, parsed_pickle_filepath,
        se_list_filepath
    ):
        data = self.load_raw_pickle(raw_pickle_filepath)
        print("raw_pickle data len: " + str(len(data)))
        se_list = self.gen_se_list(data)
        print("se_list len: " + str(len(se_list)))
        with open(se_list_filepath, "wb") as f:
            pickle.dump(se_list, f)
        data1 = self.remove_se(data)
        data2 = self.reorganize(data1, se_list)
        print("data2 len: " + str(len(data2.keys())))
        with open(parsed_pickle_filepath, "wb") as f:
            pickle.dump(data2, f)

    # helper html reading functions
    def parse_file(self, path, f_parse_line):
        tstart = time()
        entries = defaultdict(list)
        with open(path, "r") as f:
            for line in f:
                data = f_parse_line(line)
                if data is not None:
                    entries[data["izt_clean"]].append(data)
        print("parse_file({}) in {:.2f}s".format(path, time() - tstart))
        return entries

    def parse_line(self, line):
        def helper_bv_set(g_or_p):
            if g_or_p not in ["G", "P"]:
                print("Err g_or_p.")
                exit(1)
            if data.get("bv") is not None:
                if data["bv"] != g_or_p:
                    print(str(line))
                    # exit(1)
            data["bv"] = g_or_p
        data = {
            "izt": "",
            "izt_clean": "",
            "senses": defaultdict(list)
        }
        soup = BS(line, "html.parser")

        current_sense_id = "0"
        for span in soup.find_all("span"):

            # sense id
            if span.string is not None:
                rmatch = rord.match(span.string)
                if rmatch is not None:
                    current_sense_id = rmatch.group().strip()

            title = span.attrs.get("title")
            if title is not None:
                title = title.lower()

                # only verbs and adjectives
                if "glagol" in title:
                    helper_bv_set("G")
                    data["bv_full"] = title
                elif "pridevn" in title:
                    helper_bv_set("P")
                    data["bv_full"] = title

                # žšč
                if title == "iztočnica":
                    data["izt"] = span.string
                    data["izt_clean"] = span.string.translate(transtab).lower()

                # sense description
                if title == "razlaga" and span.string is not None:
                    data["senses"][current_sense_id].append(
                        ("razl", span.string))
                    if "pridevnik od" in span.string:
                        helper_bv_set("P")

                if title == "sopomenka":
                    subspan = span.find_all("a")[0]
                    if subspan.string is not None:
                        data["senses"][current_sense_id].append(
                            ("sopo", subspan.string))

        # save verbs and adjectives
        if (
            ("bv" not in data) or
            (data["bv"] != "P" and data["bv"] != "G")
        ):
            return None

        # sanity check
        if data["bv"] == "P" and " se" in data["izt_clean"]:
            print(data)
            exit(1)

        # append _ to adjective keywords
        if data["bv"] == "P":
            data["izt_clean"] = data["izt_clean"] + "_"

        # cleanup
        if "bv" not in data:
            print("Should not be here (no bv).")
            exit(1)
        del(data["bv"])
        if "bv_full" in data:
            del(data["bv_full"])

        return data

    # helper functions
    def load_raw_pickle(self, raw_pickle_filepath):
        with open(raw_pickle_filepath, "rb") as f:
            tmpstr = pickle.load(f)
            return json.loads(tmpstr)

    def helper_loop(self, data, fnc):
        for k, lst in data.items():
            for el in lst:
                fnc(el)

    def gen_se_list(self, data):

        def fnc1(el):
            ic = el["izt_clean"]
            if " se" in ic:
                se_list.append(ic)

        def fnc2(el):
            ic = el["izt_clean"]
            if ic in se_pruned:
                se_pruned.remove(ic)

        # hw entries that only exist with " se"
        se_list = []
        self.helper_loop(data, fnc1)
        se_pruned = set([hw.split(" se")[0] for hw in se_list])
        self.helper_loop(data, fnc2)
        return sorted(list(se_pruned))

    def remove_se(self, data):

        def fnc1(el):
            nel = DC(el)
            ic = nel["izt_clean"]
            if " se" in ic:
                nic = ic.split(" se")[0]
                nel["izt_clean"] = nic
            data_new[nel["izt_clean"]].append(nel)

        data_new = defaultdict(list)
        self.helper_loop(data, fnc1)
        return dict(data_new)

    def reorganize(self, data, se_list):
        # some hw entries have several headwords,
        # some senses have subsenses
        # index everything, make 1 object per hw

        def helper_prune(sense_str):
            # remove space padding
            sense_str = sense_str.strip()

            if len(sense_str) == 1:
                return sense_str

            # remove banned characters from string ending
            banned = ": ; . , - ! ?".split(" ")
            if sense_str[-1] in banned:
                return sense_str[:-1]

            return sense_str

        data_new = {}
        for k, lst in data.items():
            new_el = {
                "hw": k,
                "has_se": k in se_list,
                "senses": []
            }

            # if there is a single hw entry, hw_id is 0
            if len(lst) == 1:
                homonym_id = -1
            else:
                homonym_id = 0

            # loop homonyms
            for el in lst:
                homonym_id += 1
                # loop top lvl sense ids
                for sense_id, sens_lst in el["senses"].items():
                    # loop subsenses
                    for i, sens in enumerate(sens_lst):
                        nsid = sense_id.split(".")[0]
                        if len(sens_lst) == 1:
                            nsid += "-0"
                        else:
                            nsid += ("-" + str(i + 1))
                        new_sense = {
                            "homonym_id": homonym_id,
                            # sense_id: sense_id-subsense_id
                            "sense_id": nsid,
                            "sense_type": sens[0],
                            "sense_desc": helper_prune(sens[1]),
                        }
                        new_el["senses"].append(new_sense)
            hw = new_el["hw"]
            if hw in data_new:
                print("Shouldn't be here.")
                print(new_el)
                exit(1)
            data_new[hw] = DC(new_el)
        # return data_new

        # check
        for hw, el in data_new.items():
            for sens in el["senses"]:
                if sens["sense_desc"] is None:
                    print(sens)

        return data_new


def plst(lst):
    for el in lst:
        print(el)


if __name__ == "__main__":
    datapath = "../../../data"
    html_filepath = datapath + "/sskj/sskj2_v1.html"
    raw_pickle_filepath = datapath + "/tmp_pickles/raw_sskj.pickle"
    parsed_pickle_filepath = datapath + "/no_del_pickles/sskj_senses.pickle"
    se_list_filepath = datapath + "/no_del_pickles/se_list.pickle"

    p = Seqparser()

    if True:
        print("html_to_raw_pickle({}, {})".format(
            html_filepath, raw_pickle_filepath))
        print("Big file, this might take a while (2 min).")
        tstart = time()
        p.html_to_raw_pickle(html_filepath, raw_pickle_filepath)
        print("Finished in {:.2f}.".format(time() - tstart))

    if True:
        print("raw_pickle_to_parsed_pickle({}, {}, {})".format(
            raw_pickle_filepath, parsed_pickle_filepath, se_list_filepath))
        tstart = time()
        p.raw_pickle_to_parsed_pickle(
            raw_pickle_filepath, parsed_pickle_filepath, se_list_filepath)
        print("Finished in {:.2f}.".format(time() - tstart))
    print("Done.")
