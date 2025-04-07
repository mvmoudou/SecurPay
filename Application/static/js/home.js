document.addEventListener("DOMContentLoaded", function () {
    const openSignupBtn = document.getElementById("open-signup");
    const openLoginBtn = document.getElementById("open-login");

    const signupModal = document.getElementById("signup-modal");
    const signupContent = document.getElementById("signup-modal-content");
    const loginModal = document.getElementById("login-modal");
    const loginContent = document.getElementById("login-modal-content");

    function loadModal(endpoint, modalElem, contentElem, scriptPath, callbackFunctionName, needsFaceApi = false) {
        fetch(endpoint)
            .then(res => res.text())
            .then(html => {
                contentElem.innerHTML = html;
                modalElem.style.display = "flex";

                const loadUserScript = () => {
                    const userScript = document.createElement("script");
                    userScript.src = scriptPath;
                    userScript.onload = () => {
                        if (typeof window[callbackFunctionName] === "function") {
                            window[callbackFunctionName]();
                        }
                    };
                    document.body.appendChild(userScript);
                };

                if (needsFaceApi) {
                    const faceApiScript = document.createElement("script");
                    faceApiScript.src = "https://cdn.jsdelivr.net/npm/@vladmandic/face-api/dist/face-api.min.js";
                    faceApiScript.onload = loadUserScript;
                    document.body.appendChild(faceApiScript);
                } else {
                    loadUserScript();
                }
            });
    }

    if (openSignupBtn) {
        openSignupBtn.addEventListener("click", () => {
            loadModal("/signup-modal", signupModal, signupContent, "/static/js/signup_modal.js", "setupBiometricsCapture", true);
        });
    }

    if (openLoginBtn) {
        openLoginBtn.addEventListener("click", () => {
            loadModal("/login-modal", loginModal, loginContent, "/static/js/login_modal.js", "setupLoginWithCamera", true);
        });
    }

    // Fermer les modals si on clique à l'extérieur
    window.addEventListener("click", (e) => {
        if (e.target === signupModal) {
            signupModal.style.display = "none";
            signupContent.innerHTML = "";
        }
        if (e.target === loginModal) {
            loginModal.style.display = "none";
            loginContent.innerHTML = "";
        }
    });
});

// Pour le retour au formulaire qui est en popup après avoir lu les conditions générales d'utilisation

document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("open") === "signup") {
        const openSignupBtn = document.getElementById("open-signup");
        if (openSignupBtn) {
            openSignupBtn.click();

            // attendre que la modale se charge
            const interval = setInterval(() => {
                const checkbox = document.getElementById("accept-checkbox");
                if (checkbox) {
                    if (params.get("accept_cgu") === "yes") {
                        checkbox.checked = true;
                        const hiddenInput = document.getElementById("terms_accepted");
                        if (hiddenInput) hiddenInput.value = "yes";
                    }
                    clearInterval(interval); // on arrête d’attendre
                }
            }, 100);
        }
    }
});


