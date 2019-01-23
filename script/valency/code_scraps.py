# Probably for deletion

def plot_data(self):
    verb_freq = []
    for k, e in self.entries.items():
        verb_freq.append((k, len(e)))
    verb_freq = sorted(verb_freq, key=lambda x: x[1])
    plt.figure(1)

    # word frequencies with a median
    plt.subplot(211)
    plt.title("Frekvenčna razporeditev glagolov")
    plt.xlabel("indeks glagola")
    plt.ylabel("frekvenca")
    s = float(sum([x[1] for x in verb_freq]))
    med = 0.0
    for i, el in enumerate(verb_freq):
        med += el[1]
        if med >= s / 2:
            print(med)
            med = i
            print(i)
            break
    print("""{} words ({:.2f}%) represent the upper
        half of frequencies.""".format(
        len(verb_freq[med:]), len(verb_freq) / len(verb_freq[med:])
    ))
    ones = sum([x[1] == 1 for x in verb_freq])
    print("{} words ({:.2f}%) have a frequency of 1.".format(
        ones, ones / s * 100
    ))
    plt.plot([x[1] for x in verb_freq], '.')
    plt.axvline(med, color='r', label="mediana")

    plt.subplot(212)
    plt.title("Gostota frekvenc")
    plt.xlabel("frekvena")
    plt.ylabel("število glagolov z dano frekvenco")
    c = Counter([x[1] for x in verb_freq])
    freq_occur = sorted(c.items(), key=lambda x: x[0])
    plt.plot([x[1] for x in freq_occur], '.')
    plt.xticks(
        range(0, len(freq_occur)), [x[0] for x in freq_occur], rotation=315
    )

    plt.show()
    """
    freq = []
    for key in self.entries:
        fq = len(self.entries[key])
        freq.append(fq)
        if fq > 50:
            print("{:10s} {:5d}".format(key, fq))
    plt.hist(freq, log=True)
    plt.show()
    """