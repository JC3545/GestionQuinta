from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración de la base de datos SQLite
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "instance", "gestor_quinta.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de usuario
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), default='colaborador')

# Modelo de reservas
class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fecha_desde = db.Column(db.String(50), nullable=False)
    fecha_hasta = db.Column(db.String(50), nullable=False)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(15), nullable=False)
    tipo_evento = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=False)
    sena = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)
    dirigido_a = db.Column(db.String(100), nullable=False)
    resto = db.Column(db.Float, nullable=False)
    observaciones = db.Column(db.String(250), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Rutas de la aplicación
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos')
            return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hashear la contraseña antes de almacenarla
        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Usuario registrado con éxito')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()  # Deshacer cambios en caso de error
            flash('El usuario ya existe')
            print(e)  # Para depuración
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/verificar_fecha', methods=['POST'])
@login_required
def verificar_fecha():
    fecha_verificacion = request.form['fecha_verificacion']
    
    # Comprobar si hay reservas en esa fecha
    reservas = Reserva.query.filter(
        (Reserva.fecha_desde <= fecha_verificacion) & 
        (Reserva.fecha_hasta >= fecha_verificacion)
    ).all()

    if reservas:
        flash('La fecha ya está reservada.')  # Mensaje de fecha no disponible
        return redirect(url_for('home'))  # Redirige a la página de inicio
    else:
        return redirect(url_for('cargar_reserva'))  # Redirige a cargar reserva



@app.route('/cargar_reserva', methods=['GET', 'POST'])
@login_required
def cargar_reserva():
    if request.method == 'POST':
        fecha_desde = request.form['fecha_desde']
        fecha_hasta = request.form['fecha_hasta'] or fecha_desde  # Si está vacío, toma el valor de "desde"
        nombre_cliente = request.form['nombre_cliente']
        telefono = request.form['telefono']
        tipo_evento = request.form['tipo_evento']
        total = float(request.form['total'])
        sena = float(request.form['sena'])
        metodo_pago = request.form['metodo_pago']
        dirigido_a = request.form['dirigido_a']
        resto = float(request.form['resto'])
        observaciones = request.form['observaciones']

        nueva_reserva = Reserva(
            usuario_id=current_user.id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,  # Se asigna el valor modificado aquí
            nombre_cliente=nombre_cliente,
            telefono=telefono,
            tipo_evento=tipo_evento,
            total=total,
            sena=sena,
            metodo_pago=metodo_pago,
            dirigido_a=dirigido_a,
            resto=resto,
            observaciones=observaciones
        )

        db.session.add(nueva_reserva)
        db.session.commit()

        flash('Reserva cargada exitosamente')

        if metodo_pago.lower() == 'efectivo':
            return redirect(url_for('generar_recibo', reserva_id=nueva_reserva.id))

        return redirect(url_for('home'))
    else:
        return render_template('cargar_reserva.html')

    
@app.route('/ver_reservas')
@login_required
def ver_reservas():
    reservas = Reserva.query.filter_by(usuario_id=current_user.id).all()
    
    # Convertir las fechas de cadena a objetos datetime y luego formatear
    for reserva in reservas:
        reserva.fecha_desde = datetime.strptime(reserva.fecha_desde, '%Y-%m-%d').strftime('%d-%m-%Y')
        reserva.fecha_hasta = datetime.strptime(reserva.fecha_hasta, '%Y-%m-%d').strftime('%d-%m-%Y')

    return render_template('ver_reservas.html', reservas=reservas)


@app.route('/ver_detalle_reserva/<int:reserva_id>')
@login_required
def ver_detalle_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    return render_template('ver_detalle_reserva.html', reserva=reserva)


@app.route('/editar/<int:reserva_id>', methods=['GET', 'POST'])
@login_required
def editar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    
    if request.method == 'POST':
        reserva.fecha_desde = request.form['fecha_desde']
        reserva.fecha_hasta = request.form['fecha_hasta'] or reserva.fecha_desde  # Asigna "desde" si "hasta" está vacío
        reserva.nombre_cliente = request.form['nombre_cliente']
        reserva.telefono = request.form['telefono']
        reserva.tipo_evento = request.form['tipo_evento']
        reserva.total = float(request.form['total'])
        reserva.sena = float(request.form['sena'])
        reserva.metodo_pago = request.form['metodo_pago']
        reserva.dirigido_a = request.form['dirigido_a']
        reserva.resto = float(request.form['resto'])
        reserva.observaciones = request.form['observaciones']

        db.session.commit()
        flash('Reserva actualizada exitosamente')
        return redirect(url_for('ver_reservas'))
    
    return render_template('editar_reserva.html', reserva=reserva)

@app.route('/eliminar/<int:reserva_id>', methods=['POST'])
@login_required
def eliminar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    db.session.delete(reserva)
    db.session.commit()
    flash('Reserva eliminada exitosamente')
    return redirect(url_for('ver_reservas'))


@app.route('/generar_recibo/<int:reserva_id>')
@login_required
def generar_recibo(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)

    # Generar el PDF
    filename = f'recibo_reserva_{reserva.id}.pdf'
    filepath = os.path.join('instance', filename)
    
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 750, f"Recibo de Reserva")
    c.drawString(100, 730, f"Fecha Desde: {reserva.fecha_desde}")
    c.drawString(100, 710, f"Fecha Hasta: {reserva.fecha_hasta}")
    c.drawString(100, 690, f"Nombre del Cliente: {reserva.nombre_cliente}")
    c.drawString(100, 670, f"Teléfono: {reserva.telefono}")
    c.drawString(100, 650, f"Tipo de Evento: {reserva.tipo_evento}")
    c.drawString(100, 630, f"Total: ${reserva.total:.2f}")
    c.drawString(100, 610, f"Seña: ${reserva.sena:.2f}")
    c.drawString(100, 590, f"Método de Pago: {reserva.metodo_pago}")
    c.drawString(100, 570, f"Dirigido a: {reserva.dirigido_a}")
    c.drawString(100, 550, f"Resto: ${reserva.resto:.2f}")
    c.drawString(100, 530, f"Observaciones: {reserva.observaciones if reserva.observaciones else 'Ninguna'}")
    c.save()

    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crear las tablas si no existen
    app.run(debug=True)
