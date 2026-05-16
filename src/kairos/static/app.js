const clock = document.querySelector(".clock");

if (clock) {
  const total = Number(clock.dataset.minutes || "25") * 60;
  let remaining = total;
  let elapsed = 0;
  let timer = null;
  const minutesInput = document.querySelector("#focus-minutes");

  const render = () => {
    const minutes = Math.floor(remaining / 60).toString().padStart(2, "0");
    const seconds = (remaining % 60).toString().padStart(2, "0");
    clock.textContent = `${minutes}:${seconds}`;
    if (minutesInput) {
      minutesInput.value =
        elapsed > 0 ? Math.max(1, Math.ceil(elapsed / 60)) : Math.floor(total / 60);
    }
  };

  const tick = () => {
    if (remaining > 0) {
      remaining -= 1;
      elapsed += 1;
      render();
      return;
    }
    clearInterval(timer);
    timer = null;
  };

  document.querySelector("#timer-start")?.addEventListener("click", () => {
    if (!timer) timer = setInterval(tick, 1000);
  });

  document.querySelector("#timer-pause")?.addEventListener("click", () => {
    clearInterval(timer);
    timer = null;
  });

  document.querySelector("#timer-reset")?.addEventListener("click", () => {
    clearInterval(timer);
    timer = null;
    remaining = total;
    elapsed = 0;
    render();
  });

  render();
}

document.querySelectorAll("[data-confirm]").forEach((button) => {
  button.addEventListener("click", (event) => {
    if (!confirm(button.dataset.confirm || "Continue?")) event.preventDefault();
  });
});
