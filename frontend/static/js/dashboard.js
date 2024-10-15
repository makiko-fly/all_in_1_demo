const API_URL = 'http://localhost:5000';  // Update this with your actual API URL

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');

    if (!token) {
        window.location.href = 'login';
        return;
    }

    const userInfo = document.getElementById('user-info');
    const logoutBtn = document.getElementById('logout-btn');
    const listUsersBtn = document.getElementById('list-users-btn');
    const userList = document.getElementById('user-list');
    const servicesList = document.getElementById('services-list');

    userInfo.textContent = `Welcome, ${username}!`;

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        window.location.href = 'login';
    });

    listUsersBtn.addEventListener('click', fetchUserList);

    async function fetchUserList() {
        try {
            const response = await fetch(`${API_URL}/users`, {
                headers: { 'Authorization': token }
            });
            if (response.ok) {
                const users = await response.json();
                userList.innerHTML = users.map(user => `<li>${user.username}</li>`).join('');
            } else {
                throw new Error('Failed to fetch users');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to load users');
        }
    }

    async function fetchServicesStatus() {
        try {
            const response = await fetch(`${API_URL}/services`, {
                headers: { 'Authorization': token }
            });
            if (response.ok) {
                const services = await response.json();
                const servicesHtml = services.map(service => `
                    <div class="service-item">
                        <h3>${service.name}</h3>
                        <p>Status: ${service.status}</p>
                        <p>Instance ID: ${service.instance_id || 'N/A'}</p>
                    </div>
                `).join('');
                servicesList.innerHTML = servicesHtml;
            } else {
                throw new Error('Failed to fetch services status');
            }
        } catch (error) {
            console.error('Error:', error);
            servicesList.innerHTML = 'Failed to load services status';
        }
    }

    fetchUserList(); // Fetch user list immediately on page load
    fetchServicesStatus();
    setInterval(fetchServicesStatus, 30000); // Refresh services status every 30 seconds
});