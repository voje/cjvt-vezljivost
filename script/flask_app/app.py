# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, url_for, redirect

from valency import k_utils
from valency.ssj_struct import *
from valency.val_struct import *
from valency.reduce_functions import *

import logging
import sys
import json
from flask_cors import CORS
import hashlib
import uuid
import datetime
import string
import random
import smtplib
from email.mime.text import MIMEText
from copy import deepcopy as DC

log = logging.getLogger(__name__)

PORT = 5004
args = []


def get_arg(argname):
    for arg in args:
        if "--{}".format(argname) in arg:
            spl = arg.split("=")
            if len(spl) == 2:
                return spl[1]
            else:
                return True
    else:
        return False


vallex = None
# app = Flask(__name__)

# v2 (serving vuejs frontend)
# change api path in vue to localhost:5004
app = Flask(
    __name__,
    static_folder="./vue/dist/static",
    template_folder="./vue/dist"
)

# when running vuejs via webpack
# CORS(app)
CORS(app, resources={r"/api/*": {
    "origins": "*",
}})


# for testing functions
@app.route("/test_dev")
def test_dev():
    ret = vallex.test_dev()
    return(str(ret) or "edit val_struct.py: test_dev()")


@app.route("/")
def index():
    return(render_template("index.html"))


@app.route("/home", defaults={"pathname": ""})
@app.route("/home/<path:pathname>")
def home(pathname):
    return redirect(url_for("index"), code=302)


@app.route("/api/words")
def api_words():
    return json.dumps({
        "sorted_words": vallex.sorted_words,
        "has_se": vallex.has_se
    })


@app.route("/api/functors")
def api_functors():
    res = []
    for key in sorted(vallex.functors_index.keys()):
        res.append((key, len(vallex.functors_index[key])))
    return json.dumps(res)


@app.route("/api/register", methods=["POST"])
def api_register():
    USERS_COLL = "v2_users"
    b = request.get_data()
    data = json.loads(b.decode())
    username = data["username"]
    password = data["password"]
    email = data["email"]
    if (
        username == "" or
        password == "" or
        email == ""
    ):
        return "ERR"
    existing = list(vallex.db[USERS_COLL].find({
        "$or": [{"username": username}, {"email": email}]
    }))
    if len(existing) > 0:
        return "ERR: Username or email already exists."
    entry = {
        "username": username,
        "hpass": hashlib.sha256(
            password.encode("utf-8")).hexdigest(),
        "email": hashlib.sha256(
            email.encode("utf-8")).hexdigest()
    }
    vallex.db[USERS_COLL].insert(entry)
    return "OK"


@app.route("/api/login", methods=["POST"])
def api_login():
    USERS_COLL = "v2_users"
    TOKENS_COLL = "v2_user_tokens"
    b = request.get_data()
    data = json.loads(b.decode())
    username = data["username"]
    password = data["password"]
    hpass = hashlib.sha256(password.encode("utf-8")).hexdigest()

    db_user = list(vallex.db[USERS_COLL].find({
        "username": username,
        "hpass": hpass
    }))
    if len(db_user) == 0:
        return json.dumps({"token": None})

    # update or create token
    token = uuid.uuid4().hex
    token_entry = {
        "username": username,
        "date": datetime.datetime.utcnow(),
        "token": token
    }
    vallex.db[TOKENS_COLL].update(
        {"username": token_entry["username"]},
        token_entry,
        upsert=True
    )
    return json.dumps({"token": token})


def send_new_pass_mail(recipient, new_pass):
    # dtime = str(datetime.datetime.now())
    SENDER = "valencaglagolov@gmail.com"
    msg = MIMEText(
        "Pošiljamo vam novo geslo za "
        "vstop v aplikacijo Vezljivostni vzorci slovenskih glagolov.\n"
        "Geslo: {}.".format(new_pass)
    )
    msg["Subject"] = "Pozabljeno geslo"
    msg["From"] = SENDER
    msg["To"] = recipient

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(
            SENDER,
            "rapid limb soapy fermi"
        )
        server.sendmail(SENDER, [recipient], msg.as_string())
        server.close()
        log.info("Sent new password.")
    except Error as e:
        log.error("Sending new password failed")
        log.error(e)


@app.route("/api/new_pass", methods=["POST"])
def api_new_pass():
    b = request.get_data()
    data = json.loads(b.decode())
    username = data["username"]
    email = data["email"]
    hemail = hashlib.sha256(email.encode("utf-8")).hexdigest()
    db_res = list(vallex.db.v2_users.find({
        "username": username,
        "email": hemail
    }))
    # check if user is valid
    if len(db_res) == 0:
        return json.dumps({"confirmation": False})
    # create a new password
    new_pass = "".join([random.choice(
        string.ascii_letters + string.digits) for i in range(10)])
    # update locally
    hpass = hashlib.sha256(new_pass.encode("utf-8")).hexdigest()
    vallex.db.v2_users.update(
        {
            "username": username,
            "email": hemail
        },
        {"$set": {
            "hpass": hpass
        }}
    )
    # send via mail
    send_new_pass_mail(email, new_pass)
    return json.dumps({"confirmation": True})


def prepare_frames(ret_frames):
    # append sentences
    for frame in ret_frames:
        frame.sentences = []
        unique_sids = {".".join(x.split(".")[:-1]): x for x in frame.tids}
        log.debug(str(unique_sids))
        frame.sentences = []
        frame.aggr_sent = {}
        for sid, tid in unique_sids.items():
            hwl = vallex.get_token(tid)["lemma"]
            tmp_idx = len(frame.sentences)
            if hwl not in frame.aggr_sent:
                frame.aggr_sent[hwl] = []
            frame.aggr_sent[hwl].append(tmp_idx)
            frame.sentences.append(
                vallex.get_tokenized_sentence(tid)
            )
    # return (n-frames, rendered template)
    # json frames
    json_ret = {"frames": []}
    for frame in ret_frames:
        json_ret["frames"].append(DC(frame.to_json()))
    return json.dumps(json_ret)


@app.route("/api/frames")
def api_get_frames():
    hw = request.args.get("hw")
    if hw is None:
        return json.dumps({"error": "Headword not found."})

    rf_name = request.args.get("rf", "reduce_0")  # 2nd is default
    RF = reduce_functions[rf_name]["f"]
    entry = vallex.entries[hw]
    ret_frames = RF(entry.raw_frames, vallex)
    return prepare_frames(ret_frames)


@app.route("/api/functor-frames")
def api_get_functor_frames():
    functor = request.args.get("functor")
    if functor is None:
        return json.dumps({"error": "Missing argument: functor."})
    rf_name = request.args.get("rf", "reduce_0")  # 2nd is default
    RF = reduce_functions[rf_name]["f"]
    raw_frames = vallex.functors_index[functor]
    ret_frames = RF(raw_frames, vallex)
    return prepare_frames(ret_frames)


def token_to_username(token):
    COLLNAME = "v2_user_tokens"
    key = {
        "token": token
    }
    res = list(vallex.db[COLLNAME].find(key))
    if len(res) != 1:
        return None
    username = res[0]["username"]
    # update deletion interval
    vallex.db[COLLNAME].update(
        key, {"$set": {"date": datetime.datetime.utcnow()}})
    return username


@app.route("/api/token", methods=["POST"])
def api_token():
    # check if token is valid
    b = request.get_data()
    data = json.loads(b.decode())
    token = data.get("token")
    # user = data.get("user")
    user = token_to_username(token)
    confirm = (user is not None)
    return json.dumps({
        "confirmation": confirm,
        "username": user
    })


@app.route("/api/senses/get")
def api_senses_get():
    # returns senses and mapping for hw
    hw = request.args.get("hw")
    senses = list(vallex.db["v2_senses"].find({
        "hw": hw
    }))
    sense_map_query = list(vallex.db["v2_sense_map"].find({
        "hw": hw
    }))
    # aggregation by max date possible on DB side
    # but no simple way of returning full entries
    # aggregate hw and ssj_id by max date
    sense_map_aggr = {}
    for sm in sense_map_query:
        key = sm["hw"] + sm["ssj_id"]
        if key in sense_map_aggr:
            sense_map_aggr[key] = max(
                [sm, sense_map_aggr[key]], key=lambda x: x["date"])
        else:
            sense_map_aggr[key] = sm
    sense_map_list = [x[1] for x in sense_map_aggr.items()]
    sense_map = {}
    for el in sense_map_list:
        sense_map[el["ssj_id"]] = el
    for k, e in sense_map.items():
        del(e["_id"])
        del(e["date"])
    for e in senses:
        del(e["_id"])
        if "date" in e:
            del(e["date"])

    # sort senses: user defined first, sskj second
    # sskj senses sorted by sskj sense_id
    user_senses = [s for s in senses if s["author"] != "SSKJ"]
    sskj_senses = [s for s in senses if s["author"] == "SSKJ"]

    def sorting_helper(sense):
        arr = sense["sense_id"].split("-")
        return "{:03d}-{:03d}-{:03d}".format(
            int(arr[1]), int(arr[2]), int(arr[3]))

    sskj_senses = sorted(sskj_senses, key=sorting_helper)
    senses = user_senses + sskj_senses

    return json.dumps({
        "senses": senses,
        "sense_map": sense_map,
    })


@app.route("/api/senses/update", methods=["POST"])
def api_senses_update():
    b = request.get_data()
    data = json.loads(b.decode())
    token = data.get("token")
    hw = data.get("hw")
    sense_map = data.get("sense_map")
    new_senses = data.get("new_senses")

    username = token_to_username(token)
    if username is None:
        log.debug("Not a user.")
        return "Not a user."

    # store new senses,
    # create new sense_ids
    id_map = {}
    for ns in new_senses:
        tmp_dt = datetime.datetime.utcnow()
        new_sense_id = "{}-{}".format(
            username,
            hashlib.sha256("{}{}{}".format(
                username,
                ns["desc"],
                str(tmp_dt)
            ).encode("utf-8")).hexdigest()[:10]
        )
        frontend_sense_id = ns["sense_id"]
        ns["sense_id"] = new_sense_id
        ns["date"] = tmp_dt
        id_map[frontend_sense_id] = new_sense_id

        # insert into db
        vallex.db["v2_senses"].insert(ns)

    # replace tmp_id with mongo's _id
    for ssj_id, el in sense_map.items():
        sense_id = el["sense_id"]
        if sense_id in id_map.keys():
            sense_id = id_map[sense_id]
        data = {
            "user": username,
            "hw": hw,
            "ssj_id": ssj_id,
            "sense_id": sense_id,
            "date": datetime.datetime.utcnow()
        }
        # vallex.db["v2_sense_map"].update(key, data, upsert=True)
        vallex.db["v2_sense_map"].insert(data)
    return "OK"


if __name__ == "__main__":
    # Files needed to run:
    # pre-generated .pickle files in /data/no_del_pickles
    # temporary .pickle files can speed up startup (/data/tmp_pickles)
    # main input file: annotated sentences (ssj.xml)
    ANNOTATED_SSJ_XML_PATH = "/ssj500k-sl.TEI/ssj500k-sl.body.xml"

    # Read arguments from autostart.sh script.
    for arg in sys.argv:
        args.extend(arg.split())

    app.debug = get_arg("debug")

    # Set up logging
    logfile = get_arg("logpath") + "/main.log"
    logging.basicConfig(filename=logfile, level=logging.DEBUG)

    datapath = get_arg("datapath")
    if datapath is None:
        log.error("No path to data.")
        exit(1)

    # Prepare vallex.
    vallex = Vallex()

    vallex_pickle_path = datapath + "/tmp_pickles/vallex.pickle"
    vallex_data = k_utils.pickle_load(vallex_pickle_path)

    if vallex_data is None:
        log.info("No pickle found, creating vallex_data.")

        # get ssj data from pickle
        ssj_pickle_path = datapath + "/tmp_pickles/ssj.pickle"
        ssj = k_utils.pickle_load(ssj_pickle_path)

        if ssj is None:
            ssj_path = datapath + ANNOTATED_SSJ_XML_PATH
            log.info("No pickle found, creating ssj pickle from {}.".format(
                ssj_path))
            ssj = SsjDict()
            ssj.read_xml_v2(ssj_path)

            # create fresh pickle
            k_utils.pickle_dump(ssj, ssj_pickle_path)

        vallex.read_ssj(ssj)
        vallex_data = {
            "entries": vallex.entries,
            "tokens": vallex.tokens
        }
        k_utils.pickle_dump(vallex_data, vallex_pickle_path)

    vallex.entries = DC(vallex_data["entries"])
    vallex.tokens = DC(vallex_data["tokens"])

    # Generate senses and se_list after we've built the vallex object.
    seqparser_sskj_path = datapath + "/no_del_pickles/sskj_senses.pickle"
    seqparser_se_list_path = datapath + "/no_del_pickles/se_list.pickle"
    vallex.process_after_read(
        seqparser_sskj_path, seqparser_se_list_path,
        reload_sskj_senses=get_arg("reload_sskj_senses")
    )

    log.info(
        "\n[*] Starting the app." +
        "\n[*] args: {}".format(args) +
        "\n[*] | logfile: {}".format(logfile) +
        "\n[*] | debug: {}".format(str(app.debug))
    )
    # Run the app.
    if app.debug:
        app.run(port=PORT)
    else:
        app.run(host="0.0.0.0", port=PORT)
