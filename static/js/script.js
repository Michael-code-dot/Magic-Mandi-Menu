// ========================
// SEARCH FOOD
// ========================
document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("searchFood");

    if (searchInput) {
        searchInput.addEventListener("input", function () {

            const value = this.value.toLowerCase().trim();

            document.querySelectorAll(".card").forEach(function(card) {

                const text = card.textContent.toLowerCase();

                if (text.includes(value)) {
                    card.style.display = "";
                } else {
                    card.style.display = "none";
                }

            });

        });
    }

});

// ========================
// CATEGORY FILTER
// ========================
function filterCategory(category) {

    document.querySelectorAll(".card").forEach(function(card) {

        if (category === "All" || card.dataset.category === category) {
            card.style.display = "";
        } else {
            card.style.display = "none";
        }

    });

}