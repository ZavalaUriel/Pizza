from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from models import db, Pizza, Cliente, Pedido, DetallePedido
from forms import OrderForm, SalesQueryForm
from datetime import datetime
from sqlalchemy import extract, func
import locale

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mi_secreto_super_seguro' # Change in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pizzeria.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
csrf = CSRFProtect(app)

# Dictionary to map Spanish month names to numbers
meses = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

# Dictionary to map Spanish day names to numbers (0=lunes...6=domingo for python datetime.weekday())
dias = {
    'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2, 'jueves': 3,
    'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
}

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    form = OrderForm()
    
    if 'cart' not in session:
        session['cart'] = []
    
    # Pre-fill date with today
    if request.method == 'GET' and not form.fecha.data:
        form.fecha.data = datetime.now().strftime('%Y-%m-%d')
        
    # Calculate cart total
    header_total = sum(float(item['subtotal']) for item in session.get('cart', []))
    
    # Fetch today's sales for the side panel (based on mockup)
    today = datetime.now().date()
    ventas_hoy_query = Pedido.query.filter(Pedido.fecha == today).all()
    ventas_dia = [{'cliente_nombre': p.cliente.nombre, 'total': p.total} for p in ventas_hoy_query]
    total_dia = sum(p.total for p in ventas_hoy_query)
        
    if request.method == 'POST':
        if 'add_pizza' in request.form:
            # We don't validate the whole form, just the pizza parts
            tamano = form.tamano.data
            ingredientes = form.ingredientes.data
            cantidad = form.numero_pizzas.data
            
            if not tamano or not cantidad:
                flash('Por favor seleccione tamaño y número de pizzas.', 'error')
                return redirect(url_for('index'))
                
            # Calculate price
            precio_base = 0
            if tamano == 'Chica': precio_base = 40
            elif tamano == 'Mediana': precio_base = 80
            elif tamano == 'Grande': precio_base = 120
            
            precio_ingredientes = len(ingredientes) * 10
            subtotal = (precio_base + precio_ingredientes) * cantidad
            
            cart = session.get('cart', [])
            cart.append({
                'tamano': tamano,
                'ingredientes': ingredientes,
                'cantidad': cantidad,
                'subtotal': subtotal
            })
            session['cart'] = cart
            flash('Pizza agregada al pedido.', 'success')
            return redirect(url_for('index'))
            
        elif 'remove_pizza' in request.form:
            item_index = request.form.get('item_index')
            if item_index is not None:
                cart = session.get('cart', [])
                try:
                    idx = int(item_index)
                    if 0 <= idx < len(cart):
                        cart.pop(idx)
                        session['cart'] = cart
                        flash('Pizza removida del pedido.', 'success')
                except ValueError:
                    pass
            else:
                 flash('Seleccione una pizza para quitar con el radio button.', 'error')
            return redirect(url_for('index'))
            
        elif 'finish_order' in request.form:
            if not session.get('cart'):
                flash('El pedido está vacío. Agregue pizzas primero.', 'error')
                return redirect(url_for('index'))
                
            if form.validate():
                # Get client data
                cliente = Cliente.query.filter_by(telefono=form.telefono.data).first()
                if not cliente:
                    cliente = Cliente(
                        nombre=form.nombre.data,
                        direccion=form.direccion.data,
                        telefono=form.telefono.data
                    )
                    db.session.add(cliente)
                    db.session.flush() # Get ID
                
                try:
                    fecha_pedido = datetime.strptime(form.fecha.data, '%Y-%m-%d').date()
                except ValueError:
                    fecha_pedido = datetime.now().date()
                    
                total_pedido = sum(float(item['subtotal']) for item in session['cart'])
                
                pedido = Pedido(
                    id_cliente=cliente.id_cliente,
                    fecha=fecha_pedido,
                    total=total_pedido
                )
                db.session.add(pedido)
                db.session.flush()
                
                for item in session['cart']:
                    # Find or create pizza config in DB
                    ing_str = ', '.join(item['ingredientes']) if item['ingredientes'] else 'Sin ingredientes extra'
                    pizza = Pizza.query.filter_by(tamano=item['tamano'], ingredientes=ing_str).first()
                    if not pizza:
                        precio_unitario = float(item['subtotal']) / item['cantidad']
                        pizza = Pizza(tamano=item['tamano'], ingredientes=ing_str, precio=precio_unitario)
                        db.session.add(pizza)
                        db.session.flush()
                        
                    detalle = DetallePedido(
                        id_pedido=pedido.id_pedido,
                        id_pizza=pizza.id_pizza,
                        cantidad=item['cantidad'],
                        subtotal=item['subtotal']
                    )
                    db.session.add(detalle)
                
                db.session.commit()
                flash(f'¡Pedido registrado exitosamente! El total a pagar es de ${total_pedido:.2f}', 'success')
                session.pop('cart', None)
                return redirect(url_for('index'))
            else:
                flash('Por favor complete todos los datos del cliente (Nombre, Dirección, Teléfono, Fecha).', 'error')

    return render_template('index.html', form=form, cart=session.get('cart', []), header_total=header_total, ventas_dia=ventas_dia, total_dia=total_dia)

@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    form = SalesQueryForm()
    ventas_data = None
    total_acumulado = 0
    
    if request.method == 'POST' and form.validate():
        tipo = form.tipo_consulta.data
        valor = form.valor_consulta.data.strip().lower()
        
        query = Pedido.query.join(Cliente)
        
        if tipo == 'mes':
            mes_num = meses.get(valor)
            if mes_num:
                ventas_data = query.filter(extract('month', Pedido.fecha) == mes_num).all()
            else:
                flash('Mes no válido. Ingrese un mes como "enero" o "febrero".', 'error')
                return render_template('ventas.html', form=form, ventas_data=None)
                
        elif tipo == 'dia':
            # This requires filtering in python because sqlite date extraction for day of week is tricky
            # We fetch all and filter, or use strftime. For a simple app, fetching and filtering is fine
            all_pedidos = query.all()
            dia_num = dias.get(valor)
            if dia_num is not None:
                ventas_data = [p for p in all_pedidos if p.fecha.weekday() == dia_num]
            else:
                 flash('Día no válido. Ingrese un día como "lunes" o "martes".', 'error')
                 return render_template('ventas.html', form=form, ventas_data=None)

        if ventas_data:
            total_acumulado = sum(p.total for p in ventas_data)
        
    return render_template('ventas.html', form=form, ventas_data=ventas_data, total_acumulado=total_acumulado)

@app.route('/detalle/<int:pedido_id>')
def detalle(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    detalles = DetallePedido.query.filter_by(id_pedido=pedido.id_pedido).all()
    return render_template('detalle.html', pedido=pedido, detalles=detalles)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
