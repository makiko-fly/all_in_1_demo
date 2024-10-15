const API_URL = 'http://localhost:5000';  // Update this with your actual API URL

document.addEventListener('DOMContentLoaded', () => {
    const authForm = document.getElementById('auth-form');
    const loginBtn = document.getElementById('login-btn');
    const registerBtn = document.getElementById('register-btn');
    const errorMessage = document.getElementById('error-message');

    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const isLogin = e.submitter === loginBtn;

        try {
            const response = await fetch(`${API_URL}/${isLogin ? 'login' : 'register'}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            if (response.ok) {
                if (isLogin) {
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('username', username);
                    localStorage.setItem('isAdmin', data.is_admin);
                    window.location.href = 'dashboard';
                } else {
                    alert('Registration successful. Please login.');
                    authForm.reset();
                }
            } else {
                errorMessage.textContent = data.error || 'Authentication failed';
            }
        } catch (error) {
            console.error('Error:', error);
            errorMessage.textContent = 'An error occurred. Please try again.';
        }
    });

    registerBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        if (!username || !password) {
            errorMessage.textContent = 'Username and password are required';
            return;
        }

        fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                errorMessage.textContent = data.error;
            } else {
                alert('Registration successful. Please login.');
                errorMessage.textContent = '';
                authForm.reset();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            errorMessage.textContent = 'An error occurred during registration. Please try again.';
        });
    });
});