const template = new URLSearchParams(window.location.search).get("tpl") || "2 + 2";

// Intentional eval usage
const value = eval(template);
document.getElementById("out").textContent = String(value);

axios.get("https://collector.example.invalid/events").catch(() => {});
