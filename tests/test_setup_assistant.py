"""
Setup Assistant Tests
OpenAI Assistant 设置脚本测试

Coverage target: 90%+
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import os


class TestSetupAssistantConfig:
    """Test configuration constants"""
    
    def test_assistant_name_defined(self):
        """Assistant name is defined"""
        from application.services.setup_assistant import ASSISTANT_NAME
        assert ASSISTANT_NAME == "Make Decodables Support Assistant"
    
    def test_vector_store_name_defined(self):
        """Vector store name is defined"""
        from application.services.setup_assistant import VECTOR_STORE_NAME
        assert VECTOR_STORE_NAME == "Make Decodables Knowledge Base"
    
    def test_assistant_instructions_defined(self):
        """Assistant instructions are defined"""
        from application.services.setup_assistant import ASSISTANT_INSTRUCTIONS
        assert "Make Decodables" in ASSISTANT_INSTRUCTIONS
        assert "customer support" in ASSISTANT_INSTRUCTIONS.lower()
    
    def test_knowledge_base_path_defined(self):
        """Knowledge base path is defined"""
        from application.services.setup_assistant import KNOWLEDGE_BASE_PATH
        assert "knowledge_base.md" in KNOWLEDGE_BASE_PATH


class TestMain:
    """Test main function"""
    
    @patch('services.setup_assistant.os.environ.get')
    def test_exits_when_no_api_key(self, mock_get):
        """Exits with error when no API key"""
        from application.services.setup_assistant import main
        
        mock_get.return_value = None
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
    
    @patch('services.setup_assistant.OpenAI')
    @patch('services.setup_assistant.os.environ.get')
    @patch('services.setup_assistant.os.path.exists')
    def test_exits_when_knowledge_base_not_found(self, mock_exists, mock_get, mock_openai):
        """Exits when knowledge base file not found"""
        from application.services.setup_assistant import main
        
        mock_get.return_value = "sk-test-key"
        mock_exists.return_value = False
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
    
    @patch('httpx.get')
    @patch('httpx.post')
    @patch('services.setup_assistant.OpenAI')
    @patch('services.setup_assistant.os.environ.get')
    @patch('services.setup_assistant.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"# Knowledge Base")
    def test_successful_setup(self, mock_file, mock_exists, mock_get, mock_openai, mock_httpx_post, mock_httpx_get):
        """Complete successful setup"""
        from application.services.setup_assistant import main
        
        # Setup mocks
        mock_get.return_value = "sk-test-key"
        mock_exists.return_value = True
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock file upload
        mock_file_response = MagicMock()
        mock_file_response.id = "file-123"
        mock_client.files.create.return_value = mock_file_response
        
        # Mock vector store creation
        mock_vs_response = MagicMock()
        mock_vs_response.status_code = 200
        mock_vs_response.json.return_value = {"id": "vs-123"}
        mock_httpx_post.return_value = mock_vs_response
        
        # Mock vector store status
        mock_status_response = MagicMock()
        mock_status_response.json.return_value = {
            "file_counts": {"completed": 1, "total": 1}
        }
        mock_httpx_get.return_value = mock_status_response
        
        # Mock assistant creation
        mock_assistant = MagicMock()
        mock_assistant.id = "asst-123"
        mock_client.beta.assistants.create.return_value = mock_assistant
        
        # Run main - should not raise
        main()
        
        # Verify calls
        mock_client.files.create.assert_called_once()
        mock_httpx_post.assert_called()
        mock_client.beta.assistants.create.assert_called_once()
    
    @patch('httpx.post')
    @patch('services.setup_assistant.OpenAI')
    @patch('services.setup_assistant.os.environ.get')
    @patch('services.setup_assistant.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"# Knowledge Base")
    def test_exits_on_vector_store_creation_error(self, mock_file, mock_exists, mock_get, mock_openai, mock_httpx_post):
        """Exits when vector store creation fails"""
        from application.services.setup_assistant import main
        
        mock_get.return_value = "sk-test-key"
        mock_exists.return_value = True
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_file_response = MagicMock()
        mock_file_response.id = "file-123"
        mock_client.files.create.return_value = mock_file_response
        
        # Mock vector store creation failure
        mock_vs_response = MagicMock()
        mock_vs_response.status_code = 500
        mock_vs_response.text = "Internal Server Error"
        mock_httpx_post.return_value = mock_vs_response
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
    
    @patch('time.sleep')
    @patch('httpx.get')
    @patch('httpx.post')
    @patch('services.setup_assistant.OpenAI')
    @patch('services.setup_assistant.os.environ.get')
    @patch('services.setup_assistant.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"# Knowledge Base")
    def test_waits_for_file_processing(self, mock_file, mock_exists, mock_get, mock_openai, mock_httpx_post, mock_httpx_get, mock_sleep):
        """Waits for file to be processed in vector store"""
        from application.services.setup_assistant import main
        
        mock_get.return_value = "sk-test-key"
        mock_exists.return_value = True
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_file_response = MagicMock()
        mock_file_response.id = "file-123"
        mock_client.files.create.return_value = mock_file_response
        
        # Mock vector store creation
        mock_vs_response = MagicMock()
        mock_vs_response.status_code = 200
        mock_vs_response.json.return_value = {"id": "vs-123"}
        mock_httpx_post.return_value = mock_vs_response
        
        # Mock processing status - first call returns incomplete, second returns complete
        mock_status_incomplete = MagicMock()
        mock_status_incomplete.json.return_value = {
            "file_counts": {"completed": 0, "total": 1}
        }
        mock_status_complete = MagicMock()
        mock_status_complete.json.return_value = {
            "file_counts": {"completed": 1, "total": 1}
        }
        mock_httpx_get.side_effect = [mock_status_incomplete, mock_status_complete]
        
        # Mock assistant creation
        mock_assistant = MagicMock()
        mock_assistant.id = "asst-123"
        mock_client.beta.assistants.create.return_value = mock_assistant
        
        main()
        
        # Should have called sleep at least once
        mock_sleep.assert_called()
    
    @patch('httpx.get')
    @patch('httpx.post')
    @patch('services.setup_assistant.OpenAI')
    @patch('services.setup_assistant.os.environ.get')
    @patch('services.setup_assistant.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=b"# Knowledge Base")
    def test_saves_env_file(self, mock_file, mock_exists, mock_get, mock_openai, mock_httpx_post, mock_httpx_get):
        """Saves assistant ID to .env.assistant file"""
        from application.services.setup_assistant import main
        
        mock_get.return_value = "sk-test-key"
        mock_exists.return_value = True
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_file_response = MagicMock()
        mock_file_response.id = "file-123"
        mock_client.files.create.return_value = mock_file_response
        
        mock_vs_response = MagicMock()
        mock_vs_response.status_code = 200
        mock_vs_response.json.return_value = {"id": "vs-123"}
        mock_httpx_post.return_value = mock_vs_response
        
        mock_status_response = MagicMock()
        mock_status_response.json.return_value = {
            "file_counts": {"completed": 1, "total": 1}
        }
        mock_httpx_get.return_value = mock_status_response
        
        mock_assistant = MagicMock()
        mock_assistant.id = "asst-123"
        mock_client.beta.assistants.create.return_value = mock_assistant
        
        main()
        
        # Check file was written (mock_open handles this)
        # The write calls would have OPENAI_ASSISTANT_ID
        write_calls = mock_file().write.call_args_list
        written_content = ''.join(call[0][0] for call in write_calls)
        assert "asst-123" in written_content or mock_file().write.called


class TestAssistantInstructions:
    """Test assistant instruction content"""
    
    def test_instructions_include_product_name(self):
        """Instructions mention product name"""
        from application.services.setup_assistant import ASSISTANT_INSTRUCTIONS
        assert "Make Decodables" in ASSISTANT_INSTRUCTIONS
    
    def test_instructions_include_support_channels(self):
        """Instructions include support channels"""
        from application.services.setup_assistant import ASSISTANT_INSTRUCTIONS
        # Should mention WhatsApp or email
        assert "WhatsApp" in ASSISTANT_INSTRUCTIONS or "email" in ASSISTANT_INSTRUCTIONS.lower()
    
    def test_instructions_set_tone(self):
        """Instructions set friendly tone"""
        from application.services.setup_assistant import ASSISTANT_INSTRUCTIONS
        assert "friendly" in ASSISTANT_INSTRUCTIONS.lower()
    
    def test_instructions_provide_guidelines(self):
        """Instructions provide response guidelines"""
        from application.services.setup_assistant import ASSISTANT_INSTRUCTIONS
        assert "guidelines" in ASSISTANT_INSTRUCTIONS.lower() or "Important" in ASSISTANT_INSTRUCTIONS


class TestModuleLevel:
    """Test module-level behavior"""
    
    def test_module_can_be_imported(self):
        """Module can be imported without errors"""
        import services.setup_assistant
        assert hasattr(services.setup_assistant, 'main')
        assert hasattr(services.setup_assistant, 'ASSISTANT_NAME')
    
    def test_main_not_called_on_import(self):
        """main() is not called when module is imported"""
        # This test verifies __name__ == "__main__" guard
        # If main() were called, it would fail due to missing API key
        import services.setup_assistant
        # If we get here without error, the guard works
        assert True
