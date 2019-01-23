import os
import pickle
import nltk
import random
from time import time
import string
from polyglot.text import Word
import logging

log = logging.getLogger(__name__)
sno = nltk.stem.SnowballStemmer("english")


def dict_safe_key(dic, key):
    # Returns a list, no matter what.
    # Transform 1 element into a list.
    # Return key not found as empty list.
    if (
        dic is None or
        key not in dic
    ):
        return []
    subdic = dic[key]
    if not isinstance(subdic, list):
        return [subdic]
    return subdic


def pickle_dump(data, path):
    with open(path, "wb") as file:
        pickle.dump(data, file)
        log.info("Dumped data to {}.".format(path))
    return True


def pickle_load(path):
    ret = None
    if os.path.isfile(path):
        with open(path, "rb") as file:
            ret = pickle.load(file)
            log.info("Loaded data from {}.".format(path))
    return ret  # Returns None in case of failure.


# Implemented bucket sort for alphabetically sorting slovenian words.
# Bucket sort >>>>>>>>>>>>>>>>>>>>
def gen_sbs_alphabet():
    alphabet = "abcčdefghijklmnoprsštuvzž"
    return {letter: (idx + 1) for idx, letter in enumerate(alphabet)}


slo_bucket_sort_alphabet = gen_sbs_alphabet()


def slo_bucket_sort(words, key=None):
    if key is None:
        def key(x):
            return x

    def alph_score(word, idx):
        kword = key(word)
        if idx >= len(kword):
            return 0
        return slo_bucket_sort_alphabet.get(kword[idx]) or 0

    def list_to_bins(words, idx):
        bins = [[] for i in range(len(slo_bucket_sort_alphabet.keys()) + 1)]
        for word in words:
            bins[alph_score(word, idx)].append(word)
        return bins

    def bins_to_list(bins):
        lst = []
        for b in bins:
            for el in b:
                lst.append(el)
        return lst

    maxLen = 0
    for w in words:
        if len(key(w)) > maxLen:
            maxLen = len(key(w))
    maxIdx = maxLen - 1
    for idx in range(maxIdx, -1, -1):
        bins = list_to_bins(words, idx)
        words = bins_to_list(bins)
        """
        print(idx)
        def get_letter(idx, word):
            kword = key(word)
            if idx < len(kword):
                return(kword[idx])
            return "#"
        print([(word, get_letter(idx, word)) for word in words])
        """
    return words
# Bucket sort <<<<<<<<<<<<<<<<<<<<


def stem_slo(x):
    # Simplified;
    # Remove the last syllable.
    w = Word(x, language="sl").morphemes
    ret = "".join(w[:-1])
    return ret


def stem_eng(x):
    return sno.stem(x)


def tokenize(sentence, min_token_len=3, stem=None):
    # input: sentence string
    # output: list of token strings
    if stem is None:
        def stem(x):
            return x
    all_tokens = []
    sent_txt = nltk.sent_tokenize(sentence)
    for sent in sent_txt:
        tokens = nltk.word_tokenize(sent)
        all_tokens.extend(tokens)
    res = []
    for x in all_tokens:
        if x in string.punctuation:
            continue
        stemmed = stem(x.lower())
        if len(stemmed) >= min_token_len:
            res.append(stemmed)
    return res


def tokenize_multiple(str_list, min_token_len=3, stem=None):
    # tstart = time()
    res = []
    for sentence in str_list:
        res.extend(tokenize(sentence, min_token_len, stem))
    # log.debug("tokenize_multiple: {:.2f}s".format(time() - tstart))
    return res


def t_tokenize():
    teststring = "This is a test sentence. I hope it works. .. Asdf. asdf ,,,;"
    print(teststring)
    res = tokenize(teststring, min_token_len=None)
    print(res)


def permute_paths(list2d, x=None, y=None, paths=None, current_path=None):
    # python stuff
    if x is None:
        x = -1
    if paths is None:
        paths = []
    if current_path is None:
        current_path = []

    if x >= len(list2d) - 1:
        paths.append(current_path)
        return paths
    for i in range(len(list2d[x + 1])):
        tmp_path = current_path + [(x + 1, i)]
        # Computational complexity peoblem (prune long lists)
        # len == 12 -> 30%, len == 5 -> 100%
        # if random.randint(0, 100) <= (100 - 10 * (len(list2d) - 5)):
        if True:
            paths = permute_paths(
                list2d,
                x + 1,
                i,
                paths,
                tmp_path
            )
    return paths


def t_permute_paths():
    list2d = [
        ["Greta"],
        ["backflips"],
        ["through", "around"],
        ["North Korea", "kindergarten"],
        ["with", "without"],
        ["a"],
        ["bag of", "abundance of"],
        ["bolts", "janitors"]
    ]

    print(list2d)
    paths = permute_paths(list2d=list2d)
    for path in paths:
        print([list2d[p[0]][p[1]] for p in path])


def find_overlaps(list_a, list_b):
    # Input: two lists.
    # Output: lists of overlapping elements.
    dict_a = {}
    dict_b = {}
    lists = [list_a, list_b]
    dicts = [dict_a, dict_b]
    for lidx in range(len(lists)):
        for elidx in range(len(lists[lidx])):
            el = lists[lidx][elidx]
            if el not in dicts[lidx]:
                dicts[lidx][el] = []
            dicts[lidx][el].append(elidx)

    substrings = []

    sda = sorted(dict_a.keys())
    sdb = sorted(dict_b.keys())

    i_sda = 0
    i_sdb = 0
    while ((i_sda < len(sda) and i_sdb < len(sdb))):
        if sda[i_sda] == sdb[i_sdb]:
            lia = dict_a[sda[i_sda]]
            lib = dict_b[sdb[i_sdb]]
            for llia in lia:
                for llib in lib:
                    tmp_substr = []
                    ii = 0
                    while (
                        (llia + ii < len(list_a)) and
                        (llib + ii < len(list_b)) and
                        (list_a[llia + ii] == list_b[llib + ii])
                    ):
                        tmp_substr.append(list_a[llia + ii])
                        ii += 1
                    ii = 1
                    while (
                        (llia - ii >= 0) and
                        (llib - ii >= 0) and
                        (list_a[llia - ii] == list_b[llib - ii])
                    ):
                        tmp_substr.insert(0, list_a[llia - ii])
                        ii += 1
                    substrings.append(tmp_substr)
        if sda[i_sda] < sdb[i_sdb]:
            i_sda += 1
        else:
            i_sdb += 1

    uniques = set()
    res = []
    for ss in substrings:
        if str(ss) not in uniques:
            uniques.add(str(ss))
            res.append(ss)
    return res


def find_overlaps_str(tokens_a, tokens_b):
    # Strings only.
    overlaps = []
    for N in range(1, 5):
        ngrams_a = []
        for i in range(len(tokens_a)):
            if i + N <= len(tokens_a):
                ngrams_a.append(tuple(tokens_a[i:i + N]))
        ngrams_b = []
        for i in range(len(tokens_b)):
            if i + N <= len(tokens_b):
                ngrams_b.append(tuple(tokens_b[i:i + N]))
        overlaps.extend(list(set(ngrams_a).intersection(set(ngrams_b))))

    res = []
    for ovl in sorted(overlaps, key=lambda x: len(x), reverse=True):
        oovl = " ".join(ovl)
        for r in res:
            if oovl in r:
                break
        else:
            res.append(oovl)
    res[:] = [x.split(" ") for x in res]
    return res


def t_find_overlaps():
    res = []
    input_len = [10, 100, 1000, 10000]
    for ll in input_len:
        alen = ll + int(ll * random.uniform(0.8, 1))
        blen = ll + int(ll * random.uniform(0.8, 1))
        a = [random.randint(0, 100) for x in range(alen)]
        b = [random.randint(0, 100) for x in range(blen)]
        tstart = time()
        find_overlaps(a, b)
        res.append({
            "time": time() - tstart,
            "input_size": ll
        })
    """
    list_a = [6, 6, 4, 8, 3, 2, 2, 5, 6, 3, 4, 7, 5]
    list_b = [5, 3, 6, 8, 6, 6, 5, 3, 2, 6, 7, 8, 3, 2, 3, 2, 2, 5]
    res = find_overlaps(list_a, list_b)
    """
    for r in res:
        print(r)


def t1_find_overlaps():
    t1 = "This is a test sentence. I hope it works. .. Asdf. asdf ,,,;"
    t2 = "this is a seconde sentence. I hope my stuff works."
    print(t1)
    print(t2)
    res = find_overlaps(tokenize(t1), tokenize(t2))
    for r in res:
        print(r)

    print()

    res = find_overlaps_str(tokenize(t1), tokenize(t2))
    for r in res:
        print(r)


def t_find_overlaps_str():
    t1 = [
        'vsa', 'moja', 'možganska', 'beda', 'se', 'združuje',
        'v', 'dejstvu', 'da', 'sem', 'si', 'čeprav', 'sem', 'pozabil',
        'ulico', 'zapomnil', 'hišno', 'številko'
    ]
    t2 = [
        'narediti', 'doseči', 'da', 'se', 'kaj', 'aktivno', 'ohrani',
        'v', 'zavesti', 'zapomniti', 'si', 'imena', 'predstavljenih',
        'gostov', 'dobro', 'natančno', 'slabo', 'si', 'kaj', 'zapomniti',
        'takega', 'sem', 'si', 'zapomnil', 'zapomnite', 'te', 'prizore'
    ]
    res = find_overlaps(t1, t2)
    print(res)


def t_slo_bucket_sort():
    a1 = []
    a2 = []
    with open("./tests/m_besede2.txt") as f:
        for line in f:
            a1.append(line.split("\n")[0])
            a2.append((line.split("\n")[0], random.randint(0, 9)))

    a1 = slo_bucket_sort(a1)
    a2 = slo_bucket_sort(a2, key=lambda x: x[0])

    check = True
    for i in range(len(a1)):
        check &= (a1[i] == a2[i][0])
        print("{:<10}{:>10}".format(str(a1[i]), str(a2[i])))
    print(check)


def t1_slo_bucket_sort():
    words = "_xyz zebra. .bober raca bor borovnica antilopa".split(" ")
    words.append("test space")
    words.append("test srrrr")
    words.append("test saaa")
    for w in slo_bucket_sort(words):
        print(w)


if __name__ == "__main__":
    # t_find_overlaps()
    # t1_find_overlaps()
    # t_tokenize()
    # t_find_overlaps_str()
    t1_slo_bucket_sort()
