document.addEventListener("DOMContentLoaded", function () {

    const registerForm = document.getElementById("registerForm");

    if (registerForm) {
        registerForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const message = document.getElementById("registerMessage");

            const password = document.getElementById("password").value;
            const confirmPassword = document.getElementById("confirmPassword").value;

            if (password !== confirmPassword) {
                message.textContent = "Passwords do not match.";
                return;
            }

            const data = {
                fullname: document.getElementById("fullname").value,
                matric: document.getElementById("matric").value,
                email: document.getElementById("email").value,
                department: document.getElementById("department").value,
                level: document.getElementById("level").value,
                password: password
            };

            message.textContent = "Submitting registration...";

            try {
                const response = await fetch("/api/register", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                message.textContent = result.message || result.error;

                if (response.ok) {
                    registerForm.reset();
                    setTimeout(() => {
                        window.location.href = "login.html";
                    }, 1500);
                }
            } catch (error) {
                message.textContent = "Unable to connect to the server.";
            }
        });
    }

    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const message = document.getElementById("loginMessage");

            const data = {
                email: document.getElementById("email").value,
                password: document.getElementById("password").value
            };

            message.textContent = "Logging in...";

            try {
                const response = await fetch("/api/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    localStorage.setItem("token", result.token);
                    localStorage.setItem("role", result.role);
                    localStorage.setItem("fullname", result.fullname);

                    window.location.href = "dashboard.html";
                } else {
                    message.textContent = result.error;
                }
            } catch (error) {
                message.textContent = "Unable to connect to the server.";
            }
        });
    }

});
