"""Step 5 of the pipeline: verbalise each executed graph as a user query.

Written strictly downstream of ``graphs.py``.  For each graph the author was
shown only the topology, the tool specs and the executed trace, and asked:
*what would a person plausibly be asking, such that this graph is the answer?*

Rules kept while writing:
  * every literal that appears as a graph leaf appears in the query;
  * no intermediate value is ever stated (the model has to compute it);
  * the query names the goal, not the tool sequence - the decomposition is what
    is being tested;
  * the query is answerable by exactly this graph.
"""

QUERIES = {
    "syn-001":
        "A print run of 640 posters is scheduled. Three eighths of the run come off the "
        "press before the ink cartridge has to be changed. How many posters are still "
        "unprinted at the moment of the change?",

    "syn-002":
        "A workshop floor measures 14 metres by 9 metres. A square machine footprint with "
        "6-metre sides is bolted down in the middle of it. What fraction of the floor area "
        "is still free?",

    "syn-003":
        "A delivery van covers 240 km in 3 hours on the way out. On the return leg the "
        "driver averages 1.25 times the outbound speed. By what percentage is the return "
        "speed higher than the outbound speed?",

    "syn-004":
        "A stage designer cuts three panels out of one sheet of board: a rectangle 12 by 5, "
        "a triangle with base 10 and height 6, and a circle of radius 2.0. Working in whole "
        "square units and discarding any leftover fraction, how many square units of board "
        "do the three panels take up together?",

    "syn-005":
        "A fund of 2500 grows by a factor of 1.08 in each of three consecutive years. By "
        "what percentage is the fund larger at the end of the third year than it was at the "
        "start?",

    "syn-006":
        "This shift's sensor log arrived as the raw string \"18, 7, 42, 7, 23, 42, 5\". Pull "
        "the numbers out of it, drop any reading that repeats an earlier one, and give me "
        "the three highest readings, largest first.",

    "syn-007":
        "I have four daily load figures: {\"mon\": 62, \"tue\": 48, \"wed\": 71, \"thu\": 39}. "
        "Take the figures in order and add each one to the figure sitting in the mirrored "
        "position of the same list, so the first pairs with the last, the second with the "
        "second-to-last, and so on. Give me the two largest of those pair totals.",

    "syn-008":
        "The article is titled \"Nested API Calls, Nested API Planning!\". Normalise it into "
        "lowercase words with the punctuation stripped, drop any word that has already "
        "appeared, and join what is left back into a single space-separated display title. "
        "Derive a URL slug from that display title, then give me the finished HTML anchor "
        "tag that links the display title to the slug.",

    "syn-009":
        "Two reviewers handed in shortlists of submission IDs: [3, 9, 14, 22, 7, 31] and "
        "[22, 5, 9, 40, 31]. Keep only the IDs that both reviewers picked, rank them from "
        "highest to lowest, then promote ID 22 to the front of that ranking by swapping it "
        "with whatever currently sits in first place. Return the final ranking as a "
        "pipe-separated string.",

    "syn-010":
        "Queue lengths from the last six polls came back as the string "
        "\"12, 19, 7, 24, 15, 9\". Work out the mean queue length by totalling the readings "
        "and dividing by how many readings there are, then square that mean and report it "
        "rounded to 2 decimal places.",
}


# Surface forms a query is allowed to use instead of the bare literal.  The
# build checks that every literal leaf of the graph really is stated in the
# query - these are the cases where it is stated in words.
LITERAL_ALIASES = {
    "syn-001": {3: ["three eighths"], 8: ["three eighths"]},
    # the x100 in a percent question is carried by the words "what percentage"
    "syn-003": {100: ["by what percentage"]},
    "syn-005": {100: ["by what percentage"]},
    "syn-006": {3: ["three highest"]},
    "syn-007": {2: ["two largest"]},
    "syn-008": {" ": ["space-separated"]},
    "syn-009": {0: ["first place"], "|": ["pipe-separated"]},
    "syn-010": {2: ["2 decimal places"]},
}
