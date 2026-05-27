document.addEventListener('DOMContentLoaded', function () {

    const uploadBtn = document.getElementById("uploadBtn");
    const imageInput = document.getElementById("imageInput");
    const processType = document.getElementById("processType");
    const output = document.getElementById("output");

    uploadBtn.onclick = async () => {

        const file = imageInput.files[0];

        if (!file) {
            output.innerText = "Selecciona una imagen";
            return;
        }

        const formData = new FormData();

        // ARCHIVO
        formData.append("file", file);

        // TIPO DE PROCESAMIENTO
        formData.append(
            "process_type",
            processType.value
        );

        try {

            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            output.innerText =
                data.message || data.error;

        } catch (error) {

            output.innerText =
                "Error al subir imagen";

            console.error(error);
        }
    };
});