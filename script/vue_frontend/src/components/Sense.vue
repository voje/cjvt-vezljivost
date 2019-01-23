<template>
<div class="pb-3">
    <div v-if="sense === undefined">
        pomen ni definiran
    </div>
    <div v-else>
        <span>{{ sense.desc }}</span>
        <br>
        &nbsp;&nbsp;
        <small class="text-secondary">
            - {{ sense.author }}
            {{ gen_id() }}
        </small>
    </div>
</div>
</template>

<script>
export default {
    name: "Sense",
    props: ["sense"],
    methods: {
        gen_id: function() {
            var id_arr = this.sense.sense_id.split("-")
            var ret = ""
            if (this.sense.author === "SSKJ") {
                if (id_arr[1] !== "0") {
                    ret += ("[" + id_arr[1] + ["] "])
                }
                if (id_arr[2] !== "0") {
                    ret += ("pomen " + id_arr[2])
                    if (id_arr[3] !== "0") {
                        ret += ("." + id_arr[3])
                    }
                }
                if (id_arr[4] === "sopo") {
                    ret += " (sopomenka)"
                }
            }
            // ret = this.sense.sense_id  //debugging
            if (ret.length > 0) {
                ret = ": " + ret
            }
            return ret
        }
    }
}
</script>
