let cart = [];

// ========================
// ADD TO CART
// ========================
document.querySelectorAll(".add-btn").forEach(button => {
    button.addEventListener("click", function () {

        const name = this.dataset.name;
        const price = parseFloat(this.dataset.price);

        const existing = cart.find(item => item.name === name);

        if (existing) {
            existing.quantity++;
        } else {
            cart.push({
                name: name,
                price: price,
                quantity: 1
            });
        }

        updateCart();
    });
});

// ========================
// UPDATE CART
// ========================
function updateCart() {

    const cartDiv = document.getElementById("cart");

    if (cart.length === 0) {
        cartDiv.innerHTML = "<p>Your cart is empty.</p>";
        return;
    }

    cartDiv.innerHTML = "";

    let total = 0;

    cart.forEach((item, index) => {

        const subtotal = item.price * item.quantity;
        total += subtotal;

        cartDiv.innerHTML += `
        <div class="cart-item">
            <strong>${item.name}</strong><br>

            <button onclick="decreaseQuantity(${index})">−</button>

            ${item.quantity}

            <button onclick="increaseQuantity(${index})">+</button>

            <span>KSh ${subtotal.toFixed(2)}</span>

            <button onclick="removeItem(${index})">❌</button>

            <hr>
        </div>
        `;
    });

    cartDiv.innerHTML += `
        <h3>Total: KSh ${total.toFixed(2)}</h3>
    `;
}

// ========================
// CART FUNCTIONS
// ========================
function removeItem(index) {
    cart.splice(index, 1);
    updateCart();
}

function increaseQuantity(index) {
    cart[index].quantity++;
    updateCart();
}

function decreaseQuantity(index) {

    if (cart[index].quantity > 1) {
        cart[index].quantity--;
    } else {
        cart.splice(index, 1);
    }

    updateCart();
}

// ========================
// PLACE ORDER
// ========================
document.getElementById("placeOrderBtn").addEventListener("click", function () {

    const customerName = "Guest";
    const tableNumber = document.getElementById("table_number").value;

  

    if (!tableNumber) {
        alert("Table number missing.");
        return;
    }

    if (cart.length === 0) {
        alert("Your cart is empty.");
        return;
    }

    let total = 0;

    cart.forEach(item => {
        total += item.price * item.quantity;
    });

    fetch("/place_order", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            customer_name: customerName,
            table_number: tableNumber,
            cart: cart,
            total: total
        })

    })

    .then(response => response.json())

    .then(data => {

        alert(data.message);

        cart = [];
        updateCart();

      

        window.location.href = "/track/" + data.order_id;

    })

    .catch(error => {

        console.error(error);

        alert("Failed to place order.");

    });

});

// ========================
// SEARCH FOOD
// ========================
const searchInput = document.getElementById("searchFood");

if (searchInput) {

    searchInput.addEventListener("keyup", function () {

        const value = this.value.toLowerCase();

        document.querySelectorAll(".card").forEach(card => {

            const text = card.innerText.toLowerCase();

            if (text.includes(value)) {
                card.style.display = "block";
            } else {
                card.style.display = "none";
            }

        });

    });

}

function filterCategory(category) {
    document.querySelectorAll(".card").forEach(card => {
        if (
            category === "All" ||
            card.dataset.category.trim() === category
        ) {
            card.style.display = "";
        } else {
            card.style.display = "none";
        }
    });
}



