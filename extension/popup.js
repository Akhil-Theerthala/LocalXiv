const HOST = "com.arxiv_to_kindle.host";
const form = document.querySelector("#send-form");
const email = document.querySelector("#kindle-email");
const send = document.querySelector("#send");
const status = document.querySelector("#status");
const manual = document.querySelector("#manual");

let activeUrl = "";

function isArxivAbstract(url) {
  try {
    const parsed = new URL(url);
    return (
      parsed.protocol === "https:" &&
      ["arxiv.org", "www.arxiv.org"].includes(parsed.hostname.toLowerCase()) &&
      /^\/abs\/(?:\d{4}\.\d{4,5}|[A-Za-z][A-Za-z.-]*\/\d{7})(?:v\d+)?\/?$/.test(
        parsed.pathname,
      )
    );
  } catch {
    return false;
  }
}

function nativeMessage(value) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(HOST, value, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response);
      }
    });
  });
}

async function initialize() {
  const [{ url = "" } = {}] = await chrome.tabs.query({ active: true, currentWindow: true });
  activeUrl = url;
  const saved = await chrome.storage.local.get("kindleEmail");
  email.value = saved.kindleEmail || "";
  if (!isArxivAbstract(activeUrl)) {
    send.disabled = true;
    status.className = "error";
    status.textContent = "Open an arxiv.org/abs/… paper before using this button.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  manual.hidden = true;
  status.className = "";
  const kindleEmail = email.value.trim();
  if (!/^[^@\s]+@(?:free\.)?kindle\.com$/i.test(kindleEmail)) {
    status.className = "error";
    status.textContent = "Enter your address ending in @kindle.com.";
    email.focus();
    return;
  }

  send.disabled = true;
  send.textContent = "Working…";
  status.textContent = "Downloading source, converting, validating, and sending…";
  await chrome.storage.local.set({ kindleEmail });
  try {
    const response = await nativeMessage({ url: activeUrl, kindle_email: kindleEmail, send: true });
    if (!response?.ok) throw Object.assign(new Error(response?.message || "Conversion failed."), response);
    status.textContent = `${response.message} Saved at ${response.epub_path}`;
  } catch (error) {
    status.className = "error";
    status.textContent = error.message || "Could not reach the local converter.";
    manual.hidden = !error.epub_path;
  } finally {
    send.disabled = false;
    send.textContent = "Send to Kindle";
  }
});

initialize().catch((error) => {
  send.disabled = true;
  status.className = "error";
  status.textContent = error.message;
});
