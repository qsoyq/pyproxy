.PHONY: default format mypy build push test tox


IMAGE_NAME := qsoyq/pyproxy
PROJECT_NAME := pyproxy


default: build push


format: refactor pre-commit


refactor:
	@yapf -r -i . 
	@isort . 
	@pycln -a .


pre-commit:
	@pre-commit run --all-file


mypy:
	@mypy .


build:
	docker build --platform linux/amd64 -t $(IMAGE_NAME) .


test:
	PYTHONPATH=. pytest tests


push:
	docker push $(IMAGE_NAME)
	if [ -n ${BARK_TOKEN} ]; then curl https://api.day.app/$(BARK_TOKEN)/$(PROJECT_NAME)%20push%20success; fi;


tox:
	docker volume create tox-testenv
	docker build -t tox-testenv -f ./docker/tox-testenv.Dockerfile .
	docker run -it --rm -v tox-testenv:/app/.tox tox-testenv
