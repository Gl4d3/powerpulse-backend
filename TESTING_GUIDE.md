# PowerPulse Analytics - Testing Guide

## Quick Start

### 1. Install Test Dependencies
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or use the test runner to install dependencies
python run_tests.py --install-deps
```

### 2. Run Tests
```bash
# Run all tests with coverage
python run_tests.py

# Run only unit tests
python run_tests.py --type unit

# Run only integration tests
python run_tests.py --type integration

# Run tests without coverage
python run_tests.py --no-coverage

# Run tests quietly
python run_tests.py --quiet
```

### 3. Run Tests Directly with pytest
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_models.py

# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Run tests in parallel (if pytest-xdist installed)
pytest -n auto
```

## Test Structure

### Directory Layout
```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_models.py      # Database model tests
│   ├── test_schemas.py     # Pydantic schema tests
│   └── test_services/      # Service layer tests
├── integration/             # Integration tests
│   └── test_api_endpoints.py # API endpoint tests
├── fixtures/                # Test data fixtures
│   └── sample_conversations.json
└── utils/                   # Test utilities
    └── test_helpers.py
```

### Test Categories

#### Unit Tests (`tests/unit/`)
- **Models**: Database model functionality and relationships
- **Schemas**: Pydantic validation and serialization
- **Services**: Business logic and external API integration
- **Routes**: API endpoint logic (without full HTTP stack)

#### Integration Tests (`tests/integration/`)
- **API Endpoints**: Full HTTP request/response cycle
- **Database Operations**: End-to-end database workflows
- **External Services**: GPT API integration testing

#### Test Fixtures (`tests/fixtures/`)
- **Sample Data**: Realistic conversation data for testing
- **Edge Cases**: Invalid data, malformed JSON, etc.
- **Performance Data**: Large datasets for load testing

## Writing Tests

### Unit Test Example
```python
class TestConversationModel:
    """Test Conversation model functionality."""
    
    def test_create_conversation(self, test_db_session: Session):
        """Test creating a new conversation."""
        conversation = Conversation(
            chat_id="TEST_CHAT_001",
            first_message_time=datetime.now(),
            last_message_time=datetime.now(),
            message_count=3,
            sentiment_score=0.8,
            satisfaction_score=5,
            is_resolved=True,
            topics=["customer service", "satisfaction"]
        )
        
        test_db_session.add(conversation)
        test_db_session.commit()
        
        assert conversation.id is not None
        assert conversation.chat_id == "TEST_CHAT_001"
```

### Integration Test Example
```python
class TestUploadEndpoint:
    """Test file upload endpoint functionality."""
    
    def test_upload_valid_json(self, client: TestClient, test_db_session: Session):
        """Test successful JSON file upload."""
        test_data = {
            "FB_CHAT_ID_1": [
                {
                    "FB_CHAT_ID": "FB_CHAT_ID_1",
                    "MESSAGE_CONTENT": "Hello, I need help",
                    "DIRECTION": "to_company",
                    "SOCIAL_CREATE_TIME": "2025-01-15T10:00:00.000Z",
                    "AGENT_USERNAME": None,
                    "AGENT_EMAIL": None
                }
            ]
        }
        
        json_content = json.dumps(test_data)
        
        response = client.post(
            "/api/upload-json",
            files={"file": ("test_data.json", json_content, "application/json")},
            data={"force_reprocess": "false"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

## Test Fixtures

### Database Fixtures
- **test_db_session**: In-memory SQLite database for each test
- **client**: FastAPI TestClient with test database
- **sample_conversation_data**: Realistic conversation data

### Mock Fixtures
- **mock_gpt_response**: Simulated GPT API responses
- **sample_metrics_data**: Pre-calculated metrics for testing

## Best Practices

### 1. Test Naming
- Use descriptive test names that explain what is being tested
- Follow the pattern: `test_[method_name]_[scenario]`
- Example: `test_create_conversation_with_valid_data`

### 2. Test Structure
- **Arrange**: Set up test data and conditions
- **Act**: Execute the code being tested
- **Assert**: Verify the expected outcomes

### 3. Test Isolation
- Each test should be independent
- Use fresh database sessions for each test
- Clean up test data after each test

### 4. Coverage Goals
- **Unit Tests**: 90%+ coverage target
- **Integration Tests**: Cover all API endpoints
- **Edge Cases**: Test error conditions and boundary values

## Running Specific Tests

### By Test Name
```bash
# Run tests matching a pattern
pytest -k "test_create_conversation"

# Run tests in a specific class
pytest -k "TestConversationModel"
```

### By Markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run slow tests
pytest -m slow
```

### By File or Directory
```bash
# Run tests in specific file
pytest tests/unit/test_models.py

# Run tests in specific directory
pytest tests/unit/
```

## Debugging Tests

### Verbose Output
```bash
# Show detailed test output
pytest -v

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

### Debugging Specific Tests
```bash
# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3

# Run only failing tests
pytest --lf
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## Performance Testing

### Load Testing
```python
def test_large_dataset_processing(self, client: TestClient):
    """Test processing large datasets."""
    # Create 1000+ conversations
    large_dataset = create_large_test_dataset(1000)
    
    start_time = time.time()
    response = client.post("/api/upload-json", ...)
    processing_time = time.time() - start_time
    
    assert response.status_code == 200
    assert processing_time < 60  # Should complete within 60 seconds
```

### Memory Testing
```python
def test_memory_usage(self, client: TestClient):
    """Test memory consumption during processing."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Process large dataset
    response = client.post("/api/upload-json", ...)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable (< 100MB)
    assert memory_increase < 100 * 1024 * 1024
```

## Troubleshooting

### Common Issues

#### Import Errors
- Ensure you're running tests from the project root
- Check that all dependencies are installed
- Verify Python path includes the project directory

#### Database Errors
- Tests use in-memory SQLite by default
- Each test gets a fresh database session
- Check that models are properly imported

#### GPT API Errors
- Use mock responses for unit tests
- Only test real API integration in integration tests
- Set up proper environment variables for API keys

### Getting Help
1. Check the test output for specific error messages
2. Use `pytest -v` for verbose output
3. Add `print()` statements or use `pytest -s` for debugging
4. Check the test fixtures in `conftest.py`

## Next Steps

1. **Start with Unit Tests**: Begin testing individual components
2. **Add Integration Tests**: Test API endpoints and workflows
3. **Improve Coverage**: Aim for 90%+ test coverage
4. **Add Performance Tests**: Test with large datasets
5. **Set up CI/CD**: Automate testing in your deployment pipeline

This testing infrastructure provides a solid foundation for ensuring code quality and reliability as you polish the PowerPulse backend pipeline.
