from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from app.models import Section, Question, Challenge, AppSetting, User, Submission
from datetime import datetime, timezone

def admin_required(f):
    """Decorator to ensure a user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# In app/admin/routes.py (below the decorator)

from flask import render_template
from app import db
from app.admin import bp
from app.models import Section, Question
from app.admin.forms import SectionForm, QuestionForm



@bp.route('/section/add', methods=['GET', 'POST'])
@admin_required
def add_section():
    form = SectionForm()
    if form.validate_on_submit():
        section = Section(title=form.title.data)
        db.session.add(section)
        db.session.commit()
        flash('New section created successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/section_form.html', form=form, title='Add Section')

@bp.route('/question/add/<int:section_id>', methods=['GET', 'POST'])
@admin_required
def add_question(section_id):
    section = Section.query.get_or_404(section_id)
    form = QuestionForm()
    if form.validate_on_submit():
        question = Question(
            title=form.title.data,
            description=form.description.data,
            starter_code=form.starter_code.data,
            hints=form.hints.data,
            difficulty=form.difficulty.data,
            section_id=section.id
        )
        db.session.add(question)
        db.session.commit()
        flash('New question added successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/question_form.html', form=form, title='Add Question', section=section)



@bp.route('/section/toggle_lock/<int:section_id>', methods=['POST'])
@admin_required
def toggle_section_lock(section_id):
    section = Section.query.get_or_404(section_id)
    section.is_unlocked = not section.is_unlocked
    db.session.commit()
    flash(f"Section '{section.title}' has been {'unlocked' if section.is_unlocked else 'locked'}.", "success")
    return redirect(url_for('admin.dashboard'))

@bp.route('/section/edit/<int:section_id>', methods=['GET', 'POST'])
@admin_required
def edit_section(section_id):
    section = Section.query.get_or_404(section_id)
    form = SectionForm(obj=section)
    if form.validate_on_submit():
        section.title = form.title.data
        db.session.commit()
        flash('Section updated successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/section_form.html', form=form, title='Edit Section')

@bp.route('/section/delete/<int:section_id>', methods=['POST'])
@admin_required
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)
    db.session.delete(section)
    db.session.commit()
    flash('Section and all its questions have been deleted.', 'success')
    return redirect(url_for('admin.dashboard'))

@bp.route('/question/edit/<int:question_id>', methods=['GET', 'POST'])
@admin_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    form = QuestionForm(obj=question)
    if form.validate_on_submit():
        question.title = form.title.data
        question.description = form.description.data
        question.starter_code = form.starter_code.data
        question.hints = form.hints.data
        question.difficulty = form.difficulty.data
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/question_form.html', form=form, title='Edit Question', section=question.section)

@bp.route('/question/delete/<int:question_id>', methods=['POST'])
@admin_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Question has been deleted.', 'success')
    return redirect(url_for('admin.dashboard'))


@bp.route('/dashboard')
@admin_required
def dashboard():
    # Ensure leaderboard setting exists
    leaderboard_setting = AppSetting.query.filter_by(key='leaderboard_visible').first()
    if not leaderboard_setting:
        leaderboard_setting = AppSetting(key='leaderboard_visible', value='False')
        db.session.add(leaderboard_setting)
        db.session.commit()

    leaderboard_visible = (leaderboard_setting.value == 'True')
    hints_setting = AppSetting.query.filter_by(key='hints_enabled').first()
    if not hints_setting:
        hints_setting = AppSetting(key='hints_enabled', value='False')
        db.session.add(hints_setting)
        db.session.commit()

    hints_enabled = (hints_setting.value == 'True')
    leaderboard_visible = (leaderboard_setting.value == 'True')
    sections = Section.query.order_by(Section.id).all()
    active_challenges = {c.q_id: c for c in Challenge.query.filter_by(is_active=True).all()}

    return render_template(
        'admin/dashboard.html', 
        sections=sections, 
        challenges=active_challenges, 
        leaderboard_visible=leaderboard_visible,
    hints_enabled=hints_enabled
    )




@bp.route('/challenge/start/<int:question_id>', methods=['POST'])
@admin_required
def start_challenge(question_id):
    # End any other active challenges first to ensure only one is active at a time
    Challenge.query.filter_by(is_active=True).update({'is_active': False, 'end_time': datetime.now(timezone.utc)})

    # Start the new one
    challenge = Challenge(q_id=question_id, is_active=True, start_time=datetime.now(timezone.utc))
    db.session.add(challenge)
    db.session.commit()
    flash('Challenge started!', 'success')
    return redirect(url_for('admin.dashboard'))

@bp.route('/challenge/end/<int:challenge_id>', methods=['POST'])
@admin_required
def end_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    challenge.is_active = False
    challenge.end_time = datetime.now(timezone.utc)
    db.session.commit()
    flash('Challenge ended.', 'warning')
    return redirect(url_for('admin.dashboard'))

@bp.route('/leaderboard/toggle', methods=['POST'])
@admin_required
def toggle_leaderboard():
    setting = AppSetting.query.filter_by(key='leaderboard_visible').first()
    if setting.value == 'True':
        setting.value = 'False'
        flash('Leaderboard is now hidden.', 'warning')
    else:
        setting.value = 'True'
        flash('Leaderboard is now visible.', 'success')
    db.session.commit()
    return redirect(url_for('admin.dashboard'))



# At the end of app/admin/routes.py

@bp.route('/users')
@admin_required
def users():
    """Shows a list of all registered users."""
    all_users = User.query.order_by(User.id).all()
    return render_template('admin/users.html', users=all_users, title="User Management")

@bp.route('/user/<int:user_id>/submissions')
@admin_required
def user_submissions(user_id):
    user = User.query.get_or_404(user_id)
    
    # 1. Fetch all submissions, ordered with the latest first.
    all_submissions = Submission.query.filter_by(user_id=user.id)\
        .join(Question, Submission.q_id == Question.id)\
        .add_columns(Question.title)\
        .order_by(Submission.submitted_at.desc()).all()
    
    # 2. Filter in Python to keep only the latest for each question.
    latest_submissions = []
    seen_question_ids = set()
    for sub, q_title in all_submissions:
        if sub.q_id not in seen_question_ids:
            latest_submissions.append((sub, q_title))
            seen_question_ids.add(sub.q_id)

    return render_template(
        'admin/user_submissions.html', 
        user=user, 
        submissions=latest_submissions, 
        title=f"Submissions for {user.username}"
    )



@bp.route('/hints/toggle', methods=['POST'])
@admin_required
def toggle_hints():
    setting = AppSetting.query.filter_by(key='hints_enabled').first()
    if setting.value == 'True':
        setting.value = 'False'
        flash('Hints are now hidden for all users.', 'warning')
    else:
        setting.value = 'True'
        flash('Hints are now enabled for all users.', 'success')
    db.session.commit()
    return redirect(url_for('admin.dashboard'))
