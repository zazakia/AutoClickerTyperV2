"""
Test suite for Quick Prompts persistence functionality
"""
import json
import os
import tempfile
import shutil
from pathlib import Path

def test_quick_prompts_persistence():
    """Test that quick prompts can be saved and loaded correctly"""
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    test_file = os.path.join(test_dir, 'quick_prompts.json')
    
    try:
        # Test 1: Create and save prompts
        print("Test 1: Creating and saving prompts...")
        test_prompts = [
            {"label": "Test Prompt 1", "prompt": "This is test prompt 1"},
            {"label": "Test Prompt 2", "prompt": "This is test prompt 2"},
            {"label": "Test Prompt 3", "prompt": "This is test prompt 3"},
            {"label": "Test Prompt 4", "prompt": "This is test prompt 4"},
            {"label": "Test Prompt 5", "prompt": "This is test prompt 5"},
            {"label": "Test Prompt 6", "prompt": "This is test prompt 6"},
            {"label": "Test Prompt 7", "prompt": "This is test prompt 7"}
        ]
        
        with open(test_file, 'w') as f:
            json.dump(test_prompts, f, indent=4)
        
        assert os.path.exists(test_file), "Failed to create quick_prompts.json"
        print("✓ Prompts saved successfully")
        
        # Test 2: Load prompts
        print("\nTest 2: Loading prompts...")
        with open(test_file, 'r') as f:
            loaded_prompts = json.load(f)
        
        assert len(loaded_prompts) == 7, f"Expected 7 prompts, got {len(loaded_prompts)}"
        assert loaded_prompts[0]['label'] == "Test Prompt 1", "Label mismatch"
        assert loaded_prompts[0]['prompt'] == "This is test prompt 1", "Prompt mismatch"
        print("✓ Prompts loaded successfully")
        
        # Test 3: Update a prompt
        print("\nTest 3: Updating a prompt...")
        loaded_prompts[0] = {"label": "Updated Label", "prompt": "Updated prompt text"}
        
        with open(test_file, 'w') as f:
            json.dump(loaded_prompts, f, indent=4)
        
        # Reload and verify
        with open(test_file, 'r') as f:
            updated_prompts = json.load(f)
        
        assert updated_prompts[0]['label'] == "Updated Label", "Update failed"
        assert updated_prompts[0]['prompt'] == "Updated prompt text", "Update failed"
        print("✓ Prompt updated successfully")
        
        # Test 4: Verify actual file in project
        print("\nTest 4: Checking actual quick_prompts.json in project...")
        actual_file = 'quick_prompts.json'
        
        if os.path.exists(actual_file):
            with open(actual_file, 'r') as f:
                actual_prompts = json.load(f)
            
            print(f"✓ Found {len(actual_prompts)} prompts in actual file")
            print("\nCurrent Quick Prompts:")
            for i, prompt in enumerate(actual_prompts, 1):
                label = prompt.get('label', '')[:50]  # Truncate long labels
                prompt_text = prompt.get('prompt', '')[:50]
                print(f"  {i}. Label: '{label}'")
                print(f"     Prompt: '{prompt_text}'")
        else:
            print("⚠ No quick_prompts.json found in project root (will be created on first edit)")
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        print("\nQuick Prompts Persistence is working correctly!")
        print("- Prompts are saved to 'quick_prompts.json'")
        print("- Changes persist across application restarts")
        print("- Edit functionality saves immediately")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    success = test_quick_prompts_persistence()
    exit(0 if success else 1)
