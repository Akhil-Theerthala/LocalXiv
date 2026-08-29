importScripts("shared.js");

const HOST = "com.arxiv_to_kindle.host";
const JOB_KEY = "jobState";

let working = false;

async function setJob(job) {
  await chrome.storage.session.set({ [JOB_KEY]: job });
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "start") return false;
  if (working) {
    sendResponse({ ok: false, message: "A conversion is already running." });
    return false;
  }

  working = true;
  const identity = XivKindle.jobIdentity(message.request);
  setJob({ state: "working", message: "Starting local converter.", ...identity })
    .then(() => {
      const port = chrome.runtime.connectNative(HOST);
      let terminalReceived = false;
      port.onMessage.addListener(async (response) => {
        if (terminalReceived) return;
        if (response?.type === "progress") {
          await setJob({
            state: "working",
            message: response.message || "Working.",
            current: response.current,
            total: response.total,
            ...identity,
          });
          return;
        }
        terminalReceived = true;
        await XivKindle.storeTerminalJob(response, chrome.storage.session, identity);
        working = false;
        port.disconnect();
      });
      port.onDisconnect.addListener(async () => {
        if (terminalReceived) return;
        const error = chrome.runtime.lastError?.message;
        if (!working) return;
        working = false;
        await setJob({
          state: "error",
          message: error || "The local converter stopped before finishing.",
          ...identity,
        });
      });
      port.postMessage({ ...message.request, stream_progress: true });
      sendResponse({ ok: true });
    })
    .catch(async (error) => {
      working = false;
      await setJob({
        state: "error",
        message: error.message || "Could not start conversion.",
        ...identity,
      });
      sendResponse({ ok: false, message: error.message || "Could not start conversion." });
    });
  return true;
});
