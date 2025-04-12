document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("searchInput");
    const rows = document.querySelectorAll("#transactionsTable tbody tr");

    input?.addEventListener("input", () => {
        const query = input.value.toLowerCase();

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(query) ? "" : "none";
        });
    });
});
