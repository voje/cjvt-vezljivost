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
        data-id="login.username" 
        class="form-control js-login__username"
        placeholder="Uporabnik"
        v-model="credentials.username"
      >
    </div>
    <div class="form-group">
      <input
        type="password"
        class="form-control js-login__password "
        placeholder="Geslo"
        v-model="credentials.password"
      >
    </div>
    <button 
      data-id="login.submit"
      class="btn btn-primary solid blank js-login__submit" 
      @click="submit()"
    >
      Prijava<i class="fa fa-arrow-circle-o-right"></i>
    </button>
    <br>
    <br>
    <br>
    <router-link to="/new_pass">Ste pozabili geslo?</router-link>
    <br>
    <br>
    Nov uporabnik?
    <br>
    <router-link to="/register">Ustvarite nov račun.</router-link>

  </div>
</div>
</template>

<script>
export default {
  name: 'Login',
  data () {
    return {
      credentials: {
        username: '',
        password: ''
      },
      loggingIn: false,
      error: ''
    }
  },
  methods: {
    submit () {
      this.error = ""
      //this.loggingIn = true
      // Auth.login() returns a promise. A redirect will happen on success.
      // For errors, use .then() to capture the response to output
      // error_description (if exists) as shown below:
      /*
      this.$auth.login(credentials, 'dashboard').then((response) => {
        this.loggingIn = false
        this.error = utils.getError(response)
      })
      */

      if (  this.credentials.username === "" || 
            this.credentials.password === ""
      ) {
        this.error = "Izpolnite vsa polja."
        return  
      }


      var data = {
        username: this.credentials.username,
        password: this.credentials.password
      }

      var component = this
      this.$http.post(this.$root.storeGet("api_addr") + "/api/login", 
        data, // the data to post
        { headers: {
          'Content-type': 'application/x-www-form-urlencoded',
        }
        })
        .then(function (response) {
          component.$root.store.api_error = null
          var token = response.data.token
          if (token === null) {
            component.error = "Napačno uporabniško ime ali geslo."
          } else {
            // set cookies (if the page reloads)
            component.$root.store.username = component.credentials.username
            component.$root.store.token = token
            component.$router.go(-1)
            component.$cookies.set("valency_token", token, 60*60*48)
          }
        })
        .catch(function (err) {
          component.$root.store.api_error = err
        })
    },
  },
}
</script>

<style scoped>
.ev-login {
  margin-top: 100px;
}
</style>