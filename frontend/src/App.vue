<template>
  <div id="app">
    <NavBar class="navbar" v-if="isLoggedIn" /> <!-- Menampilkan NavBar hanya jika sudah login -->
    <div class="flex">
      <Sidebar :activeMenu="activeMenu" :selectMenu="selectMenu" v-if="isLoggedIn" class="sidebar" />
      <Main :activeMenu="activeMenu" v-if="isLoggedIn" class="main-content" />
      <Login v-else @loginSuccess="handleLoginSuccess" /> <!-- Tampilkan Login jika belum login -->
    </div>
  </div>
</template>

<script>
import NavBar from './components/NavBar.vue';
import Sidebar from './components/SideBar.vue';
import Main from './components/MainContent.vue';
import Login from './components/Login.vue'; // Impor komponen Login

export default {
  name: "App",
  components: {
    NavBar,
    Sidebar,
    Main,
    Login, // Daftarkan komponen Login
  },
  data() {
    return {
      activeMenu: "sendMessage",
      isLoggedIn: false, // Status login
    };
  },
  methods: {
    selectMenu(menu) {
      this.activeMenu = menu;
    },
    handleLoginSuccess() {
      this.isLoggedIn = true; // Ubah status login menjadi true
    },
  },
};
</script>

<style>
#app {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Mengatur tinggi penuh viewport */
  overflow: hidden; /* Menyembunyikan overflow agar tidak bisa scroll */
}
</style>
