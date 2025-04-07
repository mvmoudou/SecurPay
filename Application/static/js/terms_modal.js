document.addEventListener("DOMContentLoaded", () => {
    const openBtn = document.getElementById("show-terms");
    const modal = document.getElementById("terms-modal");
    const overlay = document.getElementById("terms-overlay");
    const closeBtn = document.getElementById("close-terms");
    const acceptBtn = document.getElementById("accept-terms");
    const checkbox = document.getElementById("accept-checkbox");

    if (openBtn && modal && overlay && closeBtn && acceptBtn && checkbox) {
        openBtn.addEventListener("click", (e) => {
            e.preventDefault();
            modal.classList.remove("hidden");
            overlay.classList.remove("hidden");
        });

        closeBtn.addEventListener("click", () => {
            modal.classList.add("hidden");
            overlay.classList.add("hidden");
        });

        acceptBtn.addEventListener("click", () => {
            checkbox.checked = true;
            document.getElementById("terms_accepted").value = "yes";
            modal.classList.add("hidden");
            overlay.classList.add("hidden");
        });
        

        overlay.addEventListener("click", () => {
            modal.classList.add("hidden");
            overlay.classList.add("hidden");
        });
    }
});
