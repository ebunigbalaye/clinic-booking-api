// Read the API key from the URL fragment.

function initializeApiKey() {
    const hashParams = new URLSearchParams(
        window.location.hash.slice(1)
    );

    const keyFromUrl = hashParams.get("key");

    if (keyFromUrl) {
        sessionStorage.setItem("api_key", keyFromUrl);

        // Remove the key from the visible URL and browser history entry.
        window.history.replaceState(
            null,
            "",
            window.location.pathname + window.location.search
        );
    }

    return sessionStorage.getItem("api_key");
}

const API_BASE = "";

const slotsList = document.getElementById("slots-list");
const slotsStatus = document.getElementById("slots-status");
const providerFilter = document.getElementById("provider-filter");
const refreshButton = document.getElementById("refresh-button");

const pagination = document.getElementById("pagination");
const previousPageButton = document.getElementById("previous-page");
const nextPageButton = document.getElementById("next-page");
const pageInfo = document.getElementById("page-info");

const bookingForm = document.getElementById("booking-form");
const submitButton = document.getElementById("submit-button");
const formError = document.getElementById("form-error");

const selectionSummary = document.getElementById("selection-summary");
const confirmation = document.getElementById("confirmation");
const confirmationMessage = document.getElementById("confirmation-message");
const bookingReference = document.getElementById("booking-reference");
const newBookingButton = document.getElementById("new-booking-button");

let allSlots = [];
let availableSlots = [];
let selectedSlot = null;
let pendingRequest = null;

const PAGE_SIZE = 10;
let currentPage = 1;


const API_KEY = initializeApiKey();

if (API_KEY) {
    loadSlots();
} else {
    slotsStatus.textContent =
        "Access link required. Please use the link provided to you.";
}


// Format a date in the patient's browser timezone.
function formatDateTime(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Date unavailable";
    }

    return new Intl.DateTimeFormat(undefined, {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(date);
}


// Make an API request and handle JSON responses.
async function apiRequest(url, options = {}) {
    if (!API_KEY) {
        throw new Error(
            "API key missing. Please open the application using your access link."
        );
    }

    const headers = new Headers(options.headers || {});

    headers.set("X-API-Key", API_KEY);

    const response = await fetch(url, {
        ...options,
        headers,
    });

    let data = {};

    try {
        data = await response.json();
    } catch {
        // Handle responses without JSON.
    }

    if (!response.ok) {
        throw new Error(
            data.error || data.detail || `Request failed (${response.status})`
        );
    }

    return data;
}


// Retrieve appointment slots from the backend.
async function loadSlots() {
    slotsStatus.textContent = "Loading appointments...";
    refreshButton.disabled = true;

    try {
        const data = await apiRequest("/slots");

        // Keep every slot so we can identify all providers.
        allSlots = data.slots;

        // Only available slots can be selected for booking.
        availableSlots = allSlots.filter(slot => slot.available);

        // Clear a selection if it is no longer available.
        if (
            selectedSlot &&
            !availableSlots.some(slot => slot.id === selectedSlot.id)
        ) {
            selectedSlot = null;
            updateSelection();
        }

        populateProviderFilter();
        renderSlots();

    } catch (error) {
        slotsStatus.textContent = error.message;
        slotsList.replaceChildren();
        pagination.hidden = true;

    } finally {
        refreshButton.disabled = false;
    }
}


// Populate the provider filter using the available appointments.
function populateProviderFilter() {
    const previousValue = providerFilter.value;

    const providers = [
        ...new Set(allSlots.map(slot => slot.provider))
    ].sort();

    providerFilter.replaceChildren();

    const allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = "All providers";
    providerFilter.appendChild(allOption);

    providers.forEach(provider => {
        const option = document.createElement("option");
        option.value = provider;
        option.textContent = provider;
        providerFilter.appendChild(option);
    });

    if (providers.includes(previousValue)) {
        providerFilter.value = previousValue;
    }
}


// Display available appointments.
function renderSlots() {
    slotsList.replaceChildren();

    const provider = providerFilter.value;

    const filteredSlots = availableSlots.filter(slot => {
        return !provider || slot.provider === provider;
    });

    if (filteredSlots.length === 0) {
        slotsStatus.textContent = availableSlots.length === 0
            ? "There are currently no available appointments."
            : "No appointments found for this provider.";

        pagination.hidden = true;
        return;
    }

    // Calculate the number of pages.
    const totalPages = Math.ceil(filteredSlots.length / PAGE_SIZE);

    // Keep the current page within valid limits.
    currentPage = Math.min(currentPage, totalPages);

    // Get only the appointments for the current page.
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    const endIndex = startIndex + PAGE_SIZE;

    const pageSlots = filteredSlots.slice(startIndex, endIndex);

    slotsStatus.textContent =
        `${filteredSlots.length} appointment(s) available`;

    pageSlots.forEach(slot => {
        const card = document.createElement("article");
        card.className = "slot-card";

        if (selectedSlot?.id === slot.id) {
            card.classList.add("selected");
        }

        const info = document.createElement("div");
        info.className = "slot-info";

        const providerName = document.createElement("strong");
        providerName.textContent = slot.provider;

        const date = document.createElement("p");
        date.textContent = formatDateTime(slot.start_time);

        const duration = document.createElement("p");
        duration.textContent =
            `Ends: ${formatDateTime(slot.end_time)}`;

        info.append(providerName, date, duration);

        const selectButton = document.createElement("button");
        selectButton.type = "button";
        selectButton.className = "slot-select";
        selectButton.textContent =
            selectedSlot?.id === slot.id ? "Selected" : "Select";

        selectButton.addEventListener("click", () => {
            selectedSlot = slot;
            updateSelection();
            renderSlots();
        });

        card.append(info, selectButton);
        slotsList.appendChild(card);
    });

    // Update pagination controls.
    pagination.hidden = totalPages <= 1;

    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

    previousPageButton.disabled = currentPage === 1;
    nextPageButton.disabled = currentPage === totalPages;
}


// Update the appointment summary and booking button.
function updateSelection() {
    submitButton.disabled = !selectedSlot;

    selectionSummary.replaceChildren();

    const icon = document.createElement("span");
    icon.className = "summary-icon";
    icon.textContent = selectedSlot ? "✓" : "+";

    const details = document.createElement("div");

    const title = document.createElement("strong");
    title.textContent = selectedSlot
        ? selectedSlot.provider
        : "No appointment selected";

    const description = document.createElement("p");
    description.textContent = selectedSlot
        ? formatDateTime(selectedSlot.start_time)
        : "Choose an available slot to continue.";

    details.append(title, description);
    selectionSummary.append(icon, details);
}


// Submit the patient's booking.
bookingForm.addEventListener("submit", async event => {
    event.preventDefault();

    if (!selectedSlot) {
        formError.textContent = "Please select an appointment first.";
        return;
    }

    formError.textContent = "";

    const formData = new FormData(bookingForm);

    const bookingData = {
        slot_id: selectedSlot.id,
        name: formData.get("name").trim(),
        email: formData.get("email").trim().toLowerCase(),
    };

    // Reuse the key if the same request needs to be retried.
    const requestSignature = JSON.stringify(bookingData);

    if (
        !pendingRequest ||
        pendingRequest.signature !== requestSignature
    ) {
        pendingRequest = {
            signature: requestSignature,
            key: crypto.randomUUID(),
        };
    }

    submitButton.disabled = true;
    submitButton.textContent = "Booking...";

    try {
        const booking = await apiRequest("/bookings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Idempotency-Key": pendingRequest.key,
            },
            body: JSON.stringify(bookingData),
        });

        pendingRequest = null;

        showConfirmation(booking);

        selectedSlot = null;
        bookingForm.reset();
        updateSelection();

        await loadSlots();

    } catch (error) {
        formError.textContent = error.message;

        // A conflict may mean another patient booked this slot.
        await loadSlots();

    } finally {
        submitButton.textContent = "Confirm appointment";
        submitButton.disabled = !selectedSlot;
    }
});


// Show the server's booking confirmation.
function showConfirmation(booking) {
    bookingForm.hidden = true;
    selectionSummary.hidden = true;
    confirmation.hidden = false;

    const patientName = booking.name;

    confirmationMessage.textContent =
        `Thank you, ${patientName}. Your appointment has been confirmed.`;

    bookingReference.textContent = booking.id;
}


// Allow the patient to start another booking.
newBookingButton.addEventListener("click", () => {
    confirmation.hidden = true;
    bookingForm.hidden = false;
    selectionSummary.hidden = false;

    formError.textContent = "";
    pendingRequest = null;
    selectedSlot = null;

    updateSelection();
    renderSlots();
});

// Allow the patient to start another booking.
newBookingButton.addEventListener("click", () => {
    confirmation.hidden = true;
    bookingForm.hidden = false;
    selectionSummary.hidden = false;

    formError.textContent = "";
    pendingRequest = null;
    selectedSlot = null;

    currentPage = 1;

    updateSelection();
    renderSlots();
});

// Event listeners.
// Event listeners.
providerFilter.addEventListener("change", () => {
    currentPage = 1;
    renderSlots();
});

refreshButton.addEventListener("click", loadSlots);

previousPageButton.addEventListener("click", () => {
    if (currentPage > 1) {
        currentPage--;
        renderSlots();
    }
});

nextPageButton.addEventListener("click", () => {
    currentPage++;
    renderSlots();
});


// Initial page load.
loadSlots();
