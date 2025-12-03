from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    SelectField, FileField, TextAreaField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(6, 128)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('I am a', choices=[('candidate', 'Candidate'), ('hr', 'HR')], validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UploadForm(FlaskForm):
    file = FileField('Resume (PDF or DOCX)', validators=[DataRequired()])
    submit = SubmitField('Upload')

class JobForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired(), Length(3, 200)])
    description = TextAreaField('Job Description', validators=[DataRequired(), Length(10)])
    submit = SubmitField('Create Job')
