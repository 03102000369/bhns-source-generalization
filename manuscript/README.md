# Astronomy and Computing journal manuscript

The canonical journal-branch sources are `main.tex`, `references.bib`, and
`supplement/supplement.tex`. The scientific baseline remains commit
`3c5bb50b1820ef89f816fc2f4da0fb6c69f359f7`, tagged
`pre-submission-scientific-freeze`. The journal preparation changes formatting,
confirmed author metadata, declarations, the abstract length, keywords, and
supplement delivery only. Main-body scientific prose, equations, tables, all
seven scientific figure PDFs, the bibliography database, and underlying data
remain unchanged apart from the explicitly authorized SI conversion note and
minor supplementary wording corrections.

Both documents use the installed official `elsarticle` class, its `5p`
two-column layout, author-year citations, and `elsarticle-harv`. No template
files were downloaded. Visible alt-text paragraphs have become source comments;
scientific captions are retained. There is no empty acknowledgements section.
The unused historical `mnras.cls` and `mnras.bst` are not submission dependencies.

## Build canonical documents

From the release root, use a fresh ignored output directory for a clean build:

```bash
PATH="/Library/TeX/texbin:$PATH" BHNS_LATEX_BUILD_DIR="$PWD/build/journal_conversion/canonical" bash manuscript/build.sh
```

On other platforms, ensure `pdflatex` and `bibtex` are on PATH and omit the macOS
PATH prefix. The build uses pdfLaTeX, BibTeX, elsarticle, elsarticle-harv, fontenc,
newtxtext/newtxmath, amsmath, booktabs, xurl, microtype, etoolbox and hyperref;
graphicx and natbib are provided through the class. Build products and logs stay
in the selected ignored directory. Omitting `BHNS_LATEX_BUILD_DIR` retains the
usual `build/manuscript/` destination. The script does not overwrite tracked PDFs.
Only after source and visual review, copy the reviewed `main.pdf` and
`supplement.pdf` to their canonical manuscript locations.

## Prepare submission copies

```bash
python manuscript/package_submission.py --build-dir build/journal_conversion/canonical
```

This creates `submission/astronomy_and_computing/`, including a flat main source,
bibliography and generated BBL, the six original main figure PDFs, review PDFs,
highlights, supplementary captions, a nine-entry flat source archive, and an
80-entry evidence archive. No model is fitted and no figure is regenerated.
The official class/style are supplied by TeX Live rather than vendored; install
`elsarticle` when the compilation environment does not already provide it.

To verify independence, extract `manuscript_source.zip` into a fresh ignored
working directory, then run `pdflatex -recorder -interaction=nonstopmode
-halt-on-error main.tex`, `bibtex main`, and repeat the same pdfLaTeX command
until the log has no unresolved citations or reference-rerun requests. No
repository-relative TeX inputs or custom TEXINPUTS setting should be needed.
Keep compilation logs and auxiliary caches out of the submission directory.

The standalone supplement links to the identical evidence bytes in the frozen
public repository. `supplementary_evidence.zip` preserves the `tables/` layout
and contains the 78 indexed evidence files plus `evidence_index.csv` and
`column_dictionary.csv`. `submission_captions.txt` supplies the two supplementary
item descriptions. Supplement TeX and Figure S1 remain in the canonical source
tree, not in the scientific evidence archive.

The separate competing-interest document must be completed in Editorial Manager;
it is not fabricated here. No graphical abstract, Zenodo record, DOI, GitHub
release, or publication metadata is claimed. The author-approved AI disclosure
and all end-matter statements are in the main manuscript. External reference/DOI
verification remains a separate task. Figure S1's historical renderer and full
proxy source-score inputs remain undistributed, as stated in the paper.
