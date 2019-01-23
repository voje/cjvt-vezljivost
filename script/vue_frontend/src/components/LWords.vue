<template>
<div>
    <select v-model="selectedLetter">
        <option v-for="letter in alphabet" :value="letter">
            {{ letter.toUpperCase() }} ({{ getNumWords(letter) }})
        </option>
    </select>
    <table>
        <tr v-for="word in getWords()">
            <td><a href="#" v-on:click="selectHw(word)">{{ word[0] }}
                <span v-if="$root.store.has_se.includes(word[0])">se</span>
            </a></td>
            <td>({{ word[1] }})</td>
        </tr>
    </table>
</div>
</template>

<script>
export default {
    name: "LWords",
    data() {return {
        alphabet: "abcčdefghijklmnoprsštuvzž",
        letters: {},
        selectedLetter: "a"
    }},
    methods: {
        apiGetWords: function() {
            var component = this
            this.$http.get(this.$root.storeGet("api_addr") + "/api/words")
                .then(function(response) {
                    component.$root.store.api_error = null
                    component.$root.store.has_se = response.data["has_se"]
                    component.letters = response.data["sorted_words"]
                })
                .catch(function(error) {
                    component.$root.store.api_error = error
                })
        },
        getNumWords: function(letter) {
            var entry = this.letters[letter]
            if (entry) {
                return entry.length
            } else {
                return 0
            }
        },
        getWords: function() {
            var entry = this.letters[this.selectedLetter]
            if (entry) {
                return entry
            } else {
                return []
            }
        },
        selectHw: function(word) {
            this.$router.push({
                name: "MainDispl", 
                params: {
                    hw: word[0],
                    fmode: false
                }
            })
        }
    },
    mounted: function() {
        this.apiGetWords()
    }
}
</script>

<style scoped>
table {
    width: 100%;
}

select {
    width: 100%;
}
</style>