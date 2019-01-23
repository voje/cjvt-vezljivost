<template>
<nav>
    <b-navbar toggleable="md" type="light" variant="light">
    <b-navbar-toggle target="nav_collapse"></b-navbar-toggle>
    <b-navbar-brand>Vezljivostni vzorci slovenskih glagolov</b-navbar-brand>
    <b-collapse is-nav id="nav_collapse">

    <b-navbar-nav>
        <b-nav-item-dropdown text="Prikaz" right>
            <b-dropdown-item v-for="option in search_options" 
                :value="option.val"
                :key="option.val"
                v-on:click="setNavSS(option.val)">
                {{ option.key }}
            </b-dropdown-item>
        </b-nav-item-dropdown>
    </b-navbar-nav>

        <!-- Right aligned nav items -->
    <b-navbar-nav class="ml-auto" right v-if="this.loggedIn()">
        <b-nav-item>
            Uporabnik: {{ this.$root.store.username }} 
            <a href="#" v-on:click="logOut()">(odjava)</a>
        </b-nav-item>
    </b-navbar-nav>
    <b-navbar-nav class="ml-auto" right v-else>
        <b-nav-item>
            <router-link to="/register">
                Registracija
            </router-link>
        </b-nav-item>
        <b-nav-item>
            <router-link to="/login">
                Prijava
            </router-link>
        </b-nav-item>
    </b-navbar-nav>

    </b-collapse>
    </b-navbar>
    </nav>
</template>

<script>
export default {
    name: "Nav",
    props: ["appState"],
    data() {return {
        search_options: [
            {key: "besede", val: "words"},
            {key: "udeleženske vloge", val: "functors"},
        ],
    }},
    methods: {
        setNavSS(val) {
            this.$root.store.radio = "one"
            this.$root.store.navSS = val
            this.$router.push({
                name: "Home"
            })
        },
        loggedIn() {
            return (this.$root.store.token !== null)
        },
        logOut() {
            this.$root.store.token = null
            this.$root.store.username = null
            this.$router.push({
                name: "Home"
            })
        }
    }
}
</script>