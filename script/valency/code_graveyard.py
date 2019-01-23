# Testing context1
    def test_context1(self, mytid, k=""):
        res = ""
        c = self.get_context1(
            mytid, collname="slownet", radius=None)
        res += ("{} | {} | {}<br>".format(
            k, self.get_sentence(mytid), c))
        return res

        res = ""
        stop = False
        for k, e in self.entries.items():
            if stop:
                break
            for frame in e.raw_frames:
                rnd = random.randint(1, 100)
                if rnd < 30:
                    res += self.test_context1(frame.tids[0], k=k)
                if rnd < 5:
                    stop = True
                    break
        return res


    # testing sense_glosses, stemming
        res = ""
        stop = False
        for k, e in self.entries.items():
            if stop:
                break
            for frame in e.raw_frames:
                rnd = random.randint(1, 100)
                if rnd < 50:
                    if (
                        self.sskj_interface.contains(k) and
                        self.slownet_interface.contains(k)
                    ):
                        r1 = self.sskj_interface.sense_glosses(k, upper_limit=30)
                        r2 = self.slownet_interface.sense_glosses(k, upper_limit=30)
                        if len(r1) == 0:
                            continue
                        if len(r2) == 0:
                            continue
                        res += "(({}))------>{}</br>{}<br><br>".format(
                            k, r1, k_utils.tokenize_multiple(
                                r1[0]["gloss"],
                                min_token_len=3,
                                stem=k_utils.stem_slo
                            ))
                        res += "(({}))------>{}<br>{}</br></br>".format(
                            k, r2, k_utils.tokenize_multiple(
                                r2[0]["gloss"],
                                min_token_len=3,
                                stem=k_utils.stem_eng
                            ))
                        res += "<br><hr><br>"
                if rnd < 5:
                    stop = True
                break


    def test_dev(self):
        res = ""
        stop = False
        for k, e in self.entries.items():
            if stop:
                break
            for frame in e.raw_frames:
                rnd = random.randint(1, 100)
                if rnd < 50:
                    # res += self.test_context1(frame.tids[0], hw=k)
                    res += "--->" + k + "(" + frame.tids[0] + ")" + "<br>"
                    res += self.get_sentence(frame.tids[0]) + "<br>"
                    res += str(self.leskFour.lesk_nltk(frame.tids[0])) + "<br>"
                    res += "<br>"
                if rnd < 5:
                    stop = True
                    break
        return res


    def test_dev(self):
        lemma = "igrati"
        res = ""
        res += str(self.sskj_interface.count_senses(lemma))
        res += "<br>"
        res += "<br>"
        res += str(self.sskj_interface.find(lemma))
        return res
        res = ""
        random.seed(time())
        stop = False
        for k, e in self.entries.items():
            if stop:
                break
            for frame in e.raw_frames:
                rnd = random.randint(1, 100)
                if rnd < 70:
                    # res += self.test_context1(frame.tids[0], hw=k)
                    res += "--->" + k + "(" + frame.tids[0] + ")" + "<br>"
                    res += str(self.slownet_interface.chain(k))
                    """
                    res += self.get_sentence(frame.tids[0]) + "<br>"
                    res += str(self.slownet_interface.sense_glosses(k))
                    res += "<br>"
                    res += str(self.leskFour.lesk_ram(frame.tids[0])) + "<br>"
                    """
                    res += "<br>"
                if rnd < 5:
                    stop = True
                    break
        return res