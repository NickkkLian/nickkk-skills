#!/usr/bin/env python3
"""formula.py — the small formula language an nk-explorer page computes with, written a second time in Python so a
checker can recompute what a page shows and compare.

    python3 formula.py "P * (1 + r/100)^n" P=1000 r=5 n=10
    python3 formula.py --selftest

The language: numbers, the names of the page's controls, + - * / and ^ (power, right to left), unary minus,
parentheses, and these functions: min max (two or more arguments), abs sqrt exp ln log10 floor ceil (one), round
(one or two: the value and a number of decimals). round, floor and ceil finish the working inside them in decimal,
exactly, before they round (see exact()), so they give what a person gets by hand. Nothing else — no assignment, no strings, no property access, no
calls to anything not on that list. That is what lets the page evaluate a formula without eval(): a name the
language does not know is an error, not a lookup.

-x^2 is -(x^2), as in mathematics. Division by zero, a negative number under sqrt, ln of a number that is not
positive, and any step of the working that is not a finite number (exp(1000), 10^400, and 1/exp(1000) too, though
its end result would be 0) are errors, reported with the part of the formula that caused them. The page stops at the
same step: a result is never worked out through an infinity on one side and not on the other.

write() puts the formula back into words the way a person reads it: a number in the formula exactly as it was typed
(1.000137 stays 1.000137, not six digits of it), and a negative value in brackets ((-3)^2, 2 × (-3)), so that the
line with values, worked out by hand or by parse() again, gives the result.
Exit: 0 printed · 1 the formula is not valid or cannot be evaluated · 2 selftest failed or usage.
"""
import math, re, sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

FUNCS = {"min": (2, None), "max": (2, None), "abs": (1, 1), "sqrt": (1, 1), "exp": (1, 1), "ln": (1, 1),
         "log10": (1, 1), "floor": (1, 1), "ceil": (1, 1), "round": (1, 2)}
TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\*\*|[-+*/^(),]))")


class FormulaError(ValueError):
    pass


def tokens(src):
    out, i = [], 0
    src = src.rstrip()
    while i < len(src):
        m = TOKEN.match(src, i)
        if not m or m.end() == i:
            raise FormulaError(f"unexpected character at {i + 1}: '{src[i:i + 12].strip()}'")
        num, name, op = m.groups()
        if num is not None:
            if not math.isfinite(float(num)):
                raise FormulaError(f"the number {num} is too large")
            out.append(("num", float(num), num))
        elif name is not None:
            out.append(("name", name, name))
        else:
            out.append(("op", "^" if op == "**" else op, op))
        i = m.end()
    return out


def parse(src):
    """Formula text → a tree of tuples: ('num', v, text) ('var', name) ('neg', a) ('bin', op, a, b) ('call', f, [args])
    ('group', a). Groups, and each number as it was typed, are kept so a formula can be written back the way it was
    given."""
    toks, pos = tokens(src), [0]

    def peek():
        return toks[pos[0]][:2] if pos[0] < len(toks) else ("end", None)

    def shown():
        return toks[pos[0]][2] if pos[0] < len(toks) else "the end"

    def take(kind=None, value=None):
        t = peek()
        if (kind and t[0] != kind) or (value is not None and t[1] != value):
            want = value or kind
            raise FormulaError(f"expected '{want}' but found '{shown()}'")
        pos[0] += 1
        return t

    def expr():
        node = term()
        while peek() in (("op", "+"), ("op", "-")):
            op = take()[1]
            node = ("bin", op, node, term())
        return node

    def term():
        node = unary()
        while peek() in (("op", "*"), ("op", "/")):
            op = take()[1]
            node = ("bin", op, node, unary())
        return node

    def unary():
        if peek() == ("op", "-"):
            take()
            return ("neg", unary())
        if peek() == ("op", "+"):
            take()
            return unary()
        return power()

    def power():
        base = atom()
        if peek() == ("op", "^"):
            take()
            return ("bin", "^", base, unary())        # right to left, and a^-b is allowed
        return base

    def atom():
        t = peek()
        if t[0] == "num":
            text = toks[pos[0]][2]
            take()
            return ("num", t[1], text)
        if t[0] == "name":
            take()
            if peek() == ("op", "("):
                if t[1] not in FUNCS:
                    raise FormulaError(f"unknown function '{t[1]}'; the language has {', '.join(sorted(FUNCS))}")
                take("op", "(")
                args = [expr()]
                while peek() == ("op", ","):
                    take()
                    args.append(expr())
                take("op", ")")
                lo, hi = FUNCS[t[1]]
                if len(args) < lo or (hi is not None and len(args) > hi):
                    raise FormulaError(f"{t[1]}() takes {lo}{'' if hi == lo else ' or more' if hi is None else f' to {hi}'} argument(s), not {len(args)}")
                return ("call", t[1], args)
            if t[1] in FUNCS:
                raise FormulaError(f"{t[1]} is a function: write {t[1]}(…)")
            return ("var", t[1])
        if t == ("op", "("):
            take()
            node = expr()
            take("op", ")")
            return ("group", node)
        raise FormulaError(f"expected a number, a name or '(' but found '{shown()}'")

    tree = expr()
    if peek()[0] != "end":
        raise FormulaError(f"unexpected '{shown()}' after a complete formula")
    return tree


def names(tree):
    """Every control name the formula reads, in order of first use."""
    out = []

    def walk(n):
        if n[0] == "var" and n[1] not in out:
            out.append(n[1])
        for child in n[1:]:
            if isinstance(child, tuple):
                walk(child)
            elif isinstance(child, list):
                for c in child:
                    walk(c)
    walk(tree)
    return out


def finite(r):
    """every step of the working has to be a finite number; the page checks the same after each step"""
    if isinstance(r, complex) or not math.isfinite(r):
        raise FormulaError("part of the working is not a finite number")
    return r


def evaluate(tree, values):
    """The value of the formula, worked in binary floating point as the page does, except that round(), floor() and
    ceil() finish their argument's working in decimal first (see exact()), so they round the number a person gets by
    hand: round(8.5 * 10.45, 2) is 88.83 and ceil(2.1 / 0.3) is 7, where rounding the binary result would give 88.82
    and 8. An error is found by the binary working, before the decimal one starts."""
    def ev(n):
        try:
            return finite(step(n))
        except (OverflowError, ZeroDivisionError):     # exp(1000), 1.5 * 10**400 and the like
            raise FormulaError("part of the working is not a finite number")

    def step(n):
        k = n[0]
        if k == "num":
            return n[1]
        if k == "var":
            if n[1] not in values:
                raise FormulaError(f"'{n[1]}' is not a control on this page")
            return float(values[n[1]])
        if k == "group":
            return ev(n[1])
        if k == "neg":
            return -ev(n[1])
        if k == "bin":
            a, b = ev(n[2]), ev(n[3])
            op = n[1]
            if op == "+":
                r = a + b
            elif op == "-":
                r = a - b
            elif op == "*":
                r = a * b
            elif op == "/":
                if b == 0:
                    raise FormulaError("division by zero")
                r = a / b
            else:
                if a < 0 and b != int(b):
                    raise FormulaError("a negative number to a fractional power")
                if a == 0 and b < 0:
                    raise FormulaError("zero to a negative power")
                r = a ** b
            return r
        if k == "call":
            args = [ev(a) for a in n[2]]
            f = n[1]
            if f == "sqrt":
                if args[0] < 0:
                    raise FormulaError("the square root of a negative number")
                return math.sqrt(args[0])
            if f == "ln":
                if args[0] <= 0:
                    raise FormulaError("ln of a number that is not positive")
                return math.log(args[0])
            if f == "log10":
                if args[0] <= 0:
                    raise FormulaError("log10 of a number that is not positive")
                return math.log10(args[0])
            if f in ("round", "floor", "ceil"):
                d = int(args[1]) if len(args) > 1 else 0
                return as_double(f, exact_rounding(f, [exact(n[2][0], values, ev)] + args[1:]), d)
            return {"min": min, "max": max, "abs": abs, "exp": math.exp}[f](*args)
        raise FormulaError(f"unknown node {k}")
    return float(ev(tree))


EXACT_POWER = 400      # a whole power larger than this is not worked exactly: its digits would run to many thousands


def written(x):
    """a number as it is written: the exact value of its shortest decimal form (the digits repr() and the page's
    toExponential() both give), so 0.3 is 3/10, not the binary double just below it"""
    return Fraction(Decimal(repr(float(x))))


def exact(tree, values, approx):
    """The working of a round(), floor() or ceil() argument done again in decimal, exactly: each number as it is
    written in the formula, each value as it is written on the line with numbers, and + - * / and whole powers as a
    person does them by hand. A step that has no exact decimal result (sqrt, exp, ln, log10, a fractional or very
    large power, and a division by a working that is exactly zero though its binary value is not) is taken as the
    number the page computes for that step, as written. approx(node) is that number."""
    def ex(n):
        k = n[0]
        if k == "num":
            return Fraction(Decimal(n[2] if len(n) > 2 else repr(n[1])))
        if k == "var":
            return written(values[n[1]])
        if k == "group":
            return ex(n[1])
        if k == "neg":
            return -ex(n[1])
        if k == "bin":
            a, b = ex(n[2]), ex(n[3])
            op = n[1]
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/":
                return a / b if b != 0 else written(approx(n))
            if b.denominator == 1 and abs(b.numerator) <= EXACT_POWER and not (a == 0 and b < 0):
                return a ** int(b)
            return written(approx(n))
        if k == "call":
            f = n[1]
            if f in ("round", "floor", "ceil"):
                return exact_rounding(f, [ex(a) for a in n[2][:1]] + [approx(a) for a in n[2][1:]])
            if f in ("min", "max"):
                args = [ex(a) for a in n[2]]
                return min(args) if f == "min" else max(args)
            if f == "abs":
                return abs(ex(n[2][0]))
            return written(approx(n))
        raise FormulaError(f"unknown node {k}")
    return ex(tree)


def exact_rounding(f, args):
    """round (halves away from zero, to d places; d may be negative), floor and ceil of an exact value"""
    q = args[0]
    if f == "floor":
        return Fraction(math.floor(q))
    if f == "ceil":
        return Fraction(math.ceil(q))
    d = int(args[1]) if len(args) > 1 else 0
    scaled = abs(q) * Fraction(10) ** d
    whole = math.floor(scaled + Fraction(1, 2))
    return (1 if q >= 0 else -1) * Fraction(whole) / Fraction(10) ** d


def as_double(f, q, d):
    """the exact result of round/floor/ceil as the page's number: its decimal digits read once, correctly rounded —
    the same text formula.js hands to parseFloat, so the twins agree"""
    if f != "round":
        return float(str(q.numerator))
    whole = q * Fraction(10) ** d
    return float(("-" if q < 0 else "") + str(abs(whole.numerator)) + "e" + str(-d))


def write(tree, values=None):
    """The formula written back: symbols as given, or — with values — each name replaced by its value. × for *, ÷ for
    /, and ^ for power, so the page and a person read the same thing. A number in the formula is written as it was
    typed; a negative value goes in brackets, so the line still works out to the result: 1 × (-3)^2, not 1 × -3^2."""
    def w(n):
        k = n[0]
        if k == "num":
            return n[2] if len(n) > 2 else fmt(n[1])
        if k == "var":
            if values is None:
                return n[1]
            return "(" + fmt(values[n[1]]) + ")" if float(values[n[1]]) < 0 else fmt(values[n[1]])
        if k == "group":
            return "(" + w(n[1]) + ")"
        if k == "neg":
            return "-" + w(n[1])
        if k == "bin":
            sym = {"+": " + ", "-": " - ", "*": " × ", "/": " ÷ ", "^": "^"}[n[1]]
            return w(n[2]) + sym + w(n[3])
        if k == "call":
            return n[1] + "(" + ", ".join(w(a) for a in n[2]) + ")"
    return w(tree)


def fmt(x):
    """A number as the page shows it: whole numbers without a decimal point; others rounded to six significant
    digits, half away from zero on the number's exact value (the page's toExponential does the same, so the two agree
    even on a tie such as 123456.5), trailing zeros dropped, and e-notation when the rounded exponent is below -4 or
    6 and up."""
    x = float(x)
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    sign, d = ("-" if x < 0 else ""), Decimal(abs(x))
    e = d.adjusted()
    q = d.quantize(Decimal(1).scaleb(e - 5), rounding=ROUND_HALF_UP)
    if q.adjusted() != e:                      # 9.999995 rounds up to 10.0000: one more digit
        e = q.adjusted()
        q = d.quantize(Decimal(1).scaleb(e - 5), rounding=ROUND_HALF_UP)
    digits = str(int(q.scaleb(5 - e)))
    if e < -4 or e >= 6:
        return sign + digits[0] + ("." + digits[1:]).rstrip("0").rstrip(".") + "e" + str(e)
    out = digits[:e + 1] + "." + digits[e + 1:] if e >= 0 else "0." + "0" * (-e - 1) + digits
    return sign + (out.rstrip("0").rstrip(".") if "." in out else out)


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c)
        lines.append(f"  {'✔' if c else '✘'} {label}")

    def val(src, **v):
        return evaluate(parse(src), v)

    def err(src, **v):
        try:
            evaluate(parse(src), v)
        except FormulaError as e:
            return str(e)
        return None

    chk(abs(val("P * (1 + r/100)^n", P=1000, r=5, n=10) - 1628.894626777442) < 1e-9, "compound interest: 1000 at 5% for 10 years")
    chk(val("2^3^2") == 512, "power runs right to left: 2^3^2 = 2^9")
    chk(val("-2^2") == -4 and val("(-2)^2") == 4, "-x^2 is -(x^2); (-x)^2 is not")
    chk(val("10 - 4 - 3") == 3 and val("24 / 4 / 3") == 2, "- and / run left to right")
    chk(val("2 * 3 + 4") == 10 and val("2 * (3 + 4)") == 14, "* before +, and parentheses change it")
    chk(val("2^-1") == 0.5, "a negative exponent needs no parentheses")
    chk(val("min(3, 1, 2) + max(4, 9)") == 10, "min and max take two or more arguments")
    chk(val("round(2.5) + round(-2.5) + round(1.2345, 2)") == 1.23, "round is half away from zero (2.5 → 3, -2.5 → -3)")
    # worked by hand, not by either twin: the number as written, halves away from zero
    by_hand = {"round(1.275, 2)": 1.28, "round(510 * 3 / 1200, 2)": 1.28, "round(1.005, 2)": 1.01, "round(0.285, 2)": 0.29,
               "round(2.675, 2)": 2.68, "round(-1.275, 2)": -1.28, "round(0.125, 2)": 0.13, "round(1234.5, -1)": 1230,
               "round(1235, -1)": 1240, "round(0.6)": 1, "round(0.004, 1)": 0, "round(99.95, 1)": 100}
    wrong = {src: val(src) for src, want in by_hand.items() if val(src) != want}
    chk(not wrong, "round works on the number as written, checked against answers worked out by hand"
        + "".join(f"; {src} gives {got}" for src, got in wrong.items()))
    # several steps of working before the rounding, each worked by hand in decimal (0.1.0 rounded the binary working
    # and gave the number after the arrow)
    by_hand = {"round(8.5 * 10.45, 2)": 88.83,                  # 88.825 → 88.83; binary 88.82499999999999 → 88.82
               "round(1000 * (1 + 4.5 / 100)^2, 2)": 1092.03,    # 1092.025 → 1092.03; binary → 1092.02
               "round(h * w, 2)": 88.83,                          # the same, with the values from controls
               "round(0.1 + 0.2, 16)": 0.3,                       # 0.3 exactly; binary 0.30000000000000004
               "round(2.675 * 1, 2)": 2.68, "round(-8.5 * 10.45, 2)": -88.83,
               "ceil(2.1 / 0.3)": 7,                              # 7 exactly; binary 7.000000000000001 → 8
               "ceil(L / w)": 7, "floor(0.3 / 0.1)": 3,          # binary 2.9999999999999996 → 2
               "floor(0.29 * 100)": 29,                           # binary 28.999999999999996 → 28
               "floor(-0.3 / 0.1)": -3, "ceil(-2.1 / 0.3)": -7,
               "round(round(8.5 * 10.45, 2) * 3, 1)": 266.5,      # 88.83 × 3 = 266.49 → 266.5
               "round(1234.5 * 1, -1)": 1230, "round(sqrt(2) * sqrt(2), 2)": 2}
    got = {src: val(src, L=2.1, w=0.3) if "L" in src else val(src, h=8.5, w=10.45) for src in by_hand}
    wrong = {src: g for src, g in got.items() if g != by_hand[src]}
    chk(not wrong, "round, floor and ceil finish the working in decimal first, checked against answers worked out by hand"
        + "".join(f"; {src} gives {got}" for src, got in wrong.items()))
    chk(val("1.5e3 + .5") == 1500.5, "e-notation and a leading decimal point")
    chk(val("2 ** 10") == 1024, "** is accepted as ^")
    for src, want in [("1 / 0", "division by zero"), ("sqrt(-1)", "square root of a negative"), ("ln(0)", "not positive"),
                      ("(-8)^(1/3)", "fractional power"), ("0^-1", "zero to a negative power"), ("q + 1", "not a control"),
                      ("10^400", "not a finite number"), ("exp(1000)", "not a finite number")]:
        chk(want in (err(src) or ""), f"error: {src} → {want}")
    for src in ["alert(1)", "constructor", "__proto__", "x.y", "a = 1", "'text'", "sqrt 4", "max(1)", "abs(1, 2)", "1 +", "(1", "1 2"]:
        try:
            evaluate(parse(src), {"x": 1, "a": 1, "constructor": 1, "__proto__": 1} if src in ("constructor", "__proto__") else {"x": 1, "a": 1})
            refused = src in ("constructor", "__proto__")          # names are fine when the page has such a control
        except FormulaError:
            refused = True
        chk(refused, f"refused or harmless: {src!r}")
    t = parse("P * (1 + r/100)^n")
    chk(names(t) == ["P", "r", "n"], "the names a formula reads, in order")
    chk(write(t) == "P × (1 + r ÷ 100)^n", f"written back symbolically ({write(t)})")
    chk(write(t, {"P": 1000, "r": 5, "n": 10}) == "1000 × (1 + 5 ÷ 100)^10", "written back with the values in place")
    q = parse("a * x^2 + b * x + c")
    line = write(q, {"a": 1, "b": 2, "c": 0, "x": -3})
    chk(line == "1 × (-3)^2 + 2 × (-3) + 0" and val(line.replace("×", "*").replace("÷", "/")) == 3 == val("a * x^2 + b * x + c", a=1, b=2, c=0, x=-3),
        f"a negative value is written in brackets, so the line works out to the result ({line} = 3)")
    d = parse("P * 1.000137^(365 * n)")
    line = write(d, {"P": 1000, "n": 10})
    chk(line == "1000 × 1.000137^(365 × 10)" and val(line.replace("×", "*")) == val("P * 1.000137^(365 * n)", P=1000, n=10),
        f"a number in the formula is written as it was typed, not to six digits ({line})")
    chk(write(parse("1.5e3 + .5 + 2 ** 3")) == "1.5e3 + .5 + 2^3", "numbers keep their own spelling (1.5e3, .5); ** is written as ^")
    for src, v in [("1 / exp(x)", {"x": 1000}), ("min(exp(x), 5)", {"x": 1000}), ("1 / 10^x", {"x": 400}), ("min(5, x * x - x * x)", {"x": 1e200})]:
        chk("not a finite number" in (err(src, **v) or ""), f"no value when a step of the working is not finite, even if the end would be: {src} at {v}")
    chk("too large" in (err("1e400 + 1") or ""), "a number too large to be finite is refused where it is written")
    chk([fmt(x) for x in (1628.894626777442, 0.5, 3.0, 1e20, 1.23456789e-7)] == ["1628.89", "0.5", "3", "1e20", "1.23457e-7"], "numbers shown as the page shows them")
    print(f"formula selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed")
    print("\n".join(lines))
    return 0 if ok else 2


def main(argv):
    if not argv or "--selftest" in argv:
        return selftest() if "--selftest" in argv else (print(__doc__.strip().split("\n\n")[1]) or 2)
    src, values = argv[0], {}
    for a in argv[1:]:
        k, _, v = a.partition("=")
        values[k] = float(v)
    try:
        tree = parse(src)
        r = evaluate(tree, values)
    except FormulaError as e:
        print(f"✘ {e}"); return 1
    print(f"{write(tree)} = {write(tree, values)} = {fmt(r)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
