<template>
<div class="container-fluid">
    <div class="row">
        <div class="col-sm-12">
            <p class="pb-0 mb-0">Urejanje pomenov za besedo: <b>{{ hw }}</b>.</p>
            <p><small>
                Z miško kliknite na poved, nato kliknite na pomen, ki ga želite dodeliti povedi. Par poved&#8210;pomen bo obarvan z modro. Pare lahko shranite s klikom na gumb "Shrani". Možno je dodajanje poljubnih pomenov. 
            </small></p>
            <button v-on:click="cancel_all">Prekliči</button>
            <button v-on:click="save_all">Shrani</button>
        </div>
    </div>
    <div class="row">

        <!-- left column: sentences -->
        <div class="my-sent col-sm-6">
            <div
                v-for="(sentence, ssj_id) in sentences" 
                v-on:click="pick_ssj_id(ssj_id)"
                class="border rounded my-sentences my-pointer" 
                v-bind:class="{
                    'border-primary': ssj_id === picked_ssj_id       
                }"
            >
                <div>
                    <span 
                        v-for="(word, index) in sentence.words" 
                        v-bind:class="{
                                'text-primary': index === parseInt(sentence.hw_idx)
                            }"
                    >
                        <span v-if="$root.mkspace(index, word)">&nbsp;</span>{{ word }}
                    </span>
                </div>
                <hr>
                <div class="col-sm-12"><small>
                    <div v-if="ssj_id in local_sense_map">
                        <Sense v-bind:sense="local_sense_map[ssj_id].sense"></Sense>
                    </div>
                    <div v-else>
                        <Sense v-bind:sense="undefined"></Sense>
                    </div>
                </small></div>
            </div>
        </div>

        <!-- right column: senses -->
        <div class="col-sm-6 border rounded my-div-scroll sticky-top">
            <div
                v-for="sense in local_senses" 
                class="my-pointer"
                v-on:click="picked_sense_id = sense.sense_id"
                v-bind:class="{
                    'text-primary': sense.sense_id === picked_sense_id
                }"
            >
                <Sense v-bind:sense="sense"></Sense>
            </div>
            <div class="row">
                <div class="col-sm-12">
                    <textarea class="my-textarea" v-model="new_sense_desc"></textarea>
                </div>
                <div class="col-sm-12">
                    <button v-on:click="new_sense">Dodaj pomen</button>
                </div>
            </div>
        </div>
    </div>
</div>
</template>

<script>
import Sense from "./Sense"
export default {
    name: "EditSenses",
    props: ["hw", "sentences", "sens"],
    components: {
        Sense: Sense
    },
    data () { return {
        picked_ssj_id: null,
        picked_sense_id: null,
        local_senses: [],  // make changes on a local copy
        local_sense_map: {},  // make changes on a local copy
        new_sense_desc: "",
        new_senses: [],  // only send changes to server
        delta_sense_map: {},  // only send changes to server
    }},
    created: function() {
        // not sure if needed, maybe move to data()
        this.local_senses = this.sens.senses
        var json = JSON.stringify(this.sens.sense_map)
        this.local_sense_map = JSON.parse(json)
        for (var ssj_id in this.local_sense_map) {
            this.local_sense_map[ssj_id].sense = this.sense_id_to_sense(
                this.local_sense_map[ssj_id].sense_id)
        }
    },
    watch: {
        picked_ssj_id: function() {
            this.new_link()
        },
        picked_sense_id: function() {
            this.new_link()
        }
    },
    methods: {
        pick_ssj_id: function(ssj_id) {
            this.picked_ssj_id = ssj_id
            if (ssj_id in this.local_sense_map) {
                this.picked_sense_id = this.local_sense_map[ssj_id].sense_id
            }
             
        },
        new_link: function() {
            if (this.picked_ssj_id === null ||
                this.picked_sense_id === null) { return }
            this.local_sense_map[this.picked_ssj_id] = {
                sense_id: this.picked_sense_id,
                sense: this.sense_id_to_sense(this.picked_sense_id)
            }
            this.delta_sense_map[this.picked_ssj_id] = { sense_id: this.picked_sense_id }
        },
        new_sense: function(sense_id) {
            if (this.new_sense_desc === "") {
                return
            }
            var new_sense = {
                hw: this.hw,
                author: this.$root.store.username,
                desc: this.new_sense_desc,
                sense_id: "tmp_sense_id" + (new Date().getTime()),
            }
            this.local_senses.push(new_sense)
            this.new_senses.push(new_sense)
            this.new_sense_desc = ""
        },
        sense_id_to_sense: function(sense_id) {
            for (var i=0; i<this.local_senses.length; i++) {
                if (this.local_senses[i].sense_id === sense_id) {
                    return this.local_senses[i] 
                }
            } 
            return undefined
        },
        cancel_all: function() {
            this.$parent.state = "normal"
        },
        save_all: function() {
            const data = {
                    token: this.$root.store.token,
                    hw: this.hw,
                    sense_map: this.delta_sense_map,
                    new_senses: this.new_senses,
            }
            var component = this
            function exit_edit(component) {
                component.$parent.state = "normal"
                component.$parent.request_reload = true
            }

            // don't update if there are no changes
            if (
                Object.keys(data.sense_map).length === 0 &&
                data.new_senses.length === 0
            ) { exit_edit(component); return }

            // exit after update
            this.$http.post(
                this.$root.store.api_addr + "/api/senses/update",
                data,
                { headers: {
                    'Content-type': 'application/json',
                }}
            ).then(function () {
                exit_edit(component)
            })
        },
    }
}
</script>

<style scoped>
.my-div-scroll {
    margin-top: 5px;
    height: 90vh;
    overflow-y: auto;
    padding-top: 5px;
}
.my-pointer {
    cursor: pointer;
}
.my-textarea {
    width: 100%;
}
.my-sentences {
    margin: 5px 0px 20px 0px;
    padding: 5px;
}
.my-sent {
    word-wrap: break-word;
}
.my-sent span {
    display: inline-block;
}
</style>
