"""import threading
from queue import Queue
#from app import create_app, db
from app.models import Submission
from app.sandbox import execute_code

# The task queue will hold submission IDs
task_queue = Queue()

def worker():
    from app import create_app, db
    #The worker function that processes tasks from the queue.
    # Create an app context to allow database access in this thread
    app = create_app()
    with app.app_context():
        print("--- Worker thread started and waiting for a job... ---")
        while True:
            # Get a submission_id from the queue. This will block until a task is available.
            submission_id = task_queue.get()
            print(f"--- Worker picked up job: {submission_id} ---")
            
            try:
                # Find the submission in the database
                submission = db.session.get(Submission, submission_id)
                if not submission:
                    continue

                submission.status = 'executing'
                db.session.commit()

                # Execute the code
                result = execute_code(submission.code)

                # Update the submission with the results
                submission.status = result.get('status', 'system_error')
                submission.output = result.get('output', '')
                # Append sandbox error to output for visibility
                if result.get('error'):
                    submission.output += f"\n--- ERROR ---\n{result.get('error')}"

                db.session.commit()

            except Exception as e:
                print(f"Error processing submission {submission_id}: {e}")
                # Optionally, update submission status to reflect system error
                db.session.rollback()
                submission = db.session.get(Submission, submission_id)
                if submission:
                    submission.status = 'system_error'
                    submission.output = 'A system error occurred during execution.'
                    db.session.commit()
            finally:
                # Signal that the task is done
                task_queue.task_done()

def start_workers(num_workers=4):
    #Starts the specified number of worker threads.
    for i in range(num_workers):
        # Daemon threads will exit when the main program exits
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    print(f"Started {num_workers} worker threads.")
    """

import threading
from queue import Queue
from app.models import Submission
from app.sandbox import execute_code

task_queue = Queue()

def worker(app): # <-- ACCEPT 'app' AS AN ARGUMENT
    """The worker function that processes tasks from the queue."""
    # REMOVED: No need to call create_app() anymore!
    with app.app_context(): # <-- USE THE PROVIDED 'app'
        # (You can remove the debug print now if you like)
        print("--- Worker thread started and waiting for a job... ---")
        while True:
            submission_id = task_queue.get()
            print(f"--- Worker picked up job: {submission_id} ---")

            # We need to get the db instance from the app's extensions
            db = app.extensions['sqlalchemy']

            try:
                submission = db.session.get(Submission, submission_id)
                if not submission:
                    continue

                # ... (rest of the try block is the same) ...
                submission.status = 'executing'
                db.session.commit()
                result = execute_code(submission.code)
                submission.status = result.get('status', 'system_error')
                submission.output = result.get('output', '')
                if result.get('error'):
                    submission.output += f"\n--- ERROR ---\n{result.get('error')}"
                db.session.commit()

            except Exception as e:
                print(f"Error processing submission {submission_id}: {e}")
                db.session.rollback()
                submission = db.session.get(Submission, submission_id)
                if submission:
                    submission.status = 'system_error'
                    submission.output = 'A system error occurred during execution.'
                    db.session.commit()
            finally:
                task_queue.task_done()

def start_workers(app, num_workers=4): # <-- ACCEPT 'app' AS AN ARGUMENT
    """Starts the specified number of worker threads."""
    for i in range(num_workers):
        # Pass the app object to the worker thread
        thread = threading.Thread(target=worker, args=(app,), daemon=True)
        thread.start()
    print(f"Started {num_workers} worker threads.")
