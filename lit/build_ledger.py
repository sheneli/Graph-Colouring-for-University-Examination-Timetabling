"""Build the evidence ledger (CSV + Markdown) and Harvard reference strings from the
verified JSONL records produced by the literature-verification agents.

Harvard style: Cite Them Right conventions (author-date). Accessed date for web sources:
4 October 2026. Duplicates (same DOI) are merged. Same-author same-year works get a/b
suffixes. Output fields 'h_pre', 'h_italic', 'h_post' allow italics in Word.
"""

from __future__ import annotations

import csv
import glob
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
ACCESSED = "4 October 2026"

# Clean venue / publication details for non-journal items: (italic part, post-italic text)
OVERRIDE = {
    "A05": ("Complexity of Computer Computations", ". Edited by R.E. Miller, J.W. Thatcher and J.D. Bohlinger. Boston, MA: Springer, pp. 85–103"),
    "A06": ("Computers and Intractability: A Guide to the Theory of NP-Completeness", ". San Francisco, CA: W.H. Freeman"),
    "A08": ("Guide to Graph Colouring: Algorithms and Applications", ". 2nd edn. Cham: Springer (Texts in Computer Science)"),
    "A14": ("LATIN 2018: Theoretical Informatics", ". Cham: Springer (Lecture Notes in Computer Science, 10807), pp. 640–652"),
    "A15": ("27th International Conference on Theory and Applications of Satisfiability Testing (SAT 2024)", ". Dagstuhl: Schloss Dagstuhl (LIPIcs, 305), pp. 12:1–12:20"),
    "A01e": ("Metaheuristics: MIC 2024", ". Cham: Springer (Lecture Notes in Computer Science, 14754), pp. 96–111"),
    "A20": ("Cliques, Coloring, and Satisfiability: Second DIMACS Implementation Challenge", ". Providence, RI: American Mathematical Society (DIMACS Series in Discrete Mathematics and Theoretical Computer Science, 26), pp. 245–284"),
    "A22": ("2019 IEEE 31st International Conference on Tools with Artificial Intelligence (ICTAI)", ". IEEE, pp. 879–885"),
    "A24": ("Integration of Constraint Programming, Artificial Intelligence, and Operations Research: CPAIOR 2019", ". Cham: Springer (Lecture Notes in Computer Science, 11494), pp. 374–390"),
    "A31a": ("Learning and Intelligent Optimization: LION 17", ". Cham: Springer (Lecture Notes in Computer Science, 14286), pp. 491–505"),
    "A32b": ("2021 IEEE Congress on Evolutionary Computation (CEC)", ". IEEE, pp. 2347–2353"),
    "A35b": ("Advances in Swarm Intelligence: ICSI 2019", ". Cham: Springer (Lecture Notes in Computer Science, 11655), pp. 210–219"),
    "B13": ("Practice and Theory of Automated Timetabling VI: PATAT 2006", ". Edited by E.K. Burke and H. Rudová. Berlin: Springer (Lecture Notes in Computer Science, 3867), pp. 364–382"),
    "B20": ("Proceedings of the 13th International Conference on the Practice and Theory of Automated Timetabling (PATAT 2022), Volume III", ". Edited by P. De Causmaecker, E. Özcan and G. Vanden Berghe. Leuven: PATAT, pp. 30–46"),
    "C01": ("Proceedings of the Twenty-Ninth Annual ACM-SIAM Symposium on Discrete Algorithms (SODA 2018)", ". Philadelphia, PA: SIAM, pp. 1–20"),
    "C11": ("17th Scandinavian Symposium and Workshops on Algorithm Theory (SWAT 2020)", ". Dagstuhl: Schloss Dagstuhl (LIPIcs, 162), pp. 17:1–17:23"),
    "C14": ("Integration of Constraint Programming, Artificial Intelligence, and Operations Research: CPAIOR 2020", ". Cham: Springer (Lecture Notes in Computer Science, 12296), pp. 317–333"),
    "C18": ("Practice and Theory of Automated Timetabling V: PATAT 2004", ". Berlin: Springer (Lecture Notes in Computer Science, 3616), pp. 126–146"),
    "C21b": ("Multi-disciplinary Trends in Artificial Intelligence: MIWAI 2023", ". Cham: Springer (Lecture Notes in Computer Science, 14078), pp. 569–579"),
    "C21d": ("Proceedings of the 11th International Conference on the Practice and Theory of Automated Timetabling (PATAT 2016)", ", pp. 207–210"),
    "C22c": ("30th Annual European Symposium on Algorithms (ESA 2022)", ". Dagstuhl: Schloss Dagstuhl (LIPIcs, 244), article 25"),
    "C23b": ("37th International Symposium on Theoretical Aspects of Computer Science (STACS 2020)", ". Dagstuhl: Schloss Dagstuhl (LIPIcs, 154), article 35"),
    "D01": ("Proceedings of the 7th Python in Science Conference (SciPy 2008)", ". Pasadena, CA, pp. 11–15"),
    "D05b": ("29th International Conference on Principles and Practice of Constraint Programming (CP 2023)", ". Dagstuhl: Schloss Dagstuhl (LIPIcs, 280), pp. 3:1–3:2"),
    "D13": ("A Guide to Experimental Algorithmics", ". Cambridge: Cambridge University Press"),
    "D15": ("Introduction to Algorithms", ". 4th edn. Cambridge, MA: MIT Press"),
    "D16": ("Data Structures, Near Neighbor Searches, and Methodology: Fifth and Sixth DIMACS Implementation Challenges", ". Providence, RI: American Mathematical Society (DIMACS Series in Discrete Mathematics and Theoretical Computer Science, 59), pp. 215–250"),
}
SOFTWARE = {
    "D05": ("CP-SAT", ". Version 9.15. Google OR-Tools"),
    "D05a": ("OR-Tools", ". Version 9.15. Google"),
    "D03a": ("scipy.optimize.linear_sum_assignment", ". SciPy v1.18 Manual"),
    "D03b": ("scipy.stats.wilcoxon", ". SciPy v1.18 Manual"),
    "D19a": ("time — Time access and conversions", ". Python 3 documentation"),
    "D19b": ("tracemalloc — Trace memory allocations", ". Python 3 documentation"),
    "D19c": ("random — Generate pseudo-random numbers", ". Python 3 documentation"),
    "D20": ("greedy_color", ". NetworkX documentation"),
}
# Journal articles are dated by the issue they appear in (Cite Them Right), not the online-first
# date: Crossref published-print 2018-02 (TCS 711) and 2018-06 (J. Heuristics 24(3)), checked 4 Oct 2026.
YEAR_FIX = {"D05": 2026, "D05a": 2026, "C23a": 2018, "C09": 2018}
# Record corrections made after the agents' verification pass (source checked in this session).
RECORD_FIX = {
    "C01": {
        "access_level": "full_text",
        "key_finding": ("Fast dynamic algorithms maintaining a proper vertex colouring under edge insertions and "
                        "deletions: randomized (Delta+1)-colouring with O(log Delta) expected amortized update time, "
                        "and deterministic (1+o(1))Delta-colouring. Full text (arXiv 1711.04355, sections 3.1 and "
                        "3.3, read 4 Oct 2026): a colour is 'blank' for a vertex if no relevant neighbour has it and "
                        "'unique' if exactly one does; a vertex being recoloured picks a random blank or unique "
                        "colour, and if the colour is unique the single neighbour holding it is recoloured "
                        "recursively."),
        "limitations": ("Theoretical. The palette is tied to the maximum degree (about Delta+1 colours), not a fixed "
                        "number of periods; no minimal-perturbation objective. Only sections 3.1 and 3.3 of the full "
                        "text were read."),
    },
    "C21b": {
        "access_level": "metadata+abstract",
        "key_finding": ("Abstract (Springer chapter page, read 4 Oct 2026): when unprecedented events disturb the "
                        "academic calendar, exams must be re-dated; the paper models re-scheduling as a Markov "
                        "decision process and checks schedule feasibility with Bellman equations, temporal-"
                        "difference learning, policy iteration and value iteration, mapping a disturbed exam to a "
                        "plausible new date."),
        "limitations": ("Full text not read. Re-dating of exams after calendar disruptions, not clash repair after "
                        "late enrolments; no move budget or Toronto data mentioned in the abstract. LNCS 14078."),
    },
}
TYPE_FIX = {"D16": "chapter"}
NO_URL = {"A06", "D15"}  # print books: no URL needed
NOT_CITED = {"C21c": "Not cited: conference volume could not be confirmed",
             "C22b": "Not cited: conference volume could not be confirmed"}

# Extra (manually verified in this session) web sources
EXTRA = [
    {"id": "W01", "type": "web", "authors": ["University of Nottingham"], "year": None,
     "title": "Benchmark data sets in exam timetabling", "venue": "School of Computer Science",
     "url": "https://people.cs.nott.ac.uk/pszrq/data.htm", "access_level": "full_text",
     "key_finding": "Lists the 13 Toronto instances with exams, students, enrolments, conflict density and published period counts; documents versions I, II and IIc.",
     "limitations": "No explicit licence or redistribution terms stated.", "in_window": True, "status": "verified"},
    {"id": "W02", "type": "web", "authors": ["Sajib-006"], "year": None,
     "title": "Eaxam-Scheduler-Using-Graph-Coloring-and-Kempe-Chain [GitHub repository, Toronto/ directory]",
     "venue": "GitHub", "url": "https://github.com/Sajib-006/Eaxam-Scheduler-Using-Graph-Coloring-and-Kempe-Chain",
     "access_level": "full_text",
     "key_finding": "Mirror of the Toronto version-I .crs/.stu files used in this project; statistics checked against W01 (all 13 match on exams, students and enrolments).",
     "limitations": "Third-party mirror without a licence statement; provenance relies on the statistical match with W01.",
     "in_window": True, "status": "verified"},
    {"id": "A06b", "type": "journal", "authors": ["Garey, M.R.", "Johnson, D.S.", "Stockmeyer, L."], "year": 1976,
     "title": "Some simplified NP-complete graph problems", "venue": "Theoretical Computer Science", "volume": "1",
     "issue": "3", "pages": "237-267", "doi": "10.1016/0304-3975(76)90059-1",
     "access_level": "metadata+abstract",
     "key_finding": ("Abstract (ScienceDirect, read 4 Oct 2026): several NP-complete problems remain NP-complete on "
                     "substantially restricted domains; for Graph 3-Colorability (and Node Cover, Undirected "
                     "Hamiltonian Circuit) the paper determines essentially the lowest node-degree bounds for which "
                     "the problems remain NP-complete."),
     "limitations": "Pre-window foundational original; abstract only.", "in_window": False, "status": "verified"},
    {"id": "W03", "type": "web", "authors": ["Cardiff Metropolitan University"], "year": None,
     "title": "AI Student Hub", "venue": "", "url": "https://www.cardiffmet.ac.uk/about/artificial-intelligence/ai-student-hub/",
     "access_level": "full_text",
     "key_finding": "States that assessment rules on AI are set at module level and that students remain responsible for their own work.",
     "limitations": "Retrieved via a page summariser; wording should be checked on the live page.", "in_window": True, "status": "verified"},
]

USE = {
    "A01": "Q3/Q4 initial-timetable constructor (DSATUR); baseline M4 core; algorithm review",
    "A02": "Q1 origin of the colouring-timetabling link; constructor; algorithm review",
    "A03": "Constructor (RLF); algorithm review",
    "A04": "Constructor (smallest-last); algorithm review",
    "A05": "Q2 NP-completeness of k-colouring",
    "A06": "Q2 complexity background",
    "A06b": "Q2 NP-completeness of 3-colourability (fixed k >= 3)",
    "A07": "Q2 inapproximability of chromatic number",
    "A08": "Background; Kempe chains; algorithm descriptions",
    "A14": "Algorithm review (ILP formulations)", "A15": "Algorithm review (SAT encodings)",
    "A16": "Algorithm review (branch-and-price)", "A17": "Algorithm review (column generation)",
    "A23": "Algorithm review (exact DSATUR B&B)", "A01e2": "Algorithm review (exact DSATUR B&B, recent)",
    "A24": "Algorithm review (hybrid exact)", "A29": "Algorithm review (inclusion-exclusion exact)",
    "A17e": "Algorithm review (branch-and-price, recent evidence)",
    "B01": "Q1/Q2 Toronto benchmark origin; Carter proximity cost; data provenance",
    "B02": "Exam timetabling survey; dataset versions",
    "B03": "Application-level requirements (ITC2007)",
    "B04": "Recent survey: benchmarks and state of the art", "B05": "Recent exam-timetabling survey",
    "B25": "Recent systematic review (exam timetabling)",
    "B06": "State of the art on Toronto (SA); algorithm review", "B07": "Algorithm review (FastSA)",
    "B20": "Proven optimum for sta83 (conference)", "B26g": "Proven optimum for sta83 (journal)",
    "B24": "Nearest exam-specific related work (robust timetables)",
    "C12": "Nearest prior work (MPP, IP, enrolment changes)", "C16": "Nearest prior work (budgeted perturbation)",
    "C13": "Related work (MPP case study)", "C14": "Related work (MPP MaxSAT)", "C15": "Related work (quality recovery)",
    "C17": "Related work (robust course timetabling)", "C18": "Origin of the MPP in timetabling",
    "C23a": "Q2/Q6 complexity of the repair problem (Color-Fixing); FPT basis of Tier 4",
    "C01": "Unique-neighbour recolouring basis of Tier 2; dynamic colouring",
    "C02": "Recourse vs colours trade-off", "C03": "Recourse vs colours trade-off",
    "C06": "Experimental dynamic colouring", "C09": "Kempe chains in edge-dynamic colouring",
    "C21b": "Exam rescheduling (different problem); novelty check",
    "D02": "Python ecosystem (NumPy)", "D03": "Python ecosystem (SciPy)", "D03a": "Hungarian/JV relabelling in M4",
    "D03b": "Statistical test implementation", "D05": "Exact oracle solver", "D05a": "Exact oracle solver suite",
    "D05b": "CP-SAT technical description", "D07": "Assignment algorithm used by SciPy",
    "D08": "Wilcoxon signed-rank test", "D09": "Statistical comparison method", "D11": "Python performance trade-off",
    "D12": "Reproducibility practice", "D17a": "Python performance trade-off", "D17b": "Python in optimisation research",
    "D17c": "Alternative language (Julia)", "D18a": "Benchmarking practice", "D18b": "Reproducibility practice",
    "D19a": "Timing method", "D19b": "Memory measurement method", "D19c": "Seeded randomness",
    "D20": "Library cross-check of constructors", "W01": "Dataset provenance", "W02": "Dataset source used",
    "W03": "AI-use rules",
}


def norm_type(t):
    t = (t or "").lower()
    if t in ("journal", "journal-article", "review"):
        return "journal"
    if t in ("conference", "conference-paper"):
        return "conference"
    return t


def norm_author(a):
    """'Karp, R. M.' -> 'Karp, R.M.'"""
    if "," not in a:
        return a.strip()
    fam, ini = a.split(",", 1)
    ini = re.sub(r"\.\s+(?=[A-Z])", ".", ini.strip())
    return f"{fam.strip()}, {ini}"


def fmt_authors(auth):
    a = [norm_author(x) for x in auth if x and x.strip()]
    if len(a) == 1:
        return a[0]
    return ", ".join(a[:-1]) + " and " + a[-1]


def surname(a):
    return a.split(",")[0].strip()


def citekey(auth):
    s = [surname(x) for x in auth]
    if len(s) == 1:
        return s[0]
    if len(s) == 2:
        return f"{s[0]} and {s[1]}"
    if len(s) == 3:
        return f"{s[0]}, {s[1]} and {s[2]}"
    return f"{s[0]} et al."


def pages_txt(p):
    if not p:
        return ""
    p = str(p).replace("-", "–")
    if "–" in p or ":" in p:
        return f", pp. {p}"
    return f", article {p}"


def main():
    recs, seen_doi = [], {}
    for f in sorted(glob.glob(str(HERE / "verified_*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            doi = (r.get("doi") or "").lower()
            if doi and doi in seen_doi:
                seen_doi[doi]["merged_ids"].append(r["id"])
                continue
            r["merged_ids"] = [r["id"]]
            if doi:
                seen_doi[doi] = r
            recs.append(r)
    recs.extend(EXTRA)
    for r in recs:
        r.setdefault("merged_ids", [r["id"]])
        r["year"] = YEAR_FIX.get(r["id"], r.get("year"))
        r.update(RECORD_FIX.get(r["id"], {}))
    # year suffixes
    groups = defaultdict(list)
    for r in recs:
        groups[(citekey(r["authors"]), r.get("year"))].append(r)
    for (_k, _y), g in groups.items():
        g.sort(key=lambda x: x.get("title", ""))
        for i, r in enumerate(g):
            r["suffix"] = (" " if not r.get("year") else "") + "abcdefghij"[i] if len(g) > 1 else ""
    rows = []
    for r in recs:
        t = norm_type(TYPE_FIX.get(r["id"], r.get("type")))
        yr = r.get("year")
        ytxt = (str(yr) if yr else "no date") + r["suffix"]
        auth = fmt_authors(r["authors"])
        doi = r.get("doi")
        link = f"https://doi.org/{doi}" if doi else (None if r["id"] in NO_URL else r.get("url"))
        avail = f" Available at: {link}" + ("" if doi else f" (Accessed: {ACCESSED})") + "." if link else ""
        title = (r.get("title") or "").strip().rstrip(".")
        rid = r["id"]
        if rid in SOFTWARE:
            it, post = SOFTWARE[rid]
            pre = f"{auth} ({ytxt}) "
            post = post + "." + avail
        elif t == "journal":
            vol = r.get("volume") or ""
            iss = f"({r['issue']})" if r.get("issue") else ""
            pre = f"{auth} ({ytxt}) '{title}', "
            it = r.get("venue") or ""
            post = f", {vol}{iss}{pages_txt(r.get('pages'))}." + avail
        elif t in ("conference", "chapter"):
            it, post = OVERRIDE.get(rid, (r.get("venue") or "", pages_txt(r.get("pages"))))
            pre = f"{auth} ({ytxt}) '{title}', in "
            post = post + "." + avail
        elif t == "book":
            it, post = OVERRIDE.get(rid, (title, ""))
            pre = f"{auth} ({ytxt}) "
            post = post + "." + avail
        elif t == "preprint":
            pre = f"{auth} ({ytxt}) '{title}'. "
            it = "arXiv"
            post = " [Preprint]." + avail
        else:  # web
            pre = f"{auth} ({ytxt}) "
            it = title
            post = (f". {r['venue']}" if r.get("venue") else "") + "." + avail
        harvard = pre + it + post
        harvard = re.sub(r"\.\.+", ".", harvard).replace(" ,", ",")
        rows.append({
            "source_id": rid, "merged_ids": ";".join(r["merged_ids"]),
            "cite": f"{citekey(r['authors'])}, {ytxt}", "type": t, "year": yr or "",
            "in_window": r.get("in_window"), "harvard": harvard, "h_pre": pre, "h_italic": it,
            "h_post": re.sub(r"\.\.+", ".", post), "doi_url": link or "", "access_level": r.get("access_level"),
            "status": r.get("status"), "finding": (r.get("key_finding") or "").replace("\n", " "),
            "limitations": (r.get("limitations") or "").replace("\n", " ") if r.get("limitations") else "",
            "report_use": NOT_CITED.get(rid, USE.get(rid, "Algorithm review / literature synthesis")),
            "algorithm": r.get("algorithm") or "", "title": title,
        })
    rows.sort(key=lambda x: (x["cite"].lower()))
    with open(HERE / "evidence_ledger.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(HERE / "evidence_ledger.md", "w") as fh:
        fh.write("# Evidence ledger\n\nResearch date 4 October 2026; recency window 4 Oct 2016 – 4 Oct 2026. "
                 "Access level: metadata+abstract = bibliographic record and abstract read; full_text = full text read; "
                 "metadata_only = no abstract obtained. Findings are restricted to what was read.\n\n")
        fh.write("| Source ID | Harvard reference | Year | DOI/URL | Access level | Relevant finding | Limitations | Report use |\n|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            cells = [r["source_id"] + (f" (={r['merged_ids']})" if ";" in r["merged_ids"] else ""), r["harvard"],
                     str(r["year"]), r["doi_url"], str(r["access_level"]), r["finding"], r["limitations"], r["report_use"]]
            fh.write("| " + " | ".join(c.replace("|", "/") for c in cells) + " |\n")
    print(len(rows), "unique sources;", sum(1 for r in rows if r["in_window"] is True), "in window")


if __name__ == "__main__":
    main()
