// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App'
import router from './router'
import VueCookies from "vue-cookies"

// bootstrap
import BootstrapVue from "bootstrap-vue"
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'

// ajax
import axios from "axios"

// config
import config_data from "../config/config.json"
// console.log(config_data)

Vue.config.productionTip = false

// cokies
Vue.use(VueCookies)

// bootstrap
Vue.use(BootstrapVue)

// CORS
// Vue.$http.headers.common['Access-Control-Allow-Origin'] = true

Vue.prototype.$http = axios

// hand-made global storage
const store = {
    api_error: null,
    api_addr: config_data.api_addr,
    // api_addr: "http://localhost:5004",  // development (webpack)
    // api_addr: "http://193.2.76.103:5004",  // production
    token: null,
    username: null,
    navSS: "words",
    radio: "one",
    has_se: [],  // used for appending (se) to certain verbs
}

const store_methods = {
  storeSet: function(key, val) {
    store[key] = val
  },
  storeGet: function(key) {
    // returns undefined if not in dict.
    // check if (variable)
    return store[key]
  }
}

const login_methods = {
    checkToken: function () {
        var tthis = this
        return new Promise(function (resolve, reject) {
            if (tthis.store.token === null) {
                tthis.store.username = null
                reject(false)
            }
            var data = {
                token: tthis.store.token,
                user: tthis.store.username
            }
            tthis.$http.post(tthis.store.api_addr + "/api/token", data, 
                { headers: {
                        'Content-type': 'application/x-www-form-urlencoded',
                }}
            )
            .then(function (response) {
                tthis.store.api_error = null
                if (response.data.confirmation) {
                    resolve(true)
                } else {
                    tthis.store.username = null
                    tthis.store.token = null
                    reject(false)
                }
            })
            .catch(function (err) {
                tthis.store.api_error = err
                reject(err)
            })
        })
    }
}

const other_methods = {
    routeBack: function() {
      this.$router.go(-1)
    },
    mkspace: function (idx, word) {
        var stopwords = [".", ",", ":", ";"]
        if (stopwords.includes(word)) return false
        return true
    }
}

/* eslint-disable no-new */
new Vue({
  el: '#app',
  router,
  components: { App },
  template: '<App/>',
  data() { return {
    store: store,
  }},
  methods: Object.assign(store_methods, login_methods, other_methods),
  beforeCreate: function() {
    document.title = "Vezljivostni vzorci"
    if (this.$cookies.isKey("valency_token")) {
        var cookie_token = this.$cookies.get("valency_token")
        var data = {
            token: cookie_token,
        }
        var component = this
        this.$http.post(store.api_addr + "/api/token", 
            data, // the data to post
            { headers: {
              'Content-type': 'application/x-www-form-urlencoded',
            }
            })
            .then(function (response) {
                if (response.data.confirmation) {
                    store.username = response.data.username
                    store.token = cookie_token
                } else {
                    this.$cookies.remove("valency_token")
                }
            })
            .catch(function (err) {
              store.api_error = err
            })
        }
    }
})
