/* Search over the estate's records, scored in the page as the engine scores
 * it (terrane/search.py): the index comes from GET /api/search/index, built
 * once by the engine, and every weight in it is a whole number, so the page
 * only adds and compares them and its answers cannot differ from Python's in
 * a last digit. TestTheSearchInThePage holds the two to the same answers;
 * a change here is a change there.
 *
 * Loaded before app.js, which reads window.TerraneSearch. */
(function (root) {
  "use strict";

  var VERSION = 1;
  // How much of a word's weight a query's word gets, in tenths: the whole
  // word, its start, a near spelling, and a word an alias added.
  var WHOLE = 10, START = 7, NEAR = 5, ADDED = 5;
  var NEAR_FROM = 4;
  var own = Object.prototype.hasOwnProperty;

  function has(table, key) { return own.call(table, key); }

  function split(value) {
    return String(value == null ? "" : value).replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
  }

  function singular(word) {
    if (word.length > 3 && word.charAt(word.length - 1) === "s" && word.charAt(word.length - 2) !== "s") {
      return word.slice(0, -1);
    }
    return word;
  }

  function words(value, little) {
    return (split(value).match(/[a-z]+|[0-9]+/g) || []).filter(function (w) { return !has(little, w); });
  }

  function isNumber(word) { return /^[0-9]+$/.test(word); }

  function key(list) {
    var seen = {}, out = [];
    list.forEach(function (w) { if (!has(seen, w)) { seen[w] = true; out.push(w); } });
    out.sort();
    return out.join(" ");
  }

  function grams(word) {
    var text = " " + word + " ", out = {};
    for (var i = 0; i + 3 <= text.length; i++) out[text.slice(i, i + 3)] = true;
    return out;
  }

  function near(a, b) {
    // Dice over three-letter pieces at a half or more, in whole numbers.
    var na = 0, nb = 0, both = 0, g;
    for (g in a) { if (has(a, g)) { na++; if (has(b, g)) both++; } }
    for (g in b) { if (has(b, g)) nb++; }
    return 4 * both >= na + nb;
  }

  // What the page works out once an index: its words in order, its little
  // words as a table, and each word's three-letter pieces when first asked.
  function prepared(index) {
    if (index.__prepared) return index.__prepared;
    var little = {};
    (index.little || []).forEach(function (w) { little[w] = true; });
    var p = { vocab: Object.keys(index.terms || {}).sort(), little: little, grams: {} };
    Object.defineProperty(index, "__prepared", { value: p, enumerable: false });
    return p;
  }

  function gramsOf(p, word) {
    if (!has(p.grams, word)) p.grams[word] = grams(word);
    return p.grams[word];
  }

  function queryWords(index, p, query) {
    var mine = [], have = {};
    words(query, p.little).forEach(function (typed) {
      var w = singular(typed);
      if (!has(have, w)) { have[w] = true; mine.push([w, typed]); }
    });
    var added = [];
    (index.expand || []).forEach(function (pair) {
      if (pair[0].every(function (w) { return has(have, w); })) {
        pair[1].forEach(function (w) {
          if (!has(have, w) && added.indexOf(w) === -1) added.push(w);
        });
      }
    });
    return { own: mine, added: added };
  }

  function cmp(a, b) { return a < b ? -1 : a > b ? 1 : 0; }

  /* The records `query` finds, best first, as terrane.search.search gives
   * them: {id, type, name, matched, named, score, added, words}. `opts.limit`
   * keeps the first so many (all when it is 0 or missing), `opts.type` one
   * type. An index of another version finds nothing. */
  function search(index, query, opts) {
    opts = opts || {};
    if (!index || index.version !== VERSION) return [];
    var p = prepared(index);
    var terms = index.terms || {};
    var docs = index.docs || [];
    var q = queryWords(index, p, query);
    var score = {}, extra = {}, matched = {}, said = {};

    function offer(best, word, share) {
      var post = terms[word];
      for (var i = 0; i < post.length; i += 2) {
        var k = post[i], value = share * post[i + 1], held = best[k];
        // The larger counts; between two equal, the word first in order, as
        // the engine has it, whichever of the two is met first.
        if (!held || value > held[0] || (value === held[0] && word < held[1])) best[k] = [value, word];
      }
    }

    function take(best, ownWord, w, typed) {
      Object.keys(best).forEach(function (k) {
        var value = best[k][0], word = best[k][1];
        // A word had whole is said as it was typed: "rdbms", not "rdbm".
        if (typed && word === w) word = typed;
        if (!has(score, k)) score[k] = 0;
        if (ownWord) {
          score[k] += value;
          matched[k] = (matched[k] || 0) + 1;
        } else {
          extra[k] = (extra[k] || 0) + value;
        }
        if (!has(said, k)) said[k] = [];
        if (said[k].indexOf(word) === -1) said[k].push(word);
      });
    }

    q.own.forEach(function (pair) {
      var w = pair[0], typed = pair[1], best = {}, found = false;
      if (has(terms, w)) offer(best, w, WHOLE);
      // A number is whole or nothing: "01" is not the start of "010".
      if (!isNumber(w)) {
        p.vocab.forEach(function (t) {
          if (t !== w && t.indexOf(typed) === 0) offer(best, t, START);
        });
      }
      for (var k in best) { if (has(best, k)) { found = true; break; } }
      if (!found && w.length >= NEAR_FROM && !isNumber(w)) {
        var mine = grams(w);
        p.vocab.forEach(function (t) {
          if (near(mine, gramsOf(p, t))) offer(best, t, NEAR);
        });
      }
      take(best, true, w, typed);
    });
    q.added.forEach(function (w) {
      var best = {};
      if (has(terms, w)) offer(best, w, ADDED);
      take(best, false);
    });

    var named = key(q.own.map(function (pair) { return pair[0]; }));
    var hits = Object.keys(score).map(Number).filter(function (k) {
      return !opts.type || docs[k][1] === opts.type;
    }).map(function (k) {
      var d = docs[k];
      return {
        k: k, id: d[0], type: d[1], name: d[2], size: d[3],
        matched: matched[k] || 0,
        named: !!named && (named === d[4] || named === d[5]),
        score: score[k], added: extra[k] || 0, words: said[k],
      };
    });
    hits.sort(function (a, b) {
      return (b.matched - a.matched) || ((a.named ? 0 : 1) - (b.named ? 0 : 1)) || (b.score - a.score)
        || (a.size - b.size) || (b.added - a.added) || cmp(a.id, b.id) || cmp(a.type, b.type) || (a.k - b.k);
    });
    if (opts.limit > 0) hits = hits.slice(0, opts.limit);
    return hits.map(function (h) {
      return { id: h.id, type: h.type, name: h.name, matched: h.matched, named: h.named,
        score: h.score, added: h.added, words: h.words };
    });
  }

  root.TerraneSearch = { search: search, words: words, singular: singular, VERSION: VERSION };
})(typeof window !== "undefined" ? window : this);
