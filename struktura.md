# Drevesna struktura direktorija:

* data -- vhodne datoteke (sskj, ssj500k, slownet) (prazno)
* script -- izvorna koda
    * flask_app -- zaledni del, backend
        * app.py -- vhodna točka (main)
    * valency -- modul za obdelavo vhodnih korpusov (glavna logika)
        * seqparser -- orodje za razčlenjevanje vhodnega korpusa v .xml obliki
        * dictionary_interface.py -- vmesnik za delo s slovarji v MongDB bazi
        * evaluation.py -- algoritmi za evalvacijo
            * rand_index()
            * clustering_purity()
            * ars() -- adjusted_rand_index sem uvozil iz sklearn.metrics
        * frame.py -- objekt za valenčni okvir
        * k_means.py -- algoritem k-voditeljev
            * k_means()
            * bkm() -- bisekcijski k-means
            * silhouette_wrapper -- izračun silhuetne ocene
            * kmeans_wrapper() -- kliče izbran algoritem k-means z različnimi vrednostmi K,
                s pomočjo funkcije silhouette_wrapper() izbere najbolj optimalen K
            * k_utils.py -- podporna orodja
                * slo_bucket_sort() -- sort za slovenske besede
                * stem_slo() -- približek korenjenja slovenskih besed
            * leskFour.py -- implementacija štirih verzij Leskovega algoritma
                * lesk_nltk()
                * lesk_sl()
                * lesk_al()
                * lesk_ram()
            * reduce_functions.py -- funkcije za združevanje vezljivostnih vzorcev (uporaljene v aplikaciji)
            * ssj_struct.py -- vmesni objekt za branje korpusa
            * sskj_scraper.py -- orodje za zbiranje podatkov iz spletnega SSKJ
            * val_struct.py() -- objekt, ki predstavlja prebrani korpus
    * vue_frontend -- uporabniški vmesnik