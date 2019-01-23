from valency.val_struct import *
from valency.ssj_struct import *
from valency import k_utils
from valency.lesk import Lesk

vallex_path = "../../data/vallex.xml"
vallex = k_utils.pickle_load(vallex_path)
if vallex is None:
    ssj_path = "../../data/anno_final.conll.xml"
    # ssj_path = "../../data/ssj500kv1_1-SRL_500_stavkov_2017-04-11.xml"
    ssj = k_utils.pickle_load(ssj_path)
    if ssj is None:
        ssj = SsjDict()
        ssj.read_xml(ssj_path)
        k_utils.pickle_dump(ssj, ssj_path)

    vallex = Vallex()
    vallex.read_ssj(ssj)
    k_utils.pickle_dump(vallex, vallex_path)

vallex.process_after_read(False, False)

random_frame = None
lesk = Lesk()
successes = 0
for k, e in vallex.entries.items():
    for rf in e.raw_frames:
        random_frame = rf
        break
    print(rf.to_string())
    print(vallex.get_token(random_frame.tids[0]))
    print(vallex.get_sentence(random_frame.tids[0]))
    tid = random_frame.tids[0]
    token = vallex.get_token(tid)
    context = vallex.get_context(tid)
    sense = lesk.lesk(token, context)
    if sense is not None:
        successes += 1
    if successes >= 10:
        break
