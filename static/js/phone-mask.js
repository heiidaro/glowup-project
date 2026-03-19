(function () {
  const TEMPLATE = "+7 (___) ___-__-__";

  const onlyDigits = (s) => (s || "").replace(/\D/g, "");

  function normalizeDigits(inputDigits) {
    // Приводим к виду 7XXXXXXXXXX (11 цифр) без дублей
    let d = inputDigits;

    // если начали с 8 — заменяем на 7
    if (d.startsWith("8")) d = "7" + d.slice(1);

    // если начали с 9 и ввели без кода страны — добавляем 7
    if (d.length > 0 && !d.startsWith("7")) d = "7" + d;

    // ограничим 11 цифрами
    return d.slice(0, 11);
  }

  function formatPhone(d11) {
    // d11: 7XXXXXXXXXX (до 11 цифр)
    if (!d11) return "";

    // национальная часть (10 цифр после 7)
    const n = d11.slice(1);

    // НЕ заполняем цифрами — только то, что ввели
    const a = n.slice(0, 3);
    const b = n.slice(3, 6);
    const c = n.slice(6, 8);
    const d = n.slice(8, 10);

    let out = "+7";
    if (a.length) out += " (" + a;
    if (a.length === 3) out += ")";
    if (b.length) out += " " + b;
    if (c.length) out += "-" + c;
    if (d.length) out += "-" + d;

    return out;
  }

  function countDigitsBeforeCaret(value, caretPos) {
    return onlyDigits(value.slice(0, caretPos)).length;
  }

  function caretPosForDigitIndex(formattedValue, digitIndex) {
    // digitIndex — сколько цифр должно быть слева от каретки
    if (digitIndex <= 0) return 0;

    let count = 0;
    for (let i = 0; i < formattedValue.length; i++) {
      if (/\d/.test(formattedValue[i])) count++;
      if (count >= digitIndex) return i + 1;
    }
    return formattedValue.length;
  }

  function applyMask(input, force = false) {
    const raw = input.value;

    const startsLikePhone = /^[\d+]/.test(raw.trim());
    const hasLetters = /[A-Za-zА-Яа-я]/.test(raw);

    if (!startsLikePhone && hasLetters) return;

    // Если вообще не похоже на телефон (не цифра и не "+") — тоже не трогаем
    if (!startsLikePhone && !raw.includes("@")) return;

    // если это email — маску не трогаем
    if (raw.includes("@")) return;

    const caret = input.selectionStart ?? raw.length;

    // сколько цифр было слева от каретки в том, что ввёл пользователь
    let digitsBefore = countDigitsBeforeCaret(raw, caret);

    const rawDigits = onlyDigits(raw);
    // пользователь сам ввёл код страны (7/8) или нет
    const hadCountry = rawDigits.startsWith("7") || rawDigits.startsWith("8");

    // нормализуем (внутри может добавиться "7")
    let d = normalizeDigits(rawDigits);

    // если код страны НЕ был введён пользователем, но мы добавили "7",
    // сдвигаем целевую каретку на 1 цифру вправо, чтобы курсор оказался после первой введённой цифры
    if (!hadCountry && digitsBefore > 0) {
      digitsBefore += 1;
    }


    // если пользователь удалил всё — оставляем пусто (не подставляем 777/шаблон)
    if (!d || d === "7") {
      input.value = "";
      return;
    }

    const formatted = formatPhone(d);
    input.value = formatted;

    // восстановим каретку
    const newPos = caretPosForDigitIndex(formatted, digitsBefore);
    try {
      input.setSelectionRange(newPos, newPos);
    } catch (_) {}
  }

  document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("id_contact");
    if (!input) return;

    // подсказка-формат (не value!)
    input.setAttribute("placeholder", TEMPLATE);
    input.setAttribute("inputmode", "tel");
    input.setAttribute("autocomplete", "tel");

    input.addEventListener("input", () => applyMask(input));
    input.addEventListener("paste", () => setTimeout(() => applyMask(input), 0));

    // корректное удаление: если удаляем до пустого — очищаем поле
    input.addEventListener("keydown", (e) => {
      if (e.key !== "Backspace" && e.key !== "Delete") return;
      if (input.value.includes("@")) return;

      // если в поле мало цифр — после удаления делаем пусто
      const d = normalizeDigits(onlyDigits(input.value));
      if (!d || d.length <= 2) {
        // даём браузеру удалить символ, затем очищаем
        setTimeout(() => {
          const d2 = normalizeDigits(onlyDigits(input.value));
          if (!d2 || d2.length <= 1) input.value = "";
        }, 0);
      }
    });

    // на blur не "дозаполняем", просто оставляем как есть
    input.addEventListener("blur", () => applyMask(input, true));
  });
})();
