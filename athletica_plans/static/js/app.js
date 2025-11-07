document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("search-form");
  const resultsContainer = document.getElementById("results");
  const errorBox = document.getElementById("error-box");
  const spinner = document.getElementById("spinner");
  const minutesInput = document.getElementById("session_minutes");
  const minutesValue = document.getElementById("minutes-value");

  minutesValue.textContent = minutesInput.value;
  minutesInput.addEventListener("input", () => {
    minutesValue.textContent = minutesInput.value;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    clearResults();
    toggleSpinner(true);

    try {
      const payload = buildPayload(form);
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = data?.detail || "No se pudo completar la busqueda.";
        throw new Error(detail);
      }

      const data = await response.json();
      renderResults(data);
    } catch (error) {
      showError(error.message);
    } finally {
      toggleSpinner(false);
    }
  });

  function buildPayload(formElement) {
    const formData = new FormData(formElement);

    // Multi-objetivo
    const objectives = formData.getAll("objectives").map((v) => v.toString());
    // Nivel
    const level = (formData.get("level") || "medio").toString();

    const sessionMinutes = Number(formData.get("session_minutes"));
    const query = formData.get("query");
    const pathologies = formData.getAll("pathologies").map((v) => v.toString());

    return {
      objectives, // SIEMPRE como lista
      session_minutes: sessionMinutes,
      pathologies,
      level,
      q: query ? query.trim() : null,
    };
  }

  function renderResults(data) {
    if (!data?.results?.length) {
      resultsContainer.innerHTML =
        '<p class="text-neutral-400">Sin rutinas disponibles para esta configuracion.</p>';
      return;
    }

    const fragment = document.createDocumentFragment();
    data.results.forEach((routine) => {
      fragment.appendChild(createRoutineCard(routine));
    });
    resultsContainer.appendChild(fragment);
  }

  function createRoutineCard(routine) {
    const card = document.createElement("article");
    card.className = "result-card";

    const header = document.createElement("header");

    const title = document.createElement("h3");
    title.className = "text-lg font-semibold text-accent";
    const readableLevel = routine.level ? ` - ${capitalize(routine.level)}` : "";
    title.textContent = `${capitalize(routine.objective)} ${routine.minutes_target} min${readableLevel}`;

    const subtitle = document.createElement("p");
    subtitle.className = "text-sm text-neutral-400";
    subtitle.textContent = routine.name;
    if (routine.objective === "mixto") {
      subtitle.appendChild(document.createTextNode(" "));
      const badge = document.createElement("span");
      badge.className = "tag";
      badge.textContent = "Mixto";
      subtitle.appendChild(badge);
    }

    header.appendChild(title);
    header.appendChild(subtitle);
    card.appendChild(header);

    const sectionsWrapper = document.createElement("div");
    sectionsWrapper.className = "space-y-3";

    Object.entries(routine.sections).forEach(([sectionKey, sectionData]) => {
      sectionsWrapper.appendChild(
        createSectionBlock(sectionKey, sectionData)
      );
    });

    card.appendChild(sectionsWrapper);
    return card;
  }

  function createSectionBlock(sectionKey, sectionData) {
    const details = document.createElement("details");
    if (sectionKey === "warmup") {
      details.open = true;
    }

    const summary = document.createElement("summary");
    summary.innerHTML = `
      <span class="section-title">${labelFor(sectionKey)}</span>
      <span class="text-sm text-neutral-400">${sectionData.minutes} min</span>
    `;

    const list = document.createElement("div");
    list.className = "exercise-list";

    sectionData.items.forEach((item) => {
      list.appendChild(createExerciseCard(item));
    });

    details.appendChild(summary);
    details.appendChild(list);
    return details;
  }

  function createExerciseCard(item) {
    const wrapper = document.createElement("div");
    wrapper.className = "exercise-card";

    const title = document.createElement("div");
    title.className = "flex flex-wrap items-center gap-2 justify-between";

    const name = document.createElement("span");
    name.className = "font-semibold";
    name.textContent = item.name;
    title.appendChild(name);

    if (item.pattern) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = item.pattern;
      title.appendChild(tag);
    }

    wrapper.appendChild(title);

    const details = [];
    if (item.sets) details.push(`${item.sets} series`);
    if (item.reps) details.push(`${item.reps} reps`);
    if (item.minutes && !item.sets) details.push(`${item.minutes} min`);
    if (item.rest) details.push(`descanso ${item.rest}`);
    if (item.intensity) details.push(`intensidad ${item.intensity}`);

    if (details.length) {
      const detailText = document.createElement("p");
      detailText.textContent = details.join(" | ");
      wrapper.appendChild(detailText);
    }

    if (item.notes) {
      const notes = document.createElement("p");
      notes.textContent = item.notes;
      wrapper.appendChild(notes);
    }

    // --- NUEVO: chips de contraindicaciones ---
    let contras = item.contraindications;
    if (typeof contras === "string") {
      contras = contras.trim() ? [contras.trim()] : [];
    }
    if (Array.isArray(contras) && contras.length) {
      const row = document.createElement("div");
      row.className = "mt-2 flex flex-wrap gap-2";
      contras.forEach((c) => {
        const chip = document.createElement("span");
        chip.className = "tag";
        chip.textContent = c;
        row.appendChild(chip);
      });
      wrapper.appendChild(row);
    }

    if (item.is_fallback) {
      const badge = document.createElement("p");
      badge.textContent = "Sugerencia automática";
      badge.className = "text-xs uppercase tracking-wide text-neutral-500 mt-2";
      wrapper.appendChild(badge);
    }

    return wrapper;
  }

  function clearResults() {
    resultsContainer.textContent = "";
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
  }

  function clearError() {
    errorBox.textContent = "";
    errorBox.classList.add("hidden");
  }

  function toggleSpinner(enable) {
    if (enable) {
      spinner.classList.remove("hidden");
    } else {
      spinner.classList.add("hidden");
    }
  }

  function labelFor(sectionKey) {
    switch (sectionKey) {
      case "warmup":
        return "Calentamiento";
      case "main":
        return "Bloque principal";
      case "cooldown":
        return "Vuelta a la calma";
      default:
        return capitalize(sectionKey);
    }
  }

  function capitalize(value) {
    if (!value) return "";
    return value.charAt(0).toUpperCase() + value.slice(1);
  }
});
