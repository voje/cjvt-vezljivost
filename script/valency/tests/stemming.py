from polyglot.text import Word
from valency import k_utils


def my_stem(word):
    # Works fine, tokenize the text first.
    w = Word(word, language="sl")
    return w[:-1]


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

besedila1 = [
    'z grabljenjem', 'spraviti skupaj', 'pograbiti listje, seno',
    'pograbiti odpadke v kot', 'pograbiti travo na kup', 'očistiti, izravnati',
    'pograbiti stezice v parku', 'spomladi pograbijo vrtove',
    'pograbiti gredice, krtine',
    'z rokami spraviti k sebi', 'papirje na pisalni mizi je pograbil na kup',
    'pohlepno si prisvojiti dobrine', 'vse hoče pograbiti, hišo in gozd',
]

besedila2 = [
    "berem, beremo, bere, branje, berljiv, berljivost",
    "berljivo, brati, bratje, bratskost, brat, berač, beračiti, beračimo",
]

testing = besedila2

stemmed = sorted(k_utils.tokenize_multiple(
    testing, min_token_len=3, stem=k_utils.stem_slo))

for w in stemmed:
    print(w)

"""
for b in besedila1:
    for w in b.split(" "):
        stem = k_utils.stem_slo(w)
        stemmed.append((w, stem))
for entry in sorted(stemmed, key=lambda x: x[0]):
    print("{:<20}{:<20}".format(entry[0], entry[1]))
"""
