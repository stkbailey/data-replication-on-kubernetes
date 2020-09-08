ACCOUNT := stkbailey
REPO := target-csv

docker-publish:
	docker login
	docker build --tag ${ACCOUNT}/${REPO}:latest .
	docker push ${ACCOUNT}/${REPO}:latest
