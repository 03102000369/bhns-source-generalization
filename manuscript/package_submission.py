"""Assemble journal submission copies from built, reviewed manuscript sources.

No scientific computation or figure rendering is performed. Run from the release
root after manuscript/build.sh, passing its output directory with --build-dir.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript"
OUTPUT = ROOT / "submission" / "astronomy_and_computing"


def archive(path, files):
    """Write deterministic archives without host paths or directory metadata."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, source in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, source.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build/manuscript")
    args = parser.parse_args()
    built = args.build_dir.resolve()
    # Avoid silently packaging a PDF/BibTeX output from a different source.
    for relative in ("main.tex", "references.bib", "supplement/supplement.tex"):
        if (built / relative).read_bytes() != (MANUSCRIPT / relative).read_bytes():
            raise ValueError(f"Build source differs from canonical source: {relative}")
    figures = sorted((MANUSCRIPT / "figures").glob("figure_*.pdf"))
    if len(figures) != 6:
        raise ValueError("Expected exactly six validated main figures")
    evidence = sorted((MANUSCRIPT / "supplement/tables").iterdir())
    if len(evidence) != 80 or not all(p.is_file() for p in evidence):
        raise ValueError("Expected the frozen 80-file supplementary evidence set")
    sources = {"references.bib": MANUSCRIPT / "references.bib",
               "main.bbl": built / "main.bbl"}
    sources.update({p.name: p for p in figures})
    copies = {**sources, "main.pdf": built / "main.pdf",
              "supplement.pdf": built / "supplement.pdf",
              "highlights.txt": MANUSCRIPT / "highlights.txt",
              "supplementary_captions.txt": MANUSCRIPT / "supplement/submission_captions.txt"}
    expected = set(copies) | {"main.tex", "manuscript_source.zip", "supplementary_evidence.zip"}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    unexpected = {p.name for p in OUTPUT.iterdir()} - expected
    if unexpected:
        raise ValueError(f"Unexpected files in submission directory: {sorted(unexpected)}")
    for name, source in copies.items():
        shutil.copyfile(source, OUTPUT / name)
    text = (MANUSCRIPT / "main.tex").read_text()
    for figure in figures:
        old = "{figures/" + figure.name + "}"
        if text.count(old) != 1:
            raise ValueError(f"Expected one figure input: {figure.name}")
        text = text.replace(old, "{" + figure.name + "}")
    (OUTPUT / "main.tex").write_text(text)
    source_files = {name: OUTPUT / name for name in sources}
    source_files["main.tex"] = OUTPUT / "main.tex"
    archive(OUTPUT / "manuscript_source.zip", source_files)
    archive(OUTPUT / "supplementary_evidence.zip", {"tables/" + p.name: p for p in evidence})
    # Check that the distributable archive contains the exact evidence bytes.
    with zipfile.ZipFile(OUTPUT / "supplementary_evidence.zip") as bundle:
        for path in evidence:
            if hashlib.sha256(bundle.read("tables/" + path.name)).digest() != hashlib.sha256(path.read_bytes()).digest():
                raise ValueError(f"Evidence archive mismatch: {path.name}")
    print(f"Prepared {len(expected)} submission files; {len(source_files)} flat source entries; {len(evidence)} unchanged evidence entries.")


if __name__ == "__main__":
    main()
