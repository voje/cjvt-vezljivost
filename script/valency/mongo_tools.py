import pymongo
import xmltodict
import xml.etree.ElementTree as ET
from time import time
import json
from valency.sskj_scraper import SskjScraper
from bs4 import BeautifulSoup

# Get rid of accented characters.
intab = "ÁÉÍÓÚàáäçèéêìíîñòóôöùúüčŔŕ"
outtb = "AEIOUaaaceeeiiinoooouuučRr"
transtab = str.maketrans(intab, outtb)


def mongo_test():
    client = pymongo.MongoClient(
        "mongodb://{}:{}@127.0.0.1:26633/texts".format("kristjan", "simple567")
    )

    db = client.texts

    coll = db.test

    print(coll.find_one())


def basic_connection(ip_addr=None, port=None):
    if ip_addr is None:
        ip_addr = "127.0.0.1"
    if port is None:
        port = 26644
    client = pymongo.MongoClient(
        "mongodb://{}:{}@{}:{}/texts".format(
            "kristjan", "simple567", ip_addr, str(port))
    )
    err_msg = "OK"
    try:
        client.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as err:
        err_msg = err
        return (None, err_msg)
    db = client.texts
    return (db, err_msg)


def check_collections(db, coll_names):
    collections = db.collection_names()
    for cn in coll_names:
        if cn not in collections:
            db.create_collection(cn)


def prepare_user_tokens(db):
    CNAME = "v2_user_tokens"
    db[CNAME].drop()
    db.create_collection(CNAME)
    EXPIRE = 151200  # 2 days
    # EXPIRE = 10  # 10 sec
    db[CNAME].ensure_index("date", expireAfterSeconds=EXPIRE)

    # user this: utc_timestamp = datetime.datetime.utcnow()
    # user_tokens.insert({
    #   '_id': 'utc_session', "date": utc_timestamp,
    #   "session": "test session"})


def sskj_to_mongo(sskj_path):
    # Deprecated, use sskj2_to_mongo
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    ts = time()
    sskj = ET.parse(sskj_path).getroot()
    db = basic_connection()
    col_names = ["sskj"]
    for cn in col_names:
        if cn in db.collection_names():
            db[cn].drop()
    text = sskj.find("tei:text", ns)
    body = text.find("tei:body", ns)
    n_ent = 0
    for entry in body.findall("tei:entry", ns):
        n_ent += 1
        tmpstr = ET.tostring(entry)
        datachunk = xmltodict.parse(tmpstr)
        dictchunk = json.loads(json.dumps(datachunk))
        """
        pp = pprint.PrettyPrinter()
        pp.pprint(dictchunk)
        """
        db.sskj.insert(dictchunk)
    # iskanje: db.sskj.find({'ns0:entry.ns0:form.ns0:orth':"kaplanček"})
    print("sskj to mongo: {} entries in {:.2f}s".format(n_ent, time() - ts))


def slownet_to_mongo(slw_path):
    # .slownet contains the database from .xml file
    # added toplevel field ["slo_lemma"] for faster querying
    ts = time()
    slownet = ET.parse(slw_path).getroot()
    db = basic_connection()
    col_names = ["slownet_map", "slownet"]
    for cn in col_names:
        if cn in db.collection_names():
            db[cn].drop()

    slo_to_id = {}
    for synset in slownet.findall("SYNSET"):
        tmpstr = ET.tostring(synset)
        datachunk = xmltodict.parse(tmpstr)
        dictchunk = json.loads(json.dumps(datachunk))
        dictchunk = dictchunk["SYNSET"]
        # pp.pprint(dictchunk)

        # insert into slo_ti_id
        if "SYNONYM" in dictchunk:
            synonyms = dictchunk["SYNONYM"]
            if not isinstance(synonyms, list):
                synonyms = [synonyms]
            for syn in synonyms:
                if syn["@xml:lang"] == "sl":
                    if "LITERAL" in syn:
                        literals = syn["LITERAL"]
                        if not isinstance(literals, list):
                            literals = [literals]
                        for lit in literals:
                            slo_keyword = lit["#text"]
                            if "." in slo_keyword:
                                continue
                            if "slo_lemma" not in dictchunk:
                                dictchunk["slo_lemma"] = []
                            dictchunk["slo_lemma"].append(slo_keyword)
        db.slownet.insert(dictchunk)

    # pp.pprint(slo_to_id)
    db.slownet.ensure_index([("id", pymongo.ASCENDING)])
    db.slo_to_id.insert(slo_to_id)
    print("sloWNet to mongo in {:.2f}s".format(time() - ts))


def scrape_sskj():
    # Deprecated!
    # Walk through keys in slo_to_id and scrape sskj data.
    client = pymongo.MongoClient(
        "mongodb://{}:{}@127.0.0.1:26633/texts".format("kristjan", "simple567")
    )
    db = client.texts
    words_list = sorted(db.slo_to_id.find_one())

    print(len(words_list))
    sscraper = SskjScraper()

    last_word = "nogometaš"
    db.scraped_sskj.remove({"word": last_word})
    lock = True
    for word in words_list:
        if word == last_word:
            lock = False

        if not lock:
            res = sscraper.scrape(word)
            if len(res) > 0:
                db.scraped_sskj.insert({"word": word, "bag": res})


def sskj2_to_mongo(sskj2_path):
    tstart = time()

    db = basic_connection()
    col_names = ["sskj2"]
    for cn in col_names:
        if cn in db.collection_names():
            db[cn].drop()

    with open(sskj2_path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    divs = soup.find_all("div")
    for i, div in enumerate(divs):
        if (i) % 100 == 0:
            print("{}/{}".format(i, len(divs)))
        datachunk = xmltodict.parse(str(div))
        datachunk = datachunk["div"]

        # pos (besedna vrsta)
        pos_keywords = {
            "samostalnik": 0,
            "pridevnik": 0,
            "glagol": 0,
            "prislov": 0,
            "predlog": 0,
            "členek": 0,
            "veznik": 0,
            "medmet": 0,
            "povedkovnik": 0
        }
        for span in div.find_all("span"):
            attrs = [e for k, e in span.attrs.items()]
            for attr in attrs:
                for ak in attr.split(" "):
                    akl = ak.lower()
                    if akl in pos_keywords:
                        pos_keywords[akl] += 1
        pos = "unknonw"
        pos_max = 0
        for k, e in pos_keywords.items():
            if e > pos_max:
                pos = k
                pos_max = e
        datachunk["pos"] = pos

        # izt_clean
        izts = div.find_all("span", {"title": "Iztočnica"})
        if len(izts) == 0:
            print("Entry {} has no Iztočnica.".format(i))
            continue
        izt = ((izts[0].text).translate(transtab)).lower()
        ispl = izt.split(" ")
        has_se = False
        if len(ispl) and ispl[-1] == "se":
            izt = " ".join(ispl[:-1])
            has_se = True
        datachunk["izt_clean"] = izt
        datachunk["has_se"] = has_se

        dictchunk = json.loads(json.dumps(datachunk))
        db.sskj.insert(dictchunk)

    db.sskj.create_index([("izt_clean", pymongo.TEXT)])
    print("sskj2 to mongo: {} entries in {:.2f}s".format(
        len(divs), time() - tstart))
    return None


if __name__ == "__main__":
    # slownet_path = "../../data/slownet/slownet-2015-05-07.xml"
    # slownet_to_mongo(slownet_path)

    # scrape_sskj()

    # sskj_path = "../../data/sskj/sskj.p5.xml"
    # sskj_to_mongo(sskj_path)

    # first file for testing, the original file takes up most of RAM
    # sskj2_path = "../../data/sskj/sskj2_200.html"
    # sskj2_path = "../../data/sskj/sskj2_v1.html"
    # sskj2_to_mongo(sskj2_path)

    print("nothing here")
