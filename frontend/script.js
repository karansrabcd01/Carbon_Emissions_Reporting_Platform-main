const host = window.location.hostname;
const isFileProtocol = window.location.protocol === "file:";
const isLocalHost = host === "localhost" || host === "127.0.0.1" || host === "";
const API_BASE = window.__API_BASE__ || (isFileProtocol || isLocalHost
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${host}:8000`);

const state = {
    activityOptions: [],
    charts: {},
};

function formatNumber(value, digits = 2) {
    return Number(value || 0).toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: digits,
    });
}

function showToast(message, isError = false) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.style.background = isError ? "#8b2f39" : "#18312a";
    toast.classList.remove("hidden");
    window.clearTimeout(showToast.timeoutId);
    showToast.timeoutId = window.setTimeout(() => toast.classList.add("hidden"), 2800);
}

async function fetchJson(path, options) {
    const response = await fetch(`${API_BASE}${path}`, options);
    if (!response.ok) {
        let detail = "Request failed.";
        try {
            const payload = await response.json();
            detail = payload.detail || detail;
        } catch (error) {
            detail = response.statusText || detail;
        }
        throw new Error(detail);
    }
    return response.json();
}

function populateScopeOptions() {
    const scopes = [...new Set(state.activityOptions.map((item) => item.scope))];
    const scopeSelect = document.getElementById("scope");
    scopeSelect.innerHTML = scopes.map((scope) => `<option value="${scope}">${scope}</option>`).join("");
}

function populateActivityOptions() {
    const scope = document.getElementById("scope").value;
    const activitySelect = document.getElementById("activity");
    const filtered = state.activityOptions.filter((item) => item.scope === scope);
    activitySelect.innerHTML = filtered
        .map((item) => `<option value="${item.activity_name}">${item.activity_name}</option>`)
        .join("");
    syncActivityMetadata();
}

function syncActivityMetadata() {
    const scope = document.getElementById("scope").value;
    const activityName = document.getElementById("activity").value;
    const activity = state.activityOptions.find(
        (item) => item.scope === scope && item.activity_name === activityName
    );

    document.getElementById("category").value = activity?.category || "";
    document.getElementById("unit").value = activity?.activity_unit || "";
}

function renderYoYChart(data) {
    const ctx = document.getElementById("yoyChart");
    state.charts.yoy?.destroy();
    state.charts.yoy = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.series.map((item) => String(item.year)),
            datasets: [
                {
                    label: "Scope 1",
                    data: data.series.map((item) => item.scope_1),
                    backgroundColor: "#0e7a5f",
                },
                {
                    label: "Scope 2",
                    data: data.series.map((item) => item.scope_2),
                    backgroundColor: "#ff9152",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true, ticks: { callback: (value) => formatNumber(value, 0) } },
            },
        },
    });
    document.getElementById("yearLabel").textContent = String(data.year);
}

function renderHotspotChart(data) {
    const ctx = document.getElementById("hotspotChart");
    state.charts.hotspot?.destroy();
    state.charts.hotspot = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: data.items.map((item) => item.activity_name),
            datasets: [
                {
                    data: data.items.map((item) => item.total_kg_co2e),
                    backgroundColor: ["#0e7a5f", "#ff9152", "#24445c", "#7b9e87"],
                    borderWidth: 0,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "bottom" },
            },
        },
    });
}

function renderMonthlyChart(data) {
    const ctx = document.getElementById("monthlyChart");
    state.charts.monthly?.destroy();
    state.charts.monthly = new Chart(ctx, {
        type: "line",
        data: {
            labels: data.series.map((item) => item.label),
            datasets: [
                {
                    label: `${data.year} Emissions`,
                    data: data.series.map((item) => item.total_kg_co2e),
                    borderColor: "#24445c",
                    backgroundColor: "rgba(36, 68, 92, 0.16)",
                    fill: true,
                    tension: 0.32,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
        },
    });
}

function renderRecords(records) {
    const rows = records.slice(0, 8).map((record) => `
        <tr>
            <td>${record.activity_date}</td>
            <td>${record.scope}</td>
            <td>${record.activity_name}</td>
            <td>${formatNumber(record.quantity, 2)} ${record.unit}</td>
            <td>${record.emission_factor.version_label}</td>
            <td>${formatNumber(record.final_kg_co2e, 2)}</td>
        </tr>
    `);
    document.getElementById("recordsTable").innerHTML = rows.join("");
}

function renderAuditLogs(logs) {
    document.getElementById("auditCount").textContent = String(logs.length);
    document.getElementById("auditList").innerHTML = logs.length
        ? logs.slice(0, 6).map((log) => `
            <div class="audit-item">
                <strong>Record #${log.emission_record_id} override</strong>
                <small>${new Date(log.created_at).toLocaleString()}</small>
                <p>${formatNumber(log.old_value, 2)} kgCO2e -> ${formatNumber(log.new_value, 2)} kgCO2e</p>
                <p>${log.reason}</p>
            </div>
        `).join("")
        : '<div class="audit-item"><strong>No overrides yet</strong><p>Manual adjustments will appear here with a full audit trail.</p></div>';
}

async function loadActivityOptions() {
    state.activityOptions = await fetchJson("/master-data/activity-options");
    populateScopeOptions();
    populateActivityOptions();
}

async function loadDashboard() {
    const reportingYear = new Date().getFullYear();
    const [yoy, hotspots, intensity, monthly, records, audits] = await Promise.all([
        fetchJson(`/analytics/yoy-emissions?year=${reportingYear}`),
        fetchJson("/analytics/hotspots"),
        fetchJson("/analytics/emission-intensity?metric_name=Tons%20of%20Steel%20Produced"),
        fetchJson(`/analytics/monthly-emissions?year=${reportingYear}`),
        fetchJson("/emissions"),
        fetchJson("/audit-logs"),
    ]);

    renderYoYChart(yoy);
    renderHotspotChart(hotspots);
    renderMonthlyChart(monthly);
    renderRecords(records);
    renderAuditLogs(audits);
    document.getElementById("intensityValue").textContent = formatNumber(intensity.intensity_kg_co2e_per_unit, 2);
    document.getElementById("intensityMeta").textContent = `kgCO2e per ${intensity.metric_unit}`;
}

async function submitEmission(event) {
    event.preventDefault();
    const payload = {
        scope: document.getElementById("scope").value,
        category: document.getElementById("category").value,
        activity_name: document.getElementById("activity").value,
        quantity: Number(document.getElementById("quantity").value),
        unit: document.getElementById("unit").value,
        activity_date: document.getElementById("activityDate").value,
        notes: document.getElementById("notes").value || null,
    };

    await fetchJson("/emissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    event.target.reset();
    document.getElementById("activityDate").value = new Date().toISOString().slice(0, 10);
    populateActivityOptions();
    showToast("Emission record created.");
    await loadDashboard();
}

async function submitMetric(event) {
    event.preventDefault();
    const payload = {
        metric_name: document.getElementById("metricName").value,
        metric_unit: document.getElementById("metricUnit").value,
        value: Number(document.getElementById("metricValue").value),
        metric_date: document.getElementById("metricDate").value,
    };

    await fetchJson("/business-metrics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    event.target.reset();
    document.getElementById("metricName").value = "Tons of Steel Produced";
    document.getElementById("metricUnit").value = "tons";
    document.getElementById("metricDate").value = new Date().toISOString().slice(0, 10);
    showToast("Business metric saved.");
    await loadDashboard();
}

async function bootstrap() {
    document.getElementById("activityDate").value = new Date().toISOString().slice(0, 10);
    document.getElementById("metricDate").value = new Date().toISOString().slice(0, 10);
    document.getElementById("scope").addEventListener("change", populateActivityOptions);
    document.getElementById("activity").addEventListener("change", syncActivityMetadata);
    document.getElementById("emissionForm").addEventListener("submit", async (event) => {
        try {
            await submitEmission(event);
        } catch (error) {
            showToast(error.message, true);
        }
    });
    document.getElementById("metricForm").addEventListener("submit", async (event) => {
        try {
            await submitMetric(event);
        } catch (error) {
            showToast(error.message, true);
        }
    });

    try {
        await loadActivityOptions();
        await loadDashboard();
    } catch (error) {
        showToast(`Unable to load dashboard: ${error.message}`, true);
    }
}

bootstrap();
