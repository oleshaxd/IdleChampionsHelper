/* Idle Champions Helper — isolated DPS/BUD simulator foundation.
 * No equipment model. Max-upgrade assumption applies only to data entries that explicitly declare it.
 * Unknown champion mechanics are deliberately not approximated.
 */
(() => {
  "use strict";

  const DATA_URL = "./data/simulator-champions.json";
  const roster = safeParse(localStorage.getItem("icRoster"), []);
  const savedFormation = safeParse(localStorage.getItem("icFormation"), []);
  const savedType = localStorage.getItem("icFormType") || "diamond";
  const $ = (id) => document.getElementById(id);
  let data = null;
  let selected = [];
  let specs = {};

  function safeParse(value, fallback) {
    try { return value ? JSON.parse(value) : fallback; } catch { return fallback; }
  }

  function esc(value) {
    return String(value).replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[ch]);
  }

  function championRecord(name) {
    return data?.champions?.[name] || null;
  }

  function renderRoster() {
    const box = $("roster");
    if (!roster.length) {
      box.innerHTML = '<p class="muted">В локальном ростере не найдено чемпионов. Сначала добавь их на основной странице и открой симулятор в том же браузере.</p>';
      return;
    }
    box.innerHTML = roster.map((name) => {
      const checked = selected.includes(name) ? "checked" : "";
      const record = championRecord(name);
      return `<label class="roster-item">
        <input type="checkbox" data-champion="${esc(name)}" ${checked}>
        <span><strong>${esc(name)}</strong><small>${record ? "Есть запись в базе симулятора" : "Механики пока не проверены"}</small></span>
      </label>`;
    }).join("");
    box.querySelectorAll("[data-champion]").forEach((input) => {
      input.addEventListener("change", () => {
        const name = input.dataset.champion;
        if (input.checked) {
          if (!selected.includes(name)) selected.push(name);
        } else {
          selected = selected.filter((item) => item !== name);
          delete specs[name];
        }
        renderSelected();
        renderResults();
      });
    });
  }

  function renderSelected() {
    const box = $("selected");
    if (!selected.length) {
      box.innerHTML = '<p class="muted">Выбери чемпионов из своего ростера.</p>';
      return;
    }
    box.innerHTML = selected.map((name) => {
      const record = championRecord(name);
      const options = Array.isArray(record?.specializations) ? record.specializations : [];
      const current = specs[name] || "";
      const specControl = options.length
        ? `<label class="field">Специализация<select data-spec="${esc(name)}">
            <option value="">— выбрать —</option>
            ${options.map((spec) => `<option value="${esc(spec.id)}" ${current === spec.id ? "selected" : ""}>${esc(spec.name)}</option>`).join("")}
          </select></label>`
        : '<p class="warning">Для этого чемпиона нет проверенных данных специализаций — расчёт с ним не будет выдумывать бонусы.</p>';
      return `<article class="champion">
        <div class="champion-title"><strong>${esc(name)}</strong><button type="button" class="remove" data-remove="${esc(name)}">Убрать</button></div>
        ${specControl}
        <small>${record?.dataStatus === "verified" ? "Данные проверены" : "Данные способностей не внесены или не подтверждены"}</small>
      </article>`;
    }).join("");
    box.querySelectorAll("[data-spec]").forEach((select) => {
      select.addEventListener("change", () => {
        specs[select.dataset.spec] = select.value;
        renderResults();
      });
    });
    box.querySelectorAll("[data-remove]").forEach((button) => {
      button.addEventListener("click", () => {
        const name = button.dataset.remove;
        selected = selected.filter((item) => item !== name);
        delete specs[name];
        renderRoster();
        renderSelected();
        renderResults();
      });
    });
  }

  function getVerifiedData() {
    return selected.map((name) => ({ name, record: championRecord(name), specId: specs[name] }))
      .filter((item) => item.record?.dataStatus === "verified" &&
        item.record?.specializations?.some((spec) => spec.id === item.specId) &&
        Array.isArray(item.record?.effects) &&
        item.record.effects.length > 0);
  }

  function renderResults() {
    const verified = getVerifiedData();
    const missing = selected.length - verified.length;
    $("coverage").textContent = `Выбрано чемпионов: ${selected.length}. Полностью проверенных записей с выбранной специализацией и числовыми эффектами: ${verified.length}.`;
    $("dps").textContent = "Не рассчитан";
    $("bud").textContent = "Не рассчитан";
    $("resultNote").innerHTML = selected.length
      ? `Для честного расчёта DPS/BUD нужны проверенные числовые формулы способностей и базовые параметры атак. Сейчас таких полных записей: <b>${verified.length}</b>; без них результат нельзя считать достоверным.${missing ? ` Не хватает данных для ${missing} выбранных чемпионов.` : ""}`
      : "Добавь чемпионов из своего ростера, чтобы увидеть покрытие данных.";
    $("effectList").innerHTML = verified.length
      ? verified.flatMap(({ name, record, specId }) => record.effects
          .filter((effect) => effect.specializationId === specId)
          .map((effect) => `<li><b>${esc(name)}</b>: ${esc(effect.description || effect.id)} — ${esc(effect.value)} (${esc(effect.operation)})</li>`))
          .join("") || "<li>Нет числовых эффектов, привязанных к выбранным специализациям.</li>"
      : "<li>Пока нет записей, прошедших проверку. Мы не подменяем неизвестные значения догадками.</li>";
  }

  async function init() {
    $("sourceInfo").textContent = `Ростер прочитан из этого браузера: ${roster.length} чемпионов. Формация сохранена как «${savedType}» (${savedFormation.filter(Boolean).length} занятых слотов); редактор формации пока остаётся на основной странице.`;
    try {
      const response = await fetch(DATA_URL, { cache: "no-store" });
      if (!response.ok) throw new Error("Не удалось загрузить базу данных");
      data = await response.json();
      $("dataVersion").textContent = data.gameDataVersion || "Не задана";
    } catch (error) {
      data = { champions: {} };
      $("dataVersion").textContent = "Ошибка загрузки";
      $("resultNote").textContent = error.message;
    }
    selected = [...roster];
    renderRoster();
    renderSelected();
    renderResults();
  }

  $("selectAll").addEventListener("click", () => {
    selected = [...roster];
    renderRoster();
    renderSelected();
    renderResults();
  });
  $("clearSelected").addEventListener("click", () => {
    selected = [];
    specs = {};
    renderRoster();
    renderSelected();
    renderResults();
  });
  init();
})();
