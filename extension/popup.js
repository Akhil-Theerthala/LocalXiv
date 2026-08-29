const form = document.querySelector("#send-form");
const email = document.querySelector("#kindle-email");
const emailError = document.querySelector("#email-error");
const deliverySettings = document.querySelector("#delivery-settings");
const settingsSummary = document.querySelector("#settings-summary");
const contextLabel = document.querySelector("#context-label");
const pageTitle = document.querySelector("#page-title");
const description = document.querySelector("#description");
const preview = document.querySelector("#paper-preview");
const previewMore = document.querySelector("#paper-preview-more");
const send = document.querySelector("#send");
const status = document.querySelector("#status");
const statusSource = document.querySelector("#status-source");
const statusState = document.querySelector("#status-state");
const statusMessage = document.querySelector("#status-message");
const manual = document.querySelector("#manual");

const {
  actionLabel,
  isAlphaXivFolderUrl,
  jobIdentity,
  normalizeKindleEmail,
  pageContext,
  parsePaperUrl,
} = XivKindle;

let activeUrl = "";
let context = { kind: "unsupported" };
let jobWorking = false;

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

async function collectAlphaXivFolder(tabId) {
  const [{ result } = { result: {} }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const root = document.querySelector("main") || document;
      const heading = root.querySelector("h1")?.textContent || document.title;
      return {
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
    item.textContent = paper.title;
    preview.append(item);
  }
  const remaining = context.papers.length - 5;
  if (remaining > 0) {
    previewMore.textContent = `+ ${remaining} more`;
    previewMore.hidden = false;
  }
}

function renderContext() {
  if (context.kind === "paper") {
    contextLabel.textContent = context.site === "alphaxiv" ? "alphaXiv paper" : "arXiv paper";
    pageTitle.textContent = "Ready to send";
    description.textContent = "Converted locally from arXiv source, then delivered through Mail.";
  } else if (context.kind === "collection") {
    contextLabel.textContent = "alphaXiv library";
    pageTitle.textContent = context.title;
    const noun = context.papers.length === 1 ? "paper" : "papers";
    description.textContent = context.overLimit
      ? `${context.papers.length} ${noun} found. The 50-paper limit prevents submission.`
      : `${context.papers.length} ${noun} will become one EPUB with a paper-only contents list.`;
  } else {
    contextLabel.textContent = "Unsupported page";
    pageTitle.textContent = isAlphaXivPage(activeUrl) ? "No papers found" : "Open a paper or library";
    description.textContent = isAlphaXivPage(activeUrl)
      ? "Open a loaded alphaXiv paper or library folder, then try again."
      : "Use an arXiv or alphaXiv abstract page, or an alphaXiv library folder.";
  }
  renderPreview();
  send.textContent = actionLabel(context);
  if (context.kind === "collection" && context.overLimit) send.textContent = "50 paper limit";
  send.disabled = jobWorking || context.kind === "unsupported" || context.overLimit;
}

function renderSettings(value) {
  const saved = normalizeKindleEmail(value);
  settingsSummary.textContent = XivKindle.settingsSummary(saved || "");
  deliverySettings.open = !saved;
}

function renderJob(job) {
  jobWorking = job?.state === "working";
  if (!job?.state || job.state === "idle") {
    status.hidden = true;
    manual.hidden = true;
    renderContext();
    return;
  }
  status.hidden = false;
  status.className = job.state;
  statusSource.hidden = !job.job_label;
  const paperCount = job.paper_count;
  statusSource.textContent = job.job_label
    ? `${job.job_label} · ${paperCount} ${paperCount === 1 ? "paper" : "papers"}`
    : "";
  statusState.textContent =
    job.state === "working" ? "Working" : job.state === "success" ? "Complete" : "Needs attention";
  statusMessage.textContent = job.message || "Working.";
  manual.hidden = !(job.state === "error" && job.epub_path);
  renderContext();
  if (jobWorking) send.textContent = "Working in background";
}

async function discoverPage(tab) {
  activeUrl = tab?.url || "";
  if (parsePaperUrl(activeUrl)) return pageContext(activeUrl, [], "");
  if (!isAlphaXivFolderUrl(activeUrl) || !tab?.id) return { kind: "unsupported" };
  const folder = await collectAlphaXivFolder(tab.id);
  return pageContext(activeUrl, folder.papers || [], folder.title || "");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  emailError.hidden = true;
  const kindleEmail = normalizeKindleEmail(email.value);
  if (!kindleEmail) {
    deliverySettings.open = true;
    emailError.textContent = "Enter an address ending in @kindle.com.";
    emailError.hidden = false;
    email.focus();
    return;
  }
  if (context.kind === "unsupported" || context.overLimit) return;

  email.value = kindleEmail;
  await chrome.storage.local.set({ kindleEmail });
  renderSettings(kindleEmail);
  const request = {
    kindle_email: kindleEmail,
    send: true,
    ...(context.kind === "collection"
      ? { urls: context.urls, collection_title: context.title }
      : { url: activeUrl }),
  };
  const identity = jobIdentity(request);
  try {
    const response = await chrome.runtime.sendMessage({ type: "start", request });
    if (!response?.ok) throw new Error(response?.message || "Could not start conversion.");
    renderJob({ state: "working", message: "Starting local converter.", ...identity });
  } catch (error) {
    renderJob({ state: "error", message: error.message || "Could not start conversion.", ...identity });
  }
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "session" && changes.jobState) renderJob(changes.jobState.newValue);
});

async function initialize() {
  const [[tab], saved, job] = await Promise.all([
    chrome.tabs.query({ active: true, currentWindow: true }),
    chrome.storage.local.get("kindleEmail"),
    chrome.storage.session.get("jobState"),
  ]);
  email.value = saved.kindleEmail || "";
  renderSettings(email.value);
  context = await discoverPage(tab);
  renderJob(job.jobState || { state: "idle" });
}

initialize().catch((error) => {
  context = { kind: "unsupported" };
  renderContext();
  renderJob({ state: "error", message: error.message || "Could not inspect this page." });
});
