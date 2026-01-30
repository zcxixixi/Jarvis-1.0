# Mock onnxruntime if not available (for bypass)
import sys
from unittest.mock import MagicMock

class MockOrt:
    class InferenceSession:
        def __init__(self, *args, **kwargs): pass
        def run(self, *args, **kwargs): return [[0.0]] # Mock low probability
        def get_inputs(self): return [MagicMock(name='input')]
    
    class SessionOptions:
        def __init__(self): pass
        
try:
    import onnxruntime
except ImportError:
    print("⚠️ [MOCK] onnxruntime not found. Using Mock for wake word bypass.")
    sys.modules["onnxruntime"] = MockOrt()
