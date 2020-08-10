DOCKER := docker

.PHONY: docker-build docker-build-nocache

docker-build: download
	$(DOCKER) build $(DOCKER_BUILD_ARGS) --tag $(IMAGE):latest .

docker-build-nocache: DOCKER_BUILD_ARGS := --no-cache
docker-build-nocache: docker-build
