import warnings

# Suppress harmless Starlette testclient deprecation warnings about httpx
warnings.filterwarnings("ignore", message=r".*httpx.*", category=UserWarning)
warnings.filterwarnings("ignore", message=r".*Using `httpx`.*", category=UserWarning)
