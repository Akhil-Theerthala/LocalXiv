const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
  actionLabel,
  cleanCollectionTitle,
  isAlphaXivFolderUrl,
  jobIdentity,
  normalizeKindleEmail,
  normalizePaperEntries,
  normalizePaperUrls,
  pageContext,
  parsePaperUrl,
  settingsSummary,
  storeTerminalJob,
} = require("../extension/shared.js");

function inMemoryStorage(initialState, { beforeGet, beforeSet, beforeRemove } = {}) {
  const state = { ...initialState };
  const operations = [];
  return {
    state,
    operations,
    async get() {
      await beforeGet?.();
      return { ...state };
    },
    async set(values) {
      await beforeSet?.(values);
      operations.push(["set", Object.keys(values)]);
      Object.assign(state, values);
    },
    async remove(keys) {
      const list = Array.isArray(keys) ? keys : [keys];
      await beforeRemove?.(list);
      operations.push(["remove", list]);
      for (const key of list) delete state[key];
    },
    async clear() {
      operations.push(["clear"]);
      for (const key of Object.keys(state)) delete state[key];
    },
  };
}

function loadBackgroundWorker(sessionStorage, { postMessageError } = {}) {
  let runtimeMessageListener;
  let resolveNativeRequest;
  const nativeRequestPosted = new Promise((resolve) => {
    resolveNativeRequest = resolve;
  });
  function createNativePort() {
    let nativeMessageListener;
    let nativeDisconnectListener;
    return {
      disconnected: false,
      disconnectCalls: 0,
      onMessage: {
        addListener(listener) {
          nativeMessageListener = listener;
        },
      },
      onDisconnect: {
        addListener(listener) {
          nativeDisconnectListener = listener;
        },
      },
      postMessage(message) {
        const error = typeof postMessageError === "function" ? postMessageError() : postMessageError;
        if (error) throw error;
        resolveNativeRequest(message);
      },
      disconnect() {
        this.disconnectCalls += 1;
        this.disconnected = true;
        nativeDisconnectListener?.();
      },
      async emitNativeMessage(message) {
        await nativeMessageListener(message);
      },
      async emitDisconnect() {
        await nativeDisconnectListener?.();
      },
    };
  }
  const nativePorts = [createNativePort()];
  let nextNativePort = 0;
  const chrome = {
    runtime: {
      lastError: undefined,
      connectNative() {
        const nativePort = nativePorts[nextNativePort] || createNativePort();
        if (!nativePorts[nextNativePort]) nativePorts.push(nativePort);
        nextNativePort += 1;
        return nativePort;
      },
      onMessage: {
        addListener(listener) {
          runtimeMessageListener = listener;
        },
      },
    },
    storage: { session: sessionStorage },
  };
  const extensionDir = path.resolve(__dirname, "../extension");
  const sandbox = {
    chrome,
    URL,
    importScripts(filename) {
      vm.runInContext(fs.readFileSync(path.join(extensionDir, filename), "utf8"), context, {
        filename,
      });
    },
  };
  const context = vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(extensionDir, "background.js"), "utf8"), context, {
    filename: "background.js",
  });
  return { nativePort: nativePorts[0], nativePorts, nativeRequestPosted, runtimeMessageListener };
}

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function popupNode() {
  const listeners = {};
  return {
    attributes: {},
    children: [],
    className: "",
    disabled: false,
    hidden: false,
    max: 1,
    open: false,
    textContent: "",
    value: 0,
    addEventListener(type, listener) {
      listeners[type] = listener;
    },
    append(child) {
      this.children.push(child);
    },
    focus() {},
    async dispatch(type, event = { preventDefault() {} }) {
      await listeners[type]?.(event);
    },
    replaceChildren(...children) {
      this.children = children;
    },
    removeAttribute(name) {
      delete this.attributes[name];
    },
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
  };
}

function alphaXivPage(url, title, papers) {
  const root = {
    querySelector(selector) {
      return selector === "h1" ? { textContent: title } : null;
    },
    querySelectorAll(selector) {
      return selector === "a[href]"
        ? papers.map((paper) => ({ href: paper.url, textContent: paper.title }))
        : [];
    },
  };
  return {
    document: {
      title,
      querySelector(selector) {
        return selector === "main" ? root : null;
      },
    },
    location: { href: url },
  };
}

function loadPopup({
  tab,
  jobState,
  executeScript,
  inspectedPage,
  kindleEmail = "",
  sendMessage = async () => ({ ok: true }),
}) {
  const nodes = Object.fromEntries(
    [
      "#send-form",
      "#kindle-email",
      "#email-error",
      "#delivery-settings",
      "#settings-summary",
      "#settings-action",
      "#context-label",
      "#page-title",
      "#paper-id",
      "#description",
      "#paper-preview",
      "#paper-preview-more",
      "#send",
      "#status",
      "#status-source",
      "#status-state",
      "#status-message",
      "#status-progress-wrap",
      "#status-progress",
      "#status-progress-text",
      "#manual",
    ].map((selector) => [selector, popupNode()]),
  );
  nodes["#paper-preview"].hidden = true;
  nodes["#paper-preview-more"].hidden = true;
  nodes["#status"].hidden = true;
  nodes["#status-source"].hidden = true;
  nodes["#status-progress-wrap"].hidden = true;
  nodes["#manual"].hidden = true;
  let storageListener;
  let sendMessageCalls = 0;
  const sentMessages = [];
  const chrome = {
    runtime: {
      async sendMessage(message) {
        sendMessageCalls += 1;
        sentMessages.push(message);
        return sendMessage(message);
      },
    },
    scripting: {
      async executeScript(options) {
        if (executeScript) return executeScript(options);
        return [{ result: vm.runInNewContext(`(${options.func})()`, inspectedPage) }];
      },
    },
    storage: {
      local: {
        async get() { return { kindleEmail }; },
        async set() {},
      },
      onChanged: {
        addListener(listener) {
          storageListener = listener;
        },
      },
      session: { async get() { return { jobState }; } },
    },
    tabs: { async query() { return [tab]; } },
  };
  const document = {
    createElement() {
      return popupNode();
    },
    querySelector(selector) {
      return nodes[selector];
    },
  };
  const context = vm.createContext({ chrome, document, URL, XivKindle: require("../extension/shared.js") });
  vm.runInContext(fs.readFileSync(path.resolve(__dirname, "../extension/popup.js"), "utf8"), context, {
    filename: "popup.js",
  });
  return {
    nodes,
    sendMessageCalls() {
      return sendMessageCalls;
    },
    sentMessages,
    emitJob(nextJob) {
      storageListener({ jobState: { newValue: nextJob } }, "session");
    },
  };
}

function popupTick() {
  return new Promise((resolve) => setImmediate(resolve));
}

test("parsePaperUrl accepts trusted arXiv and alphaXiv abstract URLs", () => {
  assert.deepEqual(parsePaperUrl("https://arxiv.org/abs/2401.01234v2"), {
    id: "2401.01234v2",
    site: "arxiv",
  });
  assert.deepEqual(
    parsePaperUrl("https://www.alphaxiv.org/abs/2503.15850?chatId=private#comments"),
    { id: "2503.15850", site: "alphaxiv" },
  );
  assert.deepEqual(parsePaperUrl("https://alphaxiv.org/abs/hep-th/9901001"), {
    id: "hep-th/9901001",
    site: "alphaxiv",
  });
});

test("parsePaperUrl rejects lookalikes and non-abstract routes", () => {
  for (const url of [
    "https://alphaxiv.example/abs/2401.01234",
    "https://www.alphaxiv.org/pdf/2401.01234",
    "https://www.alphaxiv.org/abs/../../etc/passwd",
    "javascript:alert(1)",
  ]) {
    assert.equal(parsePaperUrl(url), null, url);
  }
});

test("normalizePaperUrls deduplicates by identifier in first-seen order", () => {
  assert.deepEqual(
    normalizePaperUrls([
      "https://www.alphaxiv.org/abs/2503.15850?chatId=one",
      "https://arxiv.org/abs/2401.01234",
      "https://alphaxiv.org/abs/2503.15850?chatId=two",
      "https://example.com/abs/9999.99999",
    ]),
    [
      "https://www.alphaxiv.org/abs/2503.15850",
      "https://arxiv.org/abs/2401.01234",
    ],
  );
});

test("folder helpers trust only explicit alphaXiv folder routes and preserve reviewed entries", () => {
  assert.equal(
    isAlphaXivFolderUrl("https://www.alphaxiv.org/library/folders/uncertainty?sort=added"),
    true,
  );
  assert.equal(isAlphaXivFolderUrl("https://www.alphaxiv.org/search?q=uncertainty"), false);
  assert.equal(isAlphaXivFolderUrl("https://www.alphaxiv.org/library/folders/"), false);
  assert.equal(isAlphaXivFolderUrl("https://www.alphaxiv.org/library/folders//"), false);

  assert.deepEqual(
    normalizePaperEntries([
      { url: "https://www.alphaxiv.org/abs/2503.15850?chatId=one", title: "  First\n paper " },
      { url: "https://arxiv.org/abs/2401.01234", title: "" },
      { url: "https://arxiv.org/abs/2503.15850", title: "Duplicate" },
      { url: "https://arxiv.org/abs/2401.01235", title: "x".repeat(161) },
    ]),
    [
      {
        id: "2503.15850",
        url: "https://www.alphaxiv.org/abs/2503.15850",
        title: "First paper",
      },
      {
        id: "2401.01234",
        url: "https://arxiv.org/abs/2401.01234",
        title: "Paper 2401.01234",
      },
      {
        id: "2401.01235",
        url: "https://arxiv.org/abs/2401.01235",
        title: "x".repeat(160),
      },
    ],
  );
});

test("pageContext creates collections only for explicit alphaXiv folder routes", () => {
  assert.deepEqual(
    pageContext("https://www.alphaxiv.org/abs/2503.15850?chatId=private", [], ""),
    { kind: "paper", id: "2503.15850", site: "alphaxiv" },
  );
  assert.deepEqual(
    pageContext(
      "https://www.alphaxiv.org/library/folders/uncertainty",
      [
        { url: "https://www.alphaxiv.org/abs/2503.15850", title: " First paper " },
        { url: "https://www.alphaxiv.org/abs/2401.01234", title: "Second paper" },
      ],
      "Uncertainty Quantification | alphaXiv",
    ),
    {
      kind: "collection",
      title: "Uncertainty Quantification",
      papers: [
        {
          id: "2503.15850",
          url: "https://www.alphaxiv.org/abs/2503.15850",
          title: "First paper",
        },
        {
          id: "2401.01234",
          url: "https://www.alphaxiv.org/abs/2401.01234",
          title: "Second paper",
        },
      ],
      urls: [
        "https://www.alphaxiv.org/abs/2503.15850",
        "https://www.alphaxiv.org/abs/2401.01234",
      ],
      overLimit: false,
    },
  );
  assert.deepEqual(
    pageContext(
      "https://www.alphaxiv.org/search?q=uncertainty",
      [{ url: "https://arxiv.org/abs/2401.01234", title: "A paper" }],
      "Search",
    ),
    { kind: "unsupported" },
  );
  assert.deepEqual(
    pageContext(
      "https://www.alphaxiv.org/library/folders/",
      [{ url: "https://arxiv.org/abs/2401.01234", title: "A paper" }],
      "Folder",
    ),
    { kind: "unsupported" },
  );
  assert.equal(
    pageContext(
      "https://www.alphaxiv.org/library/folders/large",
      Array.from({ length: 51 }, (_, index) => ({
        url: `https://arxiv.org/abs/2401.${String(index).padStart(5, "0")}`,
        title: `Paper ${index + 1}`,
      })),
      "Large folder",
    ).overLimit,
    true,
  );
  assert.deepEqual(pageContext("https://example.com", [], "Example"), {
    kind: "unsupported",
  });
});

test("popup shows the current paper identifier", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234v2" },
    jobState: { state: "idle" },
  });
  await popupTick();
  await popupTick();
  assert.equal(popup.nodes["#paper-id"].textContent, "arXiv 2401.01234v2");
  assert.equal(popup.nodes["#paper-id"].hidden, false);
});

test("popup renders bounded collection progress", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: {
      state: "working",
      message: "Converting paper 2 of 5.",
      current: 2,
      total: 5,
      job_label: "War Studies",
      paper_count: 5,
    },
  });
  assert.equal(popup.nodes["#status-progress"].value, 0);
  await popupTick();
  await popupTick();
  assert.equal(popup.nodes["#status-progress-wrap"].hidden, false);
  assert.equal(popup.nodes["#status-progress"].max, 5);
  assert.equal(popup.nodes["#status-progress"].value, 2);
  assert.equal(popup.nodes["#status-progress-text"].textContent, "2 / 5 · 40%");
});

test("popup delivery settings show add or edit action without revealing the saved address", async () => {
  const saved = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: { state: "idle" },
    kindleEmail: "reader@kindle.com",
  });
  const unset = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: { state: "idle" },
  });
  await popupTick();
  await popupTick();
  assert.equal(saved.nodes["#settings-action"].textContent, "Edit");
  assert.equal(unset.nodes["#settings-action"].textContent, "Add");
});

test("popup clears aria-invalid after valid Kindle input", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: { state: "idle" },
  });
  await popupTick();
  await popupTick();

  popup.nodes["#kindle-email"].value = "reader@example.com";
  await popup.nodes["#send-form"].dispatch("submit");
  assert.equal(popup.nodes["#kindle-email"].attributes["aria-invalid"], "true");

  popup.nodes["#kindle-email"].value = "reader@kindle.com";
  await popup.nodes["#kindle-email"].dispatch("input");
  assert.equal(popup.nodes["#kindle-email"].attributes["aria-invalid"], undefined);
});

test("popup keeps a newer terminal job after delayed folder discovery", async () => {
  const discovery = deferred();
  const popup = loadPopup({
    tab: { id: 1, url: "https://www.alphaxiv.org/library/folders/uncertainty" },
    jobState: {
      state: "working",
      message: "Converting.",
      job_label: "Uncertainty Lab",
      paper_count: 2,
    },
    executeScript: async () => discovery.promise,
  });
  await popupTick();

  popup.emitJob({
    state: "error",
    message: "The EPUB was saved, but Mail could not send it.",
    epub_path: "/tmp/uncertainty.epub",
    job_label: "Uncertainty Lab",
    paper_count: 2,
  });
  discovery.resolve([
    {
      result: {
        url: "https://www.alphaxiv.org/library/folders/uncertainty",
        title: "Uncertainty Lab | alphaXiv",
        papers: [{ url: "https://arxiv.org/abs/2401.01234", title: "Paper one" }],
      },
    },
  ]);
  await popupTick();

  assert.equal(popup.nodes["#status-state"].textContent, "Needs attention");
  assert.equal(popup.nodes["#manual"].hidden, false);
  assert.equal(popup.nodes["#page-title"].textContent, "Uncertainty Lab");
});

test("popup keeps a saved job when folder inspection fails", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://www.alphaxiv.org/library/folders/uncertainty" },
    jobState: {
      state: "error",
      message: "The EPUB was saved, but Mail could not send it.",
      epub_path: "/tmp/uncertainty.epub",
      job_label: "Uncertainty Lab",
    },
    executeScript: async () => { throw new Error("Folder unavailable"); },
    kindleEmail: "reader@kindle.com",
  });
  await popupTick();
  await popupTick();

  assert.equal(popup.nodes["#status-state"].textContent, "Needs attention");
  assert.equal(popup.nodes["#status-message"].textContent, "The EPUB was saved, but Mail could not send it.");
  assert.equal(popup.nodes["#status-source"].textContent, "Uncertainty Lab");
  assert.equal(popup.nodes["#manual"].hidden, false);
  assert.equal(popup.nodes["#context-label"].textContent, "Could not inspect page");
  assert.equal(popup.nodes["#send"].disabled, true);
  await popup.nodes["#send-form"].dispatch("submit");
  assert.equal(popup.sendMessageCalls(), 0);
});

test("popup previews and blocks a 51-paper folder", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://www.alphaxiv.org/library/folders/large" },
    jobState: { state: "idle" },
    executeScript: async () => [
      {
        result: {
          url: "https://www.alphaxiv.org/library/folders/large",
          title: "Large folder | alphaXiv",
          papers: Array.from({ length: 51 }, (_, index) => ({
            url: `https://arxiv.org/abs/2401.${String(index).padStart(5, "0")}`,
            title: `Paper ${index + 1}`,
          })),
        },
      },
    ],
  });
  await popupTick();
  await popupTick();

  assert.equal(popup.nodes["#context-label"].textContent, "alphaXiv library");
  assert.equal(popup.nodes["#paper-preview"].hidden, false);
  assert.equal(popup.nodes["#paper-preview"].children.length, 5);
  assert.equal(popup.nodes["#paper-preview-more"].textContent, "+ 46 more");
  assert.equal(popup.nodes["#send"].textContent, "50 paper limit");
  assert.equal(popup.nodes["#send"].disabled, true);
});

test("popup rejects paper links collected after the inspected page changes route", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://www.alphaxiv.org/library/folders/uncertainty" },
    jobState: { state: "idle" },
    kindleEmail: "reader@kindle.com",
    inspectedPage: alphaXivPage(
      "https://www.alphaxiv.org/search?q=uncertainty",
      "Search | alphaXiv",
      [{ url: "https://arxiv.org/abs/2401.01234", title: "A paper" }],
    ),
  });
  await popupTick();
  await popupTick();

  assert.equal(popup.nodes["#context-label"].textContent, "Unsupported page");
  assert.equal(popup.nodes["#send"].disabled, true);
  await popup.nodes["#send-form"].dispatch("submit");
  assert.equal(popup.sendMessageCalls(), 0);
});

test("popup keeps a newer terminal job after a delayed start response", async () => {
  const startResponse = deferred();
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: { state: "idle" },
    kindleEmail: "reader@kindle.com",
    sendMessage: async () => startResponse.promise,
  });
  await popupTick();
  await popupTick();

  const submission = popup.nodes["#send-form"].dispatch("submit");
  await popupTick();
  popup.emitJob({
    state: "error",
    message: "The EPUB was saved, but Mail could not send it.",
    epub_path: "/tmp/manual.epub",
    job_label: "Paper 2401.01234",
    paper_count: 1,
  });
  startResponse.resolve({ ok: true });
  await submission;

  assert.equal(popup.nodes["#status-state"].textContent, "Needs attention");
  assert.equal(popup.nodes["#status-message"].textContent, "The EPUB was saved, but Mail could not send it.");
  assert.equal(popup.nodes["#manual"].hidden, false);
});

test("popup keeps a newer terminal job after a delayed start error response", async () => {
  const startResponse = deferred();
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: { state: "idle" },
    kindleEmail: "reader@kindle.com",
    sendMessage: async () => startResponse.promise,
  });
  await popupTick();
  await popupTick();

  const submission = popup.nodes["#send-form"].dispatch("submit");
  await popupTick();
  popup.emitJob({
    state: "error",
    message: "The EPUB was saved, but Mail could not send it.",
    epub_path: "/tmp/manual.epub",
    job_label: "Paper 2401.01234",
    paper_count: 1,
  });
  startResponse.resolve({ ok: false, message: "The worker rejected the start." });
  await submission;

  assert.equal(popup.nodes["#status-state"].textContent, "Needs attention");
  assert.equal(popup.nodes["#status-message"].textContent, "The EPUB was saved, but Mail could not send it.");
  assert.equal(popup.nodes["#manual"].hidden, false);
});

test("popup reserves locally before two rapid submits can start twice", async () => {
  const startResponse = deferred();
  const popup = loadPopup({
    tab: { id: 1, url: "https://arxiv.org/abs/2401.01234" },
    jobState: { state: "idle" },
    kindleEmail: "reader@kindle.com",
    sendMessage: async () => startResponse.promise,
  });
  await popupTick();
  await popupTick();

  const first = popup.nodes["#send-form"].dispatch("submit");
  const second = popup.nodes["#send-form"].dispatch("submit");
  await popupTick();
  assert.equal(popup.sendMessageCalls(), 1);
  assert.deepEqual(JSON.parse(JSON.stringify(popup.sentMessages[0])), {
    type: "start",
    request: {
      kindle_email: "reader@kindle.com",
      send: true,
      url: "https://arxiv.org/abs/2401.01234",
    },
  });

  startResponse.resolve({ ok: true });
  await Promise.all([first, second]);
});

test("popup submits an inspected in-limit collection", async () => {
  const popup = loadPopup({
    tab: { id: 1, url: "https://www.alphaxiv.org/library/folders/uncertainty" },
    jobState: { state: "idle" },
    kindleEmail: "reader@kindle.com",
    inspectedPage: alphaXivPage(
      "https://www.alphaxiv.org/library/folders/uncertainty",
      "Uncertainty Lab | alphaXiv",
      [
        { url: "https://arxiv.org/abs/2401.01234", title: "Paper one" },
        { url: "https://www.alphaxiv.org/abs/2503.15850", title: "Paper two" },
      ],
    ),
  });
  await popupTick();
  await popupTick();

  await popup.nodes["#send-form"].dispatch("submit");

  assert.equal(popup.sendMessageCalls(), 1);
  assert.deepEqual(JSON.parse(JSON.stringify(popup.sentMessages[0])), {
    type: "start",
    request: {
      kindle_email: "reader@kindle.com",
      send: true,
      urls: [
        "https://arxiv.org/abs/2401.01234",
        "https://www.alphaxiv.org/abs/2503.15850",
      ],
      collection_title: "Uncertainty Lab",
    },
  });
});

test("delivery helpers validate without exposing the saved address", () => {
  assert.equal(normalizeKindleEmail(" Reader_1@Kindle.com "), "Reader_1@kindle.com");
  assert.equal(normalizeKindleEmail("reader@free.kindle.com"), "reader@free.kindle.com");
  assert.equal(normalizeKindleEmail("reader@example.com"), null);
  assert.equal(settingsSummary("reader@kindle.com"), "Kindle address saved");
  assert.equal(settingsSummary(""), "Add Kindle address");
  assert.equal(settingsSummary("reader@kindle.com").includes("reader"), false);
});

test("context copy stays short and specific", () => {
  assert.equal(cleanCollectionTitle(" Uncertainty Quantification | alphaXiv "), "Uncertainty Quantification");
  assert.equal(cleanCollectionTitle("alphaXiv"), "alphaXiv Library");
  assert.equal(actionLabel({ kind: "paper" }), "Send paper");
  assert.equal(actionLabel({ kind: "collection", urls: ["one", "two"] }), "Compile and send 2 papers");
  assert.equal(actionLabel({ kind: "unsupported" }), "Unavailable on this page");
});

test("jobIdentity names single papers and deduplicated collections", () => {
  assert.deepEqual(jobIdentity({ url: "https://arxiv.org/abs/2503.15850v2" }), {
    job_label: "Paper 2503.15850v2",
    paper_count: 1,
  });
  assert.deepEqual(
    jobIdentity({
      urls: [
        "https://www.alphaxiv.org/abs/2503.15850",
        "https://arxiv.org/abs/2503.15850",
        "https://arxiv.org/abs/2401.01234",
      ],
      collection_title: " Uncertainty Lab | alphaXiv ",
    }),
    { job_label: "Uncertainty Lab", paper_count: 2 },
  );
  assert.deepEqual(jobIdentity({ urls: {} }), {
    job_label: "Paper unknown",
    paper_count: 1,
  });
});

test("storeTerminalJob clears stale session state for a completed EPUB success", async () => {
  const storage = inMemoryStorage({
    jobState: { state: "working", message: "Converting." },
    selectedPaper: "2401.01234",
    progress: { current: 2, total: 5 },
  });

  const job = await storeTerminalJob(
    { ok: true, message: "Sent to Kindle.", epub_path: "/tmp/paper.epub" },
    storage,
    { job_label: "Paper 2401.01234", paper_count: 1 },
  );

  assert.deepEqual(job, {
    state: "success",
    message: "Sent to Kindle.",
    epub_path: "/tmp/paper.epub",
    job_label: "Paper 2401.01234",
    paper_count: 1,
  });
  assert.deepEqual(storage.state, { jobState: job });
  assert.deepEqual(storage.operations, [
    ["set", ["jobState"]],
    ["remove", ["selectedPaper", "progress"]],
  ]);
});

test("storeTerminalJob clears stale session state for a mail error with an EPUB", async () => {
  const storage = inMemoryStorage({
    jobState: { state: "working", message: "Emailing." },
    selectedPaper: "2503.15850",
  });

  const job = await storeTerminalJob(
    { ok: false, message: "Kindle delivery failed.", epub_path: "/tmp/anthology.epub" },
    storage,
    { job_label: "Uncertainty Lab", paper_count: 2 },
  );

  assert.deepEqual(job, {
    state: "error",
    message: "Kindle delivery failed.",
    epub_path: "/tmp/anthology.epub",
    job_label: "Uncertainty Lab",
    paper_count: 2,
  });
  assert.deepEqual(storage.state, { jobState: job });
  assert.deepEqual(storage.operations, [
    ["set", ["jobState"]],
    ["remove", ["selectedPaper"]],
  ]);
});

test("storeTerminalJob preserves a saved EPUB when stale cleanup fails", async () => {
  const storage = inMemoryStorage(
    { selectedPaper: "2503.15850" },
    { beforeRemove: async () => { throw new Error("Session cleanup failed."); } },
  );

  const job = await storeTerminalJob(
    { ok: true, message: "Sent to Kindle.", epub_path: "/tmp/saved.epub" },
    storage,
    { job_label: "Paper 2503.15850", paper_count: 1 },
  );

  assert.deepEqual(job, {
    state: "success",
    message: "Sent to Kindle.",
    epub_path: "/tmp/saved.epub",
    job_label: "Paper 2503.15850",
    paper_count: 1,
  });
  assert.deepEqual(storage.state, {
    selectedPaper: "2503.15850",
    jobState: job,
  });
});

test("storeTerminalJob preserves a saved EPUB when stale session inspection fails", async () => {
  const storage = inMemoryStorage(
    { selectedPaper: "2503.15850" },
    { beforeGet: async () => { throw new Error("Session inspection failed."); } },
  );

  const job = await storeTerminalJob(
    { ok: true, message: "Sent to Kindle.", epub_path: "/tmp/saved.epub" },
    storage,
    { job_label: "Paper 2503.15850", paper_count: 1 },
  );

  assert.deepEqual(storage.state, {
    selectedPaper: "2503.15850",
    jobState: job,
  });
  assert.deepEqual(storage.operations, [["set", ["jobState"]]]);
});

test("storeTerminalJob rejects when the terminal state cannot be stored", async () => {
  const storage = inMemoryStorage(
    { selectedPaper: "2503.15850" },
    { beforeSet: async () => { throw new Error("Terminal write failed."); } },
  );

  await assert.rejects(
    storeTerminalJob(
      { ok: true, message: "Sent to Kindle.", epub_path: "/tmp/saved.epub" },
      storage,
    ),
    /Terminal write failed/,
  );
  assert.deepEqual(storage.state, { selectedPaper: "2503.15850" });
});

test("storeTerminalJob preserves unrelated session state for a conversion error", async () => {
  const storage = inMemoryStorage({
    selectedPaper: "2503.15850",
    popupPreference: "compact",
  });

  const job = await storeTerminalJob(
    { ok: false, message: "Pandoc conversion failed." },
    storage,
  );

  assert.deepEqual(job, {
    state: "error",
    message: "Pandoc conversion failed.",
    epub_path: undefined,
  });
  assert.deepEqual(storage.state, {
    selectedPaper: "2503.15850",
    popupPreference: "compact",
    jobState: job,
  });
});

test("background clears stale session state after a terminal EPUB response", async () => {
  const sessionStorage = inMemoryStorage({
    selectedPaper: "2503.15850",
    progress: { current: 2, total: 5 },
  });
  const { nativePort, nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(
    sessionStorage,
  );
  let resolveStartResponse;
  const startResponse = new Promise((resolve) => {
    resolveStartResponse = resolve;
  });

  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
      {},
      resolveStartResponse,
    ),
    true,
  );
  await nativeRequestPosted;
  assert.equal((await startResponse).ok, true);

  await nativePort.emitNativeMessage({
    ok: false,
    message: "The EPUB was saved, but Mail could not send it.",
    epub_path: "/tmp/saved.epub",
  });

  assert.equal(nativePort.disconnected, true);
  assert.equal(nativePort.disconnectCalls, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(sessionStorage.state)), {
    jobState: {
      state: "error",
      message: "The EPUB was saved, but Mail could not send it.",
      epub_path: "/tmp/saved.epub",
      job_label: "Paper 2503.15850",
      paper_count: 1,
    },
  });
});

test("background rejects an identity error without poisoning a later start", async () => {
  const sessionStorage = inMemoryStorage({});
  const { nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(sessionStorage);
  const malformedRequest = {};
  Object.defineProperty(malformedRequest, "urls", {
    get() { throw new Error("Malformed collection input."); },
  });
  let malformedResponse;

  assert.equal(
    runtimeMessageListener(
      { type: "start", request: malformedRequest },
      {},
      (response) => { malformedResponse = response; },
    ),
    false,
  );
  assert.equal(malformedResponse.ok, false);
  assert.equal(malformedResponse.message, "Malformed collection input.");

  let resolveValidStart;
  const validStart = new Promise((resolve) => {
    resolveValidStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveValidStart,
    ),
    true,
  );
  await nativeRequestPosted;
  assert.equal((await validStart).ok, true);
});

test("background lets the native host reject non-array urls and accepts a later start", async () => {
  const sessionStorage = inMemoryStorage({});
  const { nativePort, nativePorts, nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(
    sessionStorage,
  );
  let resolveMalformedStart;
  const malformedStart = new Promise((resolve) => {
    resolveMalformedStart = resolve;
  });

  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { urls: {} } },
      {},
      resolveMalformedStart,
    ),
    true,
  );
  assert.deepEqual(JSON.parse(JSON.stringify(await nativeRequestPosted)).urls, {});
  assert.equal((await malformedStart).ok, true);
  await nativePort.emitNativeMessage({ ok: false, message: "urls must be an array." });

  let resolveValidStart;
  const validStart = new Promise((resolve) => {
    resolveValidStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveValidStart,
    ),
    true,
  );
  assert.equal((await validStart).ok, true);
  assert.equal(nativePorts.length, 2);
});

test("background reserves the conversion and ignores late native events after terminal storage begins", async () => {
  const terminalWriteStarted = Promise.withResolvers();
  const releaseTerminalWrite = Promise.withResolvers();
  const sessionStorage = inMemoryStorage({}, {
    beforeSet: async ({ jobState }) => {
      if (jobState?.state === "success") {
        terminalWriteStarted.resolve();
        await releaseTerminalWrite.promise;
      }
    },
  });
  const { nativePort, nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(
    sessionStorage,
  );
  let resolveFirstStart;
  const firstStart = new Promise((resolve) => {
    resolveFirstStart = resolve;
  });

  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
      {},
      resolveFirstStart,
    ),
    true,
  );
  await nativeRequestPosted;
  assert.equal((await firstStart).ok, true);

  const terminalMessage = nativePort.emitNativeMessage({
    ok: true,
    message: "Sent to Kindle.",
    epub_path: "/tmp/saved.epub",
  });
  await terminalWriteStarted.promise;

  const lateMessages = [
    nativePort.emitNativeMessage({
      type: "progress",
      message: "Late progress should be ignored.",
      current: 9,
      total: 9,
    }),
    nativePort.emitNativeMessage({
      ok: false,
      message: "Duplicate terminal response should be ignored.",
      epub_path: "/tmp/duplicate.epub",
    }),
  ];
  assert.equal(nativePort.disconnectCalls, 0);
  assert.deepEqual(JSON.parse(JSON.stringify(sessionStorage.state)).jobState, {
    state: "working",
    message: "Starting local converter.",
    job_label: "Paper 2503.15850",
    paper_count: 1,
  });

  let resolveSecondStart;
  const secondStart = new Promise((resolve) => {
    resolveSecondStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveSecondStart,
    ),
    false,
  );
  const rejectedStart = await secondStart;
  assert.equal(rejectedStart.ok, false);
  assert.equal(rejectedStart.message, "A conversion is already running.");

  releaseTerminalWrite.resolve();
  await Promise.all([terminalMessage, ...lateMessages]);
  assert.equal(nativePort.disconnectCalls, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(sessionStorage.state)).jobState, {
    state: "success",
    message: "Sent to Kindle.",
    epub_path: "/tmp/saved.epub",
    job_label: "Paper 2503.15850",
    paper_count: 1,
  });
});

test("background serializes a delayed progress write before terminal state", async () => {
  const progressWriteStarted = Promise.withResolvers();
  const releaseProgressWrite = Promise.withResolvers();
  const sessionStorage = inMemoryStorage({}, {
    beforeSet: async ({ jobState }) => {
      if (jobState?.message === "Persisting progress.") {
        progressWriteStarted.resolve();
        await releaseProgressWrite.promise;
      }
    },
  });
  const { nativePort, nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(
    sessionStorage,
  );
  let resolveStart;
  const start = new Promise((resolve) => {
    resolveStart = resolve;
  });

  runtimeMessageListener(
    { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
    {},
    resolveStart,
  );
  await nativeRequestPosted;
  assert.equal((await start).ok, true);

  const progressMessage = nativePort.emitNativeMessage({
    type: "progress",
    message: "Persisting progress.",
    current: 1,
    total: 2,
  });
  await progressWriteStarted.promise;
  const terminalMessage = nativePort.emitNativeMessage({
    ok: true,
    message: "Sent to Kindle.",
    epub_path: "/tmp/saved.epub",
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(nativePort.disconnectCalls, 0);
  releaseProgressWrite.resolve();
  await Promise.all([progressMessage, terminalMessage]);

  assert.equal(nativePort.disconnectCalls, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(sessionStorage.state)).jobState, {
    state: "success",
    message: "Sent to Kindle.",
    epub_path: "/tmp/saved.epub",
    job_label: "Paper 2503.15850",
    paper_count: 1,
  });
});

test("background keeps terminal arrival reserved through a delayed progress write", async () => {
  const progressWriteStarted = Promise.withResolvers();
  const releaseProgressWrite = Promise.withResolvers();
  const sessionStorage = inMemoryStorage({}, {
    beforeSet: async ({ jobState }) => {
      if (jobState?.message === "Held progress.") {
        progressWriteStarted.resolve();
        await releaseProgressWrite.promise;
      }
    },
  });
  const { nativePort, nativePorts, nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(
    sessionStorage,
  );
  let resolveFirstStart;
  const firstStart = new Promise((resolve) => {
    resolveFirstStart = resolve;
  });
  runtimeMessageListener(
    { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
    {},
    resolveFirstStart,
  );
  await nativeRequestPosted;
  assert.equal((await firstStart).ok, true);

  const progressMessage = nativePort.emitNativeMessage({
    type: "progress",
    message: "Held progress.",
    current: 1,
    total: 2,
  });
  await progressWriteStarted.promise;
  const terminalMessage = nativePort.emitNativeMessage({
    ok: true,
    message: "Sent to Kindle.",
    epub_path: "/tmp/saved.epub",
  });
  await nativePort.emitDisconnect();

  let resolveRejectedStart;
  const rejectedStart = new Promise((resolve) => {
    resolveRejectedStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveRejectedStart,
    ),
    false,
  );
  assert.equal((await rejectedStart).message, "A conversion is already running.");

  releaseProgressWrite.resolve();
  await Promise.all([progressMessage, terminalMessage]);
  assert.equal(nativePort.disconnectCalls, 1);

  let resolveSecondStart;
  const secondStart = new Promise((resolve) => {
    resolveSecondStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveSecondStart,
    ),
    true,
  );
  assert.equal((await secondStart).ok, true);
  assert.equal(nativePorts.length, 2);

  await nativePort.emitNativeMessage({ type: "progress", message: "Old port." });
  assert.equal(JSON.parse(JSON.stringify(sessionStorage.state)).jobState.job_label, "Paper 2401.01234");
});

test("background settles a storage failure without poisoning later starts", async () => {
  let failProgressWrite = true;
  const sessionStorage = inMemoryStorage({}, {
    beforeSet: async ({ jobState }) => {
      if (jobState?.message === "Progress write fails." && failProgressWrite) {
        failProgressWrite = false;
        throw new Error("Session storage failed.");
      }
    },
  });
  const { nativePort, nativePorts, nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(
    sessionStorage,
  );
  let resolveFirstStart;
  const firstStart = new Promise((resolve) => {
    resolveFirstStart = resolve;
  });
  runtimeMessageListener(
    { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
    {},
    resolveFirstStart,
  );
  await nativeRequestPosted;
  assert.equal((await firstStart).ok, true);

  await assert.doesNotReject(
    nativePort.emitNativeMessage({
      type: "progress",
      message: "Progress write fails.",
      current: 1,
      total: 2,
    }),
  );
  assert.equal(nativePort.disconnectCalls, 1);
  const failedJob = JSON.parse(JSON.stringify(sessionStorage.state)).jobState;
  assert.equal(failedJob.state, "error");
  assert.equal(failedJob.job_label, "Paper 2503.15850");
  assert.equal(failedJob.paper_count, 1);
  assert.equal(typeof failedJob.message, "string");

  let resolveSecondStart;
  const secondStart = new Promise((resolve) => {
    resolveSecondStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveSecondStart,
    ),
    true,
  );
  assert.equal((await secondStart).ok, true);
  assert.equal(nativePorts.length, 2);
});

test("background serializes a native disconnect behind delayed progress", async () => {
  const progressWriteStarted = Promise.withResolvers();
  const releaseProgressWrite = Promise.withResolvers();
  const sessionStorage = inMemoryStorage({}, {
    beforeSet: async ({ jobState }) => {
      if (jobState?.message === "Disconnect waits for progress.") {
        progressWriteStarted.resolve();
        await releaseProgressWrite.promise;
      }
    },
  });
  const { nativePort, nativePorts, nativeRequestPosted, runtimeMessageListener } = loadBackgroundWorker(
    sessionStorage,
  );
  let resolveFirstStart;
  const firstStart = new Promise((resolve) => {
    resolveFirstStart = resolve;
  });
  runtimeMessageListener(
    { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
    {},
    resolveFirstStart,
  );
  await nativeRequestPosted;
  assert.equal((await firstStart).ok, true);

  const progressMessage = nativePort.emitNativeMessage({
    type: "progress",
    message: "Disconnect waits for progress.",
    current: 1,
    total: 2,
  });
  await progressWriteStarted.promise;
  const disconnectMessage = nativePort.emitDisconnect();
  await new Promise((resolve) => setImmediate(resolve));

  let resolveRejectedStart;
  const rejectedStart = new Promise((resolve) => {
    resolveRejectedStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveRejectedStart,
    ),
    false,
  );
  assert.equal((await rejectedStart).message, "A conversion is already running.");

  releaseProgressWrite.resolve();
  await Promise.all([progressMessage, disconnectMessage]);
  assert.equal(nativePort.disconnectCalls, 1);

  let resolveSecondStart;
  const secondStart = new Promise((resolve) => {
    resolveSecondStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveSecondStart,
    ),
    true,
  );
  assert.equal((await secondStart).ok, true);
  await nativePort.emitNativeMessage({ type: "progress", message: "Old progress." });
  assert.equal(nativePorts.length, 2);
  assert.equal(JSON.parse(JSON.stringify(sessionStorage.state)).jobState.job_label, "Paper 2401.01234");
});

test("background holds startup ownership until its error state is stored", async () => {
  const errorWriteStarted = Promise.withResolvers();
  const releaseErrorWrite = Promise.withResolvers();
  let failPostMessage = true;
  const sessionStorage = inMemoryStorage({}, {
    beforeSet: async ({ jobState }) => {
      if (jobState?.state === "error" && jobState?.message === "Native post failed.") {
        errorWriteStarted.resolve();
        await releaseErrorWrite.promise;
      }
    },
  });
  const { nativePort, runtimeMessageListener } = loadBackgroundWorker(sessionStorage, {
    postMessageError: () => {
      if (!failPostMessage) return null;
      failPostMessage = false;
      return new Error("Native post failed.");
    },
  });
  let resolveFirstStart;
  const firstStart = new Promise((resolve) => {
    resolveFirstStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
      {},
      resolveFirstStart,
    ),
    true,
  );
  await errorWriteStarted.promise;

  let resolveRejectedStart;
  const rejectedStart = new Promise((resolve) => {
    resolveRejectedStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveRejectedStart,
    ),
    false,
  );
  assert.equal((await rejectedStart).message, "A conversion is already running.");

  releaseErrorWrite.resolve();
  const firstResponse = await firstStart;
  assert.equal(firstResponse.ok, false);
  assert.equal(firstResponse.message, "Native post failed.");
  assert.equal(nativePort.disconnectCalls, 1);
});

test("background responds and releases when startup error storage also fails", async () => {
  let failPostMessage = true;
  const sessionStorage = inMemoryStorage({}, {
    beforeSet: async ({ jobState }) => {
      if (jobState?.state === "error") throw new Error("Recovery write failed.");
    },
  });
  const { nativePort, runtimeMessageListener } = loadBackgroundWorker(sessionStorage, {
    postMessageError: () => {
      if (!failPostMessage) return null;
      failPostMessage = false;
      return new Error("Native post failed.");
    },
  });
  let resolveFirstStart;
  const firstStart = new Promise((resolve) => {
    resolveFirstStart = resolve;
  });
  runtimeMessageListener(
    { type: "start", request: { url: "https://arxiv.org/abs/2503.15850" } },
    {},
    resolveFirstStart,
  );
  const response = await Promise.race([
    firstStart,
    new Promise((resolve) => setImmediate(() => resolve("pending"))),
  ]);
  assert.notEqual(response, "pending");
  assert.equal(response.ok, false);
  assert.equal(response.message, "Native post failed.");
  assert.equal(nativePort.disconnectCalls, 1);

  let resolveSecondStart;
  const secondStart = new Promise((resolve) => {
    resolveSecondStart = resolve;
  });
  assert.equal(
    runtimeMessageListener(
      { type: "start", request: { url: "https://arxiv.org/abs/2401.01234" } },
      {},
      resolveSecondStart,
    ),
    true,
  );
  assert.equal((await secondStart).ok, true);
});
