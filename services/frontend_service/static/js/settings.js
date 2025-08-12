document.addEventListener("DOMContentLoaded", function () {
    function initZabbixModal() {
        const form = document.getElementById('zabbix-config-form');
        const testButton = document.getElementById('test-connection-button');
        const statusDiv = document.getElementById('connection-status');
        const togglePassword = document.getElementById('toggle-password');
        const passwordInput = document.getElementById('password');

        if (!form) return;

        // Toggle senha
        togglePassword.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            togglePassword.innerHTML = type === 'password' ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
        });

        // Salvar config
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            const formData = {
                url: document.getElementById('url').value,
                user: document.getElementById('user').value,
                password: document.getElementById('password').value
            };

            fetch('/zabbix/save-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert("Configuração salva com sucesso!", "success");
                    bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
                } else {
                    showAlert("Erro ao salvar: " + data.message, "danger");
                }
            })
            .catch(error => showAlert("Erro ao salvar configuração", "danger"));
        });

        // Testar conexão
        testButton.addEventListener("click", function () {
            const formData = {
                url: document.getElementById('url').value,
                user: document.getElementById('user').value,
                password: document.getElementById('password').value
            };

            if (!formData.url || !formData.user || !formData.password) {
                statusDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i><span>Preencha todos os campos!</span>';
                statusDiv.className = 'connection-status error';
                return;
            }

            statusDiv.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i><span>Testando...</span>';
            statusDiv.className = 'connection-status loading';

            fetch('/zabbix/test-connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusDiv.innerHTML = '<i class="fas fa-check-circle"></i><span>Conexão estabelecida!</span>';
                    statusDiv.className = 'connection-status success';
                    showAlert("Conexão testada com sucesso!", "success");
                } else {
                    statusDiv.innerHTML = '<i class="fas fa-times-circle"></i><span>Falha na conexão!</span>';
                    statusDiv.className = 'connection-status error';
                    showAlert("Falha: " + data.message, "danger");
                }
            })
            .catch(error => {
                statusDiv.innerHTML = '<i class="fas fa-times-circle"></i><span>Erro na conexão!</span>';
                statusDiv.className = 'connection-status error';
                showAlert("Erro ao testar conexão", "danger");
            });
        });
    }

    window.initZabbixModal = initZabbixModal;
});