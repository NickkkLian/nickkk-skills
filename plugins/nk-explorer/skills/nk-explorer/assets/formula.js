/* formula.js — the formula language of an nk-explorer page: parse, evaluate, write back. It is inlined into the page
   (make_explorer.py copies it between the markers below); scripts/formula.py is the same language written a second
   time, in Python, so a checker can recompute what the page shows. The two are compared case by case.
   Numbers, control names, + - * / ^ (power, right to left), unary minus, parentheses, and min max abs sqrt exp ln
   log10 floor ceil round. A name the language does not know is an error, never a lookup: no eval, no property
   access, nothing reachable but the page's own control values. */
/* formula:start */
var Formula = (function () {
  "use strict";
  var FUNCS = { min: [2, Infinity], max: [2, Infinity], abs: [1, 1], sqrt: [1, 1], exp: [1, 1], ln: [1, 1],
                log10: [1, 1], floor: [1, 1], ceil: [1, 1], round: [1, 2] };
  var TOKEN = /^\s*(?:(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\*\*|[-+*\/^(),]))/;
  function FormulaError(message) { this.message = message; }
  FormulaError.prototype.toString = function () { return this.message; };
  function fail(m) { throw new FormulaError(m); }
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  function tokens(src) {
    var out = [], rest = src.replace(/\s+$/, ""), at = 0;
    while (rest.length) {
      var m = TOKEN.exec(rest);
      if (!m || !m[0].length) fail("unexpected character at " + (at + 1) + ": '" + rest.slice(0, 12).trim() + "'");
      if (m[1] !== undefined) {
        if (!isFinite(parseFloat(m[1]))) fail("the number " + m[1] + " is too large");
        out.push(["num", parseFloat(m[1]), m[1]]);
      }
      else if (m[2] !== undefined) out.push(["name", m[2], m[2]]);
      else out.push(["op", m[3] === "**" ? "^" : m[3], m[3]]);
      at += m[0].length; rest = rest.slice(m[0].length);
    }
    return out;
  }

  function parse(src) {
    var toks = tokens(src), pos = 0;
    function peek() { return pos < toks.length ? toks[pos] : ["end", null]; }
    function is(kind, value) { var t = peek(); return t[0] === kind && t[1] === value; }
    function shown(t) { return t[0] === "end" ? "the end" : t[2]; }
    function take(kind, value) {
      var t = peek();
      if ((kind && t[0] !== kind) || (value !== undefined && t[1] !== value)) fail("expected '" + (value !== undefined ? value : kind) + "' but found '" + shown(t) + "'");
      pos++; return t;
    }
    function expr() { var n = term(); while (is("op", "+") || is("op", "-")) { var op = take()[1]; n = ["bin", op, n, term()]; } return n; }
    function term() { var n = unary(); while (is("op", "*") || is("op", "/")) { var op = take()[1]; n = ["bin", op, n, unary()]; } return n; }
    function unary() {
      if (is("op", "-")) { take(); return ["neg", unary()]; }
      if (is("op", "+")) { take(); return unary(); }
      return power();
    }
    function power() { var b = atom(); if (is("op", "^")) { take(); return ["bin", "^", b, unary()]; } return b; }
    function atom() {
      var t = peek();
      if (t[0] === "num") { take(); return ["num", t[1], t[2]]; }
      if (t[0] === "name") {
        take();
        if (is("op", "(")) {
          if (!has(FUNCS, t[1])) fail("unknown function '" + t[1] + "'; the language has " + Object.keys(FUNCS).sort().join(", "));
          take("op", "(");
          var args = [expr()];
          while (is("op", ",")) { take(); args.push(expr()); }
          take("op", ")");
          var lo = FUNCS[t[1]][0], hi = FUNCS[t[1]][1];
          if (args.length < lo || args.length > hi) fail(t[1] + "() takes " + lo + (hi === lo ? "" : hi === Infinity ? " or more" : " to " + hi) + " argument(s), not " + args.length);
          return ["call", t[1], args];
        }
        if (has(FUNCS, t[1])) fail(t[1] + " is a function: write " + t[1] + "(…)");
        return ["var", t[1]];
      }
      if (is("op", "(")) { take(); var n = expr(); take("op", ")"); return ["group", n]; }
      fail("expected a number, a name or '(' but found '" + shown(t) + "'");
    }
    var tree = expr();
    if (peek()[0] !== "end") fail("unexpected '" + peek()[2] + "' after a complete formula");
    return tree;
  }

  function names(tree) {
    var out = [];
    (function walk(n) {
      if (n[0] === "var" && out.indexOf(n[1]) < 0) out.push(n[1]);
      for (var i = 1; i < n.length; i++) {
        if (Array.isArray(n[i]) && typeof n[i][0] === "string") walk(n[i]);
        else if (Array.isArray(n[i])) n[i].forEach(walk);
      }
    })(tree);
    return out;
  }

  /* every step of the working has to be a finite number, as in formula.py: 1/exp(1000) has no value here either,
     rather than 0 on the page and an error in the checker */
  function finite(r) {
    if (typeof r !== "number" || !isFinite(r)) fail("part of the working is not a finite number");
    return r;
  }

  /* round(), floor() and ceil() finish their argument's working in decimal before they round, as formula.py's
     exact() does: each number as written in the formula, each value as written on the line with numbers, and + - * /
     and whole powers done exactly, on fractions of BigInts. A step with no exact decimal result (sqrt, exp, ln, log10,
     a fractional power or one larger than EXACT_POWER, a division by a working that is exactly zero) is taken as the
     number the page computes for it, as written. So round(8.5 * 10.45, 2) is 88.83 and ceil(2.1 / 0.3) is 7 here,
     in the checker and by hand. */
  var EXACT_POWER = 400, B0 = BigInt(0), B1 = BigInt(1), B10 = BigInt(10);
  function babs(n) { return n < B0 ? -n : n; }
  function gcd(a, b) { a = babs(a); b = babs(b); while (b !== B0) { var t = a % b; a = b; b = t; } return a; }
  function frac(n, d) {
    if (d < B0) { n = -n; d = -d; }
    var g = gcd(n, d); if (g > B1) { n = n / g; d = d / g; }
    return [n, d];
  }
  function pow10(k) { var r = B1; for (var i = 0; i < k; i++) r = r * B10; return r; }
  /* the exact value of a decimal numeral: 12.5, .5, 1.5e3, 1e-7 */
  function decimal(text) {
    var m = /^(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(text);
    var whole = m[1] || "", part = m[2] || "", e = (m[3] ? parseInt(m[3], 10) : 0) - part.length;
    var n = BigInt((whole + part).replace(/^0+(?=\d)/, "") || "0");
    return e >= 0 ? frac(n * pow10(e), B1) : frac(n, pow10(-e));
  }
  /* a number as written: its shortest decimal digits, from toExponential() (formula.py's repr() gives the same) */
  function written(x) {
    var parts = Math.abs(x).toExponential().split("e"), q = decimal(parts[0] + "e" + parts[1]);
    return x < 0 ? [-q[0], q[1]] : q;
  }
  function add(a, b) { return frac(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }
  function mul(a, b) { return frac(a[0] * b[0], a[1] * b[1]); }
  function cmp(a, b) { var l = a[0] * b[1], r = b[0] * a[1]; return l < r ? -1 : l > r ? 1 : 0; }
  function floorOf(q) { var t = q[0] / q[1]; return (q[0] < B0 && t * q[1] !== q[0]) ? t - B1 : t; }
  function ceilOf(q) { var t = q[0] / q[1]; return (q[0] > B0 && t * q[1] !== q[0]) ? t + B1 : t; }
  function scale(q, d) { return d >= 0 ? frac(q[0] * pow10(d), q[1]) : frac(q[0], q[1] * pow10(-d)); }
  function exactRounding(f, q, d) {
    if (f === "floor") return [floorOf(q), B1];
    if (f === "ceil") return [ceilOf(q), B1];
    var whole = floorOf(add(scale([babs(q[0]), q[1]], d), [B1, BigInt(2)]));
    return scale([q[0] < B0 ? -whole : whole, B1], -d);
  }
  function exact(tree, values, approx) {
    function ex(n) {
      var k = n[0];
      if (k === "num") return decimal(n.length > 2 ? n[2] : String(n[1]));
      if (k === "var") return written(Number(values[n[1]]));
      if (k === "group") return ex(n[1]);
      if (k === "neg") { var v = ex(n[1]); return [-v[0], v[1]]; }
      if (k === "bin") {
        var a = ex(n[2]), b = ex(n[3]), op = n[1];
        if (op === "+") return add(a, b);
        if (op === "-") return add(a, [-b[0], b[1]]);
        if (op === "*") return mul(a, b);
        if (op === "/") return b[0] !== B0 ? frac(a[0] * b[1], a[1] * b[0]) : written(approx(n));
        if (b[1] === B1 && babs(b[0]) <= BigInt(EXACT_POWER) && !(a[0] === B0 && b[0] < B0)) {
          var p = Number(b[0]), r = [B1, B1];
          for (var i = 0; i < Math.abs(p); i++) r = mul(r, a);
          return p < 0 ? frac(r[1], r[0]) : r;
        }
        return written(approx(n));
      }
      if (k === "call") {
        var f = n[1];
        if (f === "round" || f === "floor" || f === "ceil") return exactRounding(f, ex(n[2][0]), n[2].length > 1 ? Math.trunc(approx(n[2][1])) : 0);
        if (f === "min" || f === "max") {
          return n[2].map(ex).reduce(function (m, q) { return (f === "min" ? cmp(q, m) < 0 : cmp(q, m) > 0) ? q : m; });
        }
        if (f === "abs") { var w = ex(n[2][0]); return [babs(w[0]), w[1]]; }
        return written(approx(n));
      }
      fail("unknown node " + k);
    }
    return ex(tree);
  }
  /* the exact result as the page's number: its decimal digits read once by parseFloat, correctly rounded — the same
     text formula.py hands to float() */
  function asDouble(f, q, d) {
    if (f !== "round") return parseFloat(q[0].toString());
    var whole = scale(q, d)[0];
    return parseFloat((q[0] < B0 ? "-" : "") + babs(whole).toString() + "e" + (-d));
  }

  function evaluate(tree, values) {
    function ev(n) { return finite(step(n)); }
    function step(n) {
      var k = n[0];
      if (k === "num") return n[1];
      if (k === "var") { if (!has(values, n[1])) fail("'" + n[1] + "' is not a control on this page"); return Number(values[n[1]]); }
      if (k === "group") return ev(n[1]);
      if (k === "neg") return -ev(n[1]);
      if (k === "bin") {
        var a = ev(n[2]), b = ev(n[3]), op = n[1];
        if (op === "+") return a + b;
        if (op === "-") return a - b;
        if (op === "*") return a * b;
        if (op === "/") { if (b === 0) fail("division by zero"); return a / b; }
        if (a < 0 && b !== Math.trunc(b)) fail("a negative number to a fractional power");
        if (a === 0 && b < 0) fail("zero to a negative power");
        return Math.pow(a, b);
      }
      if (k === "call") {
        var args = n[2].map(ev), f = n[1], x = args[0];
        if (f === "sqrt") { if (x < 0) fail("the square root of a negative number"); return Math.sqrt(x); }
        if (f === "ln") { if (x <= 0) fail("ln of a number that is not positive"); return Math.log(x); }
        if (f === "log10") { if (x <= 0) fail("log10 of a number that is not positive"); return Math.log10(x); }
        if (f === "round" || f === "floor" || f === "ceil") {
          var d = args.length > 1 ? Math.trunc(args[1]) : 0;
          return asDouble(f, exactRounding(f, exact(n[2][0], values, ev), d), d);
        }
        if (f === "min") return Math.min.apply(null, args);
        if (f === "max") return Math.max.apply(null, args);
        return { abs: Math.abs, exp: Math.exp }[f](x);
      }
      fail("unknown node " + k);
    }
    var r = ev(tree);
    if (typeof r !== "number" || !isFinite(r)) fail("the result is not a finite number");
    return r;
  }

  /* numbers as the page shows them — the same rule as formula.py's fmt(): whole numbers plainly; others rounded to
     six significant digits by toExponential (half away from zero on the exact value), trailing zeros dropped, and
     e-notation when the rounded exponent is below -4 or 6 and up. The digits are placed by hand rather than by
     toPrecision, which switches notation on its own rule. */
  function fmt(x) {
    x = Number(x);
    if (x === Math.trunc(x) && Math.abs(x) < 1e15) return String(x === 0 ? 0 : x);
    var sign = x < 0 ? "-" : "", s = Math.abs(x).toExponential(5);
    var e = parseInt(s.split("e")[1], 10), digits = s.split("e")[0].replace(".", "");
    if (e < -4 || e >= 6) return sign + digits.charAt(0) + ("." + digits.slice(1)).replace(/0+$/, "").replace(/\.$/, "") + "e" + e;
    var out = e >= 0 ? digits.slice(0, e + 1) + "." + digits.slice(e + 1) : "0." + new Array(-e).join("0") + digits;
    if (out.indexOf(".") >= 0) out = out.replace(/0+$/, "").replace(/\.$/, "");
    return sign + out;
  }

  /* a number in the formula is written as it was typed; a negative value goes in brackets, so the line with values
     works out to the result: 1 × (-3)^2, not 1 × -3^2 (formula.py's write() is the same) */
  function write(tree, values) {
    function w(n) {
      var k = n[0];
      if (k === "num") return n.length > 2 ? n[2] : fmt(n[1]);
      if (k === "var") {
        if (!values) return n[1];
        return Number(values[n[1]]) < 0 ? "(" + fmt(values[n[1]]) + ")" : fmt(values[n[1]]);
      }
      if (k === "group") return "(" + w(n[1]) + ")";
      if (k === "neg") return "-" + w(n[1]);
      if (k === "bin") return w(n[2]) + ({ "+": " + ", "-": " - ", "*": " × ", "/": " ÷ ", "^": "^" })[n[1]] + w(n[3]);
      if (k === "call") return n[1] + "(" + n[2].map(w).join(", ") + ")";
    }
    return w(tree);
  }

  /* the same text as write(tree, values), cut into parts: [text, name] where the text is a control's value and name
     is that control, [text, null] for everything else — so the page can mark the value that just changed while the
     line still reads exactly what write() gives */
  function parts(tree, values) {
    var out = [];
    function push(t, name) { out.push([t, name || null]); }
    function w(n) {
      var k = n[0];
      if (k === "num") return push(n.length > 2 ? n[2] : fmt(n[1]));
      if (k === "var") {
        var neg = Number(values[n[1]]) < 0;
        if (neg) push("(");
        push(fmt(values[n[1]]), n[1]);
        return neg ? push(")") : undefined;
      }
      if (k === "group") { push("("); w(n[1]); return push(")"); }
      if (k === "neg") { push("-"); return w(n[1]); }
      if (k === "bin") { w(n[2]); push(({ "+": " + ", "-": " - ", "*": " \u00d7 ", "/": " \u00f7 ", "^": "^" })[n[1]]); return w(n[3]); }
      if (k === "call") {
        push(n[1] + "(");
        n[2].forEach(function (a, i) { if (i) push(", "); w(a); });
        return push(")");
      }
    }
    w(tree);
    return out;
  }

  return { parse: parse, names: names, evaluate: evaluate, write: write, parts: parts, fmt: fmt, FormulaError: FormulaError };
})();
/* formula:end */
if (typeof module !== "undefined") module.exports = Formula;
