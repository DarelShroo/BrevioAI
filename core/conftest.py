import os
import pytest

# Set environment variables at module level so they are available during collection
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["MAX_TOKENS"] = "1000"
os.environ["MAX_TOKENS_PER_CHUNK"] = "250"
os.environ["TOKENS_PER_MINUTE"] = "500"
os.environ["TEMPERATURE"] = "0.7"
os.environ["OPENAI_API_KEY"] = "fake_api_key"

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    # Redundant but keeps it explicit for test execution
    pass
