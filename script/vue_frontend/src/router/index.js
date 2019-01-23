import Vue from 'vue'
import Router from 'vue-router'
import Home from "@/components/Home"
import Login from "@/components/Login"
import Register from "@/components/Register"
import NewPass from "@/components/NewPass"
import MainDispl from "@/components/MainDispl"
import EditSenses from "@/components/EditSenses"

Vue.use(Router)

export default new Router({
    mode: "history",
    routes: [
        {
          path: '/',
          redirect: "/home"
        },
        {
          path: "/home",
          name: "Home",
          component: Home,
          children: [
            {
              path: "words/:hw",
              name: "MainDispl",
              component: MainDispl,
              props: true,
            },
          ]
        },
        {
          path: '/login',
          name: 'Login',
          component: Login
        },
        {
          path: '/register',
          name: 'Register',
          component: Register 
        },
        {
          path: '/new_pass',
          name: 'NewPass',
          component: NewPass
        }
    ]
})
