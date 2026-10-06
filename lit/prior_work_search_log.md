# Prior-work search log and novelty-risk assessment (Group C)

Research date: 2026-10-04 (all queries run on this date). Recency window: 2016-10-04 to 2026-10-04.
Tools: WebFetch (OpenAlex, Crossref, publisher and repository pages) and WebSearch only.
Output records: `verified_C.jsonl` (IDs C01–C20 verified or corrected; C21a–C21f, C22a–C22d and C23a–C23e added).

"Hits" counts the results that are relevant to the project (repair or minimal perturbation of timetables or colourings, dynamic or incremental colouring, Kempe reconfiguration). It is not the raw result count unless stated.

## 1. Access problems (these limit the search scope)

| Resource | Problem | Effect |
|---|---|---|
| OpenAlex `/works?search=` and `filter=title.search:` | HTTP 429 on all 8 attempts (listed in §2.3) | OpenAlex full-text relevance search was **not available**. OpenAlex `/autocomplete/works` (free, title-phrase matching) and DOI lookups were used instead. |
| Crossref `/works?query.bibliographic=` | 1 success, then HTTP 429 (2 attempts) | Crossref was used only to correct C19. |
| Semantic Scholar API | HTTP 429 | Not used. |
| Springer pages for C07 (10.1007/s11227-025-07696-8) and C21b (10.1007/978-3-031-36402-0_53) | Proxy 429, with an instruction not to retry | Abstracts for C07 and C21b were **not read**. |
| arXiv abstract pages 2105.12525 and 1607.06911v3 | Proxy 429 | Abstracts were taken from OpenAlex arXiv records or the publisher PDF instead. |
| hal.science (C20), orbit.dtu.dk (C15), hdl.handle.net (C16) | Permission request timed out | Abstracts were taken from Springer, RePEc or ScienceDirect instead. |
| files.core.ac.uk (C09 PDF) | robots.txt failure | The Springer fulltext page was used instead. |
| exertus.org.uk (Kingston 2016) | http/https redirect loop | The PATAT 2016 proceedings copy was used instead. |
| api.openalex.org/works/doi:10.48550/arxiv.2402.13139 | HTTP 504, twice | This arXiv item (title unknown) was not assessed. |

## 2. Query log

### 2.1 WebSearch (26 discovery queries + 7 metadata-verification queries)

| # | Query | Relevant hits | Relevant IDs / notes |
|---|---|---|---|
| W1 | `"minimal perturbation" examination timetabling` | 5 | C14, C18, C12 (PATAT 2014 version), C21d, C13. All are course or high-school; none is exam-specific. |
| W2 | `exam timetabling rescheduling disruption late enrolment changes repair existing timetable` | 3 | C21a, C21f (arXiv 2008.12342), Siew et al. 2024 IEEE Access survey (= B05) |
| W3 | `dynamic graph colouring timetabling Kempe chain repair after new constraints` | 4 | C09, C22a, C22b; Fuchs, arXiv 2511.06473 "Coloring Reconfiguration under Color Swapping" (preprint, not verified) |
| W4 | `incremental graph coloring examination scheduling new conflicts recoloring minimum changes` | 0 | Only static exam-colouring papers |
| W5 | `Kempe equivalence reconfiguration of graph colourings Kempe changes recent results` | 5 | C23b, C23c, C23d, C23e; "Kempe equivalent list colorings revisited", J. Graph Theory 2024, 10.1002/jgt.23142 (not verified) |
| W6 | `robust examination timetabling disruptions reassignment exams minimal changes heuristic` | 3 | C21a (+ arXiv 2311.17766), C14; Akkan et al. J. Sched. 2022, 10.1007/s10951-022-00722-0 (course robustness, not verified) |
| W7 | `"examination timetabling" "late" enrolment OR registration changes after publication algorithm` | 1 | C21a |
| W8 | `bounded recourse recoloring edge insertions graph coloring Kempe chain local repair` | 4 | C22a, C03; Rajaraman et al. arXiv 2408.05370 (online recolouring, not verified); arXiv 2602.09497 (edge colouring, not verified) |
| W9 | `examination timetable changes after publication students conflicts minimal perturbation UniTime exam` | 2 | C21e (MISTA 2013 / J. Sched. 2016), C18 |
| W10 | `"exam timetabling" "dynamic" OR "re-timetabling" OR "rescheduling" Toronto benchmark perturbation` | 2 | **C21b**, C21a |
| W11 | `"disruption management" OR "recovery" examination timetabling problem repair heuristic exams moved` | 2 | C21a; "Evaluating Disruption Recovery across Pareto-Representative Solutions in Multi-Objective University Course Timetabling" (JCTA; course; not verified) |
| W12 | `Hardy Lewis Thompson dynamic graph colouring timetabling Cardiff thesis edge dynamic` | 2 | C09, C22b |
| W13 | `repairing exam timetable when new student conflicts added "graph colouring" recolour few exams` | 0 | Only static exam-colouring papers |
| W14 | `"minimum perturbation" OR "minimal perturbation" "graph coloring" recoloring problem complexity` | 1 | **C23a** (Fixing improper colorings) |
| W15 | `"exam" timetable "student enrolment" uncertainty registration data robust rescheduling Bassimir Wanka` | 1 | C21a |
| W16 | `reactive OR interactive examination timetabling solver minimal changes to existing solution students added 2018..2025` | 1 | C21e |
| W17 | `"Rescheduling Exams Within the Announced Tenure Using Reinforcement Learning"` | 2 | C21b, C21c |
| W18 | `online graph recoloring competitive "recoloring" problem bounded number of recolorings per update survey 2020..2026` | 3 | C02, C03, C11 (+ Rajaraman preprint) |
| W19 | `Kempe chain neighbourhood exam timetabling Toronto benchmark local search 2018 2020 2022` | 0 repair-related | Static Kempe-chain exam local search only (e.g., PATAT 2022 ILS) |
| W20 | `"examination timetabling" reoptimization OR "warm start" OR "previous solution" new constraints minimal changes` | 0 | — |
| W21 | `dynamic graph coloring heuristic edge insertions recolor few vertices experimental evaluation scheduling application 2021 2023 2024` | 3 | C06, C07, C08; Weitz 2024 BA thesis (not peer reviewed) |
| W22 | `"Kempe" dynamic graph colouring edge insertion repair heuristic "time-step"` | 3 | C22b, C09, C22d |
| W23 | `"exam timetabling" OR "examination timetabling" "minimum perturbation" OR "minimal perturbation" OR "rescheduling" 2023 2024 2025 journal` | 3 | C21b, C13, C14 |
| W24 | `CP-SAT OR "constraint programming" minimal perturbation exam schedule repair students clash added after release` | 1 | C14 |
| W25 | `"color-fixing" OR "colour fixing" OR "recoloring" minimum number of recolored vertices proper coloring improper initial coloring parameterized` | 1 | C23a (+ arXiv 2609.09837 "Parameterized Complexity of Coloring Discovery", not verified) |
| W26 | `Kingston "Specifying and Solving Minimal Perturbation Problems in Timetabling" PATAT 2016` | 1 | C21d |
| V1–V7 | Metadata verification: Barba et al. Algorithmica; Yuan et al. PVLDB; Lemos et al. CPAIOR 2020; Lindahl et al.; Gülcü & Akkan; Akkan et al. COR; Verfaillie & Jussien | — | Gave the DOIs or pages for C02, C08, C10, C13, C14 and the abstracts for C15, C16, C17 |

### 2.2 OpenAlex `/autocomplete/works?q=` (title-phrase matching; 23 queries)

| # | q= | Count | Relevant |
|---|---|---|---|
| A1 | minimal perturbation examination timetabling | 0 | — |
| A2 | minimal perturbation | 99 (page 1 read) | C12, C18; El Sakkout & Wallace 2000 (10.1023/a:1009856210543, pre-window) |
| A3 | examination timetabling disruption | 0 | — |
| A4 | robust examination timetabl | 1 | C21a |
| A5 | dynamic graph colo | 20 (page 1 read) | C08, C02 (WADS version), C03 (+ESA 2018 version), C09, C22a (+GECCO 2019 version 10.1145/3321707.3321792); Ouerfelli & Bouziri 2011 (pre-window) |
| A6 | exam timetabling under uncertainty | 0 | — |
| A7 | Kempe chain | 16 (page 1 read) | Kempe-chain neighbourhoods for course timetabling: Mauritsius et al. 2007; Shaker & Abdullah 2009; Abdullah et al. 2010. All are static optimisation and pre-window. |
| A8 | Kempe changes | 8 | C23b, C23c (+COCOON 2019 version), C23d (+arXiv), Bonamy et al. 2021 bounded treewidth; Belavadi & Cameron arXiv 2512.00695 |
| A9 | examination rescheduling | 1 | 0 (medical physical-examination scheduling) |
| A10 | incremental graph colo | 1 | 0 (register allocation) |
| A11 | dynamic timetabling | 3 | Elkhyari, Guéret & Jussien (dynamic timetabling as dynamic RCPSP; pre-window, no DOI) |
| A12 | timetable repair | 0 | — |
| A13 | timetabling disruptions | 0 | — |
| A14 | minimal perturbation university | 2 | C21f (+arXiv version) |
| A15 | Fixing improper colorings | 3 | C23a (+arXiv, +conference version 10.1007/978-3-662-46078-8_22) |
| A16 | recoloring | 334 (page 1 read) | 0 on page 1 (image recolouring and similar) |
| A17 | timetabling perturbation | 0 | — |
| A18 | reoptimization coloring | 0 | — |
| A19 | exam rescheduling | 0 | — |
| A20 | dynamic examination timetabling | 0 | — |
| A21 | dynamic coloring | 100 (page 1 read) | 0 ("dynamic colouring" here is a different graph-theory notion) |
| A22 | limited recourse | 36 (page 1 read) | C11 |
| A23 | Specifying and solving minimal perturbation | 0 | Kingston 2016 is not indexed under this title |
| A24 | On a conjecture of Mohar concerning Kempe | 1 | C23e |

### 2.3 OpenAlex `/works?search=` attempts (all failed with HTTP 429)

1. `search=Dynamic graph coloring Barba Cardinal` (x2)
2. `search=Effective and efficient dynamic graph coloring` (x2)
3. `search=Hybrid search for minimal perturbation in dynamic CSPs`
4. `filter=title.search:minimal perturbation dynamic CSPs`
5. `search=examination timetabling minimal perturbation&per-page=10`
6. `search=exam timetabling rescheduling&per-page=10&filter=from_publication_date:2010-01-01`
7. `search=minimal perturbation timetabling&per-page=10`

### 2.4 Crossref

- `query.bibliographic=Hybrid search for minimal perturbation in Dynamic CSPs`: success. It found the correct C19 DOI and El Sakkout & Wallace 2000.
- `query.bibliographic=Dynamic graph coloring Barba ...` and `query.bibliographic=examination timetabling rescheduling disruption perturbation (from 2016)`: both HTTP 429.

### 2.5 DOI verification (OpenAlex `/works/doi:`)

Every item in `verified_C.jsonl` that has a DOI was looked up by DOI on OpenAlex. Exceptions:
- C02: OpenAlex returns 404; verified on the Springer page instead.
- C19: the draft DOI returned 404; the corrected DOI was then verified.
- C21d: has no DOI.

Many OpenAlex records have no abstract (`abstract_inverted_index` is null). In those cases the abstract was taken from Springer, ScienceDirect, RePEc, or OpenAlex's record of the arXiv version, as stated in each record's `notes`.

### 2.6 Seen but not added (unverified, or out of scope)

- Fuchs, arXiv 2511.06473
- Rajaraman et al., arXiv 2408.05370
- Belavadi & Cameron, arXiv 2512.00695
- arXiv 2609.09837
- JGT 2024 10.1002/jgt.23142
- Akkan et al. J. Sched. 2022 (10.1007/s10951-022-00722-0)
- JCTA "Evaluating Disruption Recovery …" (course)
- UniCorT, Lemos et al., J. Sched. 25(4):371–390 (10.1007/s10951-021-00695-6): metadata verified on OpenAlex, but no abstract, so its MPP content is unconfirmed
- Weitz 2024 BA thesis
- Elkhyari et al. (pre-window)
- El Sakkout & Wallace 2000 (pre-window)
- Kempe-chain course-timetabling heuristics 2007–2010 (pre-window, static)

## 3. Novelty-risk assessment (task C)

This assessment uses only the items retrieved above. The search had no OpenAlex relevance search (rate-limited), and it did not cover Scopus, Web of Science, Google Scholar or the full PATAT proceedings archive. It also cannot see paywalled full texts whose abstracts were missing.

**(i) Repair of an exam timetable after enrolment changes with a minimal-move objective: not found, but one paper could not be checked.**
- No retrieved exam-timetabling paper states, in its retrieved abstract or text, a reactive repair after enrolment changes that minimises the number of exams moved.
- The closest exam-specific work is C21a (Bassimir & Wanka, J. Sched. 2024/25). It is **proactive**: robust exam timetables built from curricula so that rescheduling is less likely once registrations are known. It is not a repair algorithm.
- C21b (Omar et al., MIWAI 2023, "Rescheduling Exams Within the Announced Tenure Using Reinforcement Learning") is exam rescheduling by title, but its abstract and full text could not be read (no abstract in OpenAlex or Crossref; Springer page rate-limited). **The search cannot rule out that it overlaps with the project.** The student should obtain and read it.
- C21c (same group, 2025) also has no abstract retrieved.
- Minimal perturbation after enrolment changes is well established for **course** timetabling: C12 (Phillips et al., which explicitly mentions enrolment changes), C13, C14, C15, C16 (with a structural-difference budget similar to B), C17 and C18.
- C23a (Garnero et al., Color-Fixing) formalises exactly the "fixed palette, fewest recoloured vertices" repair problem and proves it NP-complete for 3 or more colours and FPT in the number of recolourings. **The project should cite C23a for its exact-oracle problem and must not claim the problem formulation as new.**

**(ii) Kempe-chain or bounded recolouring for timetable repair after insertions: partially found, not in a timetabling setting.**
- C09 (Hardy et al., J. Heuristics) handles edge-dynamic graph colouring, is motivated by exam timetabling, and its text defines a Kempe-chain interchange. However, it minimises the number of colours, does not measure how many vertices change colour, and uses random graphs only.
- C22a (Bossek et al., Algorithmica 2021) analyses re-optimisation after edge insertions, including iterated local search with Kempe-chain mutation. It is runtime theory on bipartite and planar graphs, with no perturbation objective.
- Bounded-recourse recolouring is studied in theory: C02, C03, C10, C11, C22c.
- No retrieved paper combines Kempe chains, single moves and a move budget B to repair an exam timetable within a fixed number of periods.

**(iii) Evaluation of such repair on Toronto instances: not found.**
- None of the retrieved repair or minimal-perturbation papers reports Toronto instances in the text that was read. They use, respectively:
  - C12: University of Auckland data
  - C13: IST Lisbon data
  - C14: ITC 2019
  - C16, C17: ITC-2007 or ITC data
  - C18: Purdue data
  - C09: random graphs
- The datasets of C15, C21a, C21b and C21c could not be confirmed from the retrieved text.

**Overall verdict: novelty risk is moderate for the components and low to moderate for the specific combination.**

What is not new, and should be framed as prior work:
- the minimal-perturbation repair concept (C12–C18)
- its complexity on colourings (C23a)
- Kempe chains in dynamic colouring (C09, C22a)
- colour-versus-recolouring trade-offs (C02, C06, C11)

What appears defensible, within the scope above, is the specific combination:
- exam timetables
- late-enrolment edge insertions
- a fixed number of periods
- a tiered single-move, one-blocker and bounded-Kempe repair under a move budget B
- comparison against full recomputation and an exact CP-SAT minimum-perturbation oracle
- evaluation on Toronto instances

The main unresolved risk is C21b, whose content was not read.

Caveat on B05: the WebFetch summary of the Siew et al. 2024 IEEE Access exam-timetabling survey reported that it does not discuss rescheduling, perturbation, disruption or robustness. The summariser may have truncated the PDF, so this negative result is low-confidence and should not be cited as evidence of a gap.
