const navLinks = [...document.querySelectorAll(".nav a")];
const revealItems = [...document.querySelectorAll(".reveal")];
const counters = [...document.querySelectorAll("[data-count]")];
const topbar = document.querySelector(".topbar");

const formatCount = (value) => new Intl.NumberFormat("en-US").format(value);

const animateCount = (el) => {
  const target = Number(el.dataset.count);
  if (!Number.isFinite(target)) return;

  const duration = 1200;
  const start = performance.now();
  const initial = 0;

  const tick = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(initial + (target - initial) * eased);
    el.textContent = formatCount(current);
    if (progress < 1) requestAnimationFrame(tick);
  };

  requestAnimationFrame(tick);
};

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        if (entry.target.hasAttribute("data-count")) {
          animateCount(entry.target);
          observer.unobserve(entry.target);
        }
      }
    });
  },
  { threshold: 0.18 }
);

revealItems.forEach((item) => observer.observe(item));
counters.forEach((item) => observer.observe(item));

const sectionObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;

      const id = entry.target.id;
      navLinks.forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === `#${id}`);
      });
    });
  },
  { threshold: 0.42 }
);

document.querySelectorAll("section[id]").forEach((section) => sectionObserver.observe(section));

window.addEventListener("scroll", () => {
  topbar.classList.toggle("scrolled", window.scrollY > 8);
}, { passive: true });
