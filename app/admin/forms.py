# from flask_wtf import FlaskForm
# from wtforms import StringField, TextAreaField, SelectField, SubmitField
# from wtforms.validators import DataRequired
#
# class SectionForm(FlaskForm):
#     title = StringField('Section Title', validators=[DataRequired()])
#     submit = SubmitField('Create Section')
#
# class QuestionForm(FlaskForm):
#     title = StringField('Question Title', validators=[DataRequired()])
#     description = TextAreaField('Description', validators=[DataRequired()])
#     starter_code = TextAreaField('Starter Code (Optional)')
#     hints = TextAreaField('Hints (Optional)')
#     difficulty = SelectField('Difficulty', choices=[(1, '1-Easy'), (2, '2'), (3, '3'), (4, '4'), (5, '5-Hard')], coerce=int)
#     submit = SubmitField('Create Question')
#
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired

class SectionForm(FlaskForm):
    title = StringField('Section Title', validators=[DataRequired()])
    submit = SubmitField('Create Section')

class QuestionForm(FlaskForm):
    title = StringField('Question Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    starter_code = TextAreaField('Starter Code (Optional)')
    hints = TextAreaField('Hints (Optional)')
    difficulty = SelectField('Difficulty', choices=[(1, '1-Easy'), (2, '2'), (3, '3'), (4, '4'), (5, '5-Hard')], coerce=int)
    # --- ADDED ---
    # The new checkbox for the admin.
    has_file_manager = BooleanField('Enable File Manager for this Question?')
    expected_output = TextAreaField('Expected Output (for challenges)')
    submit = SubmitField('Create/Update Question')
