from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from config import Conexion
from datos import *

app = Flask(__name__)
app.secret_key = 'uhggjghlñhu'

# Conexión a la base de datos
db = Conexion()
usuarios_collection = db['usuarios']
proyectos_collection = db['proyectos']
tareas_collection = db['tareas']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    if 'correo' in session:
        usuario = usuarios_collection.find_one({'correo': session['correo']})
        if usuario:
            return render_template('home.html', usuario=usuario)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        usuario = usuarios_collection.find_one({'correo': correo})
        if usuario and check_password_hash(usuario['password'], password):
            session['correo'] = usuario['correo']
            session['role'] = usuario['role']
            return redirect(url_for('home'))
        else:
            flash('Correo o contraseña incorrectos.')
    return render_template('inicio_sesion/login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        passwordsin = request.form['password']
        role = request.form['role']
        cargo = request.form['cargo']
        habilidades = request.form['habilidades'].split(',')
        
        if usuarios_collection.find_one({'correo': correo}):
            flash('El correo ya está registrado.')
        else:
            password = generate_password_hash(passwordsin)
            nuevo_usuario = Usuario(nombre, apellido, correo, password, role, cargo, habilidades)
            usuarios_collection.insert_one(nuevo_usuario.formato_doc())
            flash('Registro exitoso. Ahora puedes iniciar sesión.')
            return redirect(url_for('login'))
    return render_template('inicio_sesion/registro.html')

@app.route('/logout')
def logout():
    session.pop('correo', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if 'correo' in session and session.get('role') == 'administrador':
        return 'Bienvenido al panel de administración.'
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('home'))
    
@app.route('/admin_proyectos', methods=['GET', 'POST'])
def admin_proyectos():
    
    if 'correo' in session and session.get('role') == 'admin':
        #Para ver los proyectos existentes
        proyectos = proyectos_collection.find()
        
        #Para agregar un nuevo proyecto
        if request.method == 'POST':
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            fechainicio = request.form['fechainicio']
            fechafinal = request.form['fechafinal']
            estado = request.form['estado']
            nuevo_proyecto = Proyecto(nombre, descripcion, fechainicio, fechafinal, estado)
            proyectos_collection.insert_one(nuevo_proyecto.formato_doc())
            flash('Proyecto creado exitosamente.')
            return redirect(url_for('admin_proyectos'))
        return render_template('admin/admin_proyectos.html', proyectos=proyectos)
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/editar', methods=['GET', 'POST'])
def editar_proyecto(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        if request.method == 'POST':
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            fechainicio = request.form['fechainicio']
            fechafinal = request.form['fechafinal']
            estado = request.form['estado']
            proyectos_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechainicio': fechainicio,
                    'fechafinal': fechafinal,
                    'estado': estado
                }}
            )
            flash('Proyecto actualizado exitosamente.')
            return redirect(url_for('admin_proyectos'))
        return render_template('admin/editar_proyecto.html', proyecto=proyecto)
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/eliminar')
def eliminar_proyecto(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyectos_collection.delete_one({'_id': ObjectId(id)})
        flash('Proyecto eliminado exitosamente.')
        return redirect(url_for('admin_proyectos'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/asignar_miembros', methods=['GET', 'POST'])
def asignar_miembros(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        if proyecto:
            if request.method == 'POST':
                # Procesar la eliminación de miembros seleccionados
                eliminar_miembros_seleccionados = request.form.getlist('eliminar_miembro')
                if eliminar_miembros_seleccionados:
                    proyecto['miembros'] = [miembro for miembro in proyecto['miembros'] if str(miembro['_id']) not in eliminar_miembros_seleccionados]
                
                # Procesar la adición de miembros seleccionados
                agregar_miembros_seleccionados = request.form.getlist('agregar_miembro')
                for miembro_id in agregar_miembros_seleccionados:
                    miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)})
                    if miembro:
                        proyecto['miembros'].append(miembro)
                
                # Actualizar el proyecto en la base de datos
                proyectos_collection.update_one({'_id': ObjectId(id)}, {'$set': proyecto})
                
                flash('Acciones de asignación de miembros realizadas exitosamente.')
                return redirect(url_for('admin_proyectos'))
            
            usuarios = usuarios_collection.find()
            return render_template('admin/asignar_miembros.html', proyecto=proyecto, usuarios=usuarios)
        else:
            flash('No se encontró el proyecto.')
            return redirect(url_for('admin_proyectos'))
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))



@app.route('/seleccionar_proyecto', methods=['GET', 'POST'])
def seleccionar_proyecto():
    if 'correo' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            proyecto_id = request.form.get('proyecto_id')
            return redirect(url_for('agregar_tarea', id=proyecto_id))
        proyectos = proyectos_collection.find()
        return render_template('admin/seleccionar_proyecto.html', proyectos=proyectos)
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/agregar_tarea', methods=['GET', 'POST'])
def agregar_tarea(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        if proyecto:
            if request.method == 'POST':
                nombre = request.form['nombre']
                descripcion = request.form['descripcion']
                fechavencimiento = request.form['fechavencimiento']
                miembroasignado = request.form['miembroasignado']
                estado = request.form['estado']
                
                nueva_tarea = {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechavencimiento': fechavencimiento,
                    'miembroasignado': miembroasignado,
                    'estado': estado,
                    'comentarios': [],
                    'tiempo_dedicado': 0
                }
                
                tarea_id = tareas_collection.insert_one(nueva_tarea).inserted_id
                nueva_tarea['_id'] = tarea_id
                proyectos_collection.update_one(
                    {'_id': ObjectId(id)},
                    {'$push': {'tareas': nueva_tarea}}
                )
                flash('Tarea agregada exitosamente.')
                return redirect(url_for('ver_todas_las_tareas'))
            
            miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto['miembros']]
            miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))
            return render_template('admin/agregar_tarea.html', proyecto=proyecto, usuarios=miembros_asignados)
        
        flash('No se encontró el proyecto.')
        return redirect(url_for('admin_proyectos'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/tareas', methods=['GET'])
def ver_todas_las_tareas():
    if 'correo' in session and session.get('role') == 'admin':
        proyectos = proyectos_collection.find()
        tareas = []
        for proyecto in proyectos:
            for tarea in proyecto.get('tareas', []):
                miembro_id = tarea.get('miembroasignado')
                miembro_nombre = "Sin asignar"
                if miembro_id:
                    if isinstance(miembro_id, dict):  # Verificar si es un diccionario
                        miembro_id = miembro_id.get('_id')  # Obtener el ID del diccionario
                    if isinstance(miembro_id, (str, bytes)):  # Verificar si es una cadena o bytes
                        miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)}, {'nombre': 1, 'apellido': 1})
                        if miembro:
                            miembro_nombre = f"{miembro['nombre']} {miembro['apellido']}"
                tarea['miembro_nombre'] = miembro_nombre
                tarea['proyecto_nombre'] = proyecto['nombre']
                tarea['proyecto_id'] = proyecto['_id']
                tareas.append(tarea)
                     
        return render_template('admin/ver_tareas.html', tareas=tareas)
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/tarea/<id>/editar', methods=['GET', 'POST'])
def editar_tarea(id):
    if 'correo' in session and session.get('role') == 'admin':
        tarea = tareas_collection.find_one({'_id': ObjectId(id)})
        if tarea:
            proyecto = proyectos_collection.find_one({'tareas._id': ObjectId(id)})
            if request.method == 'POST':
                nombre = request.form['nombre']
                descripcion = request.form['descripcion']
                fechavencimiento = request.form['fechavencimiento']
                miembroasignado = request.form['miembroasignado']
                estado = request.form['estado']

                tareas_collection.update_one(
                    {'_id': ObjectId(id)},
                    {'$set': {
                        'nombre': nombre,
                        'descripcion': descripcion,
                        'fechavencimiento': fechavencimiento,
                        'miembroasignado': miembroasignado,
                        'estado': estado
                    }}
                )

                proyectos_collection.update_one(
                    {'_id': proyecto['_id'], 'tareas._id': ObjectId(id)},
                    {'$set': {
                        'tareas.$.nombre': nombre,
                        'tareas.$.descripcion': descripcion,
                        'tareas.$.fechavencimiento': fechavencimiento,
                        'tareas.$.miembroasignado': miembroasignado,
                        'tareas.$.estado': estado
                    }}
                )

                flash('Tarea actualizada exitosamente.')
                return redirect(url_for('ver_todas_las_tareas'))
            
            miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto['miembros']]
            miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))
            return render_template('admin/editar_tarea.html', tarea=tarea, proyecto=proyecto, miembros=miembros_asignados)
        
        flash('No se encontró la tarea.')
        return redirect(url_for('ver_todas_las_tareas'))
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/tarea/<id>/eliminar', methods=['POST'])
def eliminar_tarea(id):
    if 'correo' in session and session.get('role') == 'admin':
        tarea = tareas_collection.find_one({'_id': ObjectId(id)})
        if tarea:
            tareas_collection.delete_one({'_id': ObjectId(id)})
            proyectos_collection.update_one(
                {'tareas._id': ObjectId(id)},
                {'$pull': {'tareas': {'_id': ObjectId(id)}}}
            )
            flash('Tarea eliminada exitosamente.')
        else:
            flash('No se encontró la tarea.')
        return redirect(url_for('ver_todas_las_tareas'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/miembro')
def miembro():
    if 'correo' in session and session.get('role') == 'miembro':
        return 'Bienvenido a la página de miembro del equipo.'
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)