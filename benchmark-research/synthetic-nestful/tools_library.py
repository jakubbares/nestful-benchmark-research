"""Executable tool library for the synthetic NESTFUL-style generator.

Every tool carries three things:
  * ``spec``  - the NESTFUL catalogue entry (name / description / parameters /
                output_parameters) that is shown to the model at eval time;
  * ``impl``  - a real Python callable, so every generated sequence can be
                executed and the gold answer is observed, never guessed;
  * ``phrase``- a template used to mechanically render the tool-call sequence
                back into English (the "literal" query).

Two families mirror the two halves of NESTFUL:
  * ``math`` tools use positional-style ``arg_0`` / ``arg_1`` parameters and
    return a single ``result`` output parameter (MathQA-derived half);
  * ``code`` tools use named parameters and return ``output_0``
    (StarCoder2-Instruct-derived half).
The reference suffix therefore differs per family ($var_1.result$ vs
$var1.output_0$), which is exactly the thing a model has to read off the
catalogue rather than pattern-match.
"""

import json
import math
import re
from math import comb, factorial as _factorial, gcd as _gcd

TOOLS = {}


def tool(name, family, description, parameters, output_type, output_desc, phrase, **out_extra):
    """Register a tool. Decorator returns the implementation unchanged."""
    out_key = "result" if family == "math" else "output_0"
    out_spec = {"description": output_desc, "type": output_type}
    out_spec.update(out_extra)

    def deco(fn):
        TOOLS[name] = {
            "name": name,
            "family": family,
            "out_key": out_key,
            "phrase": phrase,
            "impl": fn,
            "spec": {
                "name": name,
                "description": description,
                "parameters": parameters,
                "output_parameters": {out_key: out_spec},
            },
        }
        return fn

    return deco


NUM = "int or float"


def _n(d):
    return {"description": d, "type": NUM}


# --------------------------------------------------------------------------
# math family  (arg_0 / arg_1  ->  result)
# --------------------------------------------------------------------------

@tool("add", "math", "adds two numbers",
      {"arg_0": _n("The first number"), "arg_1": _n("The second number")},
      NUM, "The addition result", "add {arg_0} to {arg_1}")
def _add(arg_0, arg_1):
    return arg_0 + arg_1


@tool("subtract", "math", "subtract two numbers",
      {"arg_0": _n("The first number"), "arg_1": _n("The second number")},
      NUM, "The subtraction result", "subtract {arg_1} from {arg_0}")
def _sub(arg_0, arg_1):
    return arg_0 - arg_1


@tool("multiply", "math", "Multiplies two numbers",
      {"arg_0": _n("The first number"), "arg_1": _n("The second number")},
      NUM, "The multiplication result", "multiply {arg_0} by {arg_1}")
def _mul(arg_0, arg_1):
    return arg_0 * arg_1


@tool("divide", "math", "divides two numbers",
      {"arg_0": _n("The first number"), "arg_1": _n("The second number")},
      NUM, "The division result", "divide {arg_0} by {arg_1}")
def _div(arg_0, arg_1):
    return arg_0 / arg_1


@tool("power", "math", "Raise a number to the given exponent",
      {"arg_0": _n("The base"), "arg_1": _n("The exponent")},
      NUM, "The power result", "raise {arg_0} to the power of {arg_1}")
def _pow(arg_0, arg_1):
    return arg_0 ** arg_1


@tool("sqrt", "math", "Calculate the square root of a number",
      {"arg_0": _n("The input number")}, "float", "The square root",
      "take the square root of {arg_0}")
def _sqrt(arg_0):
    return math.sqrt(arg_0)


@tool("inverse", "math", "Return the inverse (reciprocal) of a number",
      {"arg_0": _n("The number to inverse")}, NUM, "The inverse result",
      "take the reciprocal of {arg_0}")
def _inv(arg_0):
    return 1 / arg_0


@tool("negate", "math", "Return the negation of a number",
      {"arg_0": _n("The number to negate")}, NUM, "The negated number",
      "negate {arg_0}")
def _neg(arg_0):
    return -arg_0


@tool("floor", "math", "Round a number down to the nearest integer",
      {"arg_0": _n("The input number")}, "int", "The floored value",
      "round {arg_0} down to a whole number")
def _floor(arg_0):
    return math.floor(arg_0)


@tool("reminder", "math", "Calculate the remainder of the division of two numbers",
      {"arg_0": _n("The dividend"), "arg_1": _n("The divisor")},
      NUM, "The remainder", "take the remainder of {arg_0} divided by {arg_1}")
def _rem(arg_0, arg_1):
    return arg_0 % arg_1


@tool("gcd", "math", "Calculate the greatest common divisor of two integers",
      {"arg_0": {"description": "The first integer", "type": "int"},
       "arg_1": {"description": "The second integer", "type": "int"}},
      "int", "The greatest common divisor", "take the greatest common divisor of {arg_0} and {arg_1}")
def _gcdf(arg_0, arg_1):
    return _gcd(int(arg_0), int(arg_1))


@tool("lcm", "math", "Calculate the least common multiple of two integers",
      {"arg_0": {"description": "The first integer", "type": "int"},
       "arg_1": {"description": "The second integer", "type": "int"}},
      "int", "The least common multiple", "take the least common multiple of {arg_0} and {arg_1}")
def _lcm(arg_0, arg_1):
    return abs(int(arg_0) * int(arg_1)) // _gcd(int(arg_0), int(arg_1))


@tool("factorial", "math", "Calculate the factorial of a non-negative integer",
      {"arg_0": {"description": "The input integer", "type": "int"}},
      "int", "The factorial result", "take the factorial of {arg_0}")
def _fact(arg_0):
    return _factorial(int(arg_0))


@tool("choose", "math", "Calculate the number of ways to choose arg_1 items out of arg_0 items",
      {"arg_0": {"description": "Total number of items", "type": "int"},
       "arg_1": {"description": "Number of items to choose", "type": "int"}},
      "int", "The number of combinations", "count the ways to choose {arg_1} items out of {arg_0}")
def _choose(arg_0, arg_1):
    return comb(int(arg_0), int(arg_1))


@tool("log", "math", "Calculate the logarithm of a number with the given base",
      {"arg_0": _n("The input number"), "arg_1": _n("The base")},
      NUM, "The logarithm result", "take the logarithm of {arg_0} in base {arg_1}")
def _log(arg_0, arg_1):
    return math.log(arg_0, arg_1)


@tool("max_val", "math", "Return the larger of two numbers",
      {"arg_0": _n("The first number"), "arg_1": _n("The second number")},
      NUM, "The larger number", "take the larger of {arg_0} and {arg_1}")
def _max(arg_0, arg_1):
    return max(arg_0, arg_1)


@tool("min_val", "math", "Return the smaller of two numbers",
      {"arg_0": _n("The first number"), "arg_1": _n("The second number")},
      NUM, "The smaller number", "take the smaller of {arg_0} and {arg_1}")
def _min(arg_0, arg_1):
    return min(arg_0, arg_1)


@tool("speed", "math", "Calculate speed given distance and time",
      {"arg_0": _n("The distance travelled"), "arg_1": _n("The time taken")},
      NUM, "The speed", "compute the speed for a distance of {arg_0} over a time of {arg_1}")
def _speed(arg_0, arg_1):
    return arg_0 / arg_1


@tool("negate_prob", "math", "Calculate the probability of an event not occurring",
      {"arg_0": {"description": "Probability of the event occurring", "type": "float"}},
      "float", "Probability of the event not occurring",
      "compute the probability that an event with probability {arg_0} does not occur")
def _negprob(arg_0):
    return 1 - arg_0


@tool("rectangle_area", "math", "Calculate the area of a rectangle",
      {"arg_0": _n("rectangle length"), "arg_1": _n("rectangle width")},
      NUM, "the rectangle area", "compute the area of a {arg_0} by {arg_1} rectangle")
def _rectarea(arg_0, arg_1):
    return arg_0 * arg_1


@tool("rectangle_perimeter", "math", "Calculate the perimeter of a rectangle",
      {"arg_0": _n("rectangle length"), "arg_1": _n("rectangle width")},
      NUM, "the rectangle perimeter", "compute the perimeter of a {arg_0} by {arg_1} rectangle")
def _rectperim(arg_0, arg_1):
    return 2 * (arg_0 + arg_1)


@tool("square_area", "math", "Calculate the area of a square given its edge length",
      {"arg_0": _n("Edge length of the square")}, NUM, "the square area",
      "compute the area of a square with edge {arg_0}")
def _sqarea(arg_0):
    return arg_0 ** 2


@tool("circle_area", "math", "Calculate the area of a circle given its radius",
      {"arg_0": {"description": "Radius of the circle", "type": "float"}},
      "float", "the circle area", "compute the area of a circle of radius {arg_0}")
def _circarea(arg_0):
    return math.pi * arg_0 ** 2


@tool("triangle_area", "math", "Calculate the area of a triangle given base and height",
      {"arg_0": _n("Base of the triangle"), "arg_1": _n("Height of the triangle")},
      NUM, "the triangle area", "compute the area of a triangle with base {arg_0} and height {arg_1}")
def _triarea(arg_0, arg_1):
    return 0.5 * arg_0 * arg_1


@tool("volume_cylinder", "math", "Calculate the volume of a cylinder",
      {"arg_0": {"description": "Radius of the base of the cylinder", "type": "float"},
       "arg_1": {"description": "Height of the cylinder", "type": "float"}},
      "float", "Volume of the cylinder",
      "compute the volume of a cylinder of radius {arg_0} and height {arg_1}")
def _volcyl(arg_0, arg_1):
    return math.pi * arg_0 ** 2 * arg_1


@tool("volume_cube", "math", "Calculate the volume of a cube given its edge length",
      {"arg_0": _n("Edge length of the cube")}, NUM, "Volume of the cube",
      "compute the volume of a cube with edge {arg_0}")
def _volcube(arg_0):
    return arg_0 ** 3


@tool("surface_cube", "math", "Calculate the surface area of a cube given its edge length",
      {"arg_0": _n("Edge length of the cube")}, NUM, "Surface area of the cube",
      "compute the surface area of a cube with edge {arg_0}")
def _surfcube(arg_0):
    return 6 * arg_0 ** 2


@tool("cube_edge_by_volume", "math", "Calculate the edge length of a cube given its volume",
      {"arg_0": {"description": "Volume of the cube", "type": "float"}},
      "float", "Edge length of the cube", "compute the edge of a cube whose volume is {arg_0}")
def _cubeedge(arg_0):
    return arg_0 ** (1 / 3)


# --------------------------------------------------------------------------
# code family  (named parameters  ->  output_0)
# --------------------------------------------------------------------------

def _arr(d, item_type=None):
    s = {"description": d, "type": "array"}
    if item_type:
        s["items"] = {"type": item_type}
    return s


@tool("parse_list_of_numbers", "code",
      "Parses a comma-separated string of numbers into a list of numbers.",
      {"text": {"description": "The string containing the numbers.", "type": "string"}},
      "array", "A list of the parsed numbers.",
      "parse the numbers out of the string {text}", items={"type": "number"})
def _parsenums(text):
    out = []
    for part in re.split(r"[,\s]+", text.strip()):
        if not part:
            continue
        out.append(float(part) if "." in part else int(part))
    return out


@tool("dedupe_preserve_order", "code",
      "Removes duplicate elements from a list while preserving first-occurrence order.",
      {"values": _arr("The list to deduplicate.")},
      "array", "The deduplicated list.", "remove the duplicates from {values}")
def _dedupe(values):
    seen, out = set(), []
    for v in values:
        k = json.dumps(v, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(v)
    return out


@tool("sort_values", "code", "Sorts a list of numbers in ascending or descending order.",
      {"values": _arr("The list of numbers to sort.", "number"),
       "descending": {"description": "Whether to sort in descending order.", "type": "boolean"}},
      "array", "The sorted list.", "sort {values} with descending={descending}", items={"type": "number"})
def _sortvals(values, descending):
    return sorted(values, reverse=bool(descending))


@tool("take_first_n", "code", "Returns the first n elements of a list.",
      {"values": _arr("The input list."),
       "n": {"description": "The number of elements to take.", "type": "integer"}},
      "array", "The first n elements.", "take the first {n} elements of {values}")
def _takefirst(values, n):
    return values[: int(n)]


@tool("sum_list", "code", "Computes the sum of a list of numbers.",
      {"values": _arr("The list of numbers to sum.", "number")},
      "number", "The sum of the list.", "sum {values}")
def _sumlist(values):
    return sum(values)


@tool("list_length", "code", "Returns the number of elements in a list.",
      {"values": _arr("The input list.")}, "integer", "The number of elements.",
      "count the elements of {values}")
def _listlen(values):
    return len(values)


@tool("mean_of_list", "code", "Computes the arithmetic mean of a list of numbers.",
      {"values": _arr("The list of numbers.", "number")}, "number", "The arithmetic mean.",
      "take the mean of {values}")
def _mean(values):
    return sum(values) / len(values)


@tool("filter_greater_than", "code",
      "Returns the elements of a list that are strictly greater than a threshold.",
      {"values": _arr("The list of numbers to filter.", "number"),
       "threshold": {"description": "The threshold to compare against.", "type": "number"}},
      "array", "The elements greater than the threshold.",
      "keep only the elements of {values} greater than {threshold}", items={"type": "number"})
def _filtergt(values, threshold):
    return [v for v in values if v > threshold]


@tool("index_of", "code",
      "Returns the index of the first occurrence of a target in a list, or -1 if absent.",
      {"values": _arr("The list to search."),
       "target": {"description": "The value to look for."}},
      "integer", "The index of the first occurrence, or -1.",
      "find the position of {target} in {values}")
def _indexof(values, target):
    try:
        return values.index(target)
    except ValueError:
        return -1


@tool("swap_by_index", "code", "Swaps the values at index i and j in the given list.",
      {"values": _arr("The list of values."),
       "i": {"description": "The index of the first value to swap.", "type": "integer"},
       "j": {"description": "The index of the second value to swap.", "type": "integer"}},
      "array", "The list with the two values swapped.",
      "swap positions {i} and {j} of {values}")
def _swap(values, i, j):
    out = list(values)
    i, j = int(i), int(j)
    out[i], out[j] = out[j], out[i]
    return out


@tool("unique_common_values", "code",
      "Returns a list of unique common values that occur in both input lists.",
      {"list1": _arr("The first input list.", "integer"),
       "list2": _arr("The second input list.", "integer")},
      "array", "A list of unique common values.",
      "find the values common to {list1} and {list2}", items={"type": "integer"})
def _common(list1, list2):
    seen, out = set(), []
    for v in list1:
        if v in list2 and v not in seen:
            seen.add(v)
            out.append(v)
    return out


@tool("replace_with_target", "code",
      "Replaces every occurrence of `target` in `src_list` with `replacement`.",
      {"src_list": _arr("A list of integers.", "integer"),
       "target": {"description": "The integer to be replaced.", "type": "integer"},
       "replacement": {"description": "The integer to replace `target` with.", "type": "integer"}},
      "array", "The list with the replacements applied.",
      "replace every {target} in {src_list} with {replacement}", items={"type": "integer"})
def _replace(src_list, target, replacement):
    return [replacement if v == target else v for v in src_list]


@tool("join_with_separator", "code", "Joins the elements of a list into a single string.",
      {"items": _arr("The elements to join."),
       "separator": {"description": "The separator placed between elements.", "type": "string"}},
      "string", "The joined string.", "join {items} with {separator}")
def _join(items, separator):
    return separator.join(str(v) for v in items)


@tool("tokenize_sentence", "code",
      "Tokenizes a sentence by removing punctuation and converting words to lowercase.",
      {"sentence": {"description": "The sentence to tokenize.", "type": "string"}},
      "array", "A list of tokens.", "tokenize the sentence {sentence}", items={"type": "string"})
def _tokenize(sentence):
    return [w for w in re.sub(r"[^\w\s]", " ", sentence.lower()).split() if w]


@tool("string_to_upper", "code", "Converts a string to upper case.",
      {"text": {"description": "The string to convert.", "type": "string"}},
      "string", "The upper-cased string.", "upper-case {text}")
def _upper(text):
    return text.upper()


@tool("convert_to_url_slug", "code",
      "Converts a string into a lowercase, hyphen-separated URL slug.",
      {"text": {"description": "The string to convert.", "type": "string"}},
      "string", "The URL slug.", "turn {text} into a URL slug")
def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@tool("make_json_string", "code", "Converts a dictionary to a JSON string.",
      {"dictionary": {"description": "The dictionary to convert to JSON.", "type": "object"}},
      "string", "A string representing the same data in JSON format.",
      "convert the dictionary {dictionary} to a JSON string")
def _mkjson(dictionary):
    return json.dumps(dictionary, separators=(", ", ": "))


@tool("get_dict_values", "code", "Returns the values of a dictionary as a list.",
      {"dictionary": {"description": "The input dictionary.", "type": "object"}},
      "array", "The dictionary values.", "take the values of {dictionary}")
def _dictvals(dictionary):
    return list(dictionary.values())


@tool("get_dict_keys", "code", "Returns the keys of a dictionary as a list.",
      {"dictionary": {"description": "The input dictionary.", "type": "object"}},
      "array", "The dictionary keys.", "take the keys of {dictionary}", items={"type": "string"})
def _dictkeys(dictionary):
    return list(dictionary.keys())


@tool("round_to", "code", "Rounds a number to the given number of decimal places.",
      {"value": {"description": "The number to round.", "type": "number"},
       "ndigits": {"description": "The number of decimal places.", "type": "integer"}},
      "number", "The rounded number.", "round {value} to {ndigits} decimal places")
def _round(value, ndigits):
    return round(value, int(ndigits))


@tool("flatten_extend", "code", "Flattens a list of lists into a single list.",
      {"matrix": _arr("The list of lists to flatten.", "array")},
      "array", "The flattened list.", "flatten {matrix}")
def _flatten(matrix):
    out = []
    for row in matrix:
        out.extend(row)
    return out


@tool("reverse_list", "code", "Returns a new list with the elements in reverse order.",
      {"values": _arr("The list to reverse.")}, "array", "The reversed list.",
      "reverse {values}")
def _reverse(values):
    return list(values)[::-1]


@tool("pad_to_len", "code", "Pads a list with a fill value until it reaches the given length.",
      {"values": _arr("The list to pad."),
       "length": {"description": "The target length.", "type": "integer"},
       "pad": {"description": "The fill value."}},
      "array", "The padded list.", "pad {values} up to length {length} with {pad}")
def _pad(values, length, pad):
    out = list(values)
    while len(out) < int(length):
        out.append(pad)
    return out


@tool("count_words_from_sentences", "code",
      "Counts the total number of whitespace-separated words across a list of sentences.",
      {"sentences": _arr("The list of sentences.", "string")},
      "integer", "The total word count.", "count the words across {sentences}")
def _countwords(sentences):
    return sum(len(s.split()) for s in sentences)


@tool("split_on_separator", "code", "Splits a string on a separator into a list of parts.",
      {"text": {"description": "The string to split.", "type": "string"},
       "separator": {"description": "The separator to split on.", "type": "string"}},
      "array", "The list of parts.", "split {text} on {separator}", items={"type": "string"})
def _split(text, separator):
    return text.split(separator)


@tool("count_elements_in_object", "code", "Counts the number of entries in a dictionary.",
      {"obj": {"description": "The dictionary to count.", "type": "object"}},
      "integer", "The number of entries.", "count the entries of {obj}")
def _countobj(obj):
    return len(obj)


@tool("zip_sum", "code", "Element-wise sum of two equally long lists of numbers.",
      {"list1": _arr("The first list.", "number"), "list2": _arr("The second list.", "number")},
      "array", "The element-wise sums.", "element-wise sum {list1} and {list2}",
      items={"type": "number"})
def _zipsum(list1, list2):
    return [a + b for a, b in zip(list1, list2)]


@tool("to_integer_list", "code", "Converts every element of a list to an integer.",
      {"values": _arr("The list to convert.")}, "array", "The list of integers.",
      "convert every element of {values} to an integer", items={"type": "integer"})
def _toints(values):
    return [int(v) for v in values]


@tool("format_html_link", "code", "Formats a text and a URL into an HTML anchor tag.",
      {"text": {"description": "The anchor text.", "type": "string"},
       "url": {"description": "The link target.", "type": "string"}},
      "string", "The HTML anchor tag.", "format {text} and {url} as an HTML link")
def _htmllink(text, url):
    return '<a href="{}">{}</a>'.format(url, text)


def family_of(name):
    return TOOLS[name]["family"]


def out_key_of(name):
    return TOOLS[name]["out_key"]
