from app import create_app, db
from app.models import User, Question, Section, Submission, Draft, Challenge

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Makes variables available in the 'flask shell' context."""
    return {
        'db': db, 
        'User': User, 
        'Question': Question, 
        'Section': Section,
        'Submission': Submission,
        'Draft': Draft,
        'Challenge': Challenge
    }

if __name__ == '__main__':
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
