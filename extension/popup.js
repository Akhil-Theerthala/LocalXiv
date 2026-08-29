const form = document.querySelector("#send-form");
const email = document.querySelector("#kindle-email");
const emailError = document.querySelector("#email-error");
const deliverySettings = document.querySelector("#delivery-settings");
const settingsSummary = document.querySelector("#settings-summary");
const settingsAction = document.querySelector("#settings-action");
const contextLabel = document.querySelector("#context-label");
const pageTitle = document.querySelector("#page-title");
const paperId = document.querySelector("#paper-id");
const description = document.querySelector("#description");
const preview = document.querySelector("#paper-preview");
const previewMore = document.querySelector("#paper-preview-more");
const chronologyRetry = document.querySelector("#chronology-retry");
const send = document.querySelector("#send");
const status = document.querySelector("#status");
const statusSource = document.querySelector("#status-source");
const statusState = document.querySelector("#status-state");
const statusMessage = document.querySelector("#status-message");
const statusProgressWrap = document.querySelector("#status-progress-wrap");
const statusProgress = document.querySelector("#status-progress");
const statusProgressText = document.querySelector("#status-progress-text");
const manual = document.querySelector("#manual");

const {
  actionLabel,
  isAlphaXivFolderUrl,
  jobIdentity,
  normalizeKindleEmail,
  pageContext,
  parsePaperUrl,
} = XivKindle;
const { resolveInitialSubmissionOrder } = XivChronology;

let activeUrl = "";
let context = { kind: "unsupported" };
let currentJob = { state: "idle" };
let initializing = false;
let jobChangedDuringInitialization = false;
let jobWorking = false;
let jobRevision = 0;
let chronologyRevision = 0;
let chronologyBusy = false;
let collectionSource = null;
let inspectedTabId = null;

function isAlphaXivPage(value) {
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      (url.hostname === "alphaxiv.org" || url.hostname === "www.alphaxiv.org")
    );
  } catch {
    return false;
  }
}

function canSubmitContext() {
  return (
    !jobWorking &&
    (
      context.kind === "paper" ||
      (
        context.kind === "collection" &&
        !context.overLimit &&
        context.chronologyState === "ready"
      )
    )
  );
}

async function collectAlphaXivFolder(tabId) {
  const [{ result } = { result: {} }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const root = document.querySelector("main") || document;
      const heading = root.querySelector("h1")?.textContent || document.title;
      return {
        url: location.href,
        title: heading,
        papers: [...root.querySelectorAll("a[href]")].map((anchor) => ({
          url: anchor.href,
          title: anchor.textContent,
        })),
      };
    },
  });
  return result || { title: "", papers: [] };
}

function renderPreview() {
  preview.replaceChildren();
  preview.hidden = context.kind !== "collection";
  previewMore.hidden = true;
  if (context.kind !== "collection") return;
  for (const paper of context.papers.slice(0, 5)) {
    const item = document.createElement("li");
    if (paper.initialSubmittedDate) {
      item.className = "preview-dated";
      const title = document.createElement("span");
      title.className = "preview-title";
      title.textContent = paper.title;
      const meta = document.createElement("span");
      meta.className = "preview-meta";
      meta.textContent = `${paper.initialSubmittedDate} · arXiv ${paper.id}`;
      item.append(title, meta);
    } else {
      item.textContent = paper.title;
    }
    preview.append(item);
  }
  const remaining = context.papers.length - 5;
  if (remaining > 0) {
    previewMore.textContent = `+ ${remaining} more`;
    previewMore.hidden = false;
  }
}

function renderContext() {
  chronologyRetry.hidden = true;
  chronologyRetry.disabled = chronologyBusy;
  if (context.kind === "paper") {
    contextLabel.textContent = context.site === "alphaxiv" ? "alphaXiv paper" : "arXiv paper";
    pageTitle.textContent = "Ready to send";
    paperId.textContent = `arXiv ${context.id}`;
    paperId.hidden = false;
    description.textContent = "Converted locally from arXiv source, then delivered through Mail.";
  } else if (context.kind === "collection") {
    contextLabel.textContent = "alphaXiv library";
    pageTitle.textContent = context.title;
    paperId.hidden = true;
    const noun = context.papers.length === 1 ? "paper" : "papers";
    if (context.overLimit) {
      description.textContent = `${context.papers.length} ${noun} found. The 50-paper limit prevents submission.`;
    } else if (context.chronologyState === "loading") {
      description.textContent = `Checking initial arXiv dates for ${context.papers.length} ${noun}.`;
    } else if (context.chronologyState === "ready") {
      description.textContent = `${context.papers.length} papers ordered oldest to newest by first arXiv submission.`;
    } else if (context.chronologyState === "error") {
      description.textContent = "Initial arXiv dates could not be verified. Retry dates to enable submission.";
      chronologyRetry.hidden = false;
    } else {
      description.textContent = `${context.papers.length} ${noun} will become one EPUB with a paper-only contents list.`;
    }
  } else if (context.kind === "inspection-error") {
    contextLabel.textContent = "Could not inspect page";
    pageTitle.textContent = "Try this page again";
    paperId.hidden = true;
    description.textContent = "The page could not be inspected. Any existing conversion status is unchanged.";
  } else {
    contextLabel.textContent = "Unsupported page";
    pageTitle.textContent = isAlphaXivPage(activeUrl) ? "No papers found" : "Open a paper or library";
    paperId.hidden = true;
    description.textContent = isAlphaXivPage(activeUrl)
      ? "Open a loaded alphaXiv paper or library folder, then try again."
      : "Use an arXiv or alphaXiv abstract page, or an alphaXiv library folder.";
  }
  renderPreview();
  send.textContent = actionLabel(context);
  if (context.kind === "collection" && context.overLimit) {
    send.textContent = "50 paper limit";
  } else if (context.kind === "collection" && context.chronologyState === "loading") {
    send.textContent = "Checking submission dates";
  } else if (context.kind === "collection" && context.chronologyState === "error") {
    send.textContent = "Dates required";
  }
  if (jobWorking) send.textContent = "Working in background";
  send.disabled = !canSubmitContext();
}

function renderSettings(value) {
  const saved = normalizeKindleEmail(value);
  settingsSummary.textContent = XivKindle.settingsSummary(saved || "");
  settingsAction.textContent = saved ? "Edit" : "Add";
  deliverySettings.open = !saved;
}

function renderJob(job) {
  currentJob = job || { state: "idle" };
  jobWorking = currentJob.state === "working";
  statusProgressWrap.hidden = true;
  if (!currentJob.state || currentJob.state === "idle") {
    status.hidden = true;
    manual.hidden = true;
    renderContext();
    return;
  }
  status.hidden = false;
  status.className = currentJob.state;
  const label = currentJob.job_label || "";
  const paperCount = currentJob.paper_count;
  statusSource.textContent = label && Number.isInteger(paperCount) && paperCount >= 0
    ? `${label} · ${paperCount} ${paperCount === 1 ? "paper" : "papers"}`
    : label;
  statusSource.hidden = !statusSource.textContent;
  statusState.textContent =
    currentJob.state === "working" ? "Working" : currentJob.state === "success" ? "Complete" : "Needs attention";
  statusMessage.textContent = currentJob.message || "Working.";
  const { current, total } = currentJob;
  if (
    currentJob.state === "working" &&
    currentJob.paper_count > 1 &&
    Number.isInteger(current) &&
    Number.isInteger(total) &&
    current >= 0 &&
    total > 0 &&
    current <= total
  ) {
    const percent = Math.round((current / total) * 100);
    statusProgressWrap.hidden = false;
    statusProgress.max = total;
    statusProgress.value = current;
    statusProgressText.textContent = `${current} / ${total} · ${percent}%`;
  }
  manual.hidden = !(currentJob.state === "error" && currentJob.epub_path);
  renderContext();
}

async function discoverPage(tab) {
  activeUrl = tab?.url || "";
  if (parsePaperUrl(activeUrl)) return pageContext(activeUrl, [], "");
  if (!isAlphaXivFolderUrl(activeUrl) || !tab?.id) return { kind: "unsupported" };
  const folder = await collectAlphaXivFolder(tab.id);
  activeUrl = folder.url || "";
  return pageContext(activeUrl, folder.papers || [], folder.title || "");
}

function collectionSnapshot(discovered) {
  const papers = Object.freeze(discovered.papers.map((paper) => Object.freeze({ ...paper })));
  return Object.freeze({
    ...discovered,
    inspectedUrl: discovered.inspectedUrl || activeUrl,
    papers,
    urls: Object.freeze(papers.map((paper) => paper.url)),
  });
}

async function prepareCollectionChronology(discovered, { bypassCache = false } = {}) {
  const revision = ++chronologyRevision;
  const source = collectionSnapshot(discovered);
  collectionSource = source;
  chronologyBusy = true;
  context = { ...source, chronologyState: "loading" };
  renderContext();
  try {
    const papers = await resolveInitialSubmissionOrder(source.papers, {
      fetchImpl: fetch,
      DOMParserImpl: DOMParser,
      sessionStorage: chrome.storage.session,
      bypassCache,
    });
    if (revision !== chronologyRevision) return;
    const currentTab = await chrome.tabs.get(inspectedTabId);
    if (revision !== chronologyRevision || currentTab?.url !== source.inspectedUrl) return;
    context = {
      ...source,
      papers,
      urls: papers.map((paper) => paper.url),
      chronologyState: "ready",
    };
  } catch {
    if (revision !== chronologyRevision) return;
    context = { ...source, chronologyState: "error" };
  } finally {
    if (revision === chronologyRevision) {
      chronologyBusy = false;
      renderContext();
    }
  }
}

chronologyRetry.addEventListener("click", async () => {
  if (!collectionSource) return;
  await prepareCollectionChronology(collectionSource, { bypassCache: true });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  email.removeAttribute("aria-invalid");
  if (!canSubmitContext()) return;
  emailError.hidden = true;
  const kindleEmail = normalizeKindleEmail(email.value);
  if (!kindleEmail) {
    deliverySettings.open = true;
    emailError.textContent = "Enter an address ending in @kindle.com.";
    emailError.hidden = false;
    email.setAttribute("aria-invalid", "true");
    email.focus();
    return;
  }
  email.value = kindleEmail;
  const request = {
    kindle_email: kindleEmail,
    send: true,
    ...(context.kind === "collection"
      ? { urls: context.urls, collection_title: context.title }
      : { url: activeUrl }),
  };
  const identity = jobIdentity(request);
  const submissionRevision = jobRevision;
  renderJob({ state: "working", message: "Starting local converter.", ...identity });
  try {
    await chrome.storage.local.set({ kindleEmail });
    renderSettings(kindleEmail);
    const response = await chrome.runtime.sendMessage({ type: "start", request });
    if (!response?.ok) throw new Error(response?.message || "Could not start conversion.");
  } catch (error) {
    if (jobRevision === submissionRevision) {
      renderJob({ state: "error", message: error.message || "Could not start conversion.", ...identity });
    }
  }
});

email.addEventListener("input", () => {
  if (!normalizeKindleEmail(email.value)) return;
  emailError.textContent = "";
  emailError.hidden = true;
  email.removeAttribute("aria-invalid");
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "session" && changes.jobState) {
    jobRevision += 1;
    if (initializing) jobChangedDuringInitialization = true;
    renderJob(changes.jobState.newValue);
  }
});

async function initialize() {
  initializing = true;
  try {
    const [[tab], saved, job] = await Promise.all([
      chrome.tabs.query({ active: true, currentWindow: true }),
      chrome.storage.local.get("kindleEmail"),
      chrome.storage.session.get("jobState"),
    ]);
    email.value = saved.kindleEmail || "";
    inspectedTabId = tab?.id || null;
    renderSettings(email.value);
    if (!jobChangedDuringInitialization) renderJob(job.jobState || { state: "idle" });
    try {
      const discovered = await discoverPage(tab);
      if (discovered.kind === "collection" && !discovered.overLimit) {
        await prepareCollectionChronology(discovered);
      } else {
        context = discovered;
        renderContext();
      }
    } catch {
      context = { kind: "inspection-error" };
      renderContext();
    }
  } finally {
    initializing = false;
  }
}

initialize().catch(() => {
  context = { kind: "inspection-error" };
  renderContext();
});
