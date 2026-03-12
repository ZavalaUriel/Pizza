from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, SelectMultipleField, IntegerField, SubmitField, widgets
from wtforms.validators import DataRequired, NumberRange

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class OrderForm(FlaskForm):
    # Datos del cliente
    nombre = StringField('Nombre', validators=[DataRequired()])
    direccion = StringField('Dirección', validators=[DataRequired()])
    telefono = StringField('Teléfono', validators=[DataRequired()])
    fecha = StringField('Fecha', validators=[DataRequired()]) # Could use DateField, but mockup just says string or maybe datepicker
    
    # Datos de la pizza
    tamano = RadioField('Tamaño Pizza', choices=[
        ('Chica', 'Chica $40'),
        ('Mediana', 'Mediana $80'),
        ('Grande', 'Grande $120')
    ], validators=[DataRequired()])
    
    ingredientes = MultiCheckboxField('Ingredientes', choices=[
        ('Jamon', 'Jamón $10'),
        ('Pina', 'Piña $10'),
        ('Champinones', 'Champiñones $10')
    ])
    
    numero_pizzas = IntegerField('Num. de Pizzas.', validators=[DataRequired(), NumberRange(min=1)])
    
    agregar = SubmitField('Agregar')
    quitar = SubmitField('Quitar')
    terminar = SubmitField('Terminar')

class SalesQueryForm(FlaskForm):
    tipo_consulta = RadioField('Consultar por', choices=[
        ('dia', 'Día de la semana'),
        ('mes', 'Mes')
    ], validators=[DataRequired()])
    valor_consulta = StringField('Valor (ej. lunes, febrero)', validators=[DataRequired()])
    consultar = SubmitField('Consultar Ventas')
