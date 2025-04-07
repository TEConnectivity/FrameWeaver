import pythonmonkey as pm
import signal

def js_worker(task_queue, result_queue):
    """Process that listens for tasks and executes JS functions."""
    decoder = pm.require("../submodules/ttn-decoder/TnnJsDecoder/TE_TtnDecoder.js")

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    while True:
        task = task_queue.get()  # Wait for task
        if task == "STOP":
            break  # Stop process
        
        try:
            func_name, args = task  # Extract function name and arguments
            if hasattr(decoder, func_name):
                result = getattr(decoder, func_name)(*args)
                result_queue.put(str(result))
            else:
                result_queue.put(f"Error: {func_name} not found in JS module")

        except Exception as e:
            result_queue.put(f"Error: {e}")
