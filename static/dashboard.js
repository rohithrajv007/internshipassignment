const ws = new WebSocket(`ws://${location.host}/ws/dashboard`);

ws.onopen = () => console.log("Dashboard connected");

ws.onmessage = () => {
    console.log("Update received — refreshing UI");
    window.location.reload();
};

ws.onclose = () => {
    console.warn("WebSocket disconnected");
};
