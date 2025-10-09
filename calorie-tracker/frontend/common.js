// Common JavaScript functionality for all pages

// Authentication helpers
function getAuthToken() {
  return localStorage.getItem('token');
}

function isAuthenticated() {
  return !!getAuthToken();
}

function authHeaders() {
  const token = getAuthToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function checkAuth() {
  if (!isAuthenticated()) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

function logout() {
  localStorage.removeItem('token');
  window.location.href = 'login.html';
}

// API endpoints
// Use relative URLs to work with any host (including IP addresses)
// This ensures API requests go to the same host/port as the frontend
const API_BASE_URL = '';

// Define API endpoints
const API = {
  login: `${API_BASE_URL}/auth/login`,
  register: `${API_BASE_URL}/auth/register`,
  currentUser: `${API_BASE_URL}/users/me`,
  meals: `${API_BASE_URL}/me/meals`,
  summary: `${API_BASE_URL}/me/summary`
};

// Fetch current user info
async function fetchCurrentUser() {
  try {
    const response = await fetch(API.currentUser, {
      headers: authHeaders()
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        logout();
        throw new Error('Authentication failed');
      }
      throw new Error('Failed to fetch user data');
    }
    
    return await response.json();
  } catch (error) {
    // Return null on error
    return null;
  }
}

// Convert UTC date string to local date object
function utcToLocal(dateString) {
  // Create a date object that correctly interprets the input as UTC
  // and then returns it in the local timezone
  const date = new Date(dateString + 'Z');
  return date;
}

// Convert local date to UTC for API
function localToUTC(localDate) {
  return new Date(localDate).toISOString();
}

// Format date for display in local timezone with time zone name
function formatDate(dateString) {
  const options = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short'
  };
  return utcToLocal(dateString).toLocaleDateString(undefined, options);
}

// Format time only with time zone name
function formatTime(dateString) {
  const options = {
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short'
  };
  return utcToLocal(dateString).toLocaleTimeString(undefined, options);
}

// Format time only without time zone name
function formatTimeShort(dateString) {
  const options = {
    hour: '2-digit',
    minute: '2-digit'
  };
  return utcToLocal(dateString).toLocaleTimeString(undefined, options);
}

// Format date for input fields (in local timezone)
function formatDateForInput(dateString) {
  const date = utcToLocal(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Get current date in ISO format (local date, start of day)
function getCurrentDateISO() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

// Get date range for the past week (in local timezone)
function getLastWeekRange() {
  const today = new Date();
  const lastWeek = new Date(today);
  lastWeek.setDate(today.getDate() - 7);
  
  return {
    from: `${lastWeek.getFullYear()}-${String(lastWeek.getMonth() + 1).padStart(2, '0')}-${String(lastWeek.getDate()).padStart(2, '0')}`,
    to: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  };
}

// Initialize navigation
function initNavigation() {
  // Get current page
  const currentPage = window.location.pathname.split('/').pop();
  
  // Set active class on current page link
  document.querySelectorAll('.navbar-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage) {
      link.classList.add('active');
    }
  });
  
  // Mobile menu toggle
  const navbarToggle = document.querySelector('.navbar-toggle');
  const navbarMenu = document.querySelector('.navbar-menu');
  
  if (navbarToggle && navbarMenu) {
    navbarToggle.addEventListener('click', () => {
      navbarMenu.classList.toggle('active');
    });
  }
}

// Display error message
function showError(elementId, message) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message;
    element.style.color = 'var(--danger-color)';
  }
}

// Display success message
function showSuccess(elementId, message) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message;
    element.style.color = 'var(--success-color)';
  }
}

// Create nutrition progress bar
function createNutritionBar(value, maxValue, color = 'var(--primary-color)') {
  const percentage = Math.min(100, (value / maxValue) * 100);
  return `
    <div class="nutrition-bar-container" style="width: 100%; background-color: #eee; border-radius: 10px; height: 20px; overflow: hidden;">
      <div class="nutrition-bar" style="width: ${percentage}%; height: 100%; background-color: ${color};"></div>
    </div>
    <div class="nutrition-bar-label" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
      <span>${value}</span>
      <span>${maxValue}</span>
    </div>
  `;
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
  // Skip authentication check on login page
  const currentPage = window.location.pathname.split('/').pop();
  if (currentPage === 'login.html') {
    return; // Skip auth check on login page
  }
  
  // Check authentication for all other pages
  if (checkAuth()) {
    // Initialize navigation
    initNavigation();
    
    // Set up logout buttons
    const logoutBtnMobile = document.getElementById('logoutBtnMobile');
    const logoutBtnDesktop = document.getElementById('logoutBtnDesktop');
    
    if (logoutBtnMobile) {
      logoutBtnMobile.addEventListener('click', logout);
    }
    
    if (logoutBtnDesktop) {
      logoutBtnDesktop.addEventListener('click', logout);
    }
    
    // Fetch and display user info
    fetchCurrentUser().then(user => {
      const userNameElement = document.getElementById('userName');
      if (userNameElement && user) {
        userNameElement.textContent = `Hello, ${user.name}!`;
      }
    });
  }
});