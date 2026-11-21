/* =========================================================
   FRESHCART FRONTEND
========================================================= */

const API = "/api";

let products = [];
let categories = [];

let cart = JSON.parse(localStorage.getItem("freshcart_cart")) || [];

let selectedCategory = null;


/* =========================================================
   PAGE START
========================================================= */

document.addEventListener("DOMContentLoaded", async () => {

    updateCartCount();

    await loadCategories();

    await loadProducts();

});


/* =========================================================
   API HELPER
========================================================= */

async function apiRequest(url, options = {}) {

    try {

        const response = await fetch(API + url, {
            credentials: "include",
            ...options,

            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });

        const data = await response.json();

        return data;

    } catch (error) {

        console.error("API Error:", error);

        return {
            success: false,
            message: "Could not connect to the server."
        };
    }
}


/* =========================================================
   LOAD CATEGORIES
========================================================= */

async function loadCategories() {

    const result = await apiRequest("/categories");

    if (!result.success) {

        document.getElementById("categoriesContainer").innerHTML =
            `<p class="error">${result.message}</p>`;

        return;
    }

    categories = result.data;

    renderCategories();

    renderCategoryFilters();
}


/* =========================================================
   CATEGORY ICON
========================================================= */

function getCategoryIcon(categoryName) {

    const name = categoryName.toLowerCase();

    if (name.includes("dairy")) {
        return "🥛";
    }

    if (name.includes("bakery")) {
        return "🥖";
    }

    if (name.includes("beverage")) {
        return "🥤";
    }

    if (name.includes("produce")) {
        return "🍎";
    }

    if (name.includes("snack")) {
        return "🍿";
    }

    return "🛒";
}


/* =========================================================
   RENDER CATEGORIES
========================================================= */

function renderCategories() {

    const container =
        document.getElementById("categoriesContainer");

    container.innerHTML = "";

    categories.forEach(category => {

        const card = document.createElement("div");

        card.className = "category-card";

        card.onclick = () => {

            filterCategory(
                category.category_id,
                null
            );

            scrollToProducts();
        };

        card.innerHTML = `
            <div class="category-icon">
                ${getCategoryIcon(category.category_name)}
            </div>

            <h3>${escapeHTML(category.category_name)}</h3>
        `;

        container.appendChild(card);
    });
}


/* =========================================================
   CATEGORY FILTERS
========================================================= */

function renderCategoryFilters() {

    const container =
        document.getElementById("categoryFilters");

    container.innerHTML = "";

    categories.forEach(category => {

        const button =
            document.createElement("button");

        button.className = "filter-btn";

        button.textContent =
            category.category_name;

        button.onclick = () => {

            filterCategory(
                category.category_id,
                button
            );
        };

        container.appendChild(button);
    });
}


/* =========================================================
   LOAD PRODUCTS
========================================================= */

async function loadProducts() {

    let url = "/products";

    const params = [];

    if (selectedCategory) {

        params.push(
            `category_id=${encodeURIComponent(selectedCategory)}`
        );
    }

    const search =
        document.getElementById("searchInput")?.value.trim();

    if (search) {

        params.push(
            `search=${encodeURIComponent(search)}`
        );
    }

    if (params.length > 0) {

        url += "?" + params.join("&");
    }

    const result =
        await apiRequest(url);

    const container =
        document.getElementById("productsContainer");

    if (!result.success) {

        container.innerHTML =
            `<p class="error">${result.message}</p>`;

        return;
    }

    products = result.data;

    renderProducts();
}


/* =========================================================
   RENDER PRODUCTS
========================================================= */

function renderProducts() {

    const container =
        document.getElementById("productsContainer");

    container.innerHTML = "";

    if (products.length === 0) {

        container.innerHTML = `
            <div class="loading">
                No products found.
            </div>
        `;

        return;
    }

    products.forEach(product => {

        const outOfStock =
            product.quantity_available <= 0;

        const card =
            document.createElement("div");

        card.className = "product-card";

        card.innerHTML = `

            <div class="product-image">

                <span class="product-category">
                    ${escapeHTML(product.category_name || "Grocery")}
                </span>

                ${
                    outOfStock
                    ?
                    `<span class="out-stock">
                        OUT OF STOCK
                    </span>`
                    :
                    ""
                }

                <span>
                    ${getProductIcon(product.product_name)}
                </span>

            </div>

            <div class="product-info">

                <h3>
                    ${escapeHTML(product.product_name)}
                </h3>

                <div class="category">
                    ${escapeHTML(product.category_name || "")}
                </div>

                <div class="product-bottom">

                    <div>

                        <div class="price">
                            Rs. ${formatPrice(product.price)}
                        </div>

                        <div class="stock">
                            ${
                                outOfStock
                                ? "Currently unavailable"
                                : `${product.quantity_available} in stock`
                            }
                        </div>

                    </div>

                    <button
                        class="add-cart"
                        ${
                            outOfStock
                            ? "disabled"
                            : ""
                        }
                        onclick="addToCart(${product.product_id})"
                        title="Add to cart">
                        +
                    </button>

                </div>

            </div>
        `;

        container.appendChild(card);
    });
}


/* =========================================================
   PRODUCT ICON
========================================================= */

function getProductIcon(name) {

    const product =
        name.toLowerCase();

    if (
        product.includes("milk") ||
        product.includes("coconut")
    ) {
        return "🥛";
    }

    if (product.includes("bread")) {
        return "🍞";
    }

    if (product.includes("chicken")) {
        return "🍗";
    }

    if (
        product.includes("banana")
    ) {
        return "🍌";
    }

    if (
        product.includes("chips") ||
        product.includes("lays")
    ) {
        return "🍟";
    }

    if (
        product.includes("sprite") ||
        product.includes("coffee")
    ) {
        return "🥤";
    }

    return "🛒";
}


/* =========================================================
   SEARCH
========================================================= */

let searchTimer;

function searchProducts() {

    clearTimeout(searchTimer);

    searchTimer =
        setTimeout(() => {

            loadProducts();

        }, 300);
}


/* =========================================================
   CATEGORY FILTER
========================================================= */

function filterCategory(categoryId, button) {

    selectedCategory =
        categoryId;

    document
        .querySelectorAll(".filter-btn")
        .forEach(btn => {
            btn.classList.remove("active");
        });

    if (button) {

        button.classList.add("active");

    } else {

        const allButton =
            document.querySelector(
                ".filter-row > .filter-btn"
            );

        if (allButton) {
            allButton.classList.add("active");
        }
    }

    loadProducts();
}


/* =========================================================
   CART
========================================================= */

function saveCart() {

    localStorage.setItem(
        "freshcart_cart",
        JSON.stringify(cart)
    );

    updateCartCount();
}


function updateCartCount() {

    const count =
        cart.reduce(
            (total, item) =>
                total + item.quantity,
            0
        );

    const element =
        document.getElementById("cartCount");

    if (element) {
        element.textContent = count;
    }
}


function addToCart(productId) {

    const product =
        products.find(
            p => p.product_id == productId
        );

    if (!product) {
        return;
    }

    const existing =
        cart.find(
            item => item.product_id == productId
        );

    if (existing) {

        if (
            existing.quantity <
            product.quantity_available
        ) {

            existing.quantity++;

        } else {

            alert("You cannot add more than the available stock.");

            return;
        }

    } else {

        cart.push({
            product_id: product.product_id,
            product_name: product.product_name,
            price: Number(product.price),
            quantity: 1,
            max_stock: product.quantity_available
        });
    }

    saveCart();

    showTemporaryMessage(
        `${product.product_name} added to cart.`
    );
}


function changeQuantity(productId, change) {

    const item =
        cart.find(
            item => item.product_id == productId
        );

    if (!item) {
        return;
    }

    item.quantity += change;

    if (item.quantity <= 0) {

        cart =
            cart.filter(
                item =>
                    item.product_id != productId
            );

    }

    if (item && item.quantity > item.max_stock) {

        item.quantity =
            item.max_stock;

        alert("Maximum available stock reached.");
    }

    saveCart();

    renderCart();
}


function removeFromCart(productId) {

    cart =
        cart.filter(
            item =>
                item.product_id != productId
        );

    saveCart();

    renderCart();
}


function calculateCartTotal() {

    return cart.reduce(
        (total, item) =>
            total +
            (item.price * item.quantity),
        0
    );
}


/* =========================================================
   CART MODAL
========================================================= */

function openCart() {

    renderCart();

    document
        .getElementById("cartModal")
        .classList.add("show");
}


function closeCart() {

    document
        .getElementById("cartModal")
        .classList.remove("show");
}


function renderCart() {

    const container =
        document.getElementById("cartItems");

    if (!container) {
        return;
    }

    if (cart.length === 0) {

        container.innerHTML = `
            <div class="loading">
                Your cart is empty.
            </div>
        `;

        document.getElementById("cartTotal")
            .textContent = "Rs. 0.00";

        return;
    }

    container.innerHTML = "";

    cart.forEach(item => {

        const row =
            document.createElement("div");

        row.className = "cart-item";

        row.innerHTML = `

            <div class="cart-item-image">
                ${getProductIcon(item.product_name)}
            </div>

            <div class="cart-item-info">

                <h4>
                    ${escapeHTML(item.product_name)}
                </h4>

                <p>
                    Rs. ${formatPrice(item.price)}
                </p>

            </div>

            <div class="quantity-controls">

                <button
                    onclick="changeQuantity(${item.product_id}, -1)">
                    −
                </button>

                <span>
                    ${item.quantity}
                </span>

                <button
                    onclick="changeQuantity(${item.product_id}, 1)">
                    +
                </button>

            </div>

            <button
                class="remove-btn"
                onclick="removeFromCart(${item.product_id})">
                Remove
            </button>
        `;

        container.appendChild(row);
    });

    document.getElementById("cartTotal")
        .textContent =
        `Rs. ${formatPrice(calculateCartTotal())}`;
}


/* =========================================================
   LOGIN
========================================================= */

function openLogin() {

    closeRegister();

    document
        .getElementById("loginModal")
        .classList.add("show");
}


function closeLogin() {

    document
        .getElementById("loginModal")
        .classList.remove("show");
}


async function loginUser(event) {

    event.preventDefault();

    const email =
        document.getElementById("loginEmail").value;

    const password =
        document.getElementById("loginPassword").value;

    const message =
        document.getElementById("loginMessage");

    message.textContent =
        "Logging in...";

    message.className =
        "form-message";


    const result =
        await apiRequest(
            "/auth/login",
            {
                method: "POST",

                body: JSON.stringify({
                    email: email,
                    password: password
                })
            }
        );


    if (!result.success) {

        message.textContent =
            result.message;

        message.className =
            "form-message error";

        return;
    }


    message.textContent =
        "Login successful!";

    message.className =
        "form-message success";


    setTimeout(() => {

        closeLogin();

        alert(
            `Welcome back, ${result.customer.full_name}!`
        );

    }, 700);
}


/* =========================================================
   REGISTER
========================================================= */

function openRegister() {

    closeLogin();

    document
        .getElementById("registerModal")
        .classList.add("show");
}


function closeRegister() {

    document
        .getElementById("registerModal")
        .classList.remove("show");
}


function openLoginFromRegister() {

    closeRegister();

    openLogin();
}


async function registerUser(event) {

    event.preventDefault();

    const message =
        document.getElementById("registerMessage");

    message.textContent =
        "Creating account...";

    message.className =
        "form-message";


    const data = {

        full_name:
            document.getElementById("registerName").value,

        email:
            document.getElementById("registerEmail").value,

        password:
            document.getElementById("registerPassword").value,

        phone:
            document.getElementById("registerPhone").value,

        address:
            document.getElementById("registerAddress").value
    };


    const result =
        await apiRequest(
            "/auth/register",
            {
                method: "POST",

                body: JSON.stringify(data)
            }
        );


    if (!result.success) {

        message.textContent =
            result.message;

        message.className =
            "form-message error";

        return;
    }


    message.textContent =
        "Account created successfully!";

    message.className =
        "form-message success";


    setTimeout(() => {

        closeRegister();

        openLogin();

    }, 900);
}


/* =========================================================
   CHECKOUT
========================================================= */

function goToCheckout() {

    if (cart.length === 0) {

        alert("Your cart is empty.");

        return;
    }

    closeCart();

    document.getElementById("checkoutTotal")
        .textContent =
        `Rs. ${formatPrice(calculateCartTotal())}`;

    document
        .getElementById("checkoutModal")
        .classList.add("show");
}


function closeCheckout() {

    document
        .getElementById("checkoutModal")
        .classList.remove("show");
}


async function placeOrder(event) {

    event.preventDefault();

    const address =
        document.getElementById("checkoutAddress")
            .value.trim();

    const paymentMethod =
        document.getElementById("paymentMethod")
            .value;

    const message =
        document.getElementById("checkoutMessage");


    if (!address) {

        message.textContent =
            "Please enter your delivery address.";

        message.className =
            "form-message error";

        return;
    }


    message.textContent =
        "Placing your order...";

    message.className =
        "form-message";


    const items =
        cart.map(item => ({
            product_id:
                item.product_id,

            quantity:
                item.quantity
        }));


    /*
       The current backend checkout endpoint
       expects customer_id.

       We retrieve it from the current login
       session by asking /api/auth/me.
    */

    const currentUser =
        await apiRequest("/auth/me");


    if (!currentUser.success) {

        message.textContent =
            "Please login before placing an order.";

        message.className =
            "form-message error";

        return;
    }


    const customerId =
        currentUser.customer.customer_id;


    const result =
        await apiRequest(
            "/orders/checkout",
            {
                method: "POST",

                body: JSON.stringify({
                    customer_id: customerId,
                    items: items,
                    payment_method: paymentMethod,
                    delivery_address: address
                })
            }
        );


    if (!result.success) {

        message.textContent =
            result.message;

        message.className =
            "form-message error";

        return;
    }


    cart = [];

    saveCart();

    closeCheckout();

    document.getElementById("successMessage")
        .textContent =
        `Your order #${result.order_id} has been placed successfully.`;

    document
        .getElementById("successModal")
        .classList.add("show");
}


function closeSuccess() {

    document
        .getElementById("successModal")
        .classList.remove("show");

    loadProducts();
}


/* =========================================================
   NAVIGATION
========================================================= */

function scrollToProducts() {

    document
        .getElementById("products")
        .scrollIntoView({
            behavior: "smooth"
        });
}


function scrollToCategories() {

    document
        .getElementById("categories")
        .scrollIntoView({
            behavior: "smooth"
        });
}


/* =========================================================
   UTILITIES
========================================================= */

function formatPrice(value) {

    return Number(value)
        .toLocaleString(
            "en-PK",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );
}


function escapeHTML(value) {

    if (value === null ||
        value === undefined) {

        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function showTemporaryMessage(text) {

    const message =
        document.createElement("div");

    message.textContent = text;

    message.style.position = "fixed";
    message.style.bottom = "25px";
    message.style.right = "25px";
    message.style.zIndex = "5000";

    message.style.background = "#395b42";
    message.style.color = "white";

    message.style.padding = "12px 18px";

    message.style.borderRadius = "7px";

    message.style.fontSize = "12px";

    message.style.boxShadow =
        "0 10px 30px rgba(0,0,0,0.15)";

    document.body.appendChild(message);

    setTimeout(() => {

        message.remove();

    }, 1800);
}


/* =========================================================
   CLOSE MODALS WHEN CLICKING OUTSIDE
========================================================= */

window.addEventListener("click", function(event) {

    if (event.target.classList.contains("modal")) {

        event.target.classList.remove("show");
    }

});