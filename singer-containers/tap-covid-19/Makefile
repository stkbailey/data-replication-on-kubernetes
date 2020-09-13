ACCOUNT := stkbailey
REPO := tap-covid-19

docker-publish:
	docker login
	docker build --tag ${ACCOUNT}/${REPO}:latest .
	docker push ${ACCOUNT}/${REPO}:latest
