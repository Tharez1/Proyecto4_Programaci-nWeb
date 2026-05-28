document.addEventListener('DOMContentLoaded', function () {

    const uploadBtn = document.getElementById('uploadBtn');

    uploadBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        const btn = document.getElementById('uploadBtn');
        btn.disabled = true;
        setStatus('loading', '<span class="spinner"></span>Subiendo imagen...');

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('process_type', getProcessType());

        try {
            const res = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.error) {
                setStatus('error', '✕ ' + data.error);
                btn.disabled = false;
                return;
            }

            // CONECTAR SSE
            const filename = data.filename;
            setStatus('loading', '<span class="spinner"></span>En cola...');

            const es = new EventSource(`/status/stream/${filename}`);

            es.onmessage = (e) => {
                const status = e.data;

                if (status === 'pendiente') {
                    setStatus('loading', '<span class="spinner"></span>Pendiente...');
                } else if (status === 'processing') {
                    setStatus('loading', '<span class="spinner"></span>Procesando imagen...');
                } else if (status === 'completed') {
                    setStatus('success', '✓ Completado · ' + filename);
                    es.close();
                    btn.disabled = false;
                } else if (status === 'error') {
                    setStatus('error', '✕ Error al procesar · ' + filename);
                    es.close();
                    btn.disabled = false;
                }
            };

            es.onerror = () => {
                setStatus('error', '✕ Error de conexión SSE');
                es.close();
                btn.disabled = false;
            };

        } catch (err) {
            setStatus('error', '✕ Error de red: ' + err.message);
            btn.disabled = false;
        }
    });

});