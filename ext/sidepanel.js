"use strict";

const API_URL = "http://127.0.0.1:8000";
const API_KEY = "";

const PRIORITY_RANK = { critical: 0, high: 1, medium: 2, low: 3 };

const $ = (id) => document.getElementById(id);

const state = {
    tab: "inbox",          
    inbox: [],             
    history: [],           
    filters: {
        q: "",
        priority: "all",
        category: "all",
        meetingOnly: false,
        unprocessedOnly: false,
        sort: "newest",
        limit: 14,
    },
    current: null,         
};


// HELPERS
function el(tag, props = {}, ...kids) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
        if (key === "class") node.className = value;
        else if (key === "text") node.textContent = value;
        else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
        else if (value !== false && value != null) node.setAttribute(key, value === true ? "" : value);
    }
    node.append(...kids.filter(Boolean));
    return node;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function isEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function senderName(sender) {
    const name = String(sender || "").replace(/<.*>/, "").replaceAll('"', "").trim();
    return name || sender || "Unknown sender";
}

function formatDate(value) {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function timestamp(value) {
    const t = Date.parse(value);
    return Number.isNaN(t) ? 0 : t;
}

function setStatus(message, isError = false) {
    const node = $("status");
    node.textContent = message;
    node.classList.toggle("error", isError);
}

async function api(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeout ?? 120000);

    try {
        const response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
                ...(options.headers || {}),
            },
            signal: controller.signal,
        });

        if (!response.ok) {
            let detail = await response.text();
            try { detail = JSON.parse(detail).detail || detail; } catch { /* plain text */ }
            throw new Error(detail || `Backend returned ${response.status}`);
        }
        return await response.json();

    } catch (error) {
        if (error.name === "AbortError") throw new Error("The request timed out");
        throw error;
    } finally {
        clearTimeout(timer);
    }
}



// PREFERENCES


async function loadPrefs() {
    try {
        const { prefs } = await chrome.storage.local.get("prefs");
        if (prefs) Object.assign(state.filters, prefs);
    } catch { /* storage unavailable */ }
}

function savePrefs() {
    try {
        chrome.storage.local.set({
            prefs: { limit: state.filters.limit, sort: state.filters.sort },
        });
    } catch { /* storage unavailable */ }
}

// DATA

// One shape for rows coming from Gmail (/api/inbox) and from the database (/emails).
function normalize(raw, forceProcessed = false) {
    const meeting = raw.parsed_meeting || {};
    return {
        key: raw.message_id || raw.email_id || raw.thread_id,
        message_id: raw.message_id || raw.email_id || raw.thread_id,
        thread_id: raw.thread_id,
        subject: raw.subject || "(no subject)",
        sender: raw.sender || "",
        date: raw.date || raw.created_at || raw.processed_at || "",
        snippet: raw.snippet || "",
        processed: forceProcessed || Boolean(raw.processed),
        category: raw.category || "",
        priority: raw.priority || "",
        status: raw.status || "",
        hasMeeting: raw.has_meeting ?? meeting.meeting_related === true,
    };
}

async function loadInbox() {
    setStatus("Loading recent emails...");
    try {
        const data = await api(`/api/inbox?limit=${state.filters.limit}`);
        state.inbox = (data.emails || []).map((e) => normalize(e));
        setStatus("");
    } catch (error) {
        setStatus(`Could not load the inbox: ${error.message}`, true);
    }
    renderList();
}

async function loadHistory() {
    try {
        const data = await api("/emails");
        state.history = (data.emails || []).map((e) => normalize(e, true));
    } catch (error) {
        setStatus(`Could not load processed emails: ${error.message}`, true);
    }
    renderList();
}



// FILTERING & LIST RENDERING
function currentSource() {
    return state.tab === "inbox" ? state.inbox : state.history;
}

function visibleItems() {
    const f = state.filters;
    const q = f.q.trim().toLowerCase();

    const items = currentSource().filter((m) => {
        if (q && !`${m.subject} ${m.sender} ${m.snippet}`.toLowerCase().includes(q)) return false;
        if (f.unprocessedOnly && m.processed) return false;
        if (f.priority !== "all" && m.priority.toLowerCase() !== f.priority) return false;
        if (f.category !== "all" && m.category !== f.category) return false;
        if (f.meetingOnly && !m.hasMeeting) return false;
        return true;
    });

    if (f.sort === "priority") {
        const rank = (m) => PRIORITY_RANK[m.priority.toLowerCase()] ?? 4;
        items.sort((a, b) => rank(a) - rank(b) || timestamp(b.date) - timestamp(a.date));
    } else {
        items.sort((a, b) => timestamp(b.date) - timestamp(a.date));
    }
    return items;
}

function refreshCategoryOptions() {
    const select = $("category");
    const categories = [...new Set([...state.inbox, ...state.history].map((m) => m.category).filter(Boolean))].sort();

    if (state.filters.category !== "all" && !categories.includes(state.filters.category)) {
        state.filters.category = "all";
    }

    select.replaceChildren(
        el("option", { value: "all", text: "All categories" }),
        ...categories.map((c) => el("option", { value: c, text: c })),
    );
    select.value = state.filters.category;
}

function renderList() {
    refreshCategoryOptions();

    const inboxTab = state.tab === "inbox";
    $("limitField").hidden = !inboxTab;
    $("unprocessedField").hidden = !inboxTab;

    const items = visibleItems();
    const total = currentSource().length;
    $("count").textContent = total ? `${items.length} of ${total} emails` : "";

    const newCount = state.inbox.filter((m) => !m.processed).length;
    const processBtn = $("processNew");
    processBtn.hidden = !inboxTab || newCount === 0;
    processBtn.textContent = `Process ${newCount} new`;

    const list = $("emailList");
    list.replaceChildren();

    if (!items.length) {
        const message = total
            ? "No emails match these filters."
            : inboxTab
                ? "No emails loaded yet. Press Refresh to fetch your latest messages."
                : "Nothing processed yet. Process an email from the Recent inbox tab.";
        list.append(el("li", { class: "empty", text: message }));
        return;
    }

    for (const item of items) list.append(renderRow(item));
}

function renderRow(m) {
    const prio = m.priority.toLowerCase();

    const body = [
        el("span", { class: "row-subject", text: m.subject }),
        el("span", { class: "row-meta", text: [senderName(m.sender), formatDate(m.date)].filter(Boolean).join("  |  ") }),
        m.snippet && !m.processed ? el("span", { class: "row-snippet", text: m.snippet }) : null,
        el("span", { class: "tags" },
            prio ? el("span", { class: "tag", text: `${m.priority} priority` }) : null,
            m.category ? el("span", { class: "tag", text: m.category }) : null,
            m.hasMeeting ? el("span", { class: "tag meet", text: "Meeting" }) : null,
            !m.processed ? el("span", { class: "tag new", text: "Not processed" }) : null,
        ),
    ];

    const main = m.processed
        ? el("button", { class: "row-main", type: "button", onclick: () => openEmail(m) }, ...body)
        : el("div", { class: "row-main" }, ...body);

    const action = m.processed
        ? null
        : el("div", { class: "row-action" },
            el("button", {
                class: "btn primary small",
                type: "button",
                text: "Process",
                onclick: (event) => processOne(m, event.currentTarget),
            }));

    return el("li", { class: `row${prio ? ` p-${prio}` : ""}` }, main, action);
}



// PROCESSING


async function processOne(m, button) {
    button.disabled = true;
    button.textContent = "Working...";
    setStatus("Running the AI pipeline. This usually takes 10-30 seconds.");

    try {
        const data = await api(`/api/process-email/${encodeURIComponent(m.message_id)}`, {
            method: "POST",
            timeout: 180000,
        });
        setStatus("");
        await Promise.all([loadInbox(), loadHistory()]);
        renderDetail(data.email, []);
        showView("detail");
    } catch (error) {
        setStatus(`Processing failed: ${error.message}`, true);
        button.disabled = false;
        button.textContent = "Process";
    }
}

async function processAllNew() {
    const button = $("processNew");
    button.disabled = true;
    setStatus("Processing new emails. This can take a minute or two.");

    try {
        const r = await api(`/api/sync?limit=${state.filters.limit}`, { method: "POST", timeout: 600000 });
        setStatus(
            r.status === "busy"
                ? "A sync is already running. Try again shortly."
                : `Processed ${r.processed} new email(s)${r.failed ? `, ${r.failed} failed` : ""}.`,
            r.failed > 0,
        );
    } catch (error) {
        setStatus(`Sync failed: ${error.message}`, true);
    }

    button.disabled = false;
    await Promise.all([loadInbox(), loadHistory()]);
}



// DETAIL VIEW


function showView(name) {
    $("listView").hidden = name !== "list";
    $("detailView").hidden = name !== "detail";
    window.scrollTo(0, 0);
}

async function openEmail(m) {
    showView("detail");
    $("detailBody").replaceChildren(el("p", { class: "muted", text: "Loading..." }));

    try {
        const [emailRes, actionsRes] = await Promise.all([
            api(`/emails/${encodeURIComponent(m.thread_id)}`),
            api(`/emails/${encodeURIComponent(m.thread_id)}/actions`).catch(() => ({ actions: [] })),
        ]);
        renderDetail(emailRes.email, actionsRes.actions || []);
    } catch (error) {
        $("detailBody").replaceChildren(el("p", { class: "error", text: `Could not open this email: ${error.message}` }));
    }
}

function renderDetail(email, actions) {
    state.current = email;

    const meeting = email.parsed_meeting || {};
    const meetingRelated = meeting.meeting_related === true;
    const attendees = meeting.attendees || [];
    const withoutEmail = attendees.filter((a) => !a.email);
    const meetLink = (actions.find((a) => a.action_type === "meeting_scheduled") || {}).action_value || "";
    const replySent = actions.some((a) => a.action_type === "reply_sent");
    const items = email.parsed_action_items || [];

    const attendeeText = attendees
        .map((a) => (a.email ? `${a.name || ""} (${a.email})` : a.name || ""))
        .join("\n");

    $("detailBody").innerHTML = `
        <div class="section">
            <h2>${escapeHtml(email.subject || "(no subject)")}</h2>
            <p class="muted">${escapeHtml(email.sender || "N/A")}</p>
            <div class="tags">
                <span class="tag">${escapeHtml(email.priority || "Low")} priority</span>
                <span class="tag">${escapeHtml(email.category || "Uncategorised")}</span>
                <span class="tag">${escapeHtml(replySent ? "Reply sent" : email.status || "Pending")}</span>
            </div>
        </div>

        <div class="section">
            <h3>Action items</h3>
            ${items.length
                ? `<ul>${items.map((i) => `
                    <li>${escapeHtml(i.task || "")}
                        ${i.deadline ? `<span class="deadline"> - due ${escapeHtml(i.deadline)}</span>` : ""}
                    </li>`).join("")}</ul>`
                : `<p class="muted">No action items found in this email.</p>`}
        </div>

        ${meetingRelated ? `
        <div class="section">
            <h3>Meeting</h3>
            <p class="muted">Intent: ${escapeHtml(meeting.meeting_intent || "none")}</p>

            <label class="label" for="meetingDate">Date</label>
            <input id="meetingDate" type="text" value="${escapeHtml(meeting.meeting_date || "")}">

            <label class="label" for="meetingTime">Time</label>
            <input id="meetingTime" type="text" value="${escapeHtml(meeting.meeting_time || "")}">

            <label class="label" for="attendees">Attendees found</label>
            <textarea id="attendees" rows="3" readonly>${escapeHtml(attendeeText)}</textarea>

            ${withoutEmail.length
                ? `<p class="warn">${withoutEmail.length} attendee(s) have no email address and will not get an invite. Add their addresses below.</p>`
                : ""}

            <label class="label" for="extraEmails">Extra invitee emails (comma separated)</label>
            <input id="extraEmails" type="text" placeholder="name@example.com, other@example.com">

            <button id="scheduleMeeting" class="btn primary block" type="button">Create Google Meet</button>
            <div id="meetingResult"></div>
        </div>` : ""}

        <div class="section">
            <h3>Draft reply</h3>
            <textarea id="draftBody" rows="11" placeholder="Draft reply...">${escapeHtml(email.parsed_draft || "")}</textarea>
            <div class="inline-actions">
                <button id="copyDraft" class="btn" type="button">Copy draft</button>
                <button id="sendReply" class="btn primary" type="button">${replySent ? "Send again" : "Send reply"}</button>
            </div>
            <div id="replyResult"></div>
        </div>
    `;

    if (meetingRelated) {
        $("scheduleMeeting").addEventListener("click", scheduleMeeting);
        if (meetLink) renderMeetLink($("meetingResult"), meetLink);
    }
    $("copyDraft").addEventListener("click", copyDraft);
    $("sendReply").addEventListener("click", sendReply);
}

function renderMeetLink(container, url) {
    container.replaceChildren(el("p", { class: "ok", text: "Meeting scheduled." }));
    // only ever link to https URLs
    if (/^https:\/\//i.test(url || "")) {
        container.append(el("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: "Open the Meet link" }));
    }
}

async function scheduleMeeting() {
    const email = state.current;
    const meeting = email.parsed_meeting || {};
    const result = $("meetingResult");
    const button = $("scheduleMeeting");

    const extras = $("extraEmails").value.split(/[,\s;]+/).filter(isEmail);
    const invitees = [...new Set([
        ...(meeting.attendees || []).map((a) => a.email).filter(Boolean),
        ...extras,
    ])];

    button.disabled = true;
    result.textContent = "Creating the event...";

    try {
        const data = await api("/schedule-meeting", {
            method: "POST",
            body: JSON.stringify({
                thread_id: email.thread_id,
                subject: email.subject || "Meeting",
                meeting_date: $("meetingDate").value,
                meeting_time: $("meetingTime").value,
                attendees: invitees,
            }),
        });
        renderMeetLink(result, data.meet_link);
    } catch (error) {
        result.replaceChildren(el("p", { class: "error", text: `Could not create the event: ${error.message}` }));
    } finally {
        button.disabled = false;
    }
}

async function copyDraft() {
    try {
        await navigator.clipboard.writeText($("draftBody").value);
        $("replyResult").textContent = "Draft copied.";
    } catch {
        $("replyResult").textContent = "Could not copy. Select the text and copy it manually.";
    }
}

async function sendReply() {
    const email = state.current;
    if (!confirm(`Send this reply to ${email.sender}?`)) return;

    const result = $("replyResult");
    const button = $("sendReply");
    button.disabled = true;
    result.textContent = "Sending...";

    try {
        await api("/send-reply", {
            method: "POST",
            body: JSON.stringify({
                thread_id: email.thread_id,
                to_email: email.sender,
                subject: email.subject,
                body_text: $("draftBody").value,
            }),
        });
        result.replaceChildren(el("p", { class: "ok", text: "Reply sent." }));
        button.textContent = "Send again";
    } catch (error) {
        result.replaceChildren(el("p", { class: "error", text: `Sending failed: ${error.message}` }));
    } finally {
        button.disabled = false;
    }
}



// EVENTS


function selectTab(name) {
    state.tab = name;
    $("tabInbox").setAttribute("aria-selected", String(name === "inbox"));
    $("tabHistory").setAttribute("aria-selected", String(name === "history"));
    renderList();
}

function bindEvents() {
    $("tabInbox").addEventListener("click", () => selectTab("inbox"));
    $("tabHistory").addEventListener("click", () => selectTab("history"));

    $("refreshBtn").addEventListener("click", () => Promise.all([loadInbox(), loadHistory()]));
    $("processNew").addEventListener("click", processAllNew);
    $("backBtn").addEventListener("click", () => showView("list"));

    $("search").addEventListener("input", (e) => { state.filters.q = e.target.value; renderList(); });
    $("category").addEventListener("change", (e) => { state.filters.category = e.target.value; renderList(); });
    $("meetingOnly").addEventListener("change", (e) => { state.filters.meetingOnly = e.target.checked; renderList(); });
    $("unprocessedOnly").addEventListener("change", (e) => { state.filters.unprocessedOnly = e.target.checked; renderList(); });

    $("sort").addEventListener("change", (e) => {
        state.filters.sort = e.target.value;
        savePrefs();
        renderList();
    });

    $("limit").addEventListener("change", (e) => {
        state.filters.limit = Number(e.target.value);
        savePrefs();
        loadInbox();
    });

    $("priorityChips").addEventListener("click", (e) => {
        const chip = e.target.closest(".chip");
        if (!chip) return;
        state.filters.priority = chip.dataset.priority;
        document.querySelectorAll("#priorityChips .chip").forEach((c) => {
            c.setAttribute("aria-pressed", String(c === chip));
        });
        renderList();
    });
}



// START


(async function init() {
    await loadPrefs();
    $("sort").value = state.filters.sort;
    $("limit").value = String(state.filters.limit);
    bindEvents();
    await Promise.all([loadInbox(), loadHistory()]);
})();
