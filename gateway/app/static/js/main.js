// Alerta temporário
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('main').insertBefore(alertDiv, document.querySelector('main').firstChild);
    
    setTimeout(() => alertDiv.remove(), 5000);
}

// Confirmação
function confirmAction(message) {
    return confirm(message);
}

// Data BR
function formatDate(dateString) {
    return new Date(dateString).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Copiar texto
function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => showAlert('Texto copiado!', 'success'))
        .catch(() => showAlert('Erro ao copiar', 'danger'));
}

// Bootstrap tooltips
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
        .forEach(el => new bootstrap.Tooltip(el));
});