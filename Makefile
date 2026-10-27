.PHONY: install test build decks assets clean clean-generated

install:
	python -m pip install -r requirements.txt
	npm install

test:
	python -m pytest

assets:
	python src/build_assets.py --input data/cards.tsv

build:
	python src/build_lessons.py --input data/cards.tsv --radicals data/radicals.tsv --output-dir dist

decks: build
	mkdir -p decks
	find decks -maxdepth 1 -type f -name '*.apkg' -delete
	cp dist/*.apkg decks/

clean-generated:
	find assets/generated -type f ! -name .gitkeep -delete
	find dist -type f -name '*.apkg' -delete

clean: clean-generated
