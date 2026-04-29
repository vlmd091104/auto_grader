- Use the service_pure.py if your machine has a strong GPU (e.g., A100 or L40)
- Use the service_lmstudio.py with LMstudio on your machine if the GPU is weak (e.g., 4GB VRAM GPUs)
- Note: Both services use the same model and prompt, so the result does not differ between the two services
- fallback_service.py uses the bag of words logic, not an AI model, to handle grading in case the main service fails
to do the job. So it is best to run it as well, though not necessary.
- After initiating the services, run mooc_app_llm.py (the demo app) and do some tests.
