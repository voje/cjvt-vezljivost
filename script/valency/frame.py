import logging

log = logging.getLogger(__name__)


class Frame():
    def __init__(self, tids, deep_links=None, slots=None, hw=None):
        self.hw = hw
        self.tids = tids   # list of tokens with the same hw_lemma
        # Each tid = "S123.t123";
        # you can get sentence with vallex.get_sentence(S123)
        self.slots = []
        if slots is None:
            self.slots = self.init_slots(deep_links)
        else:
            self.slots = slots
        self.sense_info = {}
        self.sentences = None  # Used for passing to view in app.py, get_frames
        self.aggr_sent = None  # Dictionary { hw: self.sentences idx }

    def to_json(self):
        ret = {
            "hw": self.hw,
            "tids": self.tids,
            "slots": [slot.to_json() for slot in self.slots],
            "sentences": self.sentences,
            "aggr_sent": self.aggr_sent,
            "sense_info": self.sense_info
        }
        return ret

    def init_slots(self, deep):
        slots = []
        for link in deep:
            slots.append(Slot(
                functor=link["functor"],
                tids=[link["to"]]
            ))
        return slots

    def sort_slots(self):
        # ACT, PAT, alphabetically
        srt1 = [
            x for x in self.slots
            if (x.functor == "ACT" or
                x.functor == "PAT")
        ]
        srt1 = sorted(srt1, key=lambda x: x.functor)
        srt2 = [
            x for x in self.slots
            if (x.functor != "ACT" and
                x.functor != "PAT")
        ]
        srt2 = sorted(srt2, key=lambda x: x.functor)
        self.slots = (srt1 + srt2)

    def to_string(self):
        ret = "Frame:\n"
        ret += "sense_info: {}\n".format(str(self.sense_info))
        ret += "tids: ["
        for t in self.tids:
            ret += (str(t) + ", ")
        ret += "]\n"
        if self.slots is not None:
            ret += "slots:\n"
            for sl in self.slots:
                ret += (sl.to_string() + "\n")
        return ret


class Slot():
    # Each slot is identified by its functor (ACT, PAT, ...)
    # It consists of different tokens.
    def __init__(self, functor, tids=None, count=None):
        self.functor = functor
        self.tids = tids or []
        self.count = count or 1

    def to_string(self):
        ret = "---- Slot:\n"
        ret += "functor: {}\n".format(self.functor)
        ret += "tids: ["
        for t in self.tids:
            ret += (str(t) + ", ")
        ret += "]\n"
        ret += "]\n"
        ret += "----\n"
        return ret

    def to_json(self):
        ret = {
            "functor": self.functor,
            "tids": self.tids,
            "count": self.count
        }
        return ret
