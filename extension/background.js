importScripts("shared.js");

const HOST = "com.arxiv_to_kindle.host";
const JOB_KEY = "jobState";

let working = false;
let activeJob = null;

async function setJob(job) {
  await chrome.storage.session.set({ [JOB_KEY]: job });
}

function releaseJob(job) {
  if (activeJob !== job) return;
  activeJob = null;
  working = false;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "start") return false;
  if (working) {
    sendResponse({ ok: false, message: "A conversion is already running." });
    return false;
  }

  const job = Symbol("native job");
  working = true;
  activeJob = job;
  const identity = XivKindle.jobIdentity(message.request);
  setJob({ state: "working", message: "Starting local converter.", ...identity })
    .then(() => {
      const port = chrome.runtime.connectNative(HOST);
      let terminalArrived = false;
      let settled = false;
      let messageChain = Promise.resolve();

      async function settleError(error) {
        if (settled) return;
        settled = true;
        terminalArrived = true;
        try {
          await setJob({
            state: "error",
            message: error?.message || "Could not update conversion status.",
            ...identity,
          });
        } catch {
          // Release the job even when session storage remains unavailable.
        }
        releaseJob(job);
        port.disconnect();
      }

      port.onMessage.addListener((response) => {
        if (terminalArrived || settled) return;
        if (response?.type !== "progress") terminalArrived = true;
        messageChain = messageChain
          .then(async () => {
            if (settled) return;
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
            await XivKindle.storeTerminalJob(response, chrome.storage.session, identity);
            settled = true;
            releaseJob(job);
            port.disconnect();
          })
          .catch(settleError);
        return messageChain;
      });
      port.onDisconnect.addListener(async () => {
        if (terminalArrived || settled) return;
        const error = chrome.runtime.lastError?.message || "The local converter stopped before finishing.";
        await settleError(new Error(error));
      });
      port.postMessage({ ...message.request, stream_progress: true });
      sendResponse({ ok: true });
    })
    .catch(async (error) => {
      releaseJob(job);
      await setJob({
        state: "error",
        message: error.message || "Could not start conversion.",
        ...identity,
      });
      sendResponse({ ok: false, message: error.message || "Could not start conversion." });
    });
  return true;
});
