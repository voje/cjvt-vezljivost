<template>
<div>
  <p
    v-if="this.$root.store.api_error !== null" 
    class="text-warning"
  >
    api_error: {{ this.$root.store.api_error }}
  </p>
  <Nav></Nav>
    <div class="my-home container-fluid">
      <div class="row">
        <div id="serach" class="col-sm-2 border-right fill">
          <LWords v-if="navSS()"></LWords>
          <LFunctors v-else></LFunctors>
        </div>
        <div class="col-sm-10">
          <router-view></router-view>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Nav from "./Nav"
import LWords from "./LWords"
import LFunctors from "./LFunctors"
import MainDispl from "./MainDispl"

export default {
  name: 'Home',
  components: {
    Nav: Nav,
    LWords: LWords,
    LFunctors: LFunctors,
    MainDispl: MainDispl,
  },
  methods: {
    navSS: function () {
      return this.$root.storeGet("navSS") === "words"
    }
  }
}
</script>

<style scoped>
.my-home {
  padding-top: 10px;
}
</style>
