THIS_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

.PHONY: echo

echo:
	@echo $(IMAGE)
	@echo $(REPO)


include $(THIS_DIR)repo.mk
include $(THIS_DIR)docker-build.mk
