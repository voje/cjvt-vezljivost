<template>
<!-- clicking on empty space clears highlights -->
<div v-on:click="clearOnClick" class="container-fluid">
    <hr>
    <div class="row">
        <div class="col-sm-7">
            <div class="row">
                <div class="col-sm-12">
                    št. povedi: {{ frameData.sentences.length }}
                </div>
            </div>

            <!--frame slots-->
            <div class="row my-frames">
                <div class="col-sm-12">
                    <span v-for="(slot, key) in frameData.slots">
                        <span
                            v-bind:class="{
                                'my-pointer text-danger': hasHoverTid(idx=key), 
                                'my-underline text-danger': hasSelTid(idx=key) 
                            }" 
                            v-on:mouseover="setHid(idx=key)" 
                            v-on:mouseleave="setHid()" 
                            v-on:click="setSid(idx=key)"
                        >{{ slot.functor }}</span>&nbsp;&nbsp;
                    </span>
                </div>
            </div>
        </div>

        <!--sense information-->
        <div v-if="$root.store.radio === 'three'" class="col-sm-5">
            <Sense v-bind:sense="getSense()"></Sense>
        </div>
    </div>

    <!--sentences-->
    <div class="row">
        <!-- fmode: prikaz->udelezenske vloge (drugacno razvrscanje povedi) --> 
        <div v-if="fmode" class="col-sm-12">
            <div v-for="hw in getAggrHws()">
                <blockquote v-for="sentence in getAggrSent(hw)">
                    <span class="text-secondary">&nbsp;{{ hw }}</span><br>
                    <span 
                        v-for="(token, index) in sentence" 
                        v-bind:class="{ 
                            'my-pointer text-danger': hasHoverTid(idx=null, tid=token[0]), 'my-underline text-danger': hasSelTid(idx=null, tid=token[0]), 
                            'text-primary': isHw(token[0]),
                        }" 
                        v-on:mouseover="setHid(idx=null, tid=token[0])" 
                        v-on:mouseleave="setHid()" 
                        v-on:click="setSid(idx=null, tid=token[0])" 
                        v-bind:title="token[1].msd"
                    ><span v-if="$root.mkspace(index, token[1].word)">&nbsp;</span>{{ token[1].word }}</span>
                </blockquote>
            </div>
        </div>
        <div v-else class="col-sm-12">
            <blockquote v-for="sentence in frameData.sentences">
                <span 
                    v-for="(token, index) in sentence" 
                    v-bind:class="{ 
                        'my-pointer text-danger': hasHoverTid(idx=null, tid=token[0]), 'my-underline text-danger': hasSelTid(idx=null, tid=token[0]), 
                        'text-primary': isHw(token[0]),
                    }" 
                    v-on:mouseover="setHid(idx=null, tid=token[0])" 
                    v-on:mouseleave="setHid()" 
                    v-on:click="setSid(idx=null, tid=token[0])" 
                    v-bind:title="token[1].msd"
                ><span v-if="$root.mkspace(index, token[1].word)">&nbsp;</span>{{ token[1].word }}</span>
            </blockquote>
        </div>
    </div>
    <br>
</div>
</template>

<script>
import Sense from "./Sense"
export default {
    name: "Frame",
    props: {
        frameData: {},
        sensData: {},
        fmode: {
            default: false,
            type: Boolean,
        },
    },
    data() { return {
        hid: null,  // hover functor index
        sid: null,  // select functor index (click)
    }},
    components: {
        Sense: Sense
    },
    watch: {
        frameData: function () {
            this.hid = null,
            this.sid = null
        }
    },
    methods: {
        setHid: function (idx=null, tid=null) {
            // calling this functoin without parameters
            // resets hid
            if (tid === null) {
                this.hid = idx
                return
            }
            for (var i=0; i<this.frameData.slots.length; i++) {
                if (this.frameData.slots[i].tids.includes(tid)) {
                    this.hid = i
                    return
                }
            }
        },
        clearOnClick: function (event) {
            if (event.target.tagName !== "SPAN") {
                this.sid = null
            }
        },
        setSid: function (idx=null, tid=null) {
            this.sid = null
            if (tid === null) {
                this.sid = idx
                return
            }
            for (var i=0; i<this.frameData.slots.length; i++) {
                if (this.frameData.slots[i].tids.includes(tid)) {
                    this.sid = i
                    return
                }
            }
        },
        hasHoverTid: function(idx=null, tid=null) {
            if (this.hid === null) {
                return false
            }
            if (tid === null) {
                if (idx == this.hid) {
                    return true
                }
                return false
            }
            return this.frameData.slots[this.hid].tids.includes(tid)
        },
        hasSelTid: function (idx=null, tid=null) {
            if (this.sid === null) {
                return false
            }
            if (tid === null) {
                if (idx == this.sid) {
                    return true
                }
                return false
            }
            return this.frameData.slots[this.sid].tids.includes(tid)
        },
        isHw: function (tid) {
            return this.frameData.tids.includes(tid)
        },
        getSense: function () {
            for (var i in this.sensData.senses) {
                if (this.sensData.senses[i].sense_id === this.frameData.sense_info.sense_id) {
                    return this.sensData.senses[i]
                }
            }
            return undefined
        },
        getAggrHws: function() {
            return (Object.keys(this.frameData.aggr_sent)).sort()
        },
        getAggrSent: function(hw) {
            var sentences = []
            for (var i=0; i<this.frameData.aggr_sent[hw].length; i++) {
                sentences.push(
                    this.frameData.sentences[this.frameData.aggr_sent[hw][i]]
                )
            }
            return sentences
        },
    }
}
</script>

<style scoped>
.my-pointer {
    cursor: pointer;
}
.my-underline {
    text-decoration: underline;
}
.my-frames {
    margin-top: 10px;
    margin-bottom: 2px;
}
blockquote {
  background: #ffffff;
  border-left: 4px solid #ccc;
  margin: 10px 0px 10px 10px;
  padding: 0px 0px 0px 5px;
  word-wrap: break-word;
}
blockquote span {
    display: inline-block;
}
</style>
