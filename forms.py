from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField
from wtforms.validators import DataRequired, Optional, Email, EqualTo, Length


class LoginForm(FlaskForm):
    """Connexion unique pour l'administrateur et les agents."""
    username = StringField("Nom d'utilisateur", validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])


class AgentForm(FlaskForm):
    """Création ou modification d'un compte agent par l'administrateur."""
    nom_complet = StringField('Nom complet', validators=[DataRequired()])
    nom_utilisateur = StringField("Nom d'utilisateur", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Adresse e-mail', validators=[Optional(), Email()])
    password = PasswordField('Mot de passe initial', validators=[Optional(), Length(min=4)])
    confirm_password = PasswordField(
        'Confirmation du mot de passe',
        validators=[Optional(), EqualTo('password', message='Les mots de passe ne correspondent pas.')],
    )
    role = SelectField('Rôle', choices=[('agent', 'Agent'), ('administrateur', 'Administrateur')])
    actif = BooleanField('Compte actif', default=True)
