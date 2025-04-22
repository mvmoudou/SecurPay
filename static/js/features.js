document.addEventListener("DOMContentLoaded", () => {
    const openLink = document.getElementById("open-features-link");
    const popup = document.getElementById("features-popup");
    const overlay = document.getElementById("blur-overlay");
    const closeBtn = document.querySelector(".features-close");

    if (openLink && popup && overlay && closeBtn) {
        openLink.addEventListener("click", (e) => {
            e.preventDefault();
            popup.classList.remove("hidden");
            overlay.classList.remove("hidden");
        });

        closeBtn.addEventListener("click", () => {
            popup.classList.add("hidden");
            overlay.classList.add("hidden");
        });

        overlay.addEventListener("click", () => {
            popup.classList.add("hidden");
            overlay.classList.add("hidden");
        });
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const featuresFromHome = document.getElementById("open-login-modal-from-features");
    const loginModal = document.getElementById("login-modal");
  
    if (featuresFromHome && loginModal) {
      featuresFromHome.addEventListener("click", (e) => {
        e.preventDefault();
        loginModal.classList.add("show");
        document.body.style.overflow = "hidden";
      });
  
      // Fermer la modale
      const closeBtn = loginModal.querySelector(".close-button");
      closeBtn.addEventListener("click", () => {
        loginModal.classList.remove("show");
        document.body.style.overflow = "auto";
      });
  
      // Aller vers signup
      const goToSignup = document.getElementById("go-to-signup");
      if (goToSignup) {
        goToSignup.addEventListener("click", (e) => {
          e.preventDefault();
          loginModal.classList.remove("show");
          loadModal("/signup-modal"); // ou afficher une modale d’inscription si tu l’as
        });
      }
    }
  });
  