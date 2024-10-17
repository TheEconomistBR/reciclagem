from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta
from datetime import datetime
from sqlalchemy.sql import func
import googlemaps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'YOUR_SECRET_KEY'  # Substitua por uma chave secreta forte
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///solicitacoes.db'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24) # Configura o tempo de expiração da sessão
db = SQLAlchemy(app)

# Inicializando o gerenciador de login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Define a página de login para redirecionamento

# Configurando Google Maps API (Substitua pela sua chave)
gmaps = googlemaps.Client(key='AIzaSyAEMKBzayjpWnZ7Y9GRlSteTisgSgdqHIY')


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
    tipo_lixo = db.Column(db.String(50), nullable=False)
    quantidade = db.Column(db.String(50), nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pendente')  # Status: pendente, aceito, retirado

    # Morador que solicitou a coleta (chave estrangeira para a tabela Usuario)
    morador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    morador = db.relationship('Usuario', foreign_keys=[morador_id], backref='coletas_solicitadas')

    # Catador que aceitou o pedido (chave estrangeira para a tabela Usuario)
    catador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    catador = db.relationship('Usuario', foreign_keys=[catador_id], backref='coletas_realizadas')


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



# Carregar o usuário a partir do ID da sessão
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


@app.route('/ranking')
def ranking():
    # Ranking de Moradores (baseado na quantidade de pedidos de coleta)
    ranking_moradores = (
        db.session.query(
            Usuario.nome.label('name'),
            func.count(Lixo.id).label('requests')  # Quantidade de pedidos de coleta
        )
        .join(Lixo, Lixo.morador_id == Usuario.id)
        .group_by(Usuario.id)
        .order_by(func.count(Lixo.id).desc())  # Ordena pela quantidade de pedidos, do maior para o menor
        .all()
    )

    # Ranking de Catadores (baseado na quantidade de coletas realizadas)
    ranking_catadores = (
        db.session.query(
            Usuario.nome.label('name'),
            func.count(Lixo.id).label('collected')  # Quantidade de coletas realizadas
        )
        .join(Lixo, Lixo.catador_id == Usuario.id)
        .group_by(Usuario.id)
        .order_by(func.count(Lixo.id).desc())  # Ordena pela quantidade de coletas, do maior para o menor
        .all()
    )

    return render_template('ranking.html', ranking_moradores=ranking_moradores, ranking_catadores=ranking_catadores)




@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Usuario.query.filter_by(email=email).first()

        if user and check_password_hash(user.senha, password):
            login_user(user)
            # Redireciona diretamente para a página do morador ou catador
            if user.tipo == 'prestador':
                return redirect(url_for('catador'))
            elif user.tipo == 'usuario':
                return redirect(url_for('morador'))
        else:
            flash('Login ou senha incorretos.')
    return render_template('login.html')



@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        # Pegando os dados do formulário
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # Deve ser 'usuario' ou 'prestador'

        # Pegando os dados de endereço
        tipo_via = request.form.get('tipo_via')
        nome_rua = request.form.get('nome_rua')
        numero = request.form.get('numero')
        cep = request.form.get('cep')
        referencia = request.form.get('referencia')

        # Gerar hash da senha
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Criar novo usuário com os campos do formulário, incluindo o endereço
        new_user = Usuario(
            nome=username,
            email=email,
            senha=hashed_password,
            tipo=role,
            tipo_via=tipo_via,
            nome_rua=nome_rua,
            numero=numero,
            cep=cep,
            referencia=referencia
        )

        # Salvando o novo usuário no banco de dados
        db.session.add(new_user)
        db.session.commit()

        flash('Cadastro realizado com sucesso!')
        return redirect(url_for('login'))
    
    # Renderiza o template de cadastro se for um GET request
    return render_template('cadastro.html')


@app.route('/catador', methods=['GET', 'POST'])
@login_required
def catador():
    if current_user.tipo != 'prestador':
        return redirect(url_for('index'))

    # Buscar todos os pedidos pendentes
    pedidos = Lixo.query.filter_by(status='pendente').all()

    # Caso o pedido seja aceito, capturamos o pedido_id enviado via POST
    pedido_aceito = None

    if request.method == 'POST':
        pedido_id = request.form.get('pedido_id')
        pedido_aceito = Lixo.query.get_or_404(pedido_id)

        # Atualizar o status do pedido para "aceito" e associar o catador
        if pedido_aceito.status == 'pendente':
            pedido_aceito.status = 'aceito'
            pedido_aceito.catador_id = current_user.id
            db.session.commit()

            flash('Pedido aceito com sucesso!')

    # Renderizar a página do catador com os pedidos e o pedido aceito, se aplicável
    return render_template('catador.html', pedidos=pedidos, pedido_aceito=pedido_aceito)


@app.route('/morador', methods=['GET', 'POST'])
@login_required
def morador():
    if current_user.tipo != 'usuario':
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Captura os valores do formulário
        tipo_lixo = request.form.get('tipo_lixo')
        quantidade = request.form.get('quantidade')

        # Verifica se o usuário optou por alterar o endereço
        alterar_endereco = request.form.get('alterar_endereco')
        if alterar_endereco == 'sim':
            tipo_via = request.form.get('tipo_via_novo')
            nome_rua = request.form.get('nome_rua_novo')
            numero = request.form.get('numero_novo')
            cep = request.form.get('cep_novo')
            endereco = f"{tipo_via} {nome_rua}, {numero} - CEP: {cep}"
        else:
            endereco = f"{current_user.tipo_via} {current_user.nome_rua}, {current_user.numero} - CEP: {current_user.cep}"

        # Criar o novo pedido de coleta
        novo_pedido = Lixo(tipo_lixo=tipo_lixo, quantidade=quantidade, endereco=endereco, morador_id=current_user.id, status='pendente')

        # Salvar o pedido no banco de dados
        db.session.add(novo_pedido)
        db.session.commit()

        flash('Pedido de coleta criado com sucesso!')
        return redirect(url_for('morador'))

    # Renderizar o template do morador se for GET
    return render_template('morador.html')


@app.route('/acompanhar_coleta')
@login_required
def acompanhar_coleta():
    if current_user.tipo != 'usuario':
        return redirect(url_for('index'))

    # Buscar as solicitações de coleta do usuário logado e incluir o catador (se houver)
    solicitacoes = Lixo.query.filter_by(morador_id=current_user.id).all()

    return render_template('acompanhar_coleta.html', solicitacoes=solicitacoes)

@app.route('/confirmar_retirada/<int:solicitacao_id>', methods=['POST'])
@login_required
def confirmar_retirada(solicitacao_id):
    # Buscar a solicitação pelo ID
    solicitacao = Lixo.query.get_or_404(solicitacao_id)

    # Verificar se o usuário atual é o proprietário da solicitação
    if solicitacao.morador_id != current_user.id:
        flash("Você não tem permissão para confirmar essa retirada.")
        return redirect(url_for('acompanhar_coleta'))

    # Atualizar o status para 'retirado'
    solicitacao.status = 'retirado'
    db.session.commit()

    flash("A coleta foi confirmada como retirada.")
    return redirect(url_for('acompanhar_coleta'))



@app.route('/aceitar_pedido/<int:pedido_id>', methods=['GET', 'POST'])
@login_required
def aceitar_pedido(pedido_id):
    # Verifica se o usuário é um catador
    if current_user.tipo != 'prestador':
        return redirect(url_for('index'))

    # Buscar o pedido pelo ID
    pedido = Lixo.query.get_or_404(pedido_id)

    # Atualizar o status do pedido para "aceito" e associar o catador
    if pedido.status == 'pendente':
        pedido.status = 'aceito'
        pedido.catador_id = current_user.id
        db.session.commit()

    # Construir o endereço completo do catador usando os campos tipo_via, nome_rua e numero
    endereco_catador = f"{current_user.tipo_via} {current_user.nome_rua}, {current_user.numero}"

    # Construir o endereço completo do morador usando os campos tipo_via, nome_rua e numero
    endereco_morador = f"{pedido.tipo_via} {pedido.nome_rua}, {pedido.numero}"

    # Verifique se o endereço do morador é válido
    if not endereco_morador or not endereco_catador:
        flash("O endereço do morador ou do catador está inválido.")
        return redirect(url_for('catador'))

    try:
        # Chamar a API do Google Maps para obter as direções
        directions_result = gmaps.directions(endereco_catador, endereco_morador)

        # Verificar se há resultado
        if not directions_result:
            flash("Nenhuma rota foi encontrada.")
            return redirect(url_for('catador'))

    except googlemaps.exceptions.ApiError as e:
        flash(f"Erro ao gerar a rota: {e}")
        return redirect(url_for('catador'))

    # Redirecionar para a página de exibição da rota
    return render_template('visualizar_rota.html', pedido=pedido, directions=directions_result)


@app.route('/historico_catador')
@login_required
def historico_catador():
    if current_user.tipo != 'prestador':
        return redirect(url_for('index'))

    # Buscar todas as solicitações aceitas pelo catador logado
    coletas = Lixo.query.filter_by(catador_id=current_user.id).all()

    return render_template('historico_catador.html', coletas=coletas)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)