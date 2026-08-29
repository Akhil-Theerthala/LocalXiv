importScripts("shared.js");

const HOST = "com.arxiv_to_kindle.host";
const JOB_KEY = "jobState";

let nativePort = null;
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
  setJob({ state: "working", message: "Starting local converter." })
    .then(() => {
      nativePort = chrome.runtime.connectNative(HOST);
      nativePort.onMessage.addListener(async (response) => {
        if (response?.type === "progress") {
          await setJob({
            state: "working",
            message: response.message || "Working.",
            current: response.current,
            total: response.total,
          });
          return;
        }
        working = false;
        await XivKindle.storeTerminalJob(response, chrome.storage.session);
        nativePort?.disconnect();
        nativePort = null;
      });
      nativePort.onDisconnect.addListener(async () => {
        const error = chrome.runtime.lastError?.message;
        nativePort = null;
        if (!working) return;
        working = false;
        await setJob({
          state: "error",
          message: error || "The local converter stopped before finishing.",
        });
      });
      nativePort.postMessage({ ...message.request, stream_progress: true });
      sendResponse({ ok: true });
    })
    .catch(async (error) => {
      working = false;
      await setJob({ state: "error", message: error.message || "Could not start conversion." });
      sendResponse({ ok: false, message: error.message || "Could not start conversion." });
    });
  return true;
});
