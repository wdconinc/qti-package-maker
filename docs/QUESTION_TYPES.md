# Question types

QTI Package Maker supports seven essential question types commonly used in
assessments. Each type uses a consistent set of inputs.

## Multiple Choice (MC)
**Inputs:**
- `question_text` (str): The question prompt.
- `choices_list` (list): A list of answer choices.
- `answer_text` (str): The correct answer.

## Multiple Answer (MA)
**Inputs:**
- `question_text` (str)
- `choices_list` (list)
- `answers_list` (list): A list of correct answers.

## Matching (MATCH)
**Inputs:**
- `question_text` (str)
- `prompts_list` (list): Items to be matched.
- `choices_list` (list): Possible matching answers.

## Numerical Entry (NUM)
**Inputs:**
- `question_text` (str)
- `answer_float` (float): The correct numerical answer.
- `tolerance_float` (float): Accepted tolerance range.
- `tolerance_message` (bool, default=True): Message for tolerance handling.

## Fill-in-the-Blank (FIB)
**Inputs:**
- `question_text` (str)
- `answers_list` (list): List of acceptable answers.

## Multi-Part Fill-in-the-Blank (MULTI_FIB)
**Inputs:**
- `question_text` (str)
- `answer_map` (dict): A dictionary mapping blank positions to correct answers.

## Ordered List (ORDER)
**Inputs:**
- `question_text` (str)
- `ordered_answers_list` (list): The correct sequence of answers.

## Calculated / Formula (CALC)
**Inputs:**
- `question_text` (str): Question text containing `[varname]` placeholders, e.g.
  `"A car travels [v] m/s for [t] s. Find the distance."`.
- `variables` (dict): Maps each variable name to a specification dict:
  `{"min": float, "max": float, "decimal_places": int}`.
- `formula` (str): Python/JS arithmetic expression using bare variable names,
  e.g. `"v * t"`.
- `tolerance_pct` (float, default=5.0): Percentage tolerance (0 < pct <= 100).

**Behaviour:** Each attempt the LMS (or the HTML selftest JavaScript) draws
random values for every variable within the declared ranges and evaluates the
formula to determine the expected answer.  The student response is accepted when
it is within `tolerance_pct` percent of that expected value.

See [CALC_DESIGN.md](CALC_DESIGN.md) for the full architecture decision record.
