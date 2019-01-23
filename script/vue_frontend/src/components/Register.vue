<template>
<div>
  <div class="col-sm-2">
    <a href="#" v-on:click="this.$root.routeBack">Nazaj</a>
  </div>
  <div class="ev-login col-sm-4 offset-sm-4">
    <div class="alert alert-danger" v-if="error">
      <p>{{ error }}</p>
    </div>
    <div class="form-group">
      <input 
        type="text"
        class="form-control js-login__username"
        placeholder="Uporabnik"
        v-model="credentials.username" 
        autocomplete="off"
      >
    </div>
    <div class="form-group">
      <input
        type="email"
        class="form-control"
        placeholder="e-pošta"
        v-model="credentials.email" 
        autocomplete="off"
      >
    </div>
    <div class="form-group">
      <input
        type="password"
        class="form-control js-login__password "
        placeholder="Geslo"
        v-model="credentials.password" 
        autocomplete="off"
      >
    </div>
    <div class="form-group">
      <input
        type="password"
        class="form-control js-login__password "
        placeholder="Ponovite geslo."
        v-model="credentials.snd_password" 
        autocomplete="off"
      >
    </div>
    <button 
      class="btn btn-primary solid blank js-login__submit" 
      @click="submit()"
    >
      Registracija<i class="fa fa-arrow-circle-o-right"></i>
    </button>
  </div>
</div>
</template>

<script>
export default {
    name: 'Register',
    data () { return {
        credentials: {
            username: "",
            password: "",
            snd_password: "",
            email: ""
        },
        error: ""
    }},
    methods: {
        clearFields () {
            for (var key in this.credentials) {
                this.credentials[key] = ""
            }
        },
        checkEmail () {
            // check? ... todo
            return true
        },
        submit () {
            //console.log(this.credentials.password)
            //console.log(this.credentials.snd_password)
            const credentials = {
                username: this.credentials.username,
                password: this.credentials.password
            }

            // check if fields are full
            for (var key in this.credentials) {
                if (credentials[key] === "") {
                    this.error = "Izpolnite vsa polja."
                    return
                }
            }

            // check e-mail
            if (!this.checkEmail(this.credentials.email)) {
                this.error = "Preverite e-poštni naslov."
                return
            }

            // check passwords
            if (this.credentials.password !== this.credentials.snd_password) {
                this.error = "Gesli se ne ujemata."
                this.credentials.password = ""
                this.credentials.snd_password = ""
                return
            }

            var component = this
            const post_data = {
                username: this.credentials.username,
                password: this.credentials.password,
                email: this.credentials.email,
            }
            this.$http.post(this.$root.storeGet("api_addr") + "/api/register", 
                post_data, // the data to post
                { headers: {
                    'Content-type': 'application/json',
                }
            })
                .then(function (response) {
                    component.$router.push({
                        name: "Home"
                    })
                })
                .catch(function (err) {
                    component.$root.store.api_error = err
                    component.error = "Registracija ni uspela."
                })
            }
        }
    }
</script>

<style scoped>
    .ev-login {
    margin-top: 100px;
    }
</style>