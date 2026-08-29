const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const {
  actionLabel,
  cleanCollectionTitle,
  normalizeKindleEmail,
  normalizePaperUrls,
  pageContext,
  parsePaperUrl,
  settingsSummary,
  storeTerminalJob,
} = require("../extension/shared.js");

function inMemoryStorage(initialState) {
  const state = { ...initialState };
  return {
    state,
    async clear() {
      for (const key of Object.keys(state)) delete state[key];
    },
    async set(values) {
      Object.assign(state, values);
    },
  };
}

function loadBackgroundWorker(sessionStorage) {
  let runtimeMessageListener;
  let nativeMessageListener;
  let nativeDisconnectListener;
  let resolveNativeRequest;
  const nativeRequestPosted = new Promise((resolve) => {
    resolveNativeRequest = resolve;
  });
  const nativePort = {
    disconnected: false,
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
      resolveNativeRequest(message);
    },
    disconnect() {
      this.disconnected = true;
      nativeDisconnectListener?.();
    },
    async emitNativeMessage(message) {
      await nativeMessageListener(message);
    },
  };
  const chrome = {
    runtime: {
      lastError: undefined,
      connectNative() {
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
  return { nativePort, nativeRequestPosted, runtimeMessageListener };
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

test("pageContext distinguishes papers, alphaXiv folders, and unsupported pages", () => {
  assert.deepEqual(
    pageContext("https://www.alphaxiv.org/abs/2503.15850?chatId=private", [], ""),
    { kind: "paper", id: "2503.15850", site: "alphaxiv" },
  );
  assert.deepEqual(
    pageContext(
      "https://www.alphaxiv.org/library/folders/uncertainty",
      [
        "https://www.alphaxiv.org/abs/2503.15850",
        "https://www.alphaxiv.org/abs/2401.01234",
      ],
      "Uncertainty Quantification | alphaXiv",
    ),
    {
      kind: "collection",
      title: "Uncertainty Quantification",
      urls: [
        "https://www.alphaxiv.org/abs/2503.15850",
        "https://www.alphaxiv.org/abs/2401.01234",
      ],
    },
  );
  assert.deepEqual(pageContext("https://example.com", [], "Example"), {
    kind: "unsupported",
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

test("storeTerminalJob clears stale session state for a completed EPUB success", async () => {
  const storage = inMemoryStorage({
    jobState: { state: "working", message: "Converting." },
    selectedPaper: "2401.01234",
    progress: { current: 2, total: 5 },
  });

  const job = await storeTerminalJob(
    { ok: true, message: "Sent to Kindle.", epub_path: "/tmp/paper.epub" },
    storage,
  );

  assert.deepEqual(job, {
    state: "success",
    message: "Sent to Kindle.",
    epub_path: "/tmp/paper.epub",
  });
  assert.deepEqual(storage.state, { jobState: job });
});

test("storeTerminalJob clears stale session state for a mail error with an EPUB", async () => {
  const storage = inMemoryStorage({
    jobState: { state: "working", message: "Emailing." },
    selectedPaper: "2503.15850",
  });

  const job = await storeTerminalJob(
    { ok: false, message: "Kindle delivery failed.", epub_path: "/tmp/anthology.epub" },
    storage,
  );

  assert.deepEqual(job, {
    state: "error",
    message: "Kindle delivery failed.",
    epub_path: "/tmp/anthology.epub",
  });
  assert.deepEqual(storage.state, { jobState: job });
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
  assert.deepEqual(JSON.parse(JSON.stringify(sessionStorage.state)), {
    jobState: {
      state: "error",
      message: "The EPUB was saved, but Mail could not send it.",
      epub_path: "/tmp/saved.epub",
    },
  });
});
