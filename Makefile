# One command reproduces the paper. Each stage writes only its own outputs.
PY ?= python3
.PHONY: all validate experiments analysis figures paper clean
all: validate experiments analysis figures paper
validate:    ; $(PY) experiments/validate.py
experiments: ; $(PY) experiments/run.py
analysis:    ; $(PY) analysis/analyse.py      # writes tables and paper/numbers.tex
figures:     ; $(PY) analysis/figures.py
paper:       ; cd paper && latexmk -pdf -interaction=nonstopmode main.tex
clean:       ; cd paper && latexmk -C
