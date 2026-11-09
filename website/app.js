const repository = "ChaimaaAtlagh/AJI-TSTAJI-FINAL";
const releasesUrl = `https://github.com/${repository}/releases`;
const latestUrl = `https://api.github.com/repos/${repository}/releases/latest`;

const downloadButtons = [...document.querySelectorAll(".download-button")];
const statusText = document.querySelector("#release-status");
const versionText = document.querySelector("#release-version");
const checksumLink = document.querySelector("#checksum-link");
const releaseIndicator = document.querySelector(".release-indicator");

function setReleaseUnavailable(message) {
  for (const button of downloadButtons) {
    button.href = releasesUrl;
    button.setAttribute("aria-label", "Voir les versions AJI TSTAJI sur GitHub");
    button.querySelector(".download-label").textContent = "Voir les versions Windows";
  }
  statusText.textContent = message;
  versionText.textContent = "À consulter sur GitHub";
  checksumLink.href = releasesUrl;
  checksumLink.textContent = "Toutes les versions GitHub ↗";
  releaseIndicator.classList.add("is-pending");
}

async function loadLatestRelease() {
  try {
    const response = await fetch(latestUrl, {
      headers: { Accept: "application/vnd.github+json" },
      signal: AbortSignal.timeout(7000),
    });
    if (response.status === 404) {
      setReleaseUnavailable("Aucune version Windows publique n’est disponible pour le moment.");
      return;
    }
    if (!response.ok) throw new Error("Release API unavailable");

    const release = await response.json();
    const setup = release.assets?.find((asset) => asset.name === "AJI_TSTAJI_Setup.exe");
    if (!setup) throw new Error("Windows installer not found");

    const checksum = release.assets.find((asset) => asset.name === "AJI_TSTAJI_Setup.exe.sha256");
    const displayVersion = release.tag_name || "Version récente";
    for (const button of downloadButtons) {
      button.href = setup.browser_download_url;
      button.setAttribute("aria-label", `Télécharger AJI TSTAJI pour Windows, ${displayVersion}`);
      button.querySelector(".download-label").textContent = "Télécharger pour Windows";
    }
    statusText.textContent = `Version ${displayVersion} · Installateur Windows prêt`;
    versionText.textContent = displayVersion;
    releaseIndicator.classList.remove("is-pending");
    releaseIndicator.classList.add("is-live");

    if (checksum) {
      checksumLink.href = checksum.browser_download_url;
      checksumLink.setAttribute("download", "AJI_TSTAJI_Setup.exe.sha256");
    } else {
      checksumLink.href = release.html_url || releasesUrl;
      checksumLink.textContent = "Voir la publication GitHub ↗";
    }
  } catch {
    setReleaseUnavailable("Impossible de charger la version récente. Consultez les versions GitHub.");
  }
}

const menuButton = document.querySelector(".menu-toggle");
const navLinks = document.querySelector("#nav-links");
menuButton.addEventListener("click", () => {
  const isExpanded = menuButton.getAttribute("aria-expanded") === "true";
  menuButton.setAttribute("aria-expanded", String(!isExpanded));
  menuButton.setAttribute("aria-label", isExpanded ? "Ouvrir le menu" : "Fermer le menu");
  navLinks.classList.toggle("is-open", !isExpanded);
});
navLinks.addEventListener("click", (event) => {
  if (event.target.closest("a")) {
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "Ouvrir le menu");
    navLinks.classList.remove("is-open");
  }
});

loadLatestRelease();
