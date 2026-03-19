// test.js (полная исправленная версия)
import { projectsData } from "./home-text.js";

gsap.registerPlugin(CustomEase);
CustomEase.create("hop", "0.9, 0, 0.1, 1");

document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const introScreenEl = document.querySelector('.intro-screen');
  const containerEl = document.querySelector('.container');
  const btnToH = document.querySelector('.scroll-toggle--bottom');
  const btnToTop = document.querySelector('.scroll-toggle--top');

  // состояние
  let introFinished = false;
  let isInHScroll = false;

  // изначально: интро идёт, кнопки/контейнер недоступны
  body.classList.remove('intro-ready');
  body.classList.remove('in-hscroll');
  if (btnToH) btnToH.disabled = true;
  if (btnToTop) btnToTop.disabled = true;
  if (containerEl) {
    containerEl.style.pointerEvents = 'none';
    containerEl.setAttribute('aria-hidden', 'true');
  }

  // полностью отключаем дефолтный вертикальный скролл колесом/тачем
  const blockDefaultScroll = (e) => {
    if (e.cancelable) e.preventDefault();
  };
  window.addEventListener('wheel', blockDefaultScroll, { passive: false });
  window.addEventListener('touchmove', blockDefaultScroll, { passive: false });

  // блокируем клавиши, которые могут прокручивать страницу
  window.addEventListener('keydown', (e) => {
    const k = e.key;
    const shouldBlock =
      k === ' ' || k === 'Spacebar' ||
      k === 'PageDown' || k === 'PageUp' ||
      k === 'Home' || k === 'End' ||
      k === 'ArrowDown' || k === 'ArrowUp';
    if (shouldBlock && e.cancelable) e.preventDefault();
  });

  const smoothScrollToY = (targetY, duration = 0.9) => {
    const startY = window.scrollY || window.pageYOffset || 0;
    const obj = { t: 0 };
    return new Promise((resolve) => {
      gsap.to(obj, {
        t: 1,
        duration,
        ease: 'power2.inOut',
        onUpdate: () => {
          const y = startY + (targetY - startY) * obj.t;
          window.scrollTo(0, y);
        },
        onComplete: resolve,
      });
    });
  };

  const markIntroFinished = () => {
    if (introFinished) return;
    introFinished = true;
    body.classList.add('intro-ready');
    if (btnToH) btnToH.disabled = false;
    if (containerEl) {
      containerEl.style.pointerEvents = 'auto';
      containerEl.removeAttribute('aria-hidden');
    }
  };

  const enterHScroll = async () => {
    if (!introFinished || !containerEl) return;
    if (isInHScroll) return;
    isInHScroll = true;
    btnToH?.blur();
    await smoothScrollToY(containerEl.offsetTop, 1.0);
    body.classList.add('in-hscroll');        // показывает progress/counter + верхнюю кнопку
    if (btnToTop) btnToTop.disabled = false;
  };

  const leaveHScroll = async () => {
    if (!introFinished) return;
    if (!isInHScroll) return;
    isInHScroll = false;
    body.classList.remove('in-hscroll');     // скрывает progress/counter + верхнюю кнопку
    btnToTop?.blur();
    await smoothScrollToY(0, 1.0);
    if (btnToTop) btnToTop.disabled = true;
  };

  btnToH?.addEventListener('click', enterHScroll);
  btnToTop?.addEventListener('click', leaveHScroll);






const scrollerEl = document.querySelector('.scroller');
const sectionMap = {
  about: '.about',
  faq: '.faq',
  contacts: '.contacts',
};

function getHorizontalOffsetToSection(sectionEl) {
  // Смещение внутри scroller по X
  // sectionEl.offsetLeft работает, если секции реально лежат в потоке по X (flex/inline)
  return sectionEl.offsetLeft || 0;
}

async function goToHorizontalSection(key) {
  const selector = sectionMap[key];
  if (!selector) return;

  const sectionEl = document.querySelector(selector);
  if (!sectionEl || !containerEl) return;

  // 1) Сначала перейти к горизонтальному контейнеру (как по вашей кнопке)
  await enterHScroll();

  // 2) Затем прокрутить внутри горизонтали к нужной секции
  // Вариант A: если scroller реально скроллится (scrollLeft)
  if (scrollerEl && scrollerEl.scrollWidth > scrollerEl.clientWidth) {
    const targetX = getHorizontalOffsetToSection(sectionEl);
    const startX = scrollerEl.scrollLeft;

    const obj = { t: 0 };
    gsap.to(obj, {
      t: 1,
      duration: 0.9,
      ease: 'power2.inOut',
      onUpdate: () => {
        scrollerEl.scrollLeft = startX + (targetX - startX) * obj.t;
      },
    });
    return;
  }

  // Вариант B: fallback (если у вас не scrollLeft, а другой механизм)
  sectionEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
}

document.querySelectorAll('a.nav-link[data-target]').forEach((a) => {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    const key = a.dataset.target;
    goToHorizontalSection(key);
  });
});







  async function copyTextToClipboard(text) {
  // 1) Современный API (работает на https/localhost)
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) {
    // игнорируем и пробуем fallback
  }

  // 2) Fallback для file:// и старых контекстов
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, ta.value.length);

    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch (e) {
    return false;
  }
}

document.querySelectorAll('.copy-email').forEach((el) => {
  let timer = null;

  el.addEventListener('click', async () => {
    const email = el.dataset.copy || el.textContent.trim();
    const ok = await copyTextToClipboard(email);

    // показываем "Скопировано" только если реально скопировали
    if (ok) {
      el.classList.add('is-copied');
      clearTimeout(timer);
      timer = setTimeout(() => el.classList.remove('is-copied'), 1200);
    }
  });
});







  // =========================
  // Cursor hint (следует за курсором + auto hide)
  // =========================
  const cursorHint = document.querySelector(".cursor-hint");
  document.body.classList.add("show-cursor-hint");

  const moveHint = (e) => {
    if (!cursorHint) return;
    cursorHint.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
  };

  window.addEventListener("mousemove", moveHint);

  const hideCursorHint = () => {
    document.body.classList.remove("show-cursor-hint");
    window.removeEventListener("mousemove", moveHint);
  };

  // =========================
  // Intro DOM
  // =========================
  const projectsContainer = document.querySelector(".projects");
  const locationsContainer = document.querySelector(".locations");

  const gridItems = gsap.utils.toArray(".image-grid .img");
  const heroItem = document.querySelector(".image-grid .img.hero-img");
  const nonHeroItems = gridItems.filter((el) => el !== heroItem);

  const introCopy = new SplitType(".intro-copy h3", { type: "words", absolute: false });
  const titleHeading = new SplitType(".title h1", { type: "words", absolute: false });

  const allImageSources = Array.from({ length: 9 }, (_, i) => `/static/images/img${i + 1}.jpg`);

  const FINAL_HERO_SRC = "/static/images/img10.jpg";




  // =========================
  // Skip state
  // =========================
  let didSkip = false;
  let rotationTweens = [];
  let rotationTimeout = null;
  let masterTL = null;

  const getRandomImageSet = () => {
    const shuffled = [...allImageSources].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, 9);
  };

  const stopRotation = () => {
    rotationTweens.forEach((t) => t.kill());
    rotationTweens = [];
    if (rotationTimeout) clearTimeout(rotationTimeout);
    rotationTimeout = null;
  };

  const applyFinalState = () => {
    const overlay = document.querySelector(".overlay");

    // 🔴 ВАЖНО: отключаем перехват событий
    overlay?.classList.add("is-hidden");

    gsap.set(".overlay", { opacity: 0, pointerEvents: "none" });
    gsap.set(".loader", { opacity: 0 });

    gsap.set("nav", { y: "0%" });
    gsap.set(".banner-img", { scale: 1 });

    gsap.set(".image-grid .img", {
      clipPath: "polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%)",
    });
    gsap.set(nonHeroItems, {
      clipPath: "polygon(0% 0%, 100% 0%, 100% 0%, 0% 0%)",
    });

    gsap.set(".hero-img", {
      y: 120,
      scale: 3,
      clipPath: "polygon(20% 10%, 80% 10%, 80% 90%, 20% 90%)",
    });
    gsap.set(".hero-img img", { scale: 1 });

    gsap.set(".banner-img-1", { left: "40%", rotate: -20, scale: 1 });
    gsap.set(".banner-img-2", { left: "60%", rotate: 20, scale: 1 });

    const heroImg = heroItem?.querySelector("img");
    if (heroImg) heroImg.src = FINAL_HERO_SRC;

    gsap.set(titleHeading.words, { y: "0%" });
    gsap.set(introCopy.words, { y: "0%" });
  };

  const skipAll = () => {
    if (didSkip) return;
    didSkip = true;

    stopRotation();
    gsap.killTweensOf("*");

    if (masterTL) {
      masterTL.pause(0);
      masterTL.progress(1);
    }

    applyFinalState();
    hideCursorHint();
    markIntroFinished();

  };

  window.addEventListener("pointerdown", skipAll, { once: true });

  // =========================
  // Dynamic content
  // =========================
  function initDynamicContent() {
    projectsContainer?.querySelectorAll(".project-item").forEach((n) => n.remove());
    locationsContainer?.querySelectorAll(".location-item").forEach((n) => n.remove());

    projectsData.forEach((project) => {
      const projectItem = document.createElement("div");
      projectItem.className = "project-item";

      const masters = document.createElement("p");
      masters.textContent = project.masters;

      const studios = document.createElement("p");
      studios.textContent = project.studios;

      projectItem.appendChild(masters);
      projectItem.appendChild(studios);
      projectsContainer?.appendChild(projectItem);
    });

    projectsData.forEach((project) => {
      const locationItem = document.createElement("div");
      locationItem.className = "location-item";

      const service = document.createElement("p");
      service.textContent = project.services;

      locationItem.appendChild(service);
      locationsContainer?.appendChild(locationItem);
    });
  }

  // =========================
  // Image rotation
  // =========================
  function startImageRotation() {
    const totalCycles = 20;

    for (let cycle = 0; cycle < totalCycles; cycle++) {
      const randomImages = getRandomImageSet();

      const t = gsap.to({}, {
        duration: 0,
        delay: cycle * 0.15,
        onComplete: () => {
          if (didSkip) return;

          gridItems.forEach((cell, index) => {
            const imgEl = cell.querySelector("img");
            if (!imgEl) return;

            if (cycle === totalCycles - 1 && cell === heroItem) {
              imgEl.src = FINAL_HERO_SRC;
              gsap.set(".hero-img img", { scale: 1 });
            } else {
              imgEl.src = randomImages[index] ?? randomImages[0];
            }
          });
        },
      });

      rotationTweens.push(t);
    }
  }

  // =========================
  // Initial states
  // =========================
  function setupInitialStates() {
    gsap.set("nav", { y: "-125%" });
    gsap.set(introCopy.words, { y: "110%" });
    gsap.set(titleHeading.words, { y: "110%" });

    gsap.set(".image-grid .img", {
      clipPath: "polygon(0% 0%, 100% 0%, 100% 0%, 0% 0%)",
    });

    gsap.set(".hero-img", { transformOrigin: "50% 50%" });
    gsap.set(".hero-img img", { transformOrigin: "50% 50%" });
  }

  // =========================
  // Intro timelines
  // =========================
  function createIntroTimelines() {
    const overlayTL = gsap.timeline();
    const imagesTL = gsap.timeline();
    const textTL = gsap.timeline({
      onComplete: () => {
        if (!didSkip) hideCursorHint();
        markIntroFinished();
      },
    });

    masterTL = gsap.timeline();
    masterTL.add(overlayTL).add(imagesTL, "<").add(textTL, "<");

    overlayTL.to(".logo-line-1", {
      backgroundPosition: "0% 0%",
      color: "#fff",
      duration: 1,
      ease: "none",
      delay: 0.5,
      onComplete: () => {
        if (didSkip) return;
        gsap.to(".logo-line-2", {
          backgroundPosition: "0% 0%",
          color: "#fff",
          duration: 1,
          ease: "none",
        });
      },
    });

    overlayTL.to([".projects-header", ".project-item"], {
      opacity: 1,
      duration: 0.15,
      stagger: 0.075,
      delay: 1,
    });

    overlayTL.to([".locations-header", ".location-item"], {
      opacity: 1,
      duration: 0.15,
      stagger: 0.075,
    }, "<");

    overlayTL.to(".project-item", { color: "#fff", duration: 0.15, stagger: 0.075 });
    overlayTL.to(".location-item", { color: "#fff", duration: 0.15, stagger: 0.075 }, "<");

    overlayTL.to([".projects-header", ".project-item"], {
      opacity: 0,
      duration: 0.15,
      stagger: 0.075,
    });

    overlayTL.to([".locations-header", ".location-item"], {
      opacity: 0,
      duration: 0.15,
      stagger: 0.075,
    }, "<");

    overlayTL.to(".overlay", {
      opacity: 0,
      duration: 0.5,
      delay: 1.5,
      onComplete: () => gsap.set(".overlay", { pointerEvents: "none" }),
    });

    imagesTL.to(".image-grid .img", {
      clipPath: "polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%)",
      duration: 1,
      delay: 2.5,
      stagger: 0.05,
      ease: "hop",
      onStart: () => {
        rotationTimeout = setTimeout(() => {
          if (didSkip) return;
          startImageRotation();
          gsap.to(".loader", { opacity: 0, duration: 0.3 });
        }, 1000);
      },
    });

    imagesTL.to(nonHeroItems, {
      clipPath: "polygon(0% 0%, 100% 0%, 100% 0%, 0% 0%)",
      duration: 1,
      delay: 2.5,
      stagger: 0.05,
      ease: "hop",
    });

    imagesTL.to(".hero-img", { y: 120, duration: 1, ease: "hop" });

    imagesTL.to(".hero-img", {
      scale: 3,
      clipPath: "polygon(20% 10%, 80% 10%, 80% 90%, 20% 90%)",
      duration: 1.5,
      ease: "hop",
      onStart: () => {
        if (didSkip) return;

        const heroImg = heroItem?.querySelector("img");
        if (heroImg) heroImg.src = FINAL_HERO_SRC;
        stopRotation();

        gsap.to(".hero-img img", { scale: 1, duration: 1.5, ease: "hop" });
        gsap.to(".banner-img", { scale: 1, delay: 0.5, duration: 0.5 });
        gsap.to("nav", { y: "0%", delay: 0.25, duration: 1, ease: "hop" });
      },
    });

    imagesTL.to(".banner-img-1", {
      left: "40%",
      rotate: -20,
      duration: 1.5,
      delay: 0.5,
      ease: "hop",
    }, "<");

    imagesTL.to(".banner-img-2", {
      left: "60%",
      rotate: 20,
      duration: 1.5,
      ease: "hop",
    }, "<");

    textTL.to(titleHeading.words, {
      y: "0%",
      duration: 1,
      stagger: 0.1,
      delay: 9.5,
      ease: "power3.out",
    });

    textTL.to(introCopy.words, {
      y: "0%",
      duration: 1,
      stagger: 0.1,
      delay: 0.25,
      ease: "power3.out",
    }, "<");
  }

  // =========================
  // Horizontal scroll (container)
  // =========================
  const container = document.querySelector(".container");
  const scroller = document.querySelector(".scroller");
  const progressCounter = document.querySelector(".progres-counter h1");
  const progressBar = document.querySelector(".progress-bar");

  // если контейнера нет — просто запускаем интро
  if (!container || !scroller || !progressCounter || !progressBar) {
    initDynamicContent();
    setupInitialStates();
    createIntroTimelines();
    return;
  }

  // ВАЖНО: блокируем дефолтный скролл ТОЛЬКО когда курсор над container
  let isOverContainer = false;
  container.addEventListener("pointerenter", () => (isOverContainer = true));
  container.addEventListener("pointerleave", () => (isOverContainer = false));

  const smoothFactor = 0.08;
  const touchSensitivity = 2.2;
  const bufferSize = 2;

  let targetScrollX = 0;
  let currentScrollX = 0;
  let isAnimatingScroll = false;

  let currentProgressScale = 0;
  let targetProgressScale = 0;
  let lastPercentage = 0;

  let isTouchDown = false;
  let lastTouchX = 0;
  let touchVelocity = 0;
  let lastTouchTime = 0;

  const lerp = (a, b, t) => a + (b - a) * t;

  function setupScroll() {
    scroller.querySelectorAll(".clone-section").forEach((n) => n.remove());

    const originals = Array.from(scroller.querySelectorAll("section:not(.clone-section)"));
    if (originals.length === 0) return 0;

    let sequenceWidth = 0;
    originals.forEach((s) => (sequenceWidth += s.getBoundingClientRect().width));

    for (let i = -bufferSize; i < 0; i++) {
      originals.forEach((sec, idx) => {
        const clone = sec.cloneNode(true);
        clone.classList.add("clone-section");
        clone.dataset.cloneIndex = `${i}-${idx}`;
        scroller.appendChild(clone);
      });
    }

    for (let i = 1; i <= bufferSize; i++) {
      originals.forEach((sec, idx) => {
        const clone = sec.cloneNode(true);
        clone.classList.add("clone-section");
        clone.dataset.cloneIndex = `${i}-${idx}`;
        scroller.appendChild(clone);
      });
    }

    scroller.style.width = `${sequenceWidth * (1 + bufferSize * 2)}px`;

    targetScrollX = sequenceWidth * bufferSize;
    currentScrollX = targetScrollX;
    scroller.style.transform = `translateX(-${currentScrollX}px)`;

    return sequenceWidth;
  }

  function checkBoundaryAndReset(sequenceWidth) {
    const min = sequenceWidth * (bufferSize - 0.5);
    const max = sequenceWidth * (bufferSize + 0.5);

    if (currentScrollX > max) {
      targetScrollX -= sequenceWidth;
      currentScrollX -= sequenceWidth;
      scroller.style.transform = `translateX(-${currentScrollX}px)`;
      return true;
    }

    if (currentScrollX < min) {
      targetScrollX += sequenceWidth;
      currentScrollX += sequenceWidth;
      scroller.style.transform = `translateX(-${currentScrollX}px)`;
      return true;
    }

    return false;
  }

  function updateProgress(sequenceWidth, forceReset = false) {
    const base = sequenceWidth * bufferSize;

    let pos = (currentScrollX - base) % sequenceWidth;
    if (pos < 0) pos += sequenceWidth;

    const percentage = (pos / sequenceWidth) * 100;

    const wrapping =
      (lastPercentage > 80 && percentage < 20) ||
      (lastPercentage < 20 && percentage > 80) ||
      forceReset;

    progressCounter.textContent = `${Math.round(percentage)}`;
    targetProgressScale = percentage / 100;

    if (wrapping) {
      currentProgressScale = targetProgressScale;
      progressBar.style.transform = `scaleX(${currentProgressScale})`;
    }

    lastPercentage = percentage;
  }

  function animateScroll(sequenceWidth, forceProgressReset = false) {
    currentScrollX = lerp(currentScrollX, targetScrollX, smoothFactor);
    scroller.style.transform = `translateX(-${currentScrollX}px)`;

    updateProgress(sequenceWidth, forceProgressReset);

    if (!forceProgressReset) {
      currentProgressScale = lerp(currentProgressScale, targetProgressScale, smoothFactor);
      progressBar.style.transform = `scaleX(${currentProgressScale})`;
    }

    if (Math.abs(targetScrollX - currentScrollX) < 0.05) {
      isAnimatingScroll = false;
      return;
    }

    requestAnimationFrame(() => animateScroll(sequenceWidth));
  }

  let sequenceWidth = setupScroll();
  if (sequenceWidth > 0) {
    updateProgress(sequenceWidth, true);
    progressBar.style.transform = `scaleX(${currentProgressScale})`;
  }

  function onWheel(e) {
    // если курсор НЕ над контейнером — страница скроллится обычно
    if (!isOverContainer) return;

    // если над контейнером — перехватываем колесо под горизонтальный скролл
    e.preventDefault();
    targetScrollX += e.deltaY;

    const needsReset = checkBoundaryAndReset(sequenceWidth);

    if (!isAnimatingScroll) {
      isAnimatingScroll = true;
      requestAnimationFrame(() => animateScroll(sequenceWidth, needsReset));
    }
  }

  function onTouchStart(e) {
    if (!isOverContainer) return;
    isTouchDown = true;
    lastTouchX = e.touches[0].clientX;
    lastTouchTime = performance.now();
    touchVelocity = 0;
    targetScrollX = currentScrollX;
  }

  function onTouchMove(e) {
    if (!isTouchDown) return;
    e.preventDefault();

    const x = e.touches[0].clientX;
    const dx = lastTouchX - x;

    targetScrollX += dx * touchSensitivity;

    const now = performance.now();
    const dt = now - lastTouchTime;
    if (dt > 0) touchVelocity = (dx / dt) * 16;

    lastTouchX = x;
    lastTouchTime = now;

    const needsReset = checkBoundaryAndReset(sequenceWidth);

    if (!isAnimatingScroll) {
      isAnimatingScroll = true;
      requestAnimationFrame(() => animateScroll(sequenceWidth, needsReset));
    }
  }

  function onTouchEnd() {
    isTouchDown = false;

    if (Math.abs(touchVelocity) > 0.1) {
      let v = touchVelocity * 20;

      const decay = () => {
        v *= 0.94;
        if (Math.abs(v) < 0.2) return;

        targetScrollX += v;
        const needsReset = checkBoundaryAndReset(sequenceWidth);
        if (needsReset) updateProgress(sequenceWidth, true);

        if (!isAnimatingScroll) {
          isAnimatingScroll = true;
          requestAnimationFrame(() => animateScroll(sequenceWidth, needsReset));
        }

        requestAnimationFrame(decay);
      };

      requestAnimationFrame(decay);
    }
  }

  // Вешаем на window, но блокируем дефолт только при isOverContainer
  window.addEventListener("wheel", onWheel, { passive: false });
  window.addEventListener("touchstart", onTouchStart, { passive: true });
  window.addEventListener("touchmove", onTouchMove, { passive: false });
  window.addEventListener("touchend", onTouchEnd, { passive: true });

  // resize
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      sequenceWidth = setupScroll();
      if (sequenceWidth > 0) {
        updateProgress(sequenceWidth, true);
        progressBar.style.transform = `scaleX(${currentProgressScale})`;
      }
    }, 150);
  });

  // =========================
  // Init all
  // =========================
  function init() {
    initDynamicContent();
    setupInitialStates();
    createIntroTimelines();
  }

  init();



});
