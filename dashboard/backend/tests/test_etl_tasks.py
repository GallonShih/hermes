import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.etl.tasks import log_execution, run_process_chat_messages, run_import_dicts

def test_log_execution_no_engine():
    """Test logging execution when no database engine is available."""
    with patch('app.etl.config.ETLConfig.get_engine', return_value=None):
        # Should not raise exception
        log_execution('test_job', 'Test Job', {'status': 'completed'})

@patch('app.etl.config.ETLConfig.get_engine')
def test_log_execution_success(mock_get_engine):
    """Test successful logging of execution results."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    
    result = {
        'status': 'completed',
        'total_processed': 100,
        'execution_time_seconds': 10,
        'started_at': datetime.now()
    }
    
    log_execution('test_job', 'Test Job', result)
    
    mock_conn.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

@patch('app.etl.processors.chat_processor.ChatProcessor')
@patch('app.etl.tasks.log_execution')
def test_run_process_chat_messages(mock_log, mock_processor_class):
    """Test running process chat messages task."""
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor
    mock_processor.run.return_value = {'status': 'completed', 'total_processed': 10}
    
    result = run_process_chat_messages()
    
    assert result['status'] == 'completed'
    mock_processor.run.assert_called_once()
    mock_log.assert_called_once()

@patch('app.etl.processors.dict_importer.DictImporter')
@patch('app.etl.tasks.log_execution')
def test_run_import_dicts(mock_log, mock_importer_class):
    """Test running import dicts task."""
    mock_importer = MagicMock()
    mock_importer_class.return_value = mock_importer
    mock_importer.run.return_value = {'status': 'completed'}
    
    result = run_import_dicts()
    
    assert result['status'] == 'completed'
    mock_importer.run.assert_called_once()
    mock_log.assert_called_once()

@patch('app.etl.processors.chat_processor.ChatProcessor')
@patch('app.etl.tasks.log_execution')
def test_run_process_chat_messages_failure(mock_log, mock_processor_class):
    """Test task failure handling."""
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor
    mock_processor.run.side_effect = Exception("Task failed")
    
    result = run_process_chat_messages()
    
    assert result['status'] == 'failed'
    assert 'Task failed' in result['error']
    mock_log.assert_called_once()
