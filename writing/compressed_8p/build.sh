f=$1
pdflatex -interaction=nonstopmode $f >/dev/null; bibtex $f >/dev/null; pdflatex -interaction=nonstopmode $f >/dev/null; pdflatex -interaction=nonstopmode $f >/dev/null
grep -E "Output written|Overfull|undefined|Undefined|\?\?" $f.log | head -20
