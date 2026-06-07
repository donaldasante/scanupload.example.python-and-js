import "@scanupload/qr-code-generator-vanilla/dist/index.css";
import "./scanupload-override.css";
import "./style.css";
import { QrCodeGeneratorElement } from "@scanupload/qr-code-generator-vanilla";

const form = document.querySelector("#example-form");
const widgetContainer = document.querySelector("#widget-container");
const widgetError = document.querySelector("#widget-error");
const downloadButton = document.querySelector("#download-button");
const downloadError = document.querySelector("#download-error");

const controls = {
  showLogo: document.querySelector("#show-logo"),
  clickReload: document.querySelector("#click-reload"),
  showHeader: document.querySelector("#show-header"),
  headerText: document.querySelector("#header-text"),
};

let widget;
let rebuilding = false;

function getSelectedFilePreviewMode() {
  const selected = document.querySelector(
    "input[name='file-preview-mode']:checked",
  );
  return selected?.value || "list";
}

function getSelectedSize() {
  const selected = document.querySelector("input[name='qr-size']:checked");
  return selected?.value || "large";
}

function getCurrentOptions() {
  return {
    sessionUrl: "/scanupload-api/session",
    refreshTokenUrl: "/scanupload-api/token",
    showHeader: controls.showHeader.checked,
    header: controls.headerText.value,
    size: getSelectedSize(),
    showLogo: controls.showLogo.checked,
    clickQrCodeToReload: controls.clickReload.checked,
    filePreviewMode: getSelectedFilePreviewMode(),
    injectStyles: false,
  };
}

async function updateWidgetOptions() {
  if (!widget) {
    return;
  }

  // _buildDom() (called internally by setOptions) doesn't reset _prevState
  // before its _render() call, so the diff sees no changes and the freshly
  // built loading overlay is never hidden.  Nulling it here forces a full
  // repaint once _buildDom triggers _render().
  widget._prevState = null;
  await widget.setOptions(getCurrentOptions());
}

async function buildOrRebuildWidget() {
  if (rebuilding) {
    return;
  }

  rebuilding = true;
  widgetError.textContent = "";

  try {
    if (widget) {
      widget.dispose();
      widget = undefined;
    }

    widgetContainer.innerHTML = "";

    const initialOptions = getCurrentOptions();

    widget = new QrCodeGeneratorElement({
      container: widgetContainer,
      ...initialOptions,
    });

    await widget.start();
  } catch {
    widgetError.textContent =
      "Unable to start QR widget. Check API availability and try again.";
  } finally {
    rebuilding = false;
  }
}

function getLastSessionId() {
  try {
    const raw = localStorage.getItem("qrcode-last-session-ids");
    const ids = raw ? JSON.parse(raw) : [];
    return Array.isArray(ids) && ids.length > 0 ? ids[0] : null;
  } catch {
    return null;
  }
}

async function handleDownload(event) {
  event.preventDefault();
  downloadError.textContent = "";

  const sessionId = getLastSessionId();
  if (!sessionId) {
    downloadError.textContent =
      "No active session found. Please scan the QR code first.";
    return;
  }

  downloadButton.disabled = true;
  downloadButton.textContent = "Downloading...";

  try {
    const response = await fetch(
      `/api/download-file/${encodeURIComponent(sessionId)}`,
    );
    if (!response.ok) {
      const json = await response.json().catch(() => ({}));
      downloadError.textContent = json.error || "Download failed.";
      return;
    }

    const disposition = response.headers.get("Content-Disposition");
    let fileName = "download";
    if (disposition) {
      const match =
        disposition.match(/filename\*=UTF-8''([^;]+)/i) ||
        disposition.match(/filename="?([^";]+)"?/i);
      if (match) {
        fileName = decodeURIComponent(match[1]);
      }
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch {
    downloadError.textContent = "Download failed. Please try again.";
  } finally {
    downloadButton.disabled = false;
    downloadButton.textContent = "Download Files";
  }
}

form.addEventListener("submit", handleDownload);

Object.values(controls).forEach((control) => {
  const eventName =
    control.tagName === "INPUT" && control.type === "text" ? "input" : "change";
  control.addEventListener(eventName, () => {
    void updateWidgetOptions();
  });
});

document
  .querySelectorAll("input[name='file-preview-mode'], input[name='qr-size']")
  .forEach((radio) => {
    radio.addEventListener("change", () => {
      void updateWidgetOptions();
    });
  });

buildOrRebuildWidget();
