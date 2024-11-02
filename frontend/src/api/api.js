// src/api/api.js
import axios from 'axios';

const apiUrl = 'http://localhost:8000/api/token';

// Fungsi untuk mendapatkan token
const getToken = async (username, password) => {
  try {
    const response = await axios.post(apiUrl, {
      username,
      password
    });
    return response.data; // Kembalikan data yang diterima dari server
  } catch (error) {
    console.error('Error fetching token:', error.response ? error.response.data : error.message);
    throw error; // Lempar kembali error agar dapat ditangani di tempat lain
  }
};

// Ekspor fungsi getToken agar bisa digunakan di tempat lain
export default getToken;

