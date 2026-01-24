SHELL := /bin/bash

.PHONY: deploy-aws

deploy-aws:
	./scripts/deploy_aws.sh
