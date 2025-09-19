from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
from app.models import User, Question, Draft,Submission, Section, AppSetting, Challenge # Import the Draft model
from app.sandbox import execute_code
from app.queue_system import task_queue
from sqlalchemy import func
from app import db # Import db
import io
import zipfile
import re
from flask import send_file
from datetime import datetime,timezone
bp = Blueprint('main', __name__)

# ... (index route is unchanged) ...
from app.models import Section # Make sure Section is imported

@bp.route('/')
@bp.route('/index')
def index():
    sections = Section.query.filter_by(is_unlocked=True).order_by(Section.id).all()
    active_challenge = Challenge.query.filter_by(is_active=True).first()
    return render_template('index.html', title='Home', sections=sections, active_challenge=active_challenge)


@bp.route('/practice/<int:question_id>')
@login_required
def practice_question(question_id):
    question = Question.query.get_or_404(question_id)
    draft = Draft.query.filter_by(user_id=current_user.id, q_id=question.id).first()
    initial_code = draft.code if draft else question.starter_code

    # Check if this question is part of an active challenge
    active_challenge = Challenge.query.filter_by(q_id=question_id, is_active=True).first()

    return render_template(
        'practice.html', 
        title=question.title, 
        question=question, 
        initial_code=initial_code,
        is_challenge=(active_challenge is not None) # Pass a boolean flag
    )

# MODIFIED API route to SUBMIT code
@bp.route('/api/run_code', methods=['POST'])
@login_required
def run_code():
    data = request.get_json()
    code = data.get('code', '')
    q_id = data.get('q_id')
    start_time_ms = data.get('start_time') # Get start time from frontend

    active_challenge = Challenge.query.filter_by(q_id=q_id, is_active=True).first()

    # ... create new_submission ...
    new_submission = Submission(code=code, user_id=current_user.id, q_id=q_id, status='pending')

    # Calculate time_taken if it's a challenge submission
    if active_challenge and start_time_ms:
        end_time_ms = datetime.now(timezone.utc).timestamp() * 1000
        time_taken_seconds = (end_time_ms - start_time_ms) / 1000.0
        new_submission.time_taken = time_taken_seconds

    db.session.add(new_submission)
    db.session.commit()
    task_queue.put(new_submission.id)
    return jsonify(status='queued', submission_id=new_submission.id)

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
@bp.route('/api/save_draft', methods=['POST'])
@login_required
def save_draft():
    data = request.get_json()
    q_id = data.get('q_id')
    code = data.get('code')

    if not q_id:
        return jsonify(status='error', message='Question ID missing.'), 400

    draft = Draft.query.filter_by(user_id=current_user.id, q_id=q_id).first()
    if draft:
        # Update existing draft
        draft.code = code
    else:
        # Create new draft
        draft = Draft(user_id=current_user.id, q_id=q_id, code=code)
        db.session.add(draft)

    db.session.commit()
    return jsonify(status='success', message='Draft saved.')

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
