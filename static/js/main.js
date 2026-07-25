/**
 * TechMart POS & Inventory System Javascript Engine
 * Handles Cart Management, Autocomplete Search, Keyboard Hotkeys, Voice Commands,
 * and Webcam Barcode Scanning.
 */

// 1. THEME MANAGER
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const theme = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            updateThemeIcon(theme);
        });
    }
});

function updateThemeIcon(theme) {
    const icon = document.querySelector('#theme-toggle i');
    if (icon) {
        if (theme === 'dark') {
            icon.className = 'fas fa-sun';
        } else {
            icon.className = 'fas fa-moon';
        }
    }
}

// 2. POS CART STATE MANAGER
let cart = [];
let customerId = null;
let couponCode = null;
let couponDiscountData = null;
let isStudent = false;
let customersList = [];

document.addEventListener('DOMContentLoaded', () => {
    try {
        const custJson = document.getElementById('customers-json');
        if (custJson) {
            customersList = JSON.parse(custJson.textContent);
        }
    } catch(e) {
        console.error("Failed to parse customers list:", e);
    }
});

// Format helper
const formatCurrency = (val) => `INR ${parseFloat(val).toFixed(2)}`;

// Add product to cart
function addToCart(product) {
    const existing = cart.find(item => item.id === product.id);
    if (existing) {
        if (existing.quantity + 1 > product.quantity) {
            showNotification(`Insufficient stock. Only ${product.quantity} units available.`, 'danger');
            return;
        }
        existing.quantity += 1;
    } else {
        if (product.quantity < 1) {
            showNotification(`Product is out of stock.`, 'danger');
            return;
        }
        cart.push({
            id: product.id,
            product_id: product.product_id,
            name: product.name,
            selling_price: parseFloat(product.selling_price),
            mrp: parseFloat(product.mrp),
            gst: parseFloat(product.gst),
            discount: parseFloat(product.discount),
            quantity: 1.0,
            unit: product.unit,
            max_qty: parseFloat(product.quantity)
        });
    }
    renderCart();
    showNotification(`${product.name} added to cart.`, 'success');
}

// Remove from cart
function removeFromCart(id) {
    cart = cart.filter(item => item.id !== id);
    renderCart();
}

// Update quantity
function updateQuantity(id, qty) {
    const item = cart.find(item => item.id === id);
    if (item) {
        const floatQty = parseFloat(qty);
        if (isNaN(floatQty) || floatQty <= 0) {
            removeFromCart(id);
            return;
        }
        if (floatQty > item.max_qty) {
            showNotification(`Insufficient stock. Only ${item.max_qty} units available.`, 'danger');
            item.quantity = item.max_qty;
        } else {
            item.quantity = floatQty;
        }
        renderCart();
    }
}

// Calculate and render
function renderCart() {
    const tbody = document.getElementById('cart-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    
    let subtotal = 0.0;
    let totalDiscount = 0.0;
    let totalGst = 0.0;

    cart.forEach(item => {
        const itemBaseTotal = item.selling_price * item.quantity;
        // Product specific discount
        const prodDisc = itemBaseTotal * (item.discount / 100.0);
        const itemSubtotal = itemBaseTotal - prodDisc;
        
        // Product specific GST
        const itemGst = itemSubtotal * (item.gst / 100.0);

        subtotal += itemBaseTotal;
        totalDiscount += prodDisc;
        totalGst += itemGst;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><b>${item.name}</b><br><small class="text-muted">${item.product_id}</small></td>
            <td>
                <input type="number" step="any" class="form-control form-control-sm" 
                       value="${item.quantity}" style="width: 80px;"
                       onchange="updateQuantity(${item.id}, this.value)">
                <small class="text-muted">${item.unit}</small>
            </td>
            <td>${item.mrp.toFixed(2)}</td>
            <td>${item.discount}%</td>
            <td>${item.gst}%</td>
            <td>${item.selling_price.toFixed(2)}</td>
            <td>${(itemSubtotal).toFixed(2)}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="removeFromCart(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Handle coupon/global discount adjustments
    let subtotalAfterProductDisc = subtotal - totalDiscount;
    let couponAmt = 0.0;

    if (couponDiscountData) {
        if (subtotalAfterProductDisc >= couponDiscountData.min_purchase) {
            if (couponDiscountData.type === 'Percentage') {
                couponAmt = subtotalAfterProductDisc * (couponDiscountData.value / 100.0);
            } else if (couponDiscountData.type === 'Flat') {
                couponAmt = Math.min(couponDiscountData.value, subtotalAfterProductDisc);
            }
            totalDiscount += couponAmt;
            subtotalAfterProductDisc -= couponAmt;
        } else {
            showNotification(`Coupon requires minimum purchase of INR ${couponDiscountData.min_purchase}`, 'warning');
            couponDiscountData = null;
            couponCode = null;
            const couponInput = document.getElementById('coupon-code-input');
            if (couponInput) couponInput.value = '';
        }
    }

    // Handle demographic special discounts (Membership / Student check)
    let membershipAmt = 0.0;
    // Basic gold/silver check from customer dropdown selection
    const custSelect = document.getElementById('pos-customer-select');
    if (custSelect) {
        const opt = custSelect.options[custSelect.selectedIndex];
        const points = parseInt(opt.getAttribute('data-points') || 0);
        if (points > 500) {
            // Gold discount: 5% extra
            membershipAmt = subtotalAfterProductDisc * 0.05;
            totalDiscount += membershipAmt;
            subtotalAfterProductDisc -= membershipAmt;
        } else if (points > 200) {
            // Silver discount: 2% extra
            membershipAmt = subtotalAfterProductDisc * 0.02;
            totalDiscount += membershipAmt;
            subtotalAfterProductDisc -= membershipAmt;
        }
    }

    let studentAmt = 0.0;
    if (isStudent) {
        // Student discount: 3% extra
        studentAmt = subtotalAfterProductDisc * 0.03;
        totalDiscount += studentAmt;
        subtotalAfterProductDisc -= studentAmt;
    }

    const finalGrandTotal = Math.max(0, subtotal - totalDiscount + totalGst);
    const roundedTotal = Math.round(finalGrandTotal);
    const roundOff = roundedTotal - finalGrandTotal;

    // Write numbers to sidebar
    document.getElementById('pos-subtotal').innerText = formatCurrency(subtotal);
    document.getElementById('pos-discounts').innerText = formatCurrency(totalDiscount);
    document.getElementById('pos-gst').innerText = formatCurrency(totalGst);
    document.getElementById('pos-grand-total').innerText = formatCurrency(roundedTotal);
    document.getElementById('pos-round-off').innerText = roundOff.toFixed(2);

    updateBalanceCalculation(roundedTotal);
}

function updateBalanceCalculation(grandTotal) {
    const cashRecInput = document.getElementById('cash-received-input');
    const balanceDiv = document.getElementById('pos-balance-change');
    if (!cashRecInput || !balanceDiv) return;

    const cashReceived = parseFloat(cashRecInput.value || 0.0);
    const balance = cashReceived - grandTotal;
    
    if (balance >= 0) {
        balanceDiv.innerText = formatCurrency(balance);
        balanceDiv.className = "fs-5 fw-bold text-success";
    } else {
        balanceDiv.innerText = formatCurrency(0);
        balanceDiv.className = "fs-5 fw-bold text-danger";
    }
}

// Apply coupon code via API
async function applyCoupon() {
    const input = document.getElementById('coupon-code-input');
    if (!input || !input.value.trim()) return;

    const code = input.value.trim();
    try {
        const res = await fetch(`/api/pos/check_coupon?code=${code}`);
        const data = await res.json();
        if (data.valid) {
            couponCode = code;
            couponDiscountData = data;
            showNotification(`Coupon '${code}' applied successfully!`, 'success');
            renderCart();
        } else {
            showNotification(data.message, 'danger');
            couponDiscountData = null;
            couponCode = null;
        }
    } catch (err) {
        showNotification("Failed to verify coupon code.", "danger");
    }
}

// Handle customer loyalty select updates
function onCustomerChange() {
    const select = document.getElementById('pos-customer-select');
    const nameInput = document.getElementById('pos-customer-name');
    const phoneInput = document.getElementById('pos-customer-phone');
    const emailInput = document.getElementById('pos-customer-email');
    const addressInput = document.getElementById('pos-customer-address');

    if (select) {
        customerId = select.value ? parseInt(select.value) : null;
        if (customerId) {
            const customer = customersList.find(c => c.id === customerId);
            if (customer) {
                if (nameInput) { nameInput.value = customer.name; nameInput.readOnly = true; }
                if (phoneInput) { phoneInput.value = customer.phone; phoneInput.readOnly = true; }
                if (emailInput) { emailInput.value = customer.email || ''; emailInput.readOnly = true; }
                if (addressInput) { addressInput.value = customer.address || ''; addressInput.readOnly = true; }
            }
        } else {
            // Reset to walk-in defaults
            if (nameInput) { nameInput.value = ''; nameInput.readOnly = false; }
            if (phoneInput) { phoneInput.value = ''; phoneInput.readOnly = false; }
            if (emailInput) { emailInput.value = ''; emailInput.readOnly = false; }
            if (addressInput) { addressInput.value = ''; addressInput.readOnly = false; }
        }
        renderCart();
    }
}

// Handle student checkbox triggers
function onStudentToggle(checked) {
    isStudent = checked;
    renderCart();
}

// Toast alerts helper
function showNotification(message, type = 'success') {
    const container = document.getElementById('notification-toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show shadow-sm border-0 m-2`;
    toast.role = 'alert';
    toast.style.width = '300px';
    toast.innerHTML = `
        <div>${message}</div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    container.appendChild(toast);
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(toast);
        bsAlert.close();
    }, 3000);
}

// 3. SEARCH AUTOCOMPLETE & DYNAMIC RECOMMENDATIONS
let selectedSuggestionIdx = -1;

function initPOSAutocomplete() {
    const searchInput = document.getElementById('pos-search-input');
    const suggestionsContainer = document.getElementById('pos-suggestions');
    if (!searchInput || !suggestionsContainer) return;

    searchInput.addEventListener('input', async (e) => {
        const query = e.target.value.trim();
        if (query.length < 2) {
            suggestionsContainer.innerHTML = '';
            return;
        }

        try {
            const res = await fetch(`/api/products/search?q=${encodeURIComponent(query)}`);
            const products = await res.json();
            
            suggestionsContainer.innerHTML = '';
            selectedSuggestionIdx = -1;

            if (products.length === 0) {
                // If barcode not found in suggestions, check if numeric and allow fast adding
                suggestionsContainer.innerHTML = `
                    <div class="suggestion-item text-danger d-flex justify-content-between align-items-center">
                        <span>Product not found</span>
                        <button class="btn btn-xs btn-primary py-0 px-2 fs-7" onclick="openAddProductModal('${query}')">
                            <i class="fas fa-plus"></i> Add New Product
                        </button>
                    </div>
                `;
                return;
            }

            products.forEach((p, idx) => {
                const item = document.createElement('div');
                item.className = 'suggestion-item d-flex justify-content-between align-items-center';
                item.dataset.index = idx;
                item.innerHTML = `
                    <div>
                        <strong>${p.name}</strong> <span class="badge bg-secondary ms-1">${p.unit}</span><br>
                        <small class="text-muted">Barcode: ${p.barcode || 'N/A'} | Stock: ${p.quantity}</small>
                    </div>
                    <div>
                        <span class="fw-bold text-indigo">INR ${p.selling_price.toFixed(2)}</span>
                    </div>
                `;
                item.addEventListener('click', () => {
                    addToCart(p);
                    searchInput.value = '';
                    suggestionsContainer.innerHTML = '';
                });
                suggestionsContainer.appendChild(item);
            });
        } catch (err) {
            console.error("Autocomplete search error:", err);
        }
    });

    // Close suggestions on outside click
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
            suggestionsContainer.innerHTML = '';
        }
    });
}

function openAddProductModal(scannedBarcode) {
    // Open product bootstrap modal and prefill barcode field
    const modalEl = document.getElementById('addProductModal');
    if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        const bcField = document.getElementById('modal-barcode-field');
        if (bcField) bcField.value = scannedBarcode;
        modal.show();
    }
}

// 4. WEBCAM SCANNING LAYER (Server Decoded)
let scannerStream = null;
let scannerInterval = null;

function toggleWebcamScanner() {
    const video = document.getElementById('scanner-video-preview');
    const container = document.getElementById('scanner-preview-container');
    if (!video || !container) return;

    if (scannerStream) {
        // Stop Camera
        stopWebcamScanner();
    } else {
        // Start Camera
        container.classList.remove('d-none');
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
            .then(stream => {
                scannerStream = stream;
                video.srcObject = stream;
                video.play();
                
                // Initialize scan intervals (capture & send frame every 1000ms)
                scannerInterval = setInterval(captureAndSendFrame, 1000);
                showNotification("Scanner camera activated.", "info");
            })
            .catch(err => {
                showNotification("Could not access webcam camera: " + err.message, "danger");
            });
    }
}

function stopWebcamScanner() {
    const video = document.getElementById('scanner-video-preview');
    const container = document.getElementById('scanner-preview-container');
    
    if (scannerStream) {
        scannerStream.getTracks().forEach(track => track.stop());
        scannerStream = null;
    }
    if (scannerInterval) {
        clearInterval(scannerInterval);
        scannerInterval = null;
    }
    if (video) video.srcObject = null;
    if (container) container.classList.add('d-none');
}

async function captureAndSendFrame() {
    const video = document.getElementById('scanner-video-preview');
    if (!video || video.paused || video.ended) return;

    // Create virtual canvas
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const dataUrl = canvas.toDataURL('image/jpeg');

    try {
        const res = await fetch('/api/scanner/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: dataUrl })
        });
        
        if (res.status === 501) {
            // Scanner dependencies not installed on server
            stopWebcamScanner();
            showNotification("Barcode scanning failed: OpenCV/Pyzbar not active on server.", "danger");
            return;
        }

        const data = await res.json();
        if (data.success) {
            if (data.found) {
                // Add item to cart
                addToCart(data.product);
                // Audible beep if sound works
                playBeepSound();
            } else {
                // Barcode read, but not registered in database
                stopWebcamScanner();
                playFailBeep();
                openAddProductModal(data.barcode);
                showNotification(`Product Not Found: Code '${data.barcode}'.`, "warning");
            }
        }
    } catch (err) {
        console.error("Scanner frame upload error:", err);
    }
}

function playBeepSound() {
    try {
        const context = new (window.AudioContext || window.webkitAudioContext)();
        const osc = context.createOscillator();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, context.currentTime); // high pitched beep
        osc.connect(context.destination);
        osc.start();
        osc.stop(context.currentTime + 0.1);
    } catch(e){}
}

function playFailBeep() {
    try {
        const context = new (window.AudioContext || window.webkitAudioContext)();
        const osc = context.createOscillator();
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(220, context.currentTime); // low buzz
        osc.connect(context.destination);
        osc.start();
        osc.stop(context.currentTime + 0.3);
    } catch(e){}
}

// 5. CHECKOUT BILLING COUNTER SUBMIT
async function processPOSCheckout() {
    if (cart.length === 0) {
        showNotification("Billing cart is empty.", "danger");
        return;
    }

    const payMode = document.getElementById('payment-mode-select').value;
    const cashRecField = document.getElementById('cash-received-input');
    const cashReceived = parseFloat(cashRecField ? cashRecField.value : 0.0);
    const grandTotalSpan = document.getElementById('pos-grand-total').innerText;
    const grandTotal = parseFloat(grandTotalSpan.replace("INR ", ""));

    if (payMode === 'Cash' && cashReceived < grandTotal) {
        showNotification(`Cash received must be at least ${formatCurrency(grandTotal)}`, "danger");
        return;
    }

    const customerName = document.getElementById('pos-customer-name')?.value || '';
    const customerPhone = document.getElementById('pos-customer-phone')?.value || '';
    const customerEmail = document.getElementById('pos-customer-email')?.value || '';
    const customerAddress = document.getElementById('pos-customer-address')?.value || '';

    const payload = {
        customer_id: customerId,
        customer_name: customerName,
        customer_phone: customerPhone,
        customer_email: customerEmail,
        customer_address: customerAddress,
        cart: cart.map(item => ({ product_id: item.id, quantity: item.quantity })),
        payment_mode: payMode,
        cash_received: cashReceived,
        coupon_code: couponCode,
        is_student: isStudent
    };

    try {
        const res = await fetch('/api/pos/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            showNotification("Transaction completed successfully! Redirecting to receipt.", "success");
            // Clear cart variables
            cart = [];
            localStorage.removeItem('pos_cart');
            
            // Redirect to printable invoice HTML template
            window.location.href = `/pos/invoice/${data.invoice_number}`;
        } else {
            showNotification(data.message, "danger");
        }
    } catch (err) {
        showNotification("POS Checkout request failed.", "danger");
    }
}

// 6. VOICE SEARCH ENGINE
let recognition = null;
function initVoiceSearch() {
    const voiceBtn = document.getElementById('pos-voice-search-btn');
    const searchInput = document.getElementById('pos-search-input');
    if (!voiceBtn || !searchInput) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        voiceBtn.style.display = 'none';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    voiceBtn.addEventListener('click', () => {
        try {
            recognition.start();
            voiceBtn.className = "btn btn-danger btn-theme";
            voiceBtn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            showNotification("Listening for product name...", "info");
        } catch(e) {
            recognition.stop();
        }
    });

    recognition.onresult = (event) => {
        const voiceQuery = event.results[0][0].transcript;
        searchInput.value = voiceQuery;
        // Trigger input event to run autocomplete
        searchInput.dispatchEvent(new Event('input'));
        showNotification(`Searched: "${voiceQuery}"`, 'success');
    };

    recognition.onspeechend = () => {
        recognition.stop();
        resetVoiceBtn();
    };

    recognition.onerror = () => {
        resetVoiceBtn();
    };
}

function resetVoiceBtn() {
    const voiceBtn = document.getElementById('pos-voice-search-btn');
    if (voiceBtn) {
        voiceBtn.className = "btn btn-theme";
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
}

// 7. KEYBOARD SHORTCUT HOTKEYS
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // F2 -> Focus product search
        if (e.key === 'F2') {
            e.preventDefault();
            const searchInput = document.getElementById('pos-search-input');
            if (searchInput) searchInput.focus();
        }
        
        // F4 -> Focus Cash Received
        if (e.key === 'F4') {
            e.preventDefault();
            const cashRec = document.getElementById('cash-received-input');
            if (cashRec) cashRec.focus();
        }
        
        // F7 -> Webcam Scanner toggle
        if (e.key === 'F7') {
            e.preventDefault();
            toggleWebcamScanner();
        }

        // F8 -> Set Cash mode
        if (e.key === 'F8') {
            e.preventDefault();
            const select = document.getElementById('payment-mode-select');
            if (select) {
                select.value = 'Cash';
                select.dispatchEvent(new Event('change'));
                showNotification("Payment mode updated to Cash.", "info");
            }
        }
        
        // F9 -> Set UPI mode
        if (e.key === 'F9') {
            e.preventDefault();
            const select = document.getElementById('payment-mode-select');
            if (select) {
                select.value = 'UPI';
                select.dispatchEvent(new Event('change'));
                showNotification("Payment mode updated to UPI.", "info");
            }
        }

        // F10 -> Process checkout
        if (e.key === 'F10') {
            e.preventDefault();
            processPOSCheckout();
        }
    });
}

// Initialize autocomplete & shortcuts on load
document.addEventListener('DOMContentLoaded', () => {
    initPOSAutocomplete();
    initVoiceSearch();
    initKeyboardShortcuts();

    const cashRec = document.getElementById('cash-received-input');
    if (cashRec) {
        cashRec.addEventListener('input', () => {
            const grandTotalSpan = document.getElementById('pos-grand-total').innerText;
            const grandTotal = parseFloat(grandTotalSpan.replace("INR ", ""));
            updateBalanceCalculation(grandTotal);
        });
    }

    const payMode = document.getElementById('payment-mode-select');
    const cashRecContainer = document.getElementById('cash-received-container');
    if (payMode && cashRecContainer) {
        payMode.addEventListener('change', (e) => {
            if (e.target.value === 'Cash') {
                cashRecContainer.classList.remove('d-none');
            } else {
                cashRecContainer.classList.add('d-none');
                const cashRecInput = document.getElementById('cash-received-input');
                if (cashRecInput) cashRecInput.value = '0';
                renderCart();
            }
        });
    }
});
