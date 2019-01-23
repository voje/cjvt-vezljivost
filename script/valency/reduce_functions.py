# Reduction function for frames.
# Input: list of Frame objects, output: list of Frame objects.
# App uses reduce_0, 1 and 5

from valency.frame import Frame, Slot
from copy import deepcopy as DC
import logging

log = logging.getLogger(__name__)

SENSE_UNDEFINED = "nedefinirano"


def sorted_by_len_tids(frames):
    return sorted(
        frames,
        key=lambda x: len(x.tids),
        reverse=True
    )


def reduce_0(frames, vallex=None):
    # new request... frames should be sorded by
    # functors list (basically reduce_1, just each
    # sentence gets its own frame)
    r1_frames = reduce_1(frames)
    sorting_strings = []
    separated_frames = []
    for frame in r1_frames:
        for tid in frame.tids:
            tmp_frame = DC(frame)
            tmp_frame.tids = [tid]
            separated_frames.append(tmp_frame)
            sorting_strings.append("".join(
                [slot.functor for slot in tmp_frame.slots]
            ))
    permutation = [x for _, x in sorted(
        zip(sorting_strings, range(len(sorting_strings))))]
    sorted_sep_frames = [separated_frames[i] for i in permutation]
    return sorted_sep_frames


def reduce_1(frames, vallex=None):
    # Combine frames with the same set of functors.
    # The order of functors is not important.
    frame_sets = []  # [set of functors, list of frames]
    for frame in frames:
        functors = [slot.functor for slot in frame.slots]

        for fs in frame_sets:
            if set(functors) == set(fs[0]):
                fs[1].append(frame)
                break
        else:
            # Python for else -> fires if loop has ended.
            frame_sets.append([functors, [frame]])

    ret_frames = []
    for fs in frame_sets:
        tids = []
        slots = {}
        # All possible slots in this frame.
        for functor in fs[0]:
            slots[functor] = Slot(functor=functor)
        # Reduce slots from all frames. (Merge ACT from all frames, ...)
        for frame in fs[1]:
            tids += frame.tids
            for sl in frame.slots:
                slots[sl.functor].tids += sl.tids
        slots_list = []
        for k, e in slots.items():
            slots_list.append(e)
        rf = Frame(tids=tids, slots=slots_list)
        rf.sort_slots()
        ret_frames.append(rf)
    return sorted_by_len_tids(ret_frames)


def reduce_3(raw_frames, vallex):
    # sskj simple lesk ids
    ssj_ids = [frame.tids[0] for frame in raw_frames]
    db_results = list(vallex.db.sskj_simple_lesk.find(
        {"ssj_id": {"$in": ssj_ids}}))
    id_map = {}
    for entry in db_results:
        id_map.update({entry["ssj_id"]: {
            "sense_id": entry.get("sense_id"),
            "sense_desc": entry.get("sense_desc")
        }})
    return frames_from_sense_ids(raw_frames, id_map)


def reduce_4(raw_frames, vallex):
    # kmeans ids
    ssj_ids = [frame.tids[0] for frame in raw_frames]
    db_results = list(vallex.db.kmeans.find(
        {"ssj_id": {"$in": ssj_ids}}))
    id_map = {}
    for entry in db_results:
        id_map.update({entry["ssj_id"]: {
            "sense_id": entry["sense_id"]
        }})
    return frames_from_sense_ids(raw_frames, id_map)


def reduce_5(raw_frames, vallex):
    USER_SENSE_COLL = "v2_sense_map"
    headword = raw_frames[0].hw
    ssj_ids_full = [frame.tids[0] for frame in raw_frames]
    # v2_sense_map stores only sentence half of ssj_id
    ssj_ids = [".".join(ssj_id.split(".")[:-1]) for ssj_id in ssj_ids_full]
    db_results = list(vallex.db[USER_SENSE_COLL].find({
        "ssj_id": {"$in": ssj_ids},
        "hw": headword,
    }))
    id_map = {}
    for entry in db_results:
        id_map[entry["ssj_id"]] = entry["sense_id"]

    ret_frames = frames_from_sense_ids(raw_frames, id_map)

    # sort: frames with senses to top
    senses_undefined = []
    senses_defined = []
    for frame in ret_frames:
        if frame.sense_info["sense_id"] == SENSE_UNDEFINED:
            senses_undefined.append(frame)
        else:
            senses_defined.append(frame)
    ret_frames = senses_defined + senses_undefined

    return ret_frames


def frames_from_sense_ids(raw_frames, id_map):
    # id map = dict {
    #   ssj_id: sense_id
    # }
    # id_dict = dict {
    #   sense_id: [frame, ...]
    # }
    id_dict = {}
    for frame in raw_frames:
        # long version ssj_id (S123.t12)
        frame_ssj_id = frame.tids[0]
        frame_sense_id = id_map.get(frame_ssj_id)
        if frame_sense_id is None:
            # try short version ssj_id (S123)
            frame_ssj_id = ".".join(frame_ssj_id.split(".")[:-1])
            frame_sense_id = id_map.get(frame_ssj_id)

        # set default if sense_id not found
        if frame_sense_id is None:
            frame_sense_id = SENSE_UNDEFINED
        """
        sense_id = id_map.get(frame.tids[0])
        if sense_id is not None:
            sense_id = sense_id.get("sense_id")
        else:
            sense_id = "nedefinirano"
        """
        if frame_sense_id not in id_dict:
            id_dict[frame_sense_id] = []
        id_dict[frame_sense_id].append(DC(frame))

    ret_frames = []
    for sense_id, frames in id_dict.items():
        tids = []
        reduced_slots = []
        for frame in frames:
            tids.extend(frame.tids)
            for slot in frame.slots:
                # if functor not in reduced slots,
                # add new slot; else increase count
                for rslot in reduced_slots:
                    if slot.functor == rslot.functor:
                        rslot.count += 1
                        rslot.tids.extend(slot.tids)
                        break
                else:
                    # in case for loop didn't match a slot
                    reduced_slots.append(Slot(
                        functor=slot.functor,
                        tids=slot.tids,
                        count=1
                    ))
        reduced_frame = Frame(tids, slots=reduced_slots)
        id_map_entry = (
            id_map.get(tids[0]) or
            id_map.get(".".join(tids[0].split(".")[:-1]))
        )
        if id_map_entry is None:
            reduced_frame.sense_info = {
                "sense_id": SENSE_UNDEFINED,
            }
        else:
            reduced_frame.sense_info = {
                "sense_id": id_map_entry
            }
        reduced_frame.sort_slots()
        ret_frames.append(reduced_frame)
    return ret_frames


reduce_functions = {
    "reduce_0": {
        "f": reduce_0,
        "desc":
        "Vsaka pojavitev glagola dobi svoj stavčni vzorec.",
        "simple_name": "posamezni stavki"
    },
    "reduce_1": {
        "f": reduce_1,
        "desc":
        "Združevanje stavčnih vzorcev z enako skupino udeleženskih vlog.",
        "simple_name": "združeni stavki"
    },
    "reduce_3": {
        "f": reduce_3,
        "desc":
        "Združevanje stavčnih vzorcev na osnovi pomenov povedi v SSKJ. "
        "Pomeni so dodeljeni s pomočjo algoritma Simple Lesk.",
        "simple_name": "SSKJ_pomeni"
    },
    "reduce_4": {
        "f": reduce_4,
        "desc":
        "Združevanje stavčnih vzorcev na osnovi pomenov povedi "
        "s pomočjo algoritma K-Means. Število predvidenih pomenov "
        "podano na osnovi SSKJ.",
        "simple_name": "KMeans_pomeni"
    },
    "reduce_5": {
        "f": reduce_5,
        "desc":
        "Uporabniško dodeljeni pomeni povedi.",
        "simple_name": "po meri"
    }
}
