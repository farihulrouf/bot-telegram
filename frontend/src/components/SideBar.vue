<template>
    <div class="flex h-screen bg-gray-100">
      <!-- Sidebar -->
      <aside class="w-64 bg-gray-800 text-gray-100">
        <div class="p-4 text-2xl font-bold text-center bg-gray-900">
          My Sidebar
        </div>
        <nav class="mt-5 space-y-2">
          <ul>
            <li>
              <a
                href="#"
                @click="selectMenu('sendMessage')"
                class="block px-4 py-2 text-sm font-semibold hover:bg-gray-700"
                :class="{ 'bg-gray-700': activeMenu === 'sendMessage' }"
              >
                Send Message
              </a>
            </li>
            <li>
              <a
                href="#"
                @click="selectMenu('scrapChannel')"
                class="block px-4 py-2 text-sm font-semibold hover:bg-gray-700"
                :class="{ 'bg-gray-700': activeMenu === 'scrapChannel' }"
              >
                Scrap Channel
              </a>
            </li>
            <li>
              <a
                href="#"
                @click="selectMenu('scrapGroup')"
                class="block px-4 py-2 text-sm font-semibold hover:bg-gray-700"
                :class="{ 'bg-gray-700': activeMenu === 'scrapGroup' }"
              >
                Scrap Group
              </a>
            </li>
          </ul>
        </nav>
      </aside>
  
      <!-- Main content area -->
      <main class="flex-1 p-6">
        <div v-if="activeMenu === 'sendMessage'">
          <h2 class="text-xl font-bold">Send Message</h2>
          <p>Here you can send a message.</p>
        </div>
        <div v-else-if="activeMenu === 'scrapChannel'">
          <h2 class="text-xl font-bold">Scrap Channel</h2>
          <p>Here you can scrap a channel.</p>
        </div>
        <div v-else-if="activeMenu === 'scrapGroup'">
          <h2 class="text-xl font-bold">Scrap Group</h2>
          <p>Here you can scrap a group.</p>
        </div>
      </main>
    </div>
  </template>
  
  <script>
  export default {
    data() {
      return {
        activeMenu: "sendMessage", // Default menu selection
      };
    },
    methods: {
      selectMenu(menu) {
        this.activeMenu = menu;
      },
    },
  };
  </script>
  
  <style scoped>
  /* Additional custom styles if needed */
  </style>
  