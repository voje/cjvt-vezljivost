<template>
<!--load mode-->
<div v-if="show_loader">
    <pulse-loader :color="loader_color"></pulse-loader>
</div>

<!--edit mode (button: razvrsti po pomenih)-->
<div v-else-if="state === 'editing'" class="container-fluid">
    <EditSenses 
        v-bind:hw="hw" 
        v-bind:sentences="sentences" 
        v-bind:sens="sens" 
    ></EditSenses>
</div>

<!--normal mode-->
<div v-else class="container-fluid" id="head">

    <!--header (verb/adjective, radio buttons)-->
    <div class="row">
        <div class="col-sm-4">
            <table>
                <tr><h4 id="main-displ-hw">{{ hw }}
                    <span v-if="$root.store.has_se.includes(hw)">se</span>
                </h4></tr>
                <tr>{{ calcPos() }}</tr>
            </table>
        </div>
        <div class="col-sm-8">
            <table>
                <tr>Združevanje vezljivostnih vzorcev:</tr>
                <tr>
                    <label class="radio-inline"><input value="one" v-model="$root.store.radio" v-on:change="reload()" checked="" type="radio" name="optradio">posamezne povedi</label>&nbsp;&nbsp;
                    <label class="radio-inline"><input value="two" v-model="$root.store.radio" v-on:change="reload()" type="radio" name="optradio">skupne udeleženske vloge</label>&nbsp;&nbsp;
                    <label v-if="this.$root.store.navSS === 'words'" class="radio-inline"><input value="three" v-model="$root.store.radio" v-on:change="reload()" type="radio" name="optradio">po meri</label>  
                </tr>
            </table>
        </div>
    </div>

    <!--frames-->
    <div v-if="$root.store.radio === 'three'" class="row">
        <div class="col-sm-4">
            <button v-on:click="userEdit">razvrsti po pomenih</button>
        </div>
    </div>
    <div class="row" v-for="frame in frames">
        <Frame 
            v-bind:frameData="frame" 
            v-bind:sensData="sens" 
            v-bind:fmode="fmode">
        </Frame>
    </div>

</div>
</template>

<script>
import Frame from "./Frame"
import EditSenses from "./EditSenses"
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
export default {
    name: "MainDispl",
    components: {
        Frame: Frame,
        EditSenses: EditSenses,
        PulseLoader: PulseLoader,
    },
    props: ["hw", "fmode"],
    data () { return {
        frames: [],
        sentences: {},
        sens: {
            senses: [],
            sense_map: {},
        },
        state: "loading",  // editing, normal
        request_reload: false,
        loader_color: "#007bff",
    }},
    created: function () {
        this.reload()
    },
    computed: {
        show_loader: function () {
            return this.state === "loading" && this.$root.store.api_error !== null
        }
    },
    watch: {
        hw: function () {
            this.reload()
        },
        frames: function () {
            this.buildSentences()
        },
        request_reload: function () {
            if (this.request_reload) {
                this.request_reload = false
                this.reload()
            }
        },
    },
    methods: {
        getFFrames: function(functor, reduce_fun=null) {
            // get frames in functor mode
            if (functor === null || functor === undefined) return 
            if (reduce_fun === null) {
                switch (this.$root.store.radio) {
                    case "one":
                        reduce_fun = "reduce_0"
                        break
                    case "two":
                        reduce_fun = "reduce_1"
                        break
                    default:
                        reduce_fun = "reduce_0"
                        break
                }
            }
            var component = this
            this.$http.get(
                this.$root.storeGet("api_addr") + "/api/functor-frames" + 
                    "?functor=" + functor + "&rf=" + reduce_fun)
                .then(function (response) {
                    component.$root.store.api_error = null
                    component.frames = response.data.frames
                    component.state = "normal"
                })
                .catch(function(error) {
                    component.$root.store.api_error = error
                })
        },
        getFrames: function (hw, reduce_fun=null) {
            if (hw === null || hw === undefined) return
            if (reduce_fun === null) {
                switch (this.$root.store.radio) {
                    case "one":
                        reduce_fun = "reduce_0"
                        break
                    case "two":
                        reduce_fun = "reduce_1"
                        break
                    case "three":
                        reduce_fun = "reduce_5"
                        break
                }
            }
            var component = this
            this.$http.get(
                this.$root.storeGet("api_addr") + "/api/frames" + 
                    "?hw=" + hw + "&rf=" + reduce_fun)
                .then(function (response) {
                    component.$root.store.api_error = null
                    component.frames = response.data.frames
                    component.state = "normal"
                })
                .catch(function(error) {
                    component.$root.store.api_error = error
                })
        },
        buildSentences: function () {
            if (this.frames.length == 0) {
                return
            }
            this.sentences = {}
            for (var fi in this.frames) {
                for (var si in this.frames[fi].sentences) {
                    var sentence = this.frames[fi].sentences[si]
                    // get ssj_id without .t123
                    var ssj_id = sentence[0][0].split(".")
                    ssj_id.splice(-1, 1)  // removes last element
                    ssj_id = ssj_id.join(".")
                    var words = []
                    var hw_idx = -1
                    var tmp_hw = this.hw
                    if (tmp_hw[tmp_hw.length - 1] === "_") {
                        tmp_hw = tmp_hw.substr(0, tmp_hw.length - 1)
                    }
                    for (var i in sentence) {
                        words.push(sentence[i][1].word)
                        if (sentence[i][1].lemma === tmp_hw && hw_idx == -1) {
                            hw_idx = i
                        }
                    }
                    this.sentences[ssj_id] = {
                        hw_idx: hw_idx,
                        words: words
                    }
                }
            }
        },
        getSenses: function (hw, callback) {
            if (hw === null || hw === undefined) {
                return
            }
            var component = this
            this.$http.get(
                this.$root.store.api_addr + "/api/senses/get" + "?hw=" + hw)
            .then(function(response) {
                // console.log(response.data)
                component.sens.senses = response.data.senses
                component.sens.sense_map = response.data.sense_map
                callback()
            })
        },
        reload: function () {
            this.state = "loading"
            this.sentences = {}
            if (this.$root.store.navSS === "functors") this.getFFrames(this.hw)
            else {
                this.getFrames(this.hw)
                if (this.$root.store.radio === "three") {
                    this.getSenses(this.hw, this.sortBySense)
                }
            }
            this.calcPos()
        },
        userEdit: function () {
            // authenticate the user for this
            var tthis = this
            this.$root.checkToken()
                .then(function (response) {tthis.state = "editing"})
                .catch(function (err) {alert("Za urejanje je potrebna prijava.")}
            )
        },
        calcPos: function() {
            var bfmode = this.fmode
            if (typeof(bfmode) === "string") {
                bfmode = (bfmode === "true")
            }
            if (bfmode) return "udeleženska vloga"
            else if (this.hw.substr(this.hw.length-1) === "_") return "pridevnik"
            return "glagol"
        },
        sortBySense: function() {
            // frames with defined senses on top
            var undefFrames = []
            var defFrames = []
            //console.log(Object.keys(this.sens.sense_map))
            for (var i=0; i<this.frames.length; i++) {
                var sense_id = this.frames[i].sense_info.sense_id
                if (sense_id === "nedefinirano") undefFrames.push(this.frames[i])
                else defFrames.push(this.frames[i])
            }
            this.frames = defFrames.concat(undefFrames)
        }
    }
}
</script>

<style scoped>
#main-displ-hw {
    margin: 0px;
}

</style>
