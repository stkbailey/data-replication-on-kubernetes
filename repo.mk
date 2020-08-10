.PHONY: download clean

download: clean $(REPO)

$(REPO):
	@echo "Removing and re-downloading repo"
	git clone https://github.com/immuta/$(REPO).git $@

clean:
	rm -rf $(REPO)
