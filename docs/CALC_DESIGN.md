# CALC item type - Architecture Decision Record

This document records the design decisions behind the `CALC` (arithmetic /
formula) question type.  It is kept in the repository so that upstream
reviewers can evaluate every trade-off and downstream contributors can extend
the implementation with confidence.

---

## 1. What is a CALC item?

A CALC item presents a question whose values vary each attempt.  Named
placeholders in the question text are replaced with randomly drawn numbers; a
formula string then determines the expected answer.  Most LMSes call these
"calculated", "formula", or "numeric formula" questions.

Analogues in other systems:

| System | Name |
|---|---|
| Canvas LMS | `calculated_question` |
| Blackboard Learn | `FIL` (Fill-In-the-Blank with formula) |
| Moodle | `calculated` question type |
| QTI 2.1 | `customInteraction` (no native formula type) |

---

## 2. Data model

### Constructor

```python
CALC(question_text, variables, formula, tolerance_pct=5.0)
```

### Fields

| Field | Type | Description |
|---|---|---|
| `question_text` | str | Question text with `[varname]` placeholders |
| `variables` | dict | `{varname: {"min": float, "max": float, "decimal_places": int}}` |
| `formula` | str | Python/JS arithmetic expression using bare variable names |
| `tolerance_pct` | float | Percentage tolerance, `0 < pct <= 100` (default `5.0`) |

### Example

```python
from qti_package_maker.assessment_items import item_types

item = item_types.CALC(
    question_text="A car travels [v] m/s for [t] s. Find the distance.",
    variables={
        "v": {"min": 1.0, "max": 50.0, "decimal_places": 1},
        "t": {"min": 1.0,  "max": 10.0, "decimal_places": 0},
    },
    formula="v * t",
    tolerance_pct=5.0,
)
```

---

## 3. Design decisions

### 3.1 Placeholder syntax - `[varname]`

Square brackets are chosen for consistency with the `MULTI_FIB` type (which
also uses `[key]` tokens) and with Canvas's own variable syntax.  Any
identifier that appears inside `[...]` in the question text must be declared in
the `variables` dict.

### 3.2 Formula syntax - bare identifier expressions

The formula uses bare Python/JS identifier names (e.g. `v * t`) without
bracket delimiters.  This allows the formula to be evaluated directly:

- **Python** (validators and Canvas var-set generation): `eval(formula, namespace)`
- **JavaScript** (HTML selftest): `new Function(arg_names, 'return (' + formula + ');')`

Only a safe allowlist of characters and names is permitted (alphanumerics,
arithmetic operators, parentheses, math function names).  Dangerous constructs
(`import`, `eval`, `exec`, `__`) are rejected at validation time.

### 3.3 Tolerance as percentage

Most LMSes express formula-question tolerance as a percentage rather than an
absolute range.  Storing only `tolerance_pct` avoids the need to normalise or
cache a computed answer in the item object, and it remains meaningful across
different random variable draws.

### 3.4 No pre-computed answers in the item object

The `CALC` class does not store a concrete expected answer.  Engines that need
one (Canvas `<var_sets>`) generate them deterministically at write time by
sweeping the variable ranges.  This keeps the item lightweight and
format-independent.

### 3.5 CRC derivation

The secondary CRC is derived from:

```
formula + "|" + "|".join(
    f"{name}:{min}:{max}:{decimal_places}"
    for name, spec in sorted(variables.items())
)
```

Sorting by name ensures that two `CALC` items that are structurally identical
hash to the same CRC regardless of the insertion order of the `variables` dict.

### 3.6 JavaScript formula evaluation security

The HTML selftest evaluates the formula as:

```javascript
var fn = new Function(arg_names_csv, 'return (' + formula + ');');
var result = fn(val1, val2, ...);
```

Variable values are injected as named formal arguments, not concatenated into
the expression string.  Student input is **never** passed to `new Function` or
`eval`; only the pre-validated formula (written by the author) enters the
function body.

### 3.7 Blackboard QTI 2.1 deferred

The Blackboard Learn and Ultra QTI 2.1 formats lack a standardised calculated-
question element; they use proprietary extensions that are underdocumented and
require an LMS sandbox to verify.  Both engines currently return `None` for
CALC items (silently skipped) with a `TODO` comment.  This can be filled in
once a reference export sample is available.

---

## 4. Engine-by-engine mapping

| Engine | Supported | Notes |
|---|---|---|
| `canvas_qti_v1_2` | Yes | `calculated_question`; uses `<itemproc_extension><calculated>` |
| `bbq_text_upload` | Yes | `FIL` type; variables in sorted order |
| `html_selftest` | Yes | JS randomisation + `new Function` formula evaluation |
| `human_readable` | Yes | Labelled text block |
| `blackboard_qti_v2_1` | No (TODO) | Proprietary extension not yet mapped |
| `bb_ultra_qti_v2_1` | No (TODO) | Proprietary extension not yet mapped |
| `text2qti` | No | text2qti format has no formula question type |

---

## 5. Canvas QTI 1.2 format details

Canvas expects the following structure inside each `<item>`:

```xml
<item ident="calculated_001" title="...">
  <itemmetadata>
    <fieldentry>calculated_question</fieldentry>
  </itemmetadata>
  <presentation> ... numeric input ... </presentation>
  <resprocessing> ... </resprocessing>
  <itemproc_extension>
    <calculated>
      <answer_tolerance type="percent">5.0</answer_tolerance>
      <formulas decimal_places="1">
        <formula>v * t</formula>
      </formulas>
      <vars>
        <var name="t" scale="0"><min>1.0</min><max>10.0</max></var>
        <var name="v" scale="1"><min>1.0</min><max>50.0</max></var>
      </vars>
      <var_sets>
        <var_set ident="set_001">
          <var name="t">1</var><var name="v">1.0</var>
          <answer>1.0</answer>
        </var_set>
        ...
      </var_sets>
    </calculated>
  </itemproc_extension>
</item>
```

Ten var-sets are generated by evenly spacing each variable's range across
`num_var_sets = 10` steps so that output is deterministic across runs.

---

## 6. BBQ text upload format details

Blackboard's `FIL` type:

```
FIL<TAB><question_html><TAB><varname><TAB><min><TAB><max><TAB><scale><TAB>...<TAB><formula><TAB><tolerance_pct>
```

Variables are serialised in sorted (alphabetical) order.  `scale` is the
`decimal_places` field.

---

## 7. Open questions

- Should `decimal_places` apply to the expected answer as well as the variable
  draw?  (Currently `max_decimal_places` across variables is used for the
  Canvas answer.)
- Should `tolerance_pct` accept `0` (exact match)?  Currently rejected.
- Should the Moodle `calculated` format be added as a future engine?
- Should CALC items be allowed to reference other CALC-derived sub-expressions
  (i.e. multi-formula chains)?

---

## 8. References

- [Canvas calculated question format](https://canvas.instructure.com/doc/api/file.qti.html)
- [Blackboard FIL question type](https://help.blackboard.com/Learn/Instructor/Ultra/Tests_Pools_Surveys/Question_Types/Calculated_Formula_Questions)
- [IMS QTI 2.1 spec](https://www.imsglobal.org/question/qtiv2p1/imsqti_infov2p1.html)
