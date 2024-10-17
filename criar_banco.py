from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin 
from datetime import datetime  # Importar datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///solicitacoes.db'
db = SQLAlchemy(app)

# Modelos do banco de dados
class Usuario(UserMixin, db.Model):  # Herdando de UserMixin
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(80), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'usuario' ou 'prestador'
    tipo_via = db.Column(db.String(50), nullable=True)  # Novo campo
    nome_rua = db.Column(db.String(100), nullable=True)  # Novo campo
    numero = db.Column(db.String(10), nullable=True)  # Novo campo
    cep = db.Column(db.String(20), nullable=True)  # Novo campo
    referencia = db.Column(db.String(200), nullable=True)  # Novo campo

class Lixo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_lixo = db.Column(db.String(50))
    quantidade = db.Column(db.String(50))
    endereco = db.Column(db.String(200))
    status = db.Column(db.String(50))  # pendente, aceito, retirado
    morador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    catador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))  # Quem aceitou
    catador = db.relationship('Usuario', foreign_keys=[catador_id], backref='coletas_realizadas')
    morador = db.relationship('Usuario', foreign_keys=[morador_id], backref='coletas_solicitadas')

class AvaliacaoMorador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # Nota de 1 a 5
    comentario = db.Column(db.Text, nullable=True)
    morador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Morador sendo avaliado
    catador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Catador que fez a avaliação
    data_avaliacao = db.Column(db.DateTime, default=datetime.utcnow)

class AvaliacaoCatador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # Nota de 1 a 5
    comentario = db.Column(db.Text, nullable=True)
    catador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Catador sendo avaliado
    morador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Morador que fez a avaliação
    data_avaliacao = db.Column(db.DateTime, default=datetime.utcnow)



if __name__ == '__main__':    
    # Cria as tabelas no banco de dados
    with app.app_context():
        db.create_all()
    print("Banco de dados criado com sucesso!")
