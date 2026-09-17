import pytest
from unittest.mock import AsyncMock, MagicMock
from core.brevio_api.services.progress.reporter import ProgressReporter
from core.shared.models.user.data_result import DataResult
from core.shared.enums.job_status import JobStatus
from core.brevio_api.models.user.folder_entry import FolderEntry

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    # Setup default mock return for get_folder_entry_by_id
    entry = MagicMock()
    entry.results = []
    repo.get_folder_entry_by_id.return_value = entry
    return repo

@pytest.mark.asyncio
async def test_calculate_global_progress(mock_repo):
    reporter = ProgressReporter(mock_repo, "user_1", "job_1")
    
    # Test empty results
    assert await reporter._calculate_global_progress([]) == 0
    
    # Test single result
    r1 = DataResult(id="1", weight=1, progress=50, status=JobStatus.PROCESSING.value)
    assert await reporter._calculate_global_progress([r1]) == 50
    
    # Test weighted results
    r1 = DataResult(id="1", weight=2, progress=50, status=JobStatus.PROCESSING.value)
    r2 = DataResult(id="2", weight=1, progress=100, status=JobStatus.COMPLETED.value)
    # (50*2 + 100*1) / 3 = 200 / 3 = 66
    assert await reporter._calculate_global_progress([r1, r2]) == 66
    
    # Test failed result
    r3 = DataResult(id="3", weight=1, progress=50, status=JobStatus.FAILED.value)
    # failed keeps its progress as is in our current logic
    assert await reporter._calculate_global_progress([r3]) == 50

@pytest.mark.asyncio
async def test_update_item_progress_throttling(mock_repo, monkeypatch):
    mock_publish = MagicMock()
    monkeypatch.setattr("core.brevio_api.services.progress.reporter.get_event_broker", lambda: MagicMock(publish=mock_publish))
    
    reporter = ProgressReporter(mock_repo, "user_1", "job_1")
    result = DataResult(id="1", progress=0, status=JobStatus.PROCESSING.value)
    
    # Setup mock entry to return the result
    entry = FolderEntry(id="job_1", user_id="user_1", name="Test", results=[result])
    mock_repo.get_folder_entry_by_id.return_value = entry
    
    # First update should persist
    await reporter.update_item_progress("1", result, progress=10, stage="QUEUED")
    assert mock_repo.update_data_result.call_count == 1
    
    # Minor update (diff < 5%) should NOT persist, but still emit event
    await reporter.update_item_progress("1", result, progress=12, stage="QUEUED")
    assert mock_repo.update_data_result.call_count == 1 # still 1
    assert mock_publish.call_count == 2
    
    # Stage change should persist regardless of progress diff
    await reporter.update_item_progress("1", result, progress=12, stage="PROCESSING")
    assert mock_repo.update_data_result.call_count == 2
    
    # Large progress jump should persist
    await reporter.update_item_progress("1", result, progress=50, stage="PROCESSING")
    assert mock_repo.update_data_result.call_count == 3
