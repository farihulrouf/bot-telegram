<template>
  <div id="app">
    <NavBar class="navbar" /> <!-- Memanggil komponen NavBar -->
    <div class="flex">
      <Sidebar :activeMenu="activeMenu" :selectMenu="selectMenu" class="sidebar" />
      <Main :activeMenu="activeMenu" class="main-content" />
    </div>
  </div>
</template>

<script>
import NavBar from './components/NavBar.vue';
import Sidebar from './components/SideBar.vue';
import Main from './components/MainContent.vue';

export default {
  name: "App",
  components: {
    NavBar,
    Sidebar,
    Main,
  },
  data() {
    return {
      activeMenu: "sendMessage",
    };
  },
  methods: {
    selectMenu(menu) {
      this.activeMenu = menu;
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

.flex {
  display: flex;
  flex: 1; /* Memastikan elemen ini mengisi ruang yang tersedia */
}

.sidebar {
  width: 250px; /* Atur lebar sidebar sesuai kebutuhan */
  background-color: #f4f4f4; /* Contoh warna latar belakang sidebar */
}

.main-content {
  flex: 1; /* Memastikan konten utama mengisi sisa ruang */
  padding: 20px; /* Padding untuk konten */
  background-color: #ffffff; /* Contoh warna latar belakang konten utama */
  overflow: hidden; /* Menyembunyikan overflow konten utama */
}

.navbar {
  height: 60px; /* Atur tinggi navbar sesuai kebutuhan */
  background-color: #007bff; /* Contoh warna navbar */
}
</style>
