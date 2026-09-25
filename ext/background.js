const API_URL = "http://127.0.0.1:8000";
const API_KEY = "TOKEN_78346982364987";

chrome.runtime.onInstalled.addListener(() => {
    chrome.alarms.create("inbox-poll", { periodInMinutes: 15 });
    chrome.sidePanel?.setPanelBehavior?.({ openPanelOnActionClick: true });
});

chrome.sidePanel.setPanelBehavior({
    openPanelOnActionClick: true
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
    if (alarm.name !== "inbox-poll") return;

    try {
        const res = await fetch(`${API_URL}/api/inbox?limit=14`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": "TOKEN_78346982364987",   
            },
        });
        if (!res.ok) throw new Error(String(res.status));

        const { emails } = await res.json();
        const waiting = emails.filter((e) => !e.processed).length;
        chrome.action.setBadgeText({ text: waiting ? String(waiting) : "" });
        chrome.action.setBadgeBackgroundColor({ color: "#1f4fd8" });

    } catch {
        chrome.action.setBadgeText({ text: "!" });
        chrome.action.setBadgeBackgroundColor({ color: "#b3261e" });
    }
});
