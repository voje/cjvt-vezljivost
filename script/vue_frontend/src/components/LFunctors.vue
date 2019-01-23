<template>
<div>
    <table>
        <tr v-for="functor in functors">
            <td><a href="#" v-on:click="selectFunctor(functor)">{{ functor[0] }}</a></td>
            <td>({{ functor[1] }})</td>
        </tr>
    </table>
</div>
</template>

<script>
export default {
    name: "LWords",
    props: ["appState"],
    data() {return {
        functors: []
    }},
    methods: {
        apiGetFunctors: function () {
            var component = this
            this.$http.get(this.$root.store.api_addr + "/api/functors")
                .then(function(response) {
                    component.$root.store.api_error = null
                    component.functors = response.data
                })
                .catch(function(error) {
                    component.$root.store.api_error = error
                })
        },
        selectFunctor: function (functor) {
            this.$router.push({
                name: "MainDispl", 
                params: {
                    hw: functor[0],
                    fmode: true
                }
            })
        }
    },
    mounted: function() {
        this.apiGetFunctors()
    }
}
</script>

<style>
table {
    width: 100%;
}
</style>