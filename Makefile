WHATEVER := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
$(eval $(WHATEVER):;@:)
# ^ Captures all the stuff passed after the target. If you are going
# to pass options, you may do so by using "--" e.g.:
# make up -- --build

file = docker/dev/docker-compose.yml
ifeq (${CONTEXT}, production)
	file = docker/prod/docker-compose.yml
endif

project = sozluk
cc = docker compose -p $(project) -f $(file)
ex = docker exec -it sozluk-web
dj = $(ex) python manage.py

.PHONY: *
.DEFAULT_GOAL := detach

build:
	$(cc) build $(WHATEVER)
up:
	$(cc) up $(WHATEVER)
detach:
	$(cc) up -d $(WHATEVER)
down:
	$(cc) down $(WHATEVER)
stop:
	$(cc) stop $(WHATEVER)
compose:
	$(cc) $(WHATEVER)
logs:
	docker logs $(WHATEVER) --tail 500 --follow
console:
	$(ex) /bin/sh
run:
	$(dj) $(WHATEVER)
shell:
	$(dj) shell
shell_plus:
	$(dj) shell_plus
test:
	$(dj) test --settings=djdict.settings --shuffle --timing --keepdb
format:
	pre-commit run
setup:
	$(dj) quicksetup
