<template>
    <nav class="relative flex items-center justify-between bg-teal-500 py-2 shadow-md dark:bg-neutral-700 lg:py-4">
      <div class="flex w-full items-center justify-between px-3">
        <!-- Hamburger button for mobile view -->
        <button @click="toggleMenu" class="block lg:hidden px-2">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"></path>
          </svg>
        </button>
  
        <!-- Logo / Brand name -->
        <div class="text-xl font-bold">My Brand</div>
  
        <!-- Navigation Links for desktop view -->
        <div class="hidden lg:flex space-x-6">
          <a href="#" class="hover:text-gray-700">Home</a>
          <a href="#" class="hover:text-gray-700">About</a>
          <a href="#" class="hover:text-gray-700">Services</a>
          <a href="#" class="hover:text-gray-700">Contact</a>
        </div>
  
        <!-- Icons section -->
        <div class="flex items-center space-x-4">
          <!-- Notification Icon -->
          <div class="relative">
            <button @click="toggleNotif" class="relative">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-4.215A2 2 0 0016.17 11H7.83a2 2 0 00-1.425.785L5 17h5m4 0v1a3 3 0 11-6 0v-1m9-2V5a7 7 0 10-14 0v10"></path>
              </svg>
              <span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full px-1">3</span>
            </button>
            <div v-if="isNotifOpen" class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg">
              <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-100">New Notification 1</a>
              <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-100">New Notification 2</a>
              <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-100">New Notification 3</a>
            </div>
          </div>
  
          <!-- Profile Icon with Dropdown -->
          <div class="relative">
            <button @click="toggleProfile" class="relative">
              <svg class="w-6 h-6 rounded-full bg-gray-300" fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zM12 14c-3.3 0-6 1.79-6 4v2h12v-2c0-2.21-2.7-4-6-4z"></path>
              </svg>
            </button>
            <div v-if="isProfileOpen" class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg">
              <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-100">My Profile</a>
              <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-100">Settings</a>
              <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-100">Logout</a>
            </div>
          </div>
        </div>
      </div>
  
      <!-- Mobile Menu -->
      <div v-if="isMenuOpen" class="lg:hidden mt-2 px-3">
        <a href="#" class="block py-2 text-sm hover:bg-gray-100">Home</a>
        <a href="#" class="block py-2 text-sm hover:bg-gray-100">About</a>
        <a href="#" class="block py-2 text-sm hover:bg-gray-100">Services</a>
        <a href="#" class="block py-2 text-sm hover:bg-gray-100">Contact</a>
      </div>
    </nav>
  </template>
  
  <script>
  export default {
    data() {
      return {
        isMenuOpen: false,
        isNotifOpen: false,
        isProfileOpen: false,
      };
    },
    methods: {
      toggleMenu() {
        this.isMenuOpen = !this.isMenuOpen;
      },
      toggleNotif() {
        this.isNotifOpen = !this.isNotifOpen;
        this.isProfileOpen = false;
      },
      toggleProfile() {
        this.isProfileOpen = !this.isProfileOpen;
        this.isNotifOpen = false;
      },
    },
  };
  </script>
  
  <style scoped>
  /* Menambahkan gaya khusus jika diperlukan */
  </style>
  