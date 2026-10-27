(function () {
  "use strict";

  var TONE_MARKS = /[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ]|[\u0300\u0301\u0304\u030c]/u;
  var PINYIN_PATTERN = /^[a-zv]+[0-4](?:[a-zv]*[0-4])*(?:'[a-zv]+[0-4](?:[a-zv]*[0-4])*)*$/;
  var CJK_PATTERN = /[\u2e80-\u2fdf\u3400-\u4dbf\u4e00-\u9fff]|[\u{20000}-\u{2ebef}]|[\u{30000}-\u{323af}]/u;
  // 1.0 is Hanzi Writer's default. 1.5 tolerates imprecise phone input
  // while still checking stroke order and direction.
  var HANDWRITING_LENIENCY = 1.5;

  function text(id) {
    var node = document.getElementById(id);
    return node ? node.textContent.trim() : "";
  }

  function normalizePinyin(value) {
    return value.trim().toLowerCase()
      .replace(/[’‘ʼ＇]/g, "'")
      .replace(/ü/g, "v")
      .replace(/\s+/g, "");
  }

  function checkPinyin(value, expected) {
    if (TONE_MARKS.test(value.normalize("NFD"))) {
      return { ok: false, message: "Неправильно — требуется pinyin с номерами тонов, без диакритики." };
    }
    var normalized = normalizePinyin(value);
    if (normalized.indexOf("5") !== -1) {
      return { ok: false, message: "Неправильно — тон 5 запрещён, нейтральный тон обозначается 0." };
    }
    if (!PINYIN_PATTERN.test(normalized)) {
      return { ok: false, message: "Неправильно — каждый слог должен содержать номер тона 0–4." };
    }
    return normalized === normalizePinyin(expected)
      ? { ok: true, message: "Правильно" }
      : { ok: false, message: "Неправильно" };
  }

  function normalizeRussian(value) {
    return value.trim().toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ");
  }

  function checkRussian(value, accepted) {
    var normalized = normalizeRussian(value);
    var ok = accepted.split("|").some(function (option) {
      return normalized === normalizeRussian(option);
    });
    return { ok: ok, message: ok ? "Правильно" : "Неправильно" };
  }

  function stateKey(uid, direction) {
    return "chinese-ru::" + uid + "::" + direction;
  }

  function saveState(key, state) {
    try { sessionStorage.setItem(key, JSON.stringify(state)); } catch (_) { /* storage can be disabled */ }
  }

  function loadState(key) {
    try { return JSON.parse(sessionStorage.getItem(key) || "null"); } catch (_) { return null; }
  }

  function setStatus(id, label, result) {
    var node = document.getElementById(id);
    if (!node) return;
    node.textContent = label + ": " + result.message;
    node.className = "status " + (result.ok ? "status-ok" : "status-error");
  }

  function bindPress(element, handler) {
    var touchHandled = false;
    element.classList.add("tappable");
    element.addEventListener("touchend", function (event) {
      touchHandled = true;
      event.preventDefault();
      event.stopPropagation();
      handler(event);
      window.setTimeout(function () { touchHandled = false; }, 500);
    }, { passive: false });
    element.addEventListener("click", function (event) {
      event.stopPropagation();
      if (!touchHandled) handler(event);
    });
  }

  function initRuToZh() {
    var uid = text("field-uid");
    var expectedHanzi = text("field-hanzi");
    var expectedPinyin = text("field-pinyin");
    var key = stateKey(uid, "ru-to-zh");
    var writers = [];
    var completed = [];
    var totalMistakes = 0;
    var run = 0;

    saveState(key, { direction: "ru-to-zh", checked: false });
    function resetWriters() {
      run += 1;
      var thisRun = run;
      writers.forEach(function (writer) {
        try { writer.cancelQuiz(); } catch (_) { /* instance is discarded below */ }
      });
      writers = [];
      completed = [];
      totalMistakes = 0;
      var host = document.getElementById("writers");
      host.replaceChildren();
      document.getElementById("writing-status").textContent = "";
      document.getElementById("writing-status").className = "status";
      document.getElementById("retry-writing").hidden = true;
      document.getElementById("check-answer").hidden = false;

      var chars = Array.from(expectedHanzi).filter(function (char) { return CJK_PATTERN.test(char); });
      if (!chars.length) {
        var warning = document.createElement("p");
        warning.className = "status status-error";
        warning.textContent = "В Hanzi нет поддерживаемых китайских иероглифов.";
        host.appendChild(warning);
        return;
      }
      chars.forEach(function (char, index) {
        var square = document.createElement("div");
        square.className = "writer-square";
        square.setAttribute("aria-label", "Поле для иероглифа " + (index + 1));
        host.appendChild(square);
        completed[index] = false;
        var writer = HanziWriter.create(square, char, {
          width: square.clientWidth || 200,
          height: square.clientWidth || 200,
          padding: 8,
          showCharacter: false,
          showOutline: false,
          charDataLoader: function (requestedChar) {
            return window.HANZI_DATA[requestedChar];
          }
        });
        writers.push(writer);
        writer.quiz({
          showCharacter: false,
          showOutline: false,
          showHintAfterMisses: false,
          acceptBackwardsStrokes: false,
          highlightOnComplete: false,
          leniency: HANDWRITING_LENIENCY,
          onMistake: function () {
            if (run === thisRun) totalMistakes += 1;
          },
          onComplete: function () {
            if (run === thisRun) completed[index] = true;
          }
        });
      });
    }

    bindPress(document.getElementById("retry-writing"), resetWriters);
    bindPress(document.getElementById("check-answer"), function () {
      var complete = completed.length > 0 && completed.every(Boolean);
      var perfect = complete && totalMistakes === 0;
      var writing = {
        ok: perfect,
        message: perfect ? "Правильно (0 ошибок)" : (complete ? "Есть ошибки (" + totalMistakes + ")" : "Не все иероглифы завершены (ошибок: " + totalMistakes + ")")
      };
      var pinyinValue = document.getElementById("pinyin-input").value;
      var pinyin = checkPinyin(pinyinValue, expectedPinyin);
      setStatus("writing-status", "Написание", writing);
      setStatus("pinyin-status", "Pinyin", pinyin);
      document.getElementById("retry-writing").hidden = false;
      document.getElementById("check-answer").hidden = perfect && pinyin.ok;
      saveState(key, {
        direction: "ru-to-zh",
        checked: true,
        pinyinInput: pinyinValue,
        pinyinOk: pinyin.ok,
        writingComplete: complete,
        writingPerfect: perfect,
        totalMistakes: totalMistakes
      });
    });
    resetWriters();
  }

  function initZhToRu() {
    var uid = text("field-uid");
    var key = stateKey(uid, "zh-to-ru");
    var expectedPinyin = text("field-pinyin");
    var acceptedRussian = text("field-russian-accepted");
    saveState(key, { direction: "zh-to-ru", checked: false });
    bindPress(document.getElementById("check-answer"), function () {
      var russianValue = document.getElementById("russian-input").value;
      var pinyinValue = document.getElementById("pinyin-input").value;
      var russian = checkRussian(russianValue, acceptedRussian);
      var pinyin = checkPinyin(pinyinValue, expectedPinyin);
      setStatus("russian-status", "Перевод", russian);
      setStatus("pinyin-status", "Pinyin", pinyin);
      saveState(key, {
        direction: "zh-to-ru",
        checked: true,
        russianInput: russianValue,
        russianOk: russian.ok,
        pinyinInput: pinyinValue,
        pinyinOk: pinyin.ok
      });
      document.getElementById("check-answer").hidden = russian.ok && pinyin.ok;
    });
  }

  function initBack(direction) {
    var state = loadState(stateKey(text("field-uid"), direction));
    var host = document.getElementById("answer-results");
    if (!host) return;
    if (!state || !state.checked) {
      host.textContent = "Сохранённые ответы для этой попытки недоступны.";
      return;
    }
    function row(label, value, ok) {
      var wrapper = document.createElement("div");
      wrapper.className = "answer-row";
      var valueNode = document.createElement("span");
      valueNode.textContent = label + ": " + (value || "(пусто)");
      var resultNode = document.createElement("span");
      resultNode.className = ok ? "status-ok" : "status-error";
      resultNode.textContent = ok ? "правильно" : "неправильно";
      wrapper.append(valueNode, resultNode);
      host.appendChild(wrapper);
    }
    if (direction === "ru-to-zh") {
      row("Написание", state.writingComplete ? "завершено, ошибок: " + state.totalMistakes : "не завершено, ошибок: " + state.totalMistakes, state.writingPerfect);
      row("Введённый pinyin", state.pinyinInput, state.pinyinOk);
    } else {
      row("Введённый перевод", state.russianInput, state.russianOk);
      row("Введённый pinyin", state.pinyinInput, state.pinyinOk);
    }
  }

  window.ChineseCards = {
    initRuToZh: initRuToZh,
    initZhToRu: initZhToRu,
    initBack: initBack,
    normalizePinyin: normalizePinyin,
    normalizeRussian: normalizeRussian,
    checkPinyin: checkPinyin,
    checkRussian: checkRussian
  };
}());
