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
        type="email"
        class="form-control"
        placeholder="e-pošta"
        v-model="credentials.email"
      >
    </div>
    <div>
    <p>Novo geslo bo poslano na vaš e-poštni naslov.</p>
    </div>
    <button 
      data-id="new_pass.submit"
      class="btn btn-primary solid blank js-login__submit" 
      @click="submit()"
    >
      Novo geslo<i class="fa fa-arrow-circle-o-right"></i>
    </button>
  </div>
</div>
</template>

<script>
export default {
  name: 'NewPass',
  data () {
    return {
      credentials: {
        username: '',
        email: ''
      },
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
            this.credentials.email === ""
      ) {
        this.error = "Izpolnite vsa polja."
        return  
      }


      var data = {
        username: this.credentials.username,
        email: this.credentials.email
      }

      var component = this
      this.$http.post(this.$root.storeGet("api_addr") + "/api/new_pass", 
        data, // the data to post
        { headers: {
          'Content-type': 'application/x-www-form-urlencoded',
        }
        })
        .then(function (response) {
            component.$root.store.api_error = null
            var confirmation = response.data.confirmation
            component.$router.push({
                name: "Home"
            })
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