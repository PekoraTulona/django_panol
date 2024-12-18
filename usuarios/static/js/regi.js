
    document.addEventListener("DOMContentLoaded", function () {
        const userTypeField = document.querySelector('#id_user_type');
        const asignaturaContainer = document.querySelector('#asignatura-container');
        const asignaturaSelect = document.querySelector('#id_asignaturas'); // Solo este select

        // Función para mostrar/ocultar el campo de asignatura
        function toggleAsignaturaField() {
            if (userTypeField.value === 'profesor') {
                asignaturaContainer.style.display = 'block'; // Mostrar campo de asignaturas
                asignaturaSelect.disabled = false; // Habilitar el select
                loadAsignaturas(); // Cargar asignaturas vía AJAX
            } else {
                asignaturaContainer.style.display = 'none'; // Ocultar el campo de asignaturas
                asignaturaSelect.disabled = true; // Deshabilitar el select
                asignaturaSelect.innerHTML = '<option value="">-- Selecciona una asignatura --</option>'; // Limpiar las opciones
            }
        }

        // Función para cargar asignaturas vía AJAX
        function loadAsignaturas() {
            fetch("{% url 'get_asignaturas' %}")
                .then(response => response.json())
                .then(data => {
                    asignaturaSelect.innerHTML = '<option value="">-- Selecciona una asignatura --</option>';
                    data.asignaturas.forEach(asignatura => {
                        const option = document.createElement('option');
                        option.value = asignatura.id;
                        option.textContent = asignatura.nombre;
                        asignaturaSelect.appendChild(option);
                    });
                })
                .catch(error => console.error('Error al cargar las asignaturas:', error));
        }

        // Detectar cambios en el tipo de usuario
        userTypeField.addEventListener('change', toggleAsignaturaField);

        // Llamar a la función al cargar la página
        toggleAsignaturaField();
    });

