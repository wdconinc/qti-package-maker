# Standard Library
import json

# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions

#==============
def generate_core_html(crc16_text: str, question_text: str, variables: dict) -> str:
	"""
	Build the static HTML shell for a CALC item.

	The question text contains [varname] placeholders.  JavaScript replaces
	those with randomly drawn values on DOMContentLoaded and substitutes them
	back into a display copy of the question each time the page loads.
	"""
	html_content = f"<div id=\"question_html_{crc16_text}\">\n"
	# Question statement - placeholder text is filled by JS at load time
	html_content += html_functions.format_question_text(crc16_text, question_text)
	html_content += "<div>\n"
	html_content += (
		f"<input type=\"text\" class=\"qti-input\" id=\"calc_input_{crc16_text}\" "
		"inputmode=\"decimal\" pattern=\"[0-9]*[.,]?[0-9]*\" "
		"placeholder=\"Enter your answer\" />\n"
	)
	html_content += html_functions.add_check_answer_button(crc16_text)
	html_content += html_functions.add_result_div(crc16_text)
	html_content += "</div><br/>\n"
	html_content += "</div>"
	return html_content


#==============
def generate_javascript(crc16_text: str, variables: dict,
		formula: str, tolerance_pct: float) -> str:
	"""
	Build JavaScript that:
	1. On DOMContentLoaded, randomises variable values within their declared
	   ranges, substitutes them into the question text, and caches the expected
	   answer.
	2. On "Check Answer", compares the student input against the expected answer
	   using percentage tolerance.

	Security: the formula is evaluated via `new Function(...)` with variable
	values injected as named arguments - student input is never eval()'d.
	"""
	sorted_vars = sorted(variables.items())
	var_names_js = ', '.join(f'"{name}"' for name, _ in sorted_vars)
	var_specs_js_parts = []
	for varname, spec in sorted_vars:
		var_specs_js_parts.append(
			f'{{name: "{varname}", min: {spec["min"]}, max: {spec["max"]}, '
			f'decimal_places: {spec["decimal_places"]}}}'
		)
	var_specs_js = '[' + ', '.join(var_specs_js_parts) + ']'
	arg_names = ', '.join(name for name, _ in sorted_vars)

	js = "<script>\n"
	js += f"(function() {{\n"
	js += f"  var calcVarSpecs_{crc16_text} = {var_specs_js};\n"
	js += f"  var calcExpected_{crc16_text} = null;\n"
	js += f"  var calcTolerancePct_{crc16_text} = {tolerance_pct};\n"
	js += "\n"
	# Helper: round to N decimal places
	js += "  function roundTo(val, dp) {\n"
	js += "    var factor = Math.pow(10, dp);\n"
	js += "    return Math.round(val * factor) / factor;\n"
	js += "  }\n"
	js += "\n"
	# Formula function - injected as a named-argument Function, never eval'd on user input.
	# The formula is JSON-encoded to safely embed it into the JS string literal.
	formula_js = json.dumps(formula)
	js += f"  var calcFormula_{crc16_text} = new Function({var_names_js}, 'return (' + {formula_js} + ')');\n"
	js += "\n"
	# Randomise on load
	js += f"  function initCalc_{crc16_text}() {{\n"
	js += f"    var container = document.getElementById('question_html_{crc16_text}');\n"
	js += "    if (!container) { return; }\n"
	js += f"    var stmtDiv = document.getElementById('statement_text_{crc16_text}');\n"
	js += "    if (!stmtDiv) { return; }\n"
	js += f"    var vals = {{}};\n"
	js += f"    calcVarSpecs_{crc16_text}.forEach(function(spec) {{\n"
	js += "      var raw = spec.min + Math.random() * (spec.max - spec.min);\n"
	js += "      vals[spec.name] = roundTo(raw, spec.decimal_places);\n"
	js += "    });\n"
	# Substitute placeholders in the displayed text
	js += "    var displayHtml = stmtDiv.innerHTML;\n"
	js += f"    calcVarSpecs_{crc16_text}.forEach(function(spec) {{\n"
	js += "      var re = new RegExp('\\\\[' + spec.name + '\\\\]', 'g');\n"
	js += "      displayHtml = displayHtml.replace(re, '<strong>' + vals[spec.name] + '</strong>');\n"
	js += "    });\n"
	js += "    stmtDiv.innerHTML = displayHtml;\n"
	# Compute expected answer
	arg_values_str = ', '.join(f'vals["{name}"]' for name, _ in sorted_vars)
	js += f"    calcExpected_{crc16_text} = calcFormula_{crc16_text}({arg_values_str});\n"
	js += "  }\n"
	js += "\n"
	# Check answer function
	js += f"  window.checkAnswer_{crc16_text} = function() {{\n"
	js += f"    var inputEl = document.getElementById('calc_input_{crc16_text}');\n"
	js += "    if (!inputEl) { return; }\n"
	js += "    var valStr = inputEl.value.trim();\n"
	js += f"    var resultDiv = document.getElementById('result_{crc16_text}');\n"
	js += "    if (valStr === '') {\n"
	js += "      resultDiv.style.color = 'inherit';\n"
	js += "      resultDiv.textContent = 'Please enter a value.';\n"
	js += "      return;\n"
	js += "    }\n"
	js += "    var userVal = Number(valStr);\n"
	js += "    if (Number.isNaN(userVal)) {\n"
	js += "      resultDiv.style.color = 'inherit';\n"
	js += "      resultDiv.textContent = 'Please enter a valid number.';\n"
	js += "      return;\n"
	js += "    }\n"
	js += f"    if (calcExpected_{crc16_text} === null) {{\n"
	js += "      resultDiv.style.color = 'inherit';\n"
	js += "      resultDiv.textContent = 'Question not yet initialized.';\n"
	js += "      return;\n"
	js += "    }\n"
	js += f"    var expected = calcExpected_{crc16_text};\n"
	js += f"    var tolFrac = calcTolerancePct_{crc16_text} / 100.0;\n"
	js += "    var lower = expected * (1 - tolFrac);\n"
	js += "    var upper = expected * (1 + tolFrac);\n"
	js += "    if (lower > upper) { var tmp = lower; lower = upper; upper = tmp; }\n"
	js += "    var isCorrect = (userVal >= lower && userVal <= upper);\n"
	js += "    if (isCorrect) {\n"
	js += "      resultDiv.style.color = 'var(--qti-success-fg, #008000)';\n"
	js += "      resultDiv.textContent = 'CORRECT';\n"
	js += "    } else {\n"
	js += "      resultDiv.style.color = 'var(--qti-error-fg, #9b1b1b)';\n"
	js += "      resultDiv.textContent = 'Incorrect. Try again.';\n"
	js += "    }\n"
	js += "  };\n"
	js += "\n"
	# Enter key support
	js += "  document.addEventListener('DOMContentLoaded', function() {\n"
	js += f"    initCalc_{crc16_text}();\n"
	js += f"    var inputEl = document.getElementById('calc_input_{crc16_text}');\n"
	js += "    if (!inputEl) return;\n"
	js += "    inputEl.addEventListener('keydown', function(e) {\n"
	js += f"      if (e.key === 'Enter') {{ e.preventDefault(); checkAnswer_{crc16_text}(); }}\n"
	js += "    });\n"
	js += "  });\n"
	js += "})();\n"
	js += "</script>\n"
	return js


#==============
def generate_html(item_number: int, crc16_text: str, question_text: str,
		variables: dict, formula: str, tolerance_pct: float) -> str:
	raw_html = generate_core_html(crc16_text, question_text, variables)
	formatted_html = string_functions.format_html_lxml(raw_html)
	full_html = formatted_html
	full_html += generate_javascript(crc16_text, variables, formula, tolerance_pct)
	return full_html
