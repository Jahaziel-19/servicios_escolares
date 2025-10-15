const switchImportar = document.getElementById('switch-importar');
const switchCrear = document.getElementById('switch-crear');
const formImportar = document.getElementById('form-importar');
const formCrear = document.getElementById('form-crear');

switchImportar.addEventListener('click', () => {
  switchImportar.classList.add('active');
  switchCrear.classList.remove('active');

  formCrear.classList.add('hidden');
  setTimeout(() => formImportar.classList.remove('hidden'), 300);
});

switchCrear.addEventListener('click', () => {
  switchCrear.classList.add('active');
  switchImportar.classList.remove('active');

  formImportar.classList.add('hidden');
  setTimeout(() => formCrear.classList.remove('hidden'), 300);
});

// Mantén aquí tu código JS para agregar campos dinámicos
let campos = [];

document.getElementById('nuevo_tipo').addEventListener('change', function() {
    let tipo = this.value;
    document.getElementById('opciones_nuevo_campo').style.display = 
        (tipo === 'radio' || tipo === 'checkbox') ? 'block' : 'none';
});

function agregarCampo() {
    const etiqueta = document.getElementById('nueva_etiqueta').value.trim();
    const tipo = document.getElementById('nuevo_tipo').value;
    const requerido = document.getElementById('nuevo_requerido').checked;
    const opciones = (tipo === 'radio' || tipo === 'checkbox') ?
        document.getElementById('nuevas_opciones').value.split(',').map(x => x.trim()).filter(x => x) : [];

    if (!etiqueta) {
        alert("La etiqueta no puede estar vacía");
        return;
    }

    campos.push({
        id: 'campo_' + Math.random().toString(36).substr(2, 9),
        label: etiqueta,
        type: tipo,
        required: requerido,
        options: opciones
    });

    document.getElementById('nueva_etiqueta').value = '';
    document.getElementById('nuevo_tipo').value = 'text';
    document.getElementById('nuevo_requerido').checked = false;
    document.getElementById('nuevas_opciones').value = '';
    document.getElementById('opciones_nuevo_campo').style.display = 'none';

    renderCampos();
}

function renderCampos() {
    const container = document.getElementById('campos-container');
    container.innerHTML = '';
    campos.forEach((campo, idx) => {
        let opciones = (campo.options || []).join(', ');
        let requerido = campo.required ? 'checked' : '';
        let tipo = campo.type || 'text';

        container.innerHTML += `
            <div class="bg-light rounded px-3 py-3 mb-3 d-flex align-items-center gap-3 flex-wrap">
                <input type="text" class="form-control flex-grow-1" value="${campo.label.replace(/"/g, '&quot;')}"
                    oninput="actualizarCampo(${idx}, 'label', this.value)" placeholder="Etiqueta del campo">
                
                <select class="form-select flex-grow-1" onchange="actualizarCampo(${idx}, 'type', this.value)">
                    <option value="text" ${tipo === 'text' ? 'selected' : ''}>Texto</option>
                    <option value="email" ${tipo === 'email' ? 'selected' : ''}>Email</option>
                    <option value="radio" ${tipo === 'radio' ? 'selected' : ''}>Radio</option>
                    <option value="checkbox" ${tipo === 'checkbox' ? 'selected' : ''}>Checkbox</option>
                </select>
                
                <div class="form-check d-flex align-items-center me-3">
                    <input class="form-check-input" type="checkbox" id="required_${idx}" ${requerido}
                        onchange="actualizarCampo(${idx}, 'required', this.checked)">
                    <label class="form-check-label ms-1" for="required_${idx}">Requerido</label>
                </div>
                
                ${(tipo === 'radio' || tipo === 'checkbox') ? `
                    <input type="text" class="form-control flex-grow-1" style="max-width:250px"
                        value="${opciones}" placeholder="Opciones (separadas por coma)" 
                        oninput="actualizarOpciones(${idx}, this.value)">
                ` : ''}
                
                <button type="button" class="btn btn-link text-danger p-0" title="Eliminar campo" onclick="eliminarCampo(${idx})">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="red" class="bi bi-trash" viewBox="0 0 16 16">
                      <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5.5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6zm3 .5a.5.5 0 0 1 .5-.5.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6z"/>
                      <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1-1V1h-11v1a1 1 0 0 1-1 1H1v1h14V3h-.5zm-1-1V1h-11v1h11z"/>
                    </svg>
                </button>
            </div>
        `;
    });
    document.getElementById('campos_json').value = JSON.stringify(campos);
}

function actualizarCampo(idx, key, value) {
    if (key === 'required') {
        campos[idx][key] = value;
    } else if (key === 'type') {
        campos[idx][key] = value;
        if (value !== 'radio' && value !== 'checkbox') {
            campos[idx]['options'] = [];
        }
    } else {
        campos[idx][key] = value;
    }
    renderCampos();
}

function actualizarOpciones(idx, value) {
    campos[idx]['options'] = value.split(',').map(x => x.trim()).filter(x => x);
    renderCampos();
}

function eliminarCampo(idx) {
    campos.splice(idx, 1);
    renderCampos();
}
