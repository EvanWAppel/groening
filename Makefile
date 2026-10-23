.PHONY: new-city

# Stamp a fresh metro skeleton (TASKS E6; guide: docs/new-city.md), e.g.
#   make new-city DEST=../robbins CODENAME=robbins CITY="Seattle, WA" DB=seattle
new-city:
	@test -n "$(DEST)" -a -n "$(CODENAME)" -a -n "$(CITY)" -a -n "$(DB)" || \
		{ echo "usage: make new-city DEST=<dir> CODENAME=<name> CITY=\"<City, ST>\" DB=<stem>"; exit 2; }
	uv run python new_city.py "$(DEST)" --codename "$(CODENAME)" --city "$(CITY)" --db "$(DB)"
