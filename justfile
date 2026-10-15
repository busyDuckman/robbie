#  This target gets the repo 100% ready for all development work (virtual environments etC)
#   - it will ask some questions like where AI models are typically downloaded to etc.
#   - it will copy .env.example to .env and set it up
setup:


# Basic unit test run
test:


# Full testing including model evals etc.
vet: test


# remove temporary files
clean:


# install robbie to a pi, or update the installation on a pi
deploy:

# RAG data to help robbie perform tasks
#   - A wizard that asks questions and informs about licence of downloaded work.
fetch-data

