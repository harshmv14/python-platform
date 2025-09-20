from flask_login import current_user, login_required
from app.models import User, Question, Draft,Submission, Section, AppSetting, Challenge # Import the Draft model
from app.sandbox import execute_code
from app.queue_system import task_queue
from sqlalchemy import func
from app import db # Import db
import io
import zipfile
import re
from datetime import datetime,timezone
import os
import pathlib
from flask import (
    Blueprint, render_template, request, jsonify, current_app, send_from_directory,
    send_file
)
bp = Blueprint('main', __name__)

# ... (index route is unchanged) ...
from app.models import Section # Make sure Section is imported

@bp.route('/')
@bp.route('/index')
def index():
    sections = Section.query.filter_by(is_unlocked=True).order_by(Section.id).all()
    active_challenge = Challenge.query.filter_by(is_active=True).first()
    return render_template('index.html', title='Home', sections=sections, active_challenge=active_challenge)


# In app/main.py

@bp.route('/practice/<int:question_id>')
@login_required
def practice_question(question_id):
    question = Question.query.get_or_404(question_id)
    draft = Draft.query.filter_by(user_id=current_user.id, q_id=question.id).first()
    initial_code = question.starter_code or ''
     # --- MODIFIED LOADING LOGIC ---
    if question.has_file_manager:
        # For IDE view, try to load the code from the user's main.py file.
        workspace_path = get_or_create_workspace(current_user.id, question_id)
        main_file = pathlib.Path(workspace_path) / 'main.py'
        if main_file.exists():
            initial_code = main_file.read_text()
    else:
        # For simple view, load the last saved draft from the database.
        draft = Draft.query.filter_by(user_id=current_user.id, q_id=question.id).first()
        if draft:
            initial_code = draft.code
    # --- END MODIFIED LOGIC ---
    active_challenge = Challenge.query.filter_by(q_id=question_id, is_active=True).first()
    
    # --- NEW LOGIC to find the next question ---
    next_question_id = None
    # Get all questions in the correct order (by section, then by question id)
    all_questions = Question.query.order_by(Question.section_id, Question.id).all()
    
    # Find the index of the current question in the flat list
    try:
        current_index = [q.id for q in all_questions].index(question_id)
        # If the current question is not the last one, get the next one's id
        if current_index < len(all_questions) - 1:
            next_question_id = all_questions[current_index + 1].id
    except ValueError:
        # This case should not happen if the question_id is valid
        pass
    # --- END NEW LOGIC ---
    
    return render_template(
        'practice.html', 
        title=question.title, 
        question=question, 
        initial_code=initial_code,
        is_challenge=(active_challenge is not None),
        next_question_id=next_question_id # <-- Pass the new ID to the template
    )
# MODIFIED API route to SUBMIT code

# In app/main.py, with your other API routes

@bp.route('/api/save_draft', methods=['POST'])
@login_required
def save_draft():
    data = request.get_json()
    q_id = data.get('q_id')
    code = data.get('code', '')

    draft = Draft.query.filter_by(user_id=current_user.id, q_id=q_id).first()
    if draft:
        draft.code = code
    else:
        draft = Draft(user_id=current_user.id, q_id=q_id, code=code)
        db.session.add(draft)

    db.session.commit()
    return jsonify(status="success", message="Draft saved.")



@bp.route('/api/run_code', methods=['POST'])
@login_required
def run_code():
    data = request.get_json()
    q_id = data.get('q_id')
    code = data.get('code')
    filename = data.get('filename', 'main.py')
    start_time_ms = data.get('start_time') # Get start time for challenges
    question = Question.query.get_or_404(q_id)

    if question.has_file_manager:
        workspace_path = get_or_create_workspace(current_user.id, q_id)
        result = execute_code(code, workspace_path, filename)
    else:
        result = execute_code(code, None, filename)

    # --- ADDED BACK ---
    # Check if this submission is for an active challenge
    active_challenge = Challenge.query.filter_by(q_id=q_id, is_active=True).first()
    
    new_submission = Submission(
        code=code, 
        user_id=current_user.id, 
        q_id=q_id, 
        status=result.get('status'), 
        output=result.get('output')
    )
    if result.get('error'):
        new_submission.output += f"\n--- ERROR ---\n{result.get('error')}"

    # If it's a successful challenge submission, calculate and save the time
    if active_challenge and start_time_ms and result.get('status') == 'success':
        end_time_ms = datetime.now(timezone.utc).timestamp() * 1000
        time_taken_seconds = (end_time_ms - start_time_ms) / 1000.0
        new_submission.time_taken = time_taken_seconds
    
    db.session.add(new_submission)
    db.session.commit()
    return jsonify(result)


@bp.route('/api/files/list')
@login_required
def list_files():
    q_id = request.args.get('q_id', type=int)
    workspace_path = get_or_create_workspace(current_user.id, q_id)
    files = [f.name for f in pathlib.Path(workspace_path).iterdir() if f.is_file()]
    return jsonify(files)

@bp.route('/api/files/content')
@login_required
def get_file_content():
    q_id = request.args.get('q_id', type=int)
    filename = request.args.get('filename')
    workspace_path = pathlib.Path(get_or_create_workspace(current_user.id, q_id))
    file_path = workspace_path / filename
    if file_path.is_file():
        return jsonify(content=file_path.read_text())
    return jsonify(error="File not found"), 404

@bp.route('/api/files/save', methods=['POST'])
@login_required
def save_file():
    data = request.get_json()
    q_id = data.get('q_id')
    filename = data.get('filename')
    content = data.get('content')
    workspace_path = pathlib.Path(get_or_create_workspace(current_user.id, q_id))
    (workspace_path / filename).write_text(content)
    return jsonify(status="success")

@bp.route('/api/files/create', methods=['POST'])
@login_required
def create_file():
    data = request.get_json()
    q_id = data.get('q_id')
    filename = data.get('filename')
    if not filename:
        return jsonify(error="Filename cannot be empty"), 400
    workspace_path = pathlib.Path(get_or_create_workspace(current_user.id, q_id))
    (workspace_path / filename).touch() # Creates an empty file
    return jsonify(status="success")

@bp.route('/download-file')
@login_required
def download_file():
    q_id = request.args.get('q_id', type=int)
    filename = request.args.get('filename')
    workspace_path = get_or_create_workspace(current_user.id, q_id)
    return send_from_directory(workspace_path, filename, as_attachment=True)

# NEW API route to GET results
@bp.route('/api/get_result/<int:submission_id>')
@login_required
def get_result(submission_id):
    submission = db.session.get(Submission, submission_id)
    if not submission or submission.user_id != current_user.id:
        return jsonify(status='error', message='Submission not found or unauthorized.'), 404
    
    return jsonify(
        status=submission.status,
        output=submission.output
    )



# NEW API route to save drafts
# @bp.route('/api/save_draft', methods=['POST'])
# @login_required
# def save_draft():
#     data = request.get_json()
#     q_id = data.get('q_id')
#     code = data.get('code')
#
#     if not q_id:
#         return jsonify(status='error', message='Question ID missing.'), 400
#
#     draft = Draft.query.filter_by(user_id=current_user.id, q_id=q_id).first()
#     if draft:
#         # Update existing draft
#         draft.code = code
#     else:
#         # Create new draft
#         draft = Draft(user_id=current_user.id, q_id=q_id, code=code)
#         db.session.add(draft)
#
#     db.session.commit()
#     return jsonify(status='success', message='Draft saved.')
#
@bp.app_context_processor
def inject_global_vars():
    leaderboard_setting = AppSetting.query.filter_by(key='leaderboard_visible').first()
    return dict(
        leaderboard_visible=(leaderboard_setting and leaderboard_setting.value == 'True')
    )


@bp.route('/leaderboard')
@login_required
def leaderboard():
    active_challenge = Challenge.query.filter_by(is_active=True).first()
    ranked_submissions = []

    if active_challenge:
        # Find the best (fastest) successful submission for each user for the active challenge
        ranked_submissions = db.session.query(
            User.username,
            func.min(Submission.time_taken).label('best_time')
        ).join(Submission, User.id == Submission.user_id)\
        .filter(
            Submission.q_id == active_challenge.q_id,
            Submission.status == 'success',
            Submission.time_taken.isnot(None)
        ).group_by(User.username).order_by(func.min(Submission.time_taken)).all()

    return render_template(
        'leaderboard.html',
        title='Leaderboard',
        challenge=active_challenge,
        submissions=ranked_submissions
    )



# At the end of app/main.py

def sanitize_filename(name):
    """Removes special characters to make a valid filename."""
    name = re.sub(r'[^\w\s-]', '', name).strip()
    name = re.sub(r'[-\s]+', '_', name)
    return name

@bp.route('/download-submissions')
@login_required
def download_submissions():
    """Fetches user submissions, zips them, and sends to the user."""

    # 1. Fetch all submissions for the current user
    submissions = Submission.query.filter_by(user_id=current_user.id).order_by(Submission.submitted_at.desc()).all()

    # 2. Get the latest submission for each unique question
    latest_submissions = {}
    for sub in submissions:
        if sub.q_id not in latest_submissions:
            latest_submissions[sub.q_id] = sub

    # 3. Create an in-memory zip file
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for q_id, sub in latest_submissions.items():
            question = Question.query.get(q_id)
            if not question:
                continue

            # 4. Format the content for each file
            file_content = (
                f"# Question: {question.title}\n"
                f"# Difficulty: {question.difficulty}\n"
                f"# ------------------------------------------\n"
                f"# Description:\n"
            )

            # Add multi-line description as comments
            description_lines = question.description.split('\n')
            for line in description_lines:
                file_content += f"# {line}\n"

            file_content += (
                f"# ------------------------------------------\n\n"
                f"{sub.code}"
            )

            # 5. Create the filename and write to the zip archive
            filename = f"Question_{q_id}_{sanitize_filename(question.title)}.py"
            zf.writestr(filename, file_content.encode('utf-8'))

    memory_file.seek(0)

    # 6. Send the file to the browser for download
    return send_file(
        memory_file,
        download_name='my_submissions.zip',
        as_attachment=True,
        mimetype='application/zip'
    )



# In app/main.py

@bp.app_context_processor
def inject_global_vars():
    leaderboard_setting = AppSetting.query.filter_by(key='leaderboard_visible').first()
    hints_setting = AppSetting.query.filter_by(key='hints_enabled').first() # <-- ADD THIS
    return dict(
        leaderboard_visible=(leaderboard_setting and leaderboard_setting.value == 'True'),
        hints_enabled=(hints_setting and hints_setting.value == 'True') # <-- AND THIS
    )


def get_or_create_workspace(user_id, question_id):
    """Creates a persistent workspace and seeds it with a default file if empty."""
    workspace_path = pathlib.Path(current_app.root_path).parent / 'workspaces' / str(user_id) / str(question_id)
    
    is_new_workspace = not workspace_path.exists()
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # If the workspace was just created, add a default main.py
    if is_new_workspace:
        question = Question.query.get(question_id)
        main_py_path = workspace_path / 'main.py'
        # Populate with starter code if it exists, otherwise create an empty file
        starter_content = question.starter_code if question and question.starter_code else '# Start your code here'
        main_py_path.write_text(starter_content)
            
    return str(workspace_path)


@bp.route('/api/submit_challenge', methods=['POST'])
@login_required
def submit_challenge():
    data = request.get_json()
    q_id = data.get('q_id')
    code = data.get('code')
    start_time_ms = data.get('start_time')
    
    question = Question.query.get_or_404(q_id)
    active_challenge = Challenge.query.filter_by(q_id=q_id, is_active=True).first()

    if not active_challenge:
        return jsonify(status='error', message='This challenge is no longer active.'), 400

    # Run the code to get the result
    result = execute_code(code, None, 'main.py') # Simplified execution for challenges
    
    # Validate the result
    is_correct = False
    if result.get('status') == 'success' and question.expected_output:
        # Compare the stripped output to the stripped expected output
        actual_output = result.get('output', '').strip()
        expected_output = question.expected_output.strip()
        if actual_output == expected_output:
            is_correct = True
    
    # Log the submission
    submission = Submission(code=code, user_id=current_user.id, q_id=q_id)
    submission.status = 'challenge_correct' if is_correct else 'challenge_incorrect'
    submission.output = result.get('output')
    if result.get('error'):
        submission.output += f"\n--- ERROR ---\n{result.get('error')}"

    if is_correct:
        end_time_ms = datetime.now(timezone.utc).timestamp() * 1000
        time_taken_seconds = (end_time_ms - start_time_ms) / 1000.0
        submission.time_taken = time_taken_seconds
        
    db.session.add(submission)
    db.session.commit()
    
    return jsonify({
        'is_correct': is_correct,
        'output': submission.output,
        'message': "Congratulations! Your solution is correct and your time has been logged." if is_correct else "Your output did not match the expected result. Please review your code and try again."
    })


# In app/main.py, add this with your other API routes

@bp.route('/api/files/delete', methods=['POST'])
@login_required
def delete_file():
    data = request.get_json()
    q_id = data.get('q_id')
    filename = data.get('filename')

    if not all([q_id, filename]):
        return jsonify(error="Missing required data"), 400

    workspace_path = pathlib.Path(get_or_create_workspace(current_user.id, q_id))
    file_to_delete = workspace_path / filename

    # --- Security Check ---
    # Ensure the file is actually inside the workspace to prevent path traversal attacks (e.g., ../../app.py)
    if not file_to_delete.is_file() or workspace_path not in file_to_delete.resolve().parents:
        return jsonify(error="File not found or access denied."), 404
        
    try:
        file_to_delete.unlink() # This deletes the file
        return jsonify(status="success", message=f"File '{filename}' deleted.")
    except Exception as e:
        return jsonify(error=f"Could not delete file: {e}"), 500
