ACCOUNT := stkbailey
REPO := tap-exchange-rates

docker-publish:
	docker login
	docker build --tag ${ACCOUNT}/${REPO}:latest .
	docker push ${ACCOUNT}/${REPO}:latest
