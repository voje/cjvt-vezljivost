def lesk_take3(self, tokens, debug=False):
    # Tokens are [verb token, other frame members]
    # Scoring: best (verb token, member) collocation.
    if debug:
        print(tokens)

    self.slownet_cache = {}

    sense_ids = []  # 2D array [W0: [s0, s1, s2], W1: [s0, s2, ...])
    for i, t in tokens.enumerate():
        if i == 0 and t["lemma"] not in self.slo_to_id:
            print("Verb {} not represented in SloWNet.".format(
                t["lemma"]))
            return None
        token_senses = self.slo_to_id[t["lemma"]]
        sense_ids.append(token_senses)

    for ss in sense_ids:
        print(len(ss))
