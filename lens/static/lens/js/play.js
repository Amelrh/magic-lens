/* ============================================
   La Loupe Magique — play.js (corrigé)
   Dessin couleurs + loupes + mini-jeu
   ============================================ */

(function () {
  "use strict";

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? match[2] : "";
  }

  var csrftoken = getCookie("csrftoken") || window.CSRF_TOKEN || "";

  // Valeurs envoyées au serveur (niveaux de gris)
  var pixels = Array.from({ length: 8 }, function () {
    return Array(8).fill(255);
  });
  var currentColor = 0;
  var selectedLensId = null;
  var afterPixels = null;
  var animating = false;
  var animSpeed = 160;
  var paused = false;

  // Affichage coloré pour le dessin (même valeurs 0/85/170/255)
  var COLOR_MAP = {
    0: "#1e293b",
    85: "#fbbf24",
    170: "#f9a8d4",
    255: "#93c5fd"
  };

  function displayColor(v) {
    if (COLOR_MAP[v] !== undefined) return COLOR_MAP[v];
    // Après filtre : niveaux de gris
    return "rgb(" + v + "," + v + "," + v + ")";
  }

  // Game
  var gameId = null;
  var questions = [];
  var qIndex = 0;
  var totalPoints = 0;
  var qStart = 0;
  var answered = false;

  function renderGrid(elId, data, interactive, usePalette) {
    var el = document.getElementById(elId);
    if (!el) return;
    el.innerHTML = "";
    var table = document.createElement("table");
    for (var y = 0; y < 8; y++) {
      var tr = document.createElement("tr");
      for (var x = 0; x < 8; x++) {
        var td = document.createElement("td");
        td.dataset.y = y;
        td.dataset.x = x;
        var val = data[y][x];
        td.style.background = usePalette ? displayColor(val) : displayColor(val);
        if (interactive) {
          td.style.cursor = "crosshair";
          (function (yy, xx, cell) {
            cell.addEventListener("click", function () {
              pixels[yy][xx] = currentColor;
              cell.style.background = displayColor(currentColor);
            });
            cell.addEventListener("mouseenter", function (e) {
              if (e.buttons === 1) {
                pixels[yy][xx] = currentColor;
                cell.style.background = displayColor(currentColor);
              }
            });
          })(y, x, td);
        }
        tr.appendChild(td);
      }
      table.appendChild(tr);
    }
    el.appendChild(table);
  }

  function goTab(name) {
    document.querySelectorAll(".panel").forEach(function (p) {
      p.classList.remove("active");
    });
    document.querySelectorAll(".tab").forEach(function (t) {
      t.classList.remove("active");
    });
    var panel = document.getElementById("panel-" + name);
    var tab = document.querySelector('.tab[data-tab="' + name + '"]');
    if (panel) panel.classList.add("active");
    if (tab) tab.classList.add("active");

    if (name === "board") loadLeaderboard();
    if (name === "lens") {
      renderGrid("before-grid", pixels, false, true);
      renderGrid("after-grid", afterPixels || pixels, false, false);
    }
  }

  // Tabs
  document.querySelectorAll(".tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      goTab(btn.dataset.tab);
    });
  });
  document.querySelectorAll("[data-goto]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      goTab(btn.dataset.goto);
    });
  });

  // Couleurs
  document.querySelectorAll(".color-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      currentColor = parseInt(btn.dataset.color, 10);
      document.querySelectorAll(".color-btn").forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
    });
  });
  var defColor = document.querySelector('.color-btn[data-color="0"]');
  if (defColor) defColor.classList.add("active");

  // Effacer
  var clearBtn = document.getElementById("clear-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      pixels = Array.from({ length: 8 }, function () {
        return Array(8).fill(255);
      });
      renderGrid("draw-grid", pixels, true, true);
    });
  }

  // Modèles
  document.querySelectorAll(".template-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.dataset.id;
      fetch("/api/drawing/" + id + "/")
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.pixels) {
            pixels = d.pixels;
            renderGrid("draw-grid", pixels, true, true);
          }
        })
        .catch(function (e) {
          console.error(e);
          alert("Impossible de charger le modèle.");
        });
    });
  });

  // Cartes loupes
  document.querySelectorAll(".lens-card").forEach(function (card) {
    card.addEventListener("click", function () {
      document.querySelectorAll(".lens-card").forEach(function (c) {
        c.classList.remove("selected");
      });
      card.classList.add("selected");
      selectedLensId = parseInt(card.dataset.id, 10);
      var applyBtn = document.getElementById("apply-btn");
      if (applyBtn) applyBtn.disabled = false;
    });
  });

  // Appliquer loupe
  function applySelectedLens() {
    if (!selectedLensId || animating) return;
    var applyBtn = document.getElementById("apply-btn");
    if (applyBtn) applyBtn.disabled = true;

    csrftoken = getCookie("csrftoken") || csrftoken;

    fetch("/api/apply/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken
      },
      body: JSON.stringify({
        lens_id: selectedLensId,
        pixels: pixels
      })
    })
      .then(function (r) {
        if (!r.ok) {
          return r.json().then(function (d) {
            throw new Error(d.error || ("Erreur HTTP " + r.status));
          });
        }
        return r.json();
      })
      .then(function (d) {
        if (!d.success) {
          alert(d.error || "Erreur");
          if (applyBtn) applyBtn.disabled = false;
          return;
        }

        afterPixels = d.pixels;
        var bubble = document.getElementById("bubble");
        if (bubble) {
          bubble.textContent = d.bubble_text || "Je mélange ces 9 pixels…";
        }

        var animZone = document.getElementById("anim-zone");
        if (animZone) animZone.classList.remove("hidden");

        renderGrid("before-grid", pixels, false, true);
        var blank = Array.from({ length: 8 }, function () {
          return Array(8).fill(255);
        });
        renderGrid("after-grid", blank, false, false);

        return runLensAnimation(pixels, afterPixels).then(function () {
          renderGrid("after-grid", afterPixels, false, false);
          buildCompareSlider(pixels, afterPixels);
          if (applyBtn) applyBtn.disabled = false;
        });
      })
      .catch(function (e) {
        console.error(e);
        alert("Erreur loupe : " + (e.message || e));
        if (applyBtn) applyBtn.disabled = false;
      });
  }

  var applyBtn = document.getElementById("apply-btn");
  if (applyBtn) applyBtn.addEventListener("click", applySelectedLens);

  function runLensAnimation(src, result) {
    return new Promise(function (resolve) {
      animating = true;
      paused = false;
      var beforeTable = document.querySelector("#before-grid table");
      var afterTable = document.querySelector("#after-grid table");
      if (!beforeTable || !afterTable) {
        animating = false;
        resolve();
        return;
      }

      var y, x;
      for (y = 0; y < 8; y++) {
        for (x = 0; x < 8; x++) {
          afterTable.rows[y].cells[x].style.background = displayColor(255);
        }
      }

      var step = 0;

      function clearHighlights() {
        beforeTable.querySelectorAll("td").forEach(function (td) {
          td.classList.remove("cell-highlight");
        });
      }

      function tick() {
        if (paused) {
          setTimeout(tick, 100);
          return;
        }
        if (step >= 64) {
          clearHighlights();
          animating = false;
          resolve();
          return;
        }

        var cy = Math.floor(step / 8);
        var cx = step % 8;
        clearHighlights();

        var ky, kx;
        for (ky = -1; ky <= 1; ky++) {
          for (kx = -1; kx <= 1; kx++) {
            var py = Math.max(0, Math.min(7, cy + ky));
            var px = Math.max(0, Math.min(7, cx + kx));
            beforeTable.rows[py].cells[px].classList.add("cell-highlight");
          }
        }

        afterTable.rows[cy].cells[cx].style.background = displayColor(result[cy][cx]);
        step++;
        setTimeout(tick, animSpeed);
      }

      tick();
    });
  }

  var btnPause = document.getElementById("btn-pause");
  if (btnPause) {
    btnPause.addEventListener("click", function () {
      paused = !paused;
      btnPause.textContent = paused ? "▶ Reprendre" : "⏸ Pause";
    });
  }

  var btnSpeed = document.getElementById("btn-speed");
  if (btnSpeed) {
    btnSpeed.addEventListener("click", function () {
      if (animSpeed > 70) {
        animSpeed = 50;
        btnSpeed.textContent = "🐢 Lent";
      } else {
        animSpeed = 160;
        btnSpeed.textContent = "⚡ Rapide";
      }
    });
  }

  function buildCompareSlider(before, after) {
    var wrap = document.getElementById("compare-wrap");
    if (!wrap) return;
    wrap.classList.remove("hidden");
    wrap.innerHTML = "";

    var size = 8;
    var cell = 36;
    var px = size * cell;
    wrap.style.width = px + "px";
    wrap.style.height = px + "px";

    function makeCanvas(data, palette) {
      var canvas = document.createElement("canvas");
      canvas.width = px;
      canvas.height = px;
      canvas.className = "side";
      var ctx = canvas.getContext("2d");
      var y, x;
      for (y = 0; y < size; y++) {
        for (x = 0; x < size; x++) {
          ctx.fillStyle = displayColor(data[y][x]);
          ctx.fillRect(x * cell, y * cell, cell, cell);
          ctx.strokeStyle = "#e5e7eb";
          ctx.strokeRect(x * cell, y * cell, cell, cell);
        }
      }
      return canvas;
    }

    var cAfter = makeCanvas(after, false);
    cAfter.classList.add("side-after");
    var cBefore = makeCanvas(before, true);
    cBefore.classList.add("side-before");

    var line = document.createElement("div");
    line.className = "slider-line";
    var handle = document.createElement("div");
    handle.className = "slider-handle";
    handle.textContent = "◀▶";

    wrap.appendChild(cAfter);
    wrap.appendChild(cBefore);
    wrap.appendChild(line);
    wrap.appendChild(handle);

    var dragging = false;

    function setPos(clientX) {
      var rect = wrap.getBoundingClientRect();
      var pct = ((clientX - rect.left) / rect.width) * 100;
      pct = Math.max(3, Math.min(97, pct));
      cBefore.style.clipPath = "inset(0 " + (100 - pct) + "% 0 0)";
      line.style.left = pct + "%";
      handle.style.left = pct + "%";
    }

    wrap.addEventListener("pointerdown", function (e) {
      dragging = true;
      wrap.setPointerCapture(e.pointerId);
      setPos(e.clientX);
    });
    wrap.addEventListener("pointermove", function (e) {
      if (dragging) setPos(e.clientX);
    });
    wrap.addEventListener("pointerup", function () { dragging = false; });
    wrap.addEventListener("pointercancel", function () { dragging = false; });
  }

  // Mini-jeu
  var startBtn = document.getElementById("start-game-btn");
  if (startBtn) startBtn.addEventListener("click", startGame);

  function startGame() {
    var nameEl = document.getElementById("player-name");
    var name = (nameEl && nameEl.value ? nameEl.value : "").trim();
    if (!name) {
      alert("Entre un pseudo");
      return;
    }
    csrftoken = getCookie("csrftoken") || csrftoken;

    fetch("/api/game/start/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken
      },
      body: JSON.stringify({ player_name: name })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.success) {
          alert(d.error || "Erreur");
          return;
        }
        gameId = d.game_id;
        questions = d.questions;
        qIndex = 0;
        totalPoints = 0;
        document.getElementById("game-setup").classList.add("hidden");
        document.getElementById("game-end").classList.add("hidden");
        document.getElementById("game-play").classList.remove("hidden");
        document.getElementById("score").textContent = "0";
        showQuestion();
      })
      .catch(function () {
        alert("Erreur réseau (mini-jeu)");
      });
  }

  function showQuestion() {
    answered = false;
    var q = questions[qIndex];
    document.getElementById("q-num").textContent = qIndex + 1;
    var fb = document.getElementById("game-feedback");
    fb.textContent = "";
    fb.className = "";
    document.getElementById("next-btn").classList.add("hidden");
    renderGrid("result-grid", q.result_pixels, false, false);

    var box = document.getElementById("choices");
    box.innerHTML = "";
    q.choices.forEach(function (c) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "choice-btn";
      b.textContent = c.icon + " " + c.name;
      b.addEventListener("click", function () {
        answer(c.id, b);
      });
      box.appendChild(b);
    });
    qStart = Date.now();
  }

  function answer(lensId, btnEl) {
    if (answered) return;
    answered = true;
    var seconds = Math.min(60, (Date.now() - qStart) / 1000);
    document.querySelectorAll(".choice-btn").forEach(function (b) {
      b.disabled = true;
    });
    csrftoken = getCookie("csrftoken") || csrftoken;

    fetch("/api/game/answer/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken
      },
      body: JSON.stringify({
        game_id: gameId,
        question_index: qIndex,
        chosen_lens_id: lensId,
        seconds: seconds
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.success) {
          alert(d.error || "Erreur");
          answered = false;
          document.querySelectorAll(".choice-btn").forEach(function (b) {
            b.disabled = false;
          });
          return;
        }

        totalPoints = d.total_points;
        document.getElementById("score").textContent = totalPoints;
        var fb = document.getElementById("game-feedback");

        if (d.is_correct) {
          fb.textContent = "✓ Bravo ! +" + d.points + " pts";
          fb.className = "ok";
          btnEl.classList.add("correct");
        } else {
          fb.textContent =
            "✗ Non… c'était " + d.correct_lens.icon + " " + d.correct_lens.name;
          fb.className = "ko";
          btnEl.classList.add("wrong");
          document.querySelectorAll(".choice-btn").forEach(function (b) {
            if (b.textContent.indexOf(d.correct_lens.name) !== -1) {
              b.classList.add("correct");
            }
          });
        }

        var nextBtn = document.getElementById("next-btn");
        nextBtn.textContent =
          qIndex >= 4 ? "Voir le score final" : "Question suivante →";
        nextBtn.classList.remove("hidden");
      })
      .catch(function () {
        alert("Erreur réseau");
        answered = false;
        document.querySelectorAll(".choice-btn").forEach(function (b) {
          b.disabled = false;
        });
      });
  }

  var nextBtn = document.getElementById("next-btn");
  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      if (qIndex >= 4) {
        document.getElementById("game-play").classList.add("hidden");
        document.getElementById("game-end").classList.remove("hidden");
        document.getElementById("final-score").textContent = totalPoints;
        return;
      }
      qIndex++;
      showQuestion();
    });
  }

  var replayBtn = document.getElementById("replay-btn");
  if (replayBtn) {
    replayBtn.addEventListener("click", function () {
      document.getElementById("game-end").classList.add("hidden");
      document.getElementById("game-setup").classList.remove("hidden");
      var nameEl = document.getElementById("player-name");
      if (nameEl) nameEl.value = "";
    });
  }

  function loadLeaderboard() {
    var empty = document.getElementById("board-empty");
    var table = document.getElementById("board-table");
    var body = document.getElementById("board-body");
    if (!empty || !table || !body) return;

    empty.classList.remove("hidden");
    empty.textContent = "Chargement…";
    table.classList.add("hidden");
    body.innerHTML = "";

    fetch("/api/game/leaderboard/")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.success || !d.leaderboard.length) {
          empty.textContent = "Aucune partie terminée pour le moment.";
          return;
        }
        empty.classList.add("hidden");
        table.classList.remove("hidden");
        d.leaderboard.forEach(function (row, i) {
          var tr = document.createElement("tr");
          tr.innerHTML =
            "<td>" + (i + 1) + "</td>" +
            "<td>" + row.player_name + "</td>" +
            "<td>" + row.points + "</td>" +
            "<td>" + row.date + "</td>";
          body.appendChild(tr);
        });
      })
      .catch(function () {
        empty.textContent = "Impossible de charger le classement.";
      });
  }

  // Init
  renderGrid("draw-grid", pixels, true, true);
  renderGrid("before-grid", pixels, false, true);
  renderGrid("after-grid", pixels, false, false);
})();
