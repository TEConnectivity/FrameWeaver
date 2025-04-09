import ast
from multiprocessing import Queue, Process
import pythonmonkey as pm
import signal

def js_worker(task_queue, result_queue):
    """Process that listens for tasks and executes JS functions."""
    decoder = pm.require("../../submodules/ttn-decoder/TnnJsDecoder/TE_TtnDecoder.js")

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




####### Javascript interface #######

def start_js_worker():
    """Start the JS worker process and return the queues and process."""
    task_queue = Queue()
    result_queue = Queue()
    
    worker_process = Process(target=js_worker, args=(task_queue, result_queue))
    worker_process.start()

    return worker_process, task_queue, result_queue

def stop_js_worker(task_queue: Queue, process: Process):
    # Stop the fetcher process
    task_queue.put("STOP")
    process.join()

def call_js_function(task_queue, result_queue, func_name, *args):
    """Send a JS function call request and get the result."""
    task_queue.put((func_name, args))  # Send function and args
    return result_queue.get()  # Receive result

def decode(task_queue, result_queue, raw: bytes, fPort: int) -> dict:
    result = call_js_function(task_queue, result_queue, "te_decoder", list(raw),10)
    decoded = ast.literal_eval(node_or_string=str(result))
    return decoded