/* One additional item; no interception of existing admin navigation. */
(() => {
  if (document.getElementById("swipiesPosthogLink")) return;
  const desktop = document.querySelector(".sidebar-nav"),
    mobile = document.querySelector(".mobile-nav");
  if (!desktop) return;
  const link = document.createElement("a");
  link.id = "swipiesPosthogLink";
  link.href = "/admin/posthog";
  link.title = "PostHog";
  link.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 20h16M6 16V9m6 7V4m6 12v-5"/></svg><span>PostHog</span>';
  const media = matchMedia("(max-width:768px)");
  const place = () => {
    link.className = media.matches && mobile ? "mobile-nav-item" : "nav-item";
    (media.matches && mobile ? mobile : desktop).appendChild(link);
  };
  place();
  media.addEventListener("change", place);
  link.addEventListener("click", async (event) => {
    event.preventDefault();
    const token = localStorage.getItem("swipies_admin_token");
    if (!token) {
      location.assign("/admin.html");
      return;
    }
    try {
      const response = await fetch("/api/admin/posthog/open", {
        method: "POST",
        headers: { Authorization: "Bearer " + token },
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Войдите в админку повторно.");
      location.assign("/admin/posthog");
    } catch {
      if (typeof window.showToast === "function")
        window.showToast(
          "PostHog",
          "Не удалось открыть страницу. Проверьте вход и подключение.",
          "error",
        );
    }
  });
})();
